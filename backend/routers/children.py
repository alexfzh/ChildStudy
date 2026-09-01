"""孩子档案路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids, require_parent
from models import Child, GradeHistory, Timeline, User
from schemas import ChildCreate, ChildOut, ChildUpdate, GradeHistoryCreate, GradeHistoryOut, OkResponse
from utils.grade import get_grade_history

router = APIRouter(prefix="/api/children", tags=["孩子档案"])


@router.get("", response_model=List[ChildOut])
async def list_children(
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """家长：返回本家庭所有孩子；子账号：返回空列表（子账号不应看其他孩子，自己走 /me 看）。"""
    if user.role != "parent":
        return []
    result = await db.execute(
        select(Child).where(Child.family_id == user.family_id).order_by(Child.id)
    )
    return result.scalars().all()


@router.post("", response_model=ChildOut, status_code=201)
async def create_child(
    payload: ChildCreate,
    user: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """仅家长可建孩子档案。新孩子自动归到当前家长所在家庭。"""
    from datetime import date as _date
    # 后端硬限制：超过 MAX_CHILDREN 拒绝（前端 UI 同时 disabled，双保险）
    existing_q = await db.execute(select(Child.id).where(Child.family_id == user.family_id))
    current_count = len(existing_q.scalars().all())
    if current_count >= settings.max_children:
        raise HTTPException(
            400,
            f"已达系统上限 {settings.max_children} 个孩子。如需更多请修改 backend/.env 中的 MAX_CHILDREN 并重启服务。",
        )
    data = payload.model_dump()
    data["family_id"] = user.family_id  # 强制绑定到当前家庭
    child = Child(**data)
    db.add(child)
    await db.flush()
    db.add(GradeHistory(
        child_id=child.id,
        grade=child.grade,
        effective_from=_date.today(),
        note="初始年级",
    ))
    await db.commit()
    await db.refresh(child)
    return child


@router.get("/{child_id}", response_model=ChildOut)
async def get_child(
    child_id: int,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    return child


@router.put("/{child_id}", response_model=ChildOut)
async def update_child(
    child_id: int,
    payload: ChildUpdate,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as _date
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    update_data = payload.model_dump(exclude_unset=True)
    old_grade = child.grade
    for k, v in update_data.items():
        setattr(child, k, v)
    # 如果 grade 被改了且与现有 GradeHistory 都不一致，则写入 GradeHistory
    if "grade" in update_data and update_data["grade"] != old_grade:
        # 查现有最新历史
        q = await db.execute(
            select(GradeHistory)
            .where(GradeHistory.child_id == child_id)
            .order_by(GradeHistory.effective_from.desc())
            .limit(1)
        )
        latest = q.scalar_one_or_none()
        if not latest or latest.grade != update_data["grade"]:
            db.add(GradeHistory(
                child_id=child_id,
                grade=update_data["grade"],
                effective_from=_date.today(),
                note="编辑档案时同步",
            ))
            db.add(Timeline(
                child_id=child_id,
                event_type="grade_change",
                title=f"年级更新为{update_data['grade']}",
                description=f"由「{old_grade}」变更为「{update_data['grade']}」",
                event_date=_date.today(),
                tags=["grade", "milestone"],
            ))
    await db.commit()
    await db.refresh(child)
    return child


@router.delete("/{child_id}", response_model=OkResponse)
async def delete_child(
    child_id: int,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    await db.delete(child)
    await db.commit()
    return OkResponse(message=f"已删除孩子档案：{child.name}")


# ============ 年级历史 ============
@router.get("/{child_id}/grade-history", response_model=List[GradeHistoryOut])
async def list_grade_history(
    child_id: int,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    """获取某孩子的完整年级历史（按时间倒序）"""
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    return await get_grade_history(db, child_id)


@router.post("/{child_id}/grade-history", response_model=GradeHistoryOut, status_code=201)
async def create_grade_history(
    child_id: int,
    payload: GradeHistoryCreate,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    """升年级：写入 GradeHistory + 更新 Child.grade（当前显示） + 同步写一条 Timeline 事件"""
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    old_grade = child.grade
    entry = GradeHistory(
        child_id=child_id,
        grade=payload.grade,
        effective_from=payload.effective_from,
        note=payload.note,
    )
    db.add(entry)

    # 更新 Child.grade（保持为最新 grade，供 ChildSelector 显示）
    child.grade = payload.grade

    # 同步进 Timeline（仅当 grade 真的变了）
    if old_grade != payload.grade:
        timeline_event = Timeline(
            child_id=child_id,
            event_type="grade_change",
            title=f"升入{payload.grade}",
            description=payload.note or f"年级由「{old_grade}」变更为「{payload.grade}」",
            event_date=payload.effective_from,
            tags=["grade", "milestone"],
        )
        db.add(timeline_event)

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{child_id}/grade-history/{history_id}", response_model=OkResponse)
async def delete_grade_history(
    child_id: int,
    history_id: int,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    """删除一条年级历史（用户修正误操作）。

    如果删的是最后一条历史，回滚 child.grade 到倒数第二条；否则保持 child.grade 不变。
    """
    assert_child_access(accessible, child_id)
    entry = await db.get(GradeHistory, history_id)
    if not entry or entry.child_id != child_id:
        raise HTTPException(404, "年级历史不存在")

    await db.delete(entry)
    await db.flush()  # 让 DELETE 生效，下面查时已不含该条

    # 查剩余历史中最新的那条（按 effective_from 倒序）
    q = await db.execute(
        select(GradeHistory)
        .where(GradeHistory.child_id == child_id)
        .order_by(GradeHistory.effective_from.desc())
        .limit(1)
    )
    latest_remaining = q.scalar_one_or_none()
    if latest_remaining:
        # 回滚 child.grade 到最新剩余历史的 grade
        child = await db.get(Child, child_id)
        if child:
            child.grade = latest_remaining.grade

    await db.commit()
    return OkResponse(message="年级历史已删除")
