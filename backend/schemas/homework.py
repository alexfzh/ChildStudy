"""作业记录"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ 作业记录 ============
class HomeworkBase(BaseModel):
    subject: str
    title: str
    homework_date: date
    duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    correct_questions: Optional[int] = None
    accuracy: Optional[float] = None
    completed: bool = True
    difficulty: str = "normal"
    note: Optional[str] = None
    grade_snapshot: Optional[str] = None  # 作业时的年级快照（服务端可自动补）


class HomeworkCreate(HomeworkBase):
    child_id: int


class HomeworkUpdate(BaseModel):
    subject: Optional[str] = None
    title: Optional[str] = None
    homework_date: Optional[date] = None
    duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    correct_questions: Optional[int] = None
    accuracy: Optional[float] = None
    completed: Optional[bool] = None
    difficulty: Optional[str] = None
    note: Optional[str] = None


class HomeworkOut(HomeworkBase):
    id: int
    child_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




