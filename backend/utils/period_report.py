"""学情周报/月报 数据聚合层（v1.7.0）

输入：child_id, period_type ('weekly'|'monthly'), period_start, period_end
输出：完整 dict（概览/考试/错题/KP进度/段位/建议），供 PDF 生成层消费。
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Child,
    ChildRank,
    Exam,
    Exercise,
    KnowledgePoint,
    KPStudyProgress,
    PointsLog,
    WrongQuestion,
)
from utils.analysis import build_action_suggestions, build_subject_stats

# ============ 周期工具 ============

def normalize_period(period_type: str, period_end: Optional[date] = None) -> tuple[date, date, str, str]:
    """根据 period_type 算出 (start, end, label_zh, period_key)

    - weekly:  上周一 ~ 上周日（自然周） / 当周：周一 ~ 今天
    - monthly: 上月 1 号 ~ 上月最后一天 / 当月：1号 ~ 今天
    - period_end 默认为今天
    """
    if period_end is None:
        period_end = date.today()
    period_end = period_end

    if period_type == "weekly":
        # 当周：周一 ~ 今天
        weekday = period_end.weekday()  # 0=Mon
        period_start = period_end - _timedelta(weekday)
        label = f"本周（{period_start.isoformat()} ~ {period_end.isoformat()}）"
    elif period_type == "monthly":
        period_start = period_end.replace(day=1)
        label = f"本月（{period_start.isoformat()} ~ {period_end.isoformat()}）"
    else:
        raise ValueError(f"未知 period_type: {period_type}")

    period_key = f"{period_type}_{period_start.isoformat()}_{period_end.isoformat()}"
    return period_start, period_end, label, period_key


def _timedelta(days: int):
    from datetime import timedelta
    return timedelta(days=days)


# ============ 主聚合函数 ============

async def build_period_report(
    db: AsyncSession,
    child_id: int,
    period_type: str = "weekly",
    period_end: Optional[date] = None,
) -> Dict[str, Any]:
    """聚合一个孩子在指定周期的学情数据。

    返回结构（dict），方便 PDF 层直接渲染：
      {
        "child": {id, name, grade},
        "period": {type, start, end, label},
        "overview": {
          "exam_count", "wrong_count", "exercise_count", "exercise_avg_score",
          "points_earned", "kp_total", "kp_new", "kp_learning", "kp_strong", "kp_mastered"
        },
        "subject_stats": [{subject, exam_count, avg_score, latest_score, trend, delta}, ...],
        "exams": [{date, name, subject, score, full_score, pct}, ...],
        "wrong_kp_distribution": [{kp_name, count, unit_code?}, ...],
        "kp_progress": {new, learning, strong, mastered, total},
        "ranks": [{subject, tier, stars, avg_score, exam_count, total_points}, ...],
        "action_suggestions": [str, ...],
      }
    """
    period_start, period_end, label, period_key = normalize_period(period_type, period_end)

    child = await db.get(Child, child_id)
    if not child:
        raise ValueError(f"孩子档案不存在: child_id={child_id}")

    # ── 1. 概览 ──
    exam_q = await db.execute(
        select(Exam).where(
            and_(Exam.child_id == child_id, Exam.exam_date >= period_start, Exam.exam_date <= period_end)
        ).order_by(Exam.exam_date)
    )
    exams = list(exam_q.scalars().all())

    wq_q = await db.execute(
        select(WrongQuestion).where(
            and_(WrongQuestion.child_id == child_id, WrongQuestion.created_at >= period_start_dt(period_start))
        )
    )
    wrong_questions = list(wq_q.scalars().all())

    ex_q = await db.execute(
        select(Exercise).where(
            and_(Exercise.child_id == child_id, Exercise.created_at >= period_start_dt(period_start))
        )
    )
    exercises = list(ex_q.scalars().all())

    points_q = await db.execute(
        select(PointsLog).where(
            and_(PointsLog.child_id == child_id, PointsLog.created_at >= period_start_dt(period_start))
        )
    )
    points_records = list(points_q.scalars().all())
    # 积分 = 获得 + 消费（消费负数已计入），这里只看正向获得
    points_earned = sum(p.points for p in points_records if p.points > 0)

    exercise_avg_score = (
        round(sum(e.score or 0 for e in exercises) / len(exercises), 1) if exercises else 0.0
    )

    # ── 2. KP 掌握度（全量，非周期内）──
    kp_all_q = await db.execute(
        select(KPStudyProgress).where(KPStudyProgress.child_id == child_id)
    )
    kp_all = list(kp_all_q.scalars().all())
    kp_mastery_counter = Counter(k.mastery_level for k in kp_all)
    kp_progress = {
        "new": kp_mastery_counter.get("new", 0),
        "learning": kp_mastery_counter.get("learning", 0),
        "strong": kp_mastery_counter.get("strong", 0),
        "mastered": kp_mastery_counter.get("mastered", 0),
        "total": len(kp_all),
    }

    # ── 3. 段位榜 ──
    rank_q = await db.execute(
        select(ChildRank).where(ChildRank.child_id == child_id)
    )
    rank_objs = list(rank_q.scalars().all())
    ranks = [
        {
            "subject": r.subject,
            "tier": r.tier,
            "stars": r.stars,
            "avg_score": r.avg_score or 0.0,
            "exam_count": r.exam_count,
            "total_points": r.total_points,
        }
        for r in sorted(rank_objs, key=lambda x: -(x.avg_score or 0))
    ]

    # ── 4. 各科统计 + 趋势（复用现有 utils）──
    # 周期内考试为空时，回退到近 90 天，避免趋势空跑
    stats_exams = exams if exams else await _recent_exams_fallback(db, child_id)
    subject_stats = build_subject_stats(stats_exams) if stats_exams else []

    # ── 5. 错题按 KP 分布（仅周期内新增）──
    wrong_kp_counter: Counter = Counter()
    for wq in wrong_questions:
        for kp in (wq.knowledge_points or []):
            wrong_kp_counter[kp] += 1
    # 反查 KP id → unit
    kp_names_set = list(wrong_kp_counter.keys())
    kp_unit_map: Dict[str, str] = {}
    if kp_names_set:
        kp_q = await db.execute(
            select(KnowledgePoint.name, KnowledgePoint.id).where(KnowledgePoint.name.in_(kp_names_set))
        )
        kp_names_list = [r[0] for r in kp_q.all()]
        # 简化：先把 KP 名放进 unit map 留接口
        kp_unit_map = {n: "-" for n in kp_names_list}

    wrong_kp_distribution = sorted(
        [
            {"kp_name": kp, "count": cnt, "unit_code": kp_unit_map.get(kp, "-")}
            for kp, cnt in wrong_kp_counter.items()
        ],
        key=lambda x: -x["count"],
    )

    # ── 6. 考试明细（按时间排序）──
    exam_details = [
        {
            "date": e.exam_date.isoformat(),
            "name": e.exam_name,
            "subject": e.subject,
            "score": e.score,
            "full_score": e.full_score,
            "pct": round(e.score / e.full_score * 100, 1) if e.full_score else 0.0,
        }
        for e in exams
    ]

    # ── 7. 行动建议（复用 build_action_suggestions）──
    weak_subjects = [s["subject"] for s in subject_stats if s.get("avg_score", 100) < 85]
    action_suggestions = build_action_suggestions(stats_exams, subject_stats, weak_subjects)

    # ── 概览汇总 ──
    overview = {
        "exam_count": len(exams),
        "wrong_count": len(wrong_questions),
        "exercise_count": len(exercises),
        "exercise_avg_score": exercise_avg_score,
        "points_earned": points_earned,
        "kp_new": kp_progress["new"],
        "kp_learning": kp_progress["learning"],
        "kp_strong": kp_progress["strong"],
        "kp_mastered": kp_progress["mastered"],
        "kp_total": kp_progress["total"],
    }

    return {
        "child": {"id": child.id, "name": child.name, "grade": child.grade},
        "period": {
            "type": period_type,
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "label": label,
            "key": period_key,
        },
        "overview": overview,
        "subject_stats": subject_stats,
        "exams": exam_details,
        "wrong_kp_distribution": wrong_kp_distribution,
        "kp_progress": kp_progress,
        "ranks": ranks,
        "action_suggestions": action_suggestions,
    }


async def _recent_exams_fallback(db: AsyncSession, child_id: int, days: int = 90) -> List[Exam]:
    """周期内无考试时回退到近 N 天"""
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)
    q = await db.execute(
        select(Exam).where(
            and_(Exam.child_id == child_id, Exam.exam_date >= cutoff)
        ).order_by(Exam.exam_date)
    )
    return list(q.scalars().all())


def period_start_dt(d: date) -> datetime:
    """date 转 datetime（SQLAlchemy 比较用）"""
    return datetime(d.year, d.month, d.day)
