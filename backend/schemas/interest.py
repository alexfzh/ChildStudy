"""兴趣特长"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 兴趣特长 ============
class InterestBase(BaseModel):
    # child_id 由 router 从路径参数注入，不要求 body 传
    child_id: Optional[int] = None
    record_date: date
    activity_type: str = Field(..., min_length=1, max_length=32)  # 运动/音乐/美术/编程/阅读/其他
    activity_name: str = Field(..., min_length=1, max_length=128)
    duration_minutes: Optional[int] = None
    skill_level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    note: Optional[str] = None


class InterestCreate(InterestBase):
    pass


class InterestUpdate(BaseModel):
    record_date: Optional[date] = None
    activity_type: Optional[str] = Field(None, min_length=1, max_length=32)
    activity_name: Optional[str] = Field(None, min_length=1, max_length=128)
    duration_minutes: Optional[int] = None
    skill_level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced)$")
    note: Optional[str] = None


class InterestOut(InterestBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




