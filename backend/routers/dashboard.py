"""家长看板 / Dashboard 数据路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids, require_parent
from models import Child, Exam, Homework, User
from schemas import CompareData, DashboardData, ExamOut, SubjectStat
from utils.analysis import (
    build_action_suggestions,
    build_radar_data,
    build_subject_stats,
    build_trend_data,
    detect_weak_subjects,
)

router = APIRouter(prefix="/api/dashboard", tags=["家长看板"])


@router.get("/{child_id}", response_model=DashboardData)
async def get_dashboard(
    child_id: int,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    exams_q = await db.execute(
        select(Exam).where(Exam.child_id == child_id).order_by(Exam.exam_date.desc())
    )
    exams = list(exams_q.scalars().all())

    homeworks_q = await db.execute(
        select(Homework).where(Homework.child_id == child_id)
    )
    homeworks = list(homeworks_q.scalars().all())

    stats = build_subject_stats(exams)
    weak = detect_weak_subjects(stats)
    recent = sorted(exams, key=lambda x: x.exam_date, reverse=True)[:10]

    return DashboardData(
        child_id=child.id,
        child_name=child.name,
        total_exams=len(exams),
        total_homeworks=len(homeworks),
        recent_exams=[ExamOut.model_validate(e) for e in recent],
        subject_stats=[SubjectStat(**s) for s in stats],
        weak_subjects=weak,
        radar_data=build_radar_data(stats, child.subjects or None),
        trend_data=build_trend_data(exams),
        action_suggestions=build_action_suggestions(exams, stats, weak),
    )


@router.get("/compare/all", response_model=CompareData)
async def compare_children(
    user: User = Depends(require_parent),
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    """多孩子之间的对比（仅本家庭孩子）"""
    if not accessible:
        return CompareData(children=[])
    children_q = await db.execute(
        select(Child).where(Child.id.in_(accessible)).order_by(Child.id)
    )
    children = list(children_q.scalars().all())

    result = []
    for c in children:
        exams_q = await db.execute(select(Exam).where(Exam.child_id == c.id))
        exams = list(exams_q.scalars().all())
        stats = build_subject_stats(exams)
        if stats:
            avg = sum(s["avg_score"] for s in stats) / len(stats)
            best_subject = stats[0]["subject"]
            weak_subject = stats[-1]["subject"]
        else:
            avg = 0
            best_subject = ""
            weak_subject = ""
        result.append({
            "id": c.id,
            "name": c.name,
            "grade": c.grade,
            "avatar_color": c.avatar_color,
            "total_exams": len(exams),
            "average_score": round(avg, 2),
            "best_subject": best_subject,
            "needs_attention_subject": weak_subject,
        })
    return CompareData(children=result)
