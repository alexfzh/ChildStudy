"""Dashboard 聚合数据"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.exam import ExamOut  # noqa: F401

# ============ Dashboard ============
class SubjectStat(BaseModel):
    subject: str
    avg_score: float
    max_score: float
    min_score: float
    exam_count: int
    trend: str  # up/down/flat
    latest_score: float


class DashboardData(BaseModel):
    child_id: int
    child_name: str
    total_exams: int
    total_homeworks: int
    recent_exams: List[ExamOut]
    subject_stats: List[SubjectStat]
    weak_subjects: List[str]
    radar_data: dict
    trend_data: dict
    action_suggestions: List[str] = []


class CompareData(BaseModel):
    children: List[dict]  # 每个孩子的概况




