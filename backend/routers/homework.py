"""日常作业记录路由"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, child_id_filter, get_accessible_child_ids
from models import Child, Homework, WrongQuestion
from schemas import HomeworkCreate, HomeworkOut, HomeworkUpdate, OkResponse
from utils.grade import get_grade_at_date

router = APIRouter(prefix="/api/homeworks", tags=["日常作业"])


@router.get("", response_model=List[HomeworkOut])
async def list_homeworks(
    child_id: Optional[int] = None,
    subject: Optional[str] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    if child_id is not None:
        assert_child_access(accessible, child_id)
    stmt = select(Homework).order_by(Homework.homework_date.desc(), Homework.id.desc())
    stmt = stmt.where(child_id_filter(accessible, child_id, Homework.child_id))
    if subject:
        stmt = stmt.where(Homework.subject == subject)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=HomeworkOut, status_code=201)
async def create_homework(
    payload: HomeworkCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, payload.child_id)
    child = await db.get(Child, payload.child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    data = payload.model_dump()
    # 自动计算正确率
    if data.get("accuracy") is None and data.get("total_questions") and data.get("correct_questions") is not None:
        if data["total_questions"] > 0:
            data["accuracy"] = round(data["correct_questions"] / data["total_questions"] * 100, 2)
    # 自动补 grade_snapshot
    if not data.get("grade_snapshot"):
        data["grade_snapshot"] = await get_grade_at_date(db, payload.child_id, payload.homework_date)
    hw = Homework(**data)
    db.add(hw)
    await db.commit()
    await db.refresh(hw)
    return hw


@router.put("/{hw_id}", response_model=HomeworkOut)
async def update_homework(
    hw_id: int,
    payload: HomeworkUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    hw = await db.get(Homework, hw_id)
    if not hw:
        raise HTTPException(404, "作业记录不存在")
    assert_child_access(accessible, hw.child_id)
    update_data = payload.model_dump(exclude_unset=True)
    # 如果改了 homework_date 但没传新 snapshot，重查
    if "homework_date" in update_data and "grade_snapshot" not in update_data:
        update_data["grade_snapshot"] = await get_grade_at_date(db, hw.child_id, update_data["homework_date"])
    for k, v in update_data.items():
        setattr(hw, k, v)
    # 重新计算正确率
    if hw.total_questions and hw.correct_questions is not None and hw.total_questions > 0:
        hw.accuracy = round(hw.correct_questions / hw.total_questions * 100, 2)
    await db.commit()
    await db.refresh(hw)
    return hw


@router.delete("/{hw_id}", response_model=OkResponse)
async def delete_homework(
    hw_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    hw = await db.get(Homework, hw_id)
    if not hw:
        raise HTTPException(404, "作业记录不存在")
    assert_child_access(accessible, hw.child_id)
    # DB-4：作业来源的错题（source_type="homework" 且 source_id 指向本作业）。
    # 该关联无 FK、无级联，删作业后会留下"出处已删除"的幽灵错题，一并清理。
    # 错题的复习记录由 DB 层外键 ON DELETE CASCADE 连带删除。
    await db.execute(
        delete(WrongQuestion).where(
            WrongQuestion.source_type == "homework",
            WrongQuestion.source_id == hw_id,
        )
    )
    await db.delete(hw)
    await db.commit()
    return OkResponse(message="已删除作业记录")
