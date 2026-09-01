"""KPStudyProgress 路由：知识点级别掌握度追踪 + 自动更新 hooks

  调用链：
    Exercise.submit → update_progress_on_exercise() (question_banks.py)
      → update_kp_progress_on_exercise() (本文件)
        → 更新每个 KP 的 attempts/correct/accuracy/mastery_level
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids
from models import (
    KnowledgePoint,
    KPStudyProgress,
    Question,
    QuestionKnowledgePoint,
    QuestionUnit,
    TextbookUnit,
    TextbookVersion,
)
from schemas import (
    ChildKPProgressSummary,
    KPProgressSummary,
    KPStudyProgressOut,
)

router = APIRouter(prefix="/api/kp-progress", tags=["KP学习进度"])


# ============ Mastery 判定 ============

MASTERY_THRESHOLDS = {
    "new":      (0, 59.9, 0),      # accuracy < 60%
    "learning": (60, 79.9, 3),     # accuracy 60-80%, ≥3 attempts
    "strong":   (80, 89.9, 5),     # accuracy 80-90%, ≥5 attempts
    "mastered": (90, 100.0, 8),    # accuracy ≥90%, ≥8 attempts
}


def calc_mastery_level(accuracy: float, attempts: int) -> str:
    """根据 accuracy + attempts 自动判定 mastery_level"""
    for level, (lo, hi, min_attempts) in MASTERY_THRESHOLDS.items():
        if lo <= accuracy <= hi and attempts >= min_attempts:
            return level
    # fallback: 只按 accuracy
    if accuracy >= 90:
        return "mastered" if attempts >= 8 else "strong"
    elif accuracy >= 80:
        return "strong" if attempts >= 5 else "learning"
    elif accuracy >= 60:
        return "learning"
    return "new"


# ============ 工具函数 ============

async def get_or_create_kp_progress(db: AsyncSession, child_id: int, kp_id: int, unit_id: Optional[int] = None) -> KPStudyProgress:
    kp = (await db.execute(
        select(KPStudyProgress).where(
            and_(KPStudyProgress.child_id == child_id,
                 KPStudyProgress.knowledge_point_id == kp_id,
                 KPStudyProgress.unit_id == unit_id if unit_id is not None
                 else KPStudyProgress.unit_id.is_(None))
        )
    )).scalars().first()
    if kp is None:
        kp = KPStudyProgress(child_id=child_id, knowledge_point_id=kp_id, unit_id=unit_id)
        db.add(kp)
        await db.flush()
    return kp


async def update_kp_progress_on_exercise(db: AsyncSession, child_id: int, exercise) -> dict:
    """
    答题会话提交后调用（由 question_banks.py 的 update_progress_on_exercise 调用）：
    1) 从 exercise.questions 的 answers 反查每道题关联的 KP
    2) 更新 KPStudyProgress 的 attempts/correct/accuracy
    3) 自动更新 mastery_level
    返回 {updated_kps: [...]}
    """
    updated_kps = []

    answers_by_qid = {a.get("question_id"): a for a in (exercise.answers or [])}
    if not answers_by_qid:
        return {"updated_kps": []}

    # 找出本场练习中涉及的 question_ids
    question_ids = list(answers_by_qid.keys())
    if not question_ids:
        return {"updated_kps": []}

    # 反查这些题目关联的 KP（QuestionKnowledgePoint）
    qkp_stmt = (
        select(QuestionKnowledgePoint, Question)
        .join(Question, Question.id == QuestionKnowledgePoint.question_id)
        .where(QuestionKnowledgePoint.question_id.in_(question_ids))
    )
    qkp_rows = (await db.execute(qkp_stmt)).all()
    if not qkp_rows:
        return {"updated_kps": []}

    # 按 KP 聚合：统计每 KP 的本场 attempts/correct
    kp_stats: dict[int, dict] = {}  # kp_id -> {attempts, correct, unit_id}
    for qkp, q in qkp_rows:
        kp_id = qkp.knowledge_point_id
        if kp_id not in kp_stats:
            kp_stats[kp_id] = {"attempts": 0, "correct": 0, "unit_id": None}
        kp_stats[kp_id]["attempts"] += 1
        ans = answers_by_qid.get(q.id, {})
        if ans.get("is_correct"):
            kp_stats[kp_id]["correct"] += 1
        # 取第一个非 None unit_id（多 Unit 题取第一个）
        if kp_stats[kp_id]["unit_id"] is None:
            # 反查该题关联的 Unit（用于 context）
            qu_row = (await db.execute(
                select(QuestionUnit.unit_id).where(QuestionUnit.question_id == q.id).limit(1)
            )).first()
            if qu_row:
                kp_stats[kp_id]["unit_id"] = qu_row[0]

    for kp_id, stats in kp_stats.items():
        kp = await get_or_create_kp_progress(db, child_id, kp_id, stats["unit_id"])
        kp.total_attempts += stats["attempts"]
        kp.total_correct += stats["correct"]
        kp.accuracy = round(kp.total_correct / max(kp.total_attempts, 1) * 100, 2)
        kp.mastery_level = calc_mastery_level(kp.accuracy, kp.total_attempts)
        kp.last_study_at = datetime.now(timezone.utc)
        db.add(kp)
        updated_kps.append({
            "knowledge_point_id": kp_id,
            "unit_id": stats["unit_id"],
            "attempts": kp.total_attempts,
            "correct": kp.total_correct,
            "accuracy": kp.accuracy,
            "mastery_level": kp.mastery_level,
        })

    return {"updated_kps": updated_kps}


# ============ API 路由 ============

@router.get("/child/{child_id}/unit/{unit_id}", response_model=KPProgressSummary)
async def get_kp_progress_for_unit(
    child_id: int,
    unit_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """某 Unit 内所有 KP 的掌握度汇总"""
    assert_child_access(accessible, child_id)
    unit = await db.get(TextbookUnit, unit_id)
    if not unit:
        raise HTTPException(404, "Unit 不存在")

    # 获取该 Unit 关联的所有 KP（通过 KnowledgePointUnit）
    from models import KnowledgePointUnit
    kp_ids = (await db.execute(
        select(KnowledgePointUnit.knowledge_point_id)
        .where(KnowledgePointUnit.unit_id == unit_id)
    )).scalars().all()

    if not kp_ids:
        return KPProgressSummary(
            unit_id=unit_id,
            unit_code=unit.code,
            unit_title_zh=unit.title_zh,
            total_kps=0, mastered_kps=0, learning_kps=0, strong_kps=0, new_kps=0,
            mastery_pct=0.0, kp_details=[],
        )

    # 拉取孩子对这些 KP 的进度
    progress_rows = (await db.execute(
        select(KPStudyProgress).where(
            and_(
                KPStudyProgress.child_id == child_id,
                KPStudyProgress.knowledge_point_id.in_(kp_ids),
                KPStudyProgress.unit_id == unit_id,
            )
        )
    )).scalars().unique().all()

    progress_map = {p.knowledge_point_id: p for p in progress_rows}

    details = []
    counts = {"mastered": 0, "strong": 0, "learning": 0, "new": 0}
    for kp_id in kp_ids:
        p = progress_map.get(kp_id)
        level = p.mastery_level if p else "new"
        counts[level] = counts.get(level, 0) + 1
        details.append(KPStudyProgressOut(
            id=p.id if p else 0,
            child_id=child_id,
            knowledge_point_id=kp_id,
            unit_id=unit_id,
            total_attempts=p.total_attempts if p else 0,
            total_correct=p.total_correct if p else 0,
            accuracy=p.accuracy if p else 0.0,
            mastery_level=level,
            last_study_at=p.last_study_at if p else None,
        ))

    total = len(kp_ids)
    # mastery = mastered + strong 加权（mastered=100%, strong=70%）
    mastery_score = (counts.get("mastered", 0) * 100 + counts.get("strong", 0) * 70) / max(total, 1)
    mastery_pct = round(mastery_score, 2)

    return KPProgressSummary(
        unit_id=unit_id,
        unit_code=unit.code,
        unit_title_zh=unit.title_zh,
        total_kps=total,
        mastered_kps=counts.get("mastered", 0),
        strong_kps=counts.get("strong", 0),
        learning_kps=counts.get("learning", 0),
        new_kps=counts.get("new", 0),
        mastery_pct=mastery_pct,
        kp_details=details,
    )


@router.get("/child/{child_id}/version/{version_id}", response_model=ChildKPProgressSummary)
async def get_kp_progress_for_version(
    child_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """某教材版本下所有 Unit × KP 掌握度矩阵"""
    assert_child_access(accessible, child_id)
    version = await db.get(TextbookVersion, version_id)
    if not version:
        raise HTTPException(404, "教材版本不存在")

    units = (await db.execute(
        select(TextbookUnit).where(TextbookUnit.version_id == version_id).order_by(TextbookUnit.unit_number)
    )).scalars().unique().all()

    if not units:
        return ChildKPProgressSummary(child_id=child_id, version_id=version_id,
                                       total_kps=0, overall_mastery_pct=0.0, kp_summary_by_unit=[])

    # 各 Unit 汇总（复用上面 endpoint 的逻辑，并行拉）
    summaries = []
    for u in units:
        # 调 get_kp_progress_for_unit 逻辑（内联避免嵌套调用）
        from models import KnowledgePointUnit
        kp_ids = (await db.execute(
            select(KnowledgePointUnit.knowledge_point_id).where(KnowledgePointUnit.unit_id == u.id)
        )).scalars().all()

        progress_rows = (await db.execute(
            select(KPStudyProgress).where(
                and_(
                    KPStudyProgress.child_id == child_id,
                    KPStudyProgress.knowledge_point_id.in_(kp_ids) if kp_ids else False,
                    KPStudyProgress.unit_id == u.id,
                )
            )
        )).scalars().unique().all() if kp_ids else []
        progress_map = {p.knowledge_point_id: p for p in progress_rows}

        details = []
        counts = {"mastered": 0, "strong": 0, "learning": 0, "new": 0}
        for kp_id in kp_ids:
            p = progress_map.get(kp_id)
            level = p.mastery_level if p else "new"
            counts[level] = counts.get(level, 0) + 1
            details.append(KPStudyProgressOut(
                id=p.id if p else 0,
                child_id=child_id,
                knowledge_point_id=kp_id,
                unit_id=u.id,
                total_attempts=p.total_attempts if p else 0,
                total_correct=p.total_correct if p else 0,
                accuracy=p.accuracy if p else 0.0,
                mastery_level=level,
                last_study_at=p.last_study_at if p else None,
            ))

        total = len(kp_ids)
        mastery_score = (counts.get("mastered", 0) * 100 + counts.get("strong", 0) * 70) / max(total, 1)
        summaries.append(KPProgressSummary(
            unit_id=u.id,
            unit_code=u.code,
            unit_title_zh=u.title_zh,
            total_kps=total,
            mastered_kps=counts.get("mastered", 0),
            strong_kps=counts.get("strong", 0),
            learning_kps=counts.get("learning", 0),
            new_kps=counts.get("new", 0),
            mastery_pct=round(mastery_score, 2),
            kp_details=details,
        ))

    total_kps_all = sum(s.total_kps for s in summaries)
    overall = sum((s.mastery_pct * s.total_kps) for s in summaries) / max(total_kps_all, 1)

    return ChildKPProgressSummary(
        child_id=child_id,
        version_id=version_id,
        total_kps=total_kps_all,
        overall_mastery_pct=round(overall, 2),
        kp_summary_by_unit=summaries,
    )


@router.get("/child/{child_id}/kp/{kp_id}", response_model=KPStudyProgressOut)
async def get_kp_progress_detail(
    child_id: int,
    kp_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """单个 KP 的详细进度（不限定 Unit）"""
    assert_child_access(accessible, child_id)
    kp = await db.get(KnowledgePoint, kp_id)
    if not kp:
        raise HTTPException(404, "知识点不存在")

    # 获取最近一次学习的 unit_id
    latest = (await db.execute(
        select(KPStudyProgress)
        .where(and_(KPStudyProgress.child_id == child_id, KPStudyProgress.knowledge_point_id == kp_id))
        .order_by(KPStudyProgress.last_study_at.desc())
        .limit(1)
    )).scalars().first()

    if latest is None:
        return KPStudyProgressOut(
            id=0, child_id=child_id, knowledge_point_id=kp_id, unit_id=None,
            total_attempts=0, total_correct=0, accuracy=0.0, mastery_level="new", last_study_at=None,
        )
    return latest
