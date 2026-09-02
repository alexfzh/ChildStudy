"""社交情感"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 社交情感 ============
class SocialEmotionalBase(BaseModel):
    # child_id 由 router 从路径参数注入，不要求 body 传
    child_id: Optional[int] = None
    record_date: date
    mood_score: Optional[int] = Field(None, ge=1, le=5, description="情绪指数 1-5")
    emotion_tags: List[str] = Field(default_factory=list)
    social_activity: Optional[str] = Field(None, max_length=256)
    confidence_level: Optional[int] = Field(None, ge=1, le=5, description="自信心 1-5")
    note: Optional[str] = None


class SocialEmotionalCreate(SocialEmotionalBase):
    pass


class SocialEmotionalUpdate(BaseModel):
    record_date: Optional[date] = None
    mood_score: Optional[int] = Field(None, ge=1, le=5)
    emotion_tags: Optional[List[str]] = None
    social_activity: Optional[str] = Field(None, max_length=256)
    confidence_level: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = None


class SocialEmotionalOut(SocialEmotionalBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




