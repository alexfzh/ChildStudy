"""学习进度追踪 + 自动更新 Unit 掌握度 + 触发 Rewards

  - update_progress_on_exercise(): 由 /api/question-banks/exercises/{id}/submit 调用
  - get_progress_for_child(): 一次性返回孩子某教材版本下所有 Unit 进度
  - get_progress_for_unit(): 单 Unit 进度
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids
from models import (
    Child,
    PointsLog,
    QuestionUnit,
    StudyProgress,
    TextbookUnit,
    TextbookVersion,
    UnitAchievementLog,
)
from schemas import (
    ChildProgressSummary,
    StudyProgressOut,
)

router = APIRouter(prefix="/api/study-progress", tags=["学习进度"])


# ============ 工具函数 ============

def calc_completion(attempts: int, total_questions_in_unit: int) -> float:
    """按"在该 Unit 题库里做过的题数 / 该 Unit 题库总题数"算完成度（0-100）"""
    if total_questions_in_unit <= 0:
        return 0.0
    return round(min(attempts, total_questions_in_unit) / total_questions_in_unit * 100, 2)


async def get_or_create_progress(db: AsyncSession, child_id: int, unit_id: int) -> StudyProgress:
    sp = (await db.execute(
        select(StudyProgress).where(
            and_(StudyProgress.child_id == child_id, StudyProgress.unit_id == unit_id)
        )
    )).scalars().first()
    if sp is None:
        sp = StudyProgress(child_id=child_id, unit_id=unit_id)
        db.add(sp)
        await db.flush()
    return sp


async def count_unit_questions(db: AsyncSession, unit_id: int) -> int:
    stmt = select(func.count(QuestionUnit.question_id)).where(QuestionUnit.unit_id == unit_id)
    result = await db.execute(stmt)
    return int(result.scalar_one() or 0)


# ============ 触发：答题完成时自动更新进度（核心 hooks） ============

async def update_progress_on_exercise(db: AsyncSession, child_id: int, exercise) -> dict:
    """
    答题会话提交后调用（外部 in routers/question_banks.py）：

    1) 找出 exercise.questions 中涉及的 Unit（按 question_id 反查 QuestionUnit）
    2) 更新 StudyProgress 累计 attempts/correct
    3) 检查 Unit mastery：accuracy>=85% && completion_pct>=80 触发 mastered（仅一次）
    4) 解锁 Unit 成就（去重）

    返回 {updated_units: [...], new_achievements: [...]}
    """
    updated_units = []
    new_achievements = []

    question_ids = [q.get("id") for q in (exercise.questions or []) if q.get("id")]
    if not question_ids:
        return {"updated_units": [], "new_achievements": []}

    qu_stmt = select(QuestionUnit.unit_id).where(
        QuestionUnit.question_id.in_(question_ids)
    ).distinct()
    unit_ids = [row[0] for row in (await db.execute(qu_stmt)).all()]
    if not unit_ids:
        return {"updated_units": [], "new_achievements": []}

    # 批量预取（修复 N+1）：一次取全部相关 Unit 的题目映射 → unit_id -> {question_id}
    qq_rows = (await db.execute(
        select(QuestionUnit.unit_id, QuestionUnit.question_id)
        .where(QuestionUnit.unit_id.in_(unit_ids))
    )).all()
    qids_by_unit: dict[int, set[int]] = {}
    for uid, qid in qq_rows:
        qids_by_unit.setdefault(uid, set()).add(qid)

    for unit_id in unit_ids:
        # 该 Unit 下所有关联题目
        unit_qids = qids_by_unit.get(unit_id, set())

        # 找出本场练习中归属本 Unit 的题目
        unit_qid_in_ex = unit_qids & set(question_ids)
        if not unit_qid_in_ex:
            continue

        sp = await get_or_create_progress(db, child_id, unit_id)

        unit_question_count = len(unit_qid_in_ex)
        # 通过 answers 算该 Unit 本场正确数
        answers_by_qid = {a.get("question_id"): a for a in (exercise.answers or [])}
        unit_correct = sum(
            1
            for qid in unit_qid_in_ex
            if answers_by_qid.get(qid, {}).get("is_correct")
        )
        if unit_question_count > 0:
            sp.total_attempts += unit_question_count
            sp.total_correct += unit_correct
            sp.accuracy = round(sp.total_correct / max(sp.total_attempts, 1) * 100, 2)
            sp.last_study_at = datetime.now(timezone.utc)

        total_in_unit = await count_unit_questions(db, unit_id)
        sp.completion_pct = calc_completion(sp.total_attempts, total_in_unit)

        previously_mastered = (sp.status == "mastered")
        if (not previously_mastered
                and sp.accuracy >= 85.0
                and sp.completion_pct >= 80.0
                and sp.total_attempts >= 10):
            sp.status = "mastered"
            sp.mastered_at = datetime.now(timezone.utc)
            if await award_unit_achievement(db, child_id, unit_id, "UNIT_MASTERED", points=50):
                new_achievements.append({"code": "UNIT_MASTERED", "unit_id": unit_id, "points": 50})

        if sp.status == "not_started" and sp.total_attempts > 0:
            sp.status = "in_progress"

        db.add(sp)
        updated_units.append({
            "unit_id": unit_id,
            "attempts": sp.total_attempts,
            "correct": sp.total_correct,
            "accuracy": sp.accuracy,
            "completion_pct": sp.completion_pct,
            "status": sp.status,
        })

    # 连胜 3 个 Unit mastered → STREAK_3 成就
    if new_achievements:
        streak_unit_id = await check_streak_three(db, child_id)
        if streak_unit_id:
            if await award_unit_achievement(db, child_id, streak_unit_id, "STREAK_3", points=100):
                new_achievements.append({"code": "STREAK_3", "unit_id": streak_unit_id, "points": 100})

    # 积分里程碑：本次有 Unit 成就发分后，检查总积分是否首次达到阈值（一次型，内部去重）。
    # 判断 new_achievements 非空即可——练习路径的积分只来自 Unit 成就，
    # 无新成就即无积分变化，不必查询。用非空判断而非 points>0，
    # 可避免将来接入 0 分成就时静默漏检。
    if new_achievements:
        from .rewards import check_points_milestones  # 延迟导入避免循环依赖
        await db.flush()  # autoflush=False，先落库本次 PointsLog 再求和
        await check_points_milestones(db, child_id)

    return {"updated_units": updated_units, "new_achievements": new_achievements}


async def award_unit_achievement(db: AsyncSession, child_id: int, unit_id: int, code: str, points: int) -> bool:
    """授予 Unit 成就（去重），并写入积分流水。返回是否本次新增。"""
    existing = (await db.execute(
        select(UnitAchievementLog).where(
            and_(
                UnitAchievementLog.child_id == child_id,
                UnitAchievementLog.unit_id == unit_id,
                UnitAchievementLog.achievement_code == code,
            )
        )
    )).scalars().first()
    if existing:
        return False
    db.add(UnitAchievementLog(
        child_id=child_id,
        unit_id=unit_id,
        achievement_code=code,
        points_awarded=points,
    ))
    db.add(PointsLog(
        child_id=child_id,
        source="study_progress",
        points=points,
        description=f"教材学习成就：{code}",
        source_id=unit_id,
    ))
    return True


async def check_streak_three(db: AsyncSession, child_id: int) -> Optional[int]:
    """最近按 unit_number 顺序连续 3 个 Unit 都 mastered → 返回最后一个 Unit id 否则 None"""
    stmt = (
        select(StudyProgress.unit_id, TextbookUnit.unit_number)
        .join(TextbookUnit, TextbookUnit.id == StudyProgress.unit_id)
        .where(StudyProgress.child_id == child_id, StudyProgress.status == "mastered")
        .order_by(TextbookUnit.unit_number)
    )
    rows = (await db.execute(stmt)).all()
    if len(rows) < 3:
        return None
    nums = [r[1] for r in rows]
    for i in range(len(nums) - 2):
        if nums[i + 1] == nums[i] + 1 and nums[i + 2] == nums[i] + 2:
            return rows[i + 2][0]
    return None


# ============ API 路由 ============

@router.get("/child/{child_id}/version/{version_id}", response_model=ChildProgressSummary)
async def get_progress_for_child(
    child_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子不存在")
    version = await db.get(TextbookVersion, version_id)
    if not version:
        raise HTTPException(404, "教材版本不存在")

    units = (await db.execute(
        select(TextbookUnit).where(TextbookUnit.version_id == version_id).order_by(TextbookUnit.unit_number)
    )).scalars().unique().all()
    if not units:
        raise HTTPException(404, "该教材版本下无单元")

    progress_rows = (await db.execute(
        select(StudyProgress).where(
            and_(StudyProgress.child_id == child_id, StudyProgress.unit_id.in_([u.id for u in units]))
        )
    )).scalars().unique().all()
    progress_map = {p.unit_id: p for p in progress_rows}

    mastered = sum(1 for u in units if progress_map.get(u.id) and progress_map[u.id].status == "mastered")
    mastery_pct = round(mastered / len(units) * 100, 2) if units else 0.0

    mastered_units_sorted = sorted([
        u.unit_number for u in units if progress_map.get(u.id) and progress_map[u.id].status == "mastered"
    ])
    streak = 0
    cur = 0
    for n in mastered_units_sorted:
        if n == cur + 1:
            cur = n
            streak += 1
        else:
            cur = n
            streak = 1

    ua_stmt = (
        select(func.coalesce(func.sum(UnitAchievementLog.points_awarded), 0))
        .where(UnitAchievementLog.child_id == child_id)
        .where(UnitAchievementLog.unit_id.in_([u.id for u in units]))
    )
    total_points = int((await db.execute(ua_stmt)).scalar_one() or 0)
    total_ach = (await db.execute(
        select(func.count(UnitAchievementLog.id))
        .where(UnitAchievementLog.child_id == child_id)
        .where(UnitAchievementLog.unit_id.in_([u.id for u in units]))
    )).scalar_one() or 0

    return ChildProgressSummary(
        child_id=child_id,
        version_id=version_id,
        units=list(units),
        progress_map={pid: StudyProgressOut.model_validate(p).model_dump() for pid, p in progress_map.items()},
        mastery_pct=mastery_pct,
        streak_units=streak,
        total_points=total_points,
        total_achievements=int(total_ach),
    )


@router.get("/child/{child_id}/unit/{unit_id}", response_model=StudyProgressOut)
async def get_progress_for_unit(
    child_id: int,
    unit_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    sp = await get_or_create_progress(db, child_id, unit_id)
    await db.commit()
    await db.refresh(sp)
    return sp
