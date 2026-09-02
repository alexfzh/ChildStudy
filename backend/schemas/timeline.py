"""时间轴事件"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ 时间轴事件 ============
class TimelineBase(BaseModel):
    event_type: str = "note"
    title: str
    description: Optional[str] = None
    event_date: date
    attachments: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class TimelineCreate(TimelineBase):
    child_id: int


class TimelineUpdate(BaseModel):
    event_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    attachments: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class TimelineOut(TimelineBase):
    id: int
    child_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




