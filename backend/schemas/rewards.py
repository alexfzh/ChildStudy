"""奖励系统"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 奖励系统 ============
class RankInfo(BaseModel):
    subject: str
    tier: str
    stars: int
    avg_score: Optional[float]
    exam_count: int
    total_points: int
    color: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @property
    def display(self) -> str:
        if self.stars > 0:
            return f"{self.tier} {'⭐' * self.stars}"
        return self.tier


class RewardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    reward_type: str = Field("material", pattern="^(material|spiritual|privilege)$")
    cost_points: int = Field(0, ge=0)
    description: Optional[str] = None
    icon: str = Field("🎁", max_length=32)
    is_active: bool = True


class RewardCreate(RewardBase):
    pass


class RewardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    reward_type: Optional[str] = Field(None, pattern="^(material|spiritual|privilege)$")
    cost_points: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=32)
    is_active: Optional[bool] = None


class RewardOut(RewardBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChildRewardOut(BaseModel):
    id: int
    child_id: int
    reward_id: int
    points_spent: int
    source: str
    note: Optional[str]
    earned_date: date
    status: str = "pending"          # pending=待使用 / used=已核销
    used_at: Optional[datetime] = None
    used_by: Optional[int] = None
    reward: Optional[RewardOut] = None
    model_config = ConfigDict(from_attributes=True)


class AchievementBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    icon: str = Field("🏆", max_length=32)
    condition_type: str = Field(..., min_length=1, max_length=32)
    condition_value: Optional[int] = None


# icon 白名单：仅放行 "svg:<key>" 命名空间引用、或单个/少数 emoji、或一般短字符串
# （防 AchIcon.vue 的 v-html 被恶意 SVG/HTML 标签注入；用 Pydantic 在写入侧拦下最稳）
_ICON_PATTERN = r'^(svg:[a-z][a-z0-9_-]{0,31}|[\U0001F300-\U0001FAFF\u2600-\u27BF]{1,4}|.{1,8})$'


class AchievementCreate(AchievementBase):
    icon: str = Field("🏆", max_length=32, pattern=_ICON_PATTERN)


class AchievementOut(AchievementBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChildAchievementOut(BaseModel):
    id: int
    child_id: int
    achievement_id: int
    exam_id: Optional[int]
    earned_date: date
    achievement: Optional[AchievementOut] = None
    model_config = ConfigDict(from_attributes=True)


class PointsLogOut(BaseModel):
    id: int
    child_id: int
    points: int
    source: str
    description: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PointsSummary(BaseModel):
    total: int
    earned: int
    spent: int
    recent_logs: List[PointsLogOut] = Field(default_factory=list)


class ExamRewardResponse(BaseModel):
    points_earned: int
    new_rank: Optional[RankInfo] = None
    new_achievements: List[ChildAchievementOut] = Field(default_factory=list)
    message: str


class RewardShopItem(BaseModel):
    reward: RewardOut
    can_afford: bool




