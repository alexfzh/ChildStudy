"""孩子档案 / 年级历史"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 孩子档案 ============
class ChildBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    grade: str = Field(..., min_length=1, max_length=32)
    school: Optional[str] = None
    avatar_color: str = "#6366f1"
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    gender: Optional[str] = Field(None, description="male/female")
    subjects: List[str] = Field(default_factory=lambda: ["语文", "数学", "英语"])


class ChildCreate(ChildBase):
    pass


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    avatar_color: Optional[str] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    gender: Optional[str] = None
    subjects: Optional[List[str]] = None


class ChildOut(ChildBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




# ============ 年级历史 ============
class GradeHistoryCreate(BaseModel):
    grade: str = Field(..., min_length=1, max_length=32)
    effective_from: date
    note: Optional[str] = Field(None, max_length=256)


class GradeHistoryOut(BaseModel):
    id: int
    grade: str
    effective_from: date
    note: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




