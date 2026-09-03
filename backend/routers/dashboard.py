"""家长看板 / Dashboard 数据路由"""
import time
from typing import Any

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

# 看板聚合查询缓存：TTL=60s，避免每次打开都重算「最近 30 天」统计
# key = (child_id, cache_version)，TTL 到期或显式 invalidate 后重算
_DASHBOARD_CACHE: dict[tuple[int, str], tuple[float, Any]] = {}
_DASHBOARD_TTL = 60.0


def _dashboard_cache_get(child_id: int, key: str = "v1") -> Any | None:
    """读看板缓存。命中且未过期 → 返回；否则 None。"""
    full_key = (child_id, key)
    entry = _DASHBOARD_CACHE.get(full_key)
    if entry is None:
        return None
    expires_at, value = entry
    if expires_at < time.time():
        _DASHBOARD_CACHE.pop(full_key, None)
        return None
    return value


def _dashboard_cache_put(child_id: int, value: Any, key: str = "v1") -> None:
    """写看板缓存（覆盖写）。"""
    _DASHBOARD_CACHE[(child_id, key)] = (time.time() + _DASHBOARD_TTL, value)


def invalidate_dashboard_cache(child_id: int) -> None:
    """子数据变更（考试/作业/身高体重录入）后调用，清掉该孩子看板缓存。"""
    _DASHBOARD_CACHE.pop((child_id, "v1"), None)


@router.get("/{child_id}", response_model=DashboardData)
async def get_dashboard(
    child_id: int,
    accessible: set[int] = Depends(get_accessible_child_ids),
    db: AsyncSession = Depends(get_db),
):
    assert_child_access(accessible, child_id)

    # 缓存命中直接返回（60s 内不重算）
    cached = _dashboard_cache_get(child_id)
    if cached is not None:
        return cached

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

    dashboard = DashboardData(
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
    # 写入缓存（60s TTL）
    _dashboard_cache_put(child_id, dashboard)
    return dashboard


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
