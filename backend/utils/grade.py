"""年级历史查询工具：根据 child_id + 日期返回当时的年级"""
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Child, GradeHistory


async def get_grade_at_date(db: AsyncSession, child_id: int, target_date: date) -> Optional[str]:
    """查询某孩子 target_date 当天所在的年级。

    逻辑：从 GradeHistory 找 effective_from <= target_date 中最新的那条；找不到则用 Child.grade。
    """
    q = await db.execute(
        select(GradeHistory)
        .where(GradeHistory.child_id == child_id)
        .where(GradeHistory.effective_from <= target_date)
        .order_by(GradeHistory.effective_from.desc())
        .limit(1)
    )
    entry = q.scalar_one_or_none()
    if entry:
        return entry.grade

    # 无历史时 fallback 到 Child.grade（首次使用前的当前 grade）
    child = await db.get(Child, child_id)
    if child and child.grade:
        return child.grade
    return None


async def get_grade_history(db: AsyncSession, child_id: int) -> list[GradeHistory]:
    """获取完整年级历史（按时间倒序）"""
    q = await db.execute(
        select(GradeHistory)
        .where(GradeHistory.child_id == child_id)
        .order_by(GradeHistory.effective_from.desc())
    )
    return list(q.scalars().all())
