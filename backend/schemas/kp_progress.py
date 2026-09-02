"""KPStudyProgress"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ KPStudyProgress（KP 级别掌握度） ============
class KPStudyProgressOut(BaseModel):
    id: int
    child_id: int
    knowledge_point_id: int
    unit_id: Optional[int] = None
    total_attempts: int
    total_correct: int
    accuracy: float
    mastery_level: str  # new/learning/strong/mastered
    last_study_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class KPProgressSummary(BaseModel):
    """某 Unit 内所有 KP 的掌握度汇总"""
    unit_id: int
    unit_code: str
    unit_title_zh: str
    total_kps: int
    mastered_kps: int
    learning_kps: int
    strong_kps: int
    new_kps: int
    mastery_pct: float  # 0-100
    kp_details: list[KPStudyProgressOut] = Field(default_factory=list)


class ChildKPProgressSummary(BaseModel):
    """孩子某教材版本下所有 Unit × KP 的掌握度矩阵"""
    child_id: int
    version_id: int
    total_kps: int
    overall_mastery_pct: float
    kp_summary_by_unit: list[KPProgressSummary] = Field(default_factory=list)


