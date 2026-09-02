"""题库 + 练习"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from schemas.wrong_question import KPMatchCandidateOut, MatchedQuestionOut  # noqa: F401

# ============ 题库系统 ============
class QuestionBankBase(BaseModel):
    grade: str = Field(..., max_length=32)
    subject: str = Field(..., max_length=32)
    title: str = Field(..., max_length=128)
    description: Optional[str] = None
    is_active: bool = True


class QuestionBankCreate(QuestionBankBase):
    pass


class QuestionBankUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionBankOut(QuestionBankBase):
    id: int
    question_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuestionBase(BaseModel):
    bank_id: int
    knowledge_point: str = Field(..., max_length=128)
    # single_choice: 4 选项单选; true_false: 对/错判断 (options=["正确","错误"], correct_answer=A/B)
    question_type: str = Field("single_choice", pattern="^(single_choice|true_false)$")
    difficulty: str = Field("normal", pattern="^(easy|normal|hard)$")
    content: str
    options: List[str] = Field(..., min_length=2, max_length=6)
    correct_answer: str = Field(..., min_length=1, max_length=1, pattern="^[A-F]$")
    explanation: Optional[str] = None


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    knowledge_point: Optional[str] = Field(None, max_length=128)
    question_type: Optional[str] = Field(None, pattern="^(single_choice|true_false)$")
    difficulty: Optional[str] = Field(None, pattern="^(easy|normal|hard)$")
    content: Optional[str] = None
    options: Optional[List[str]] = Field(None, min_length=2, max_length=6)
    correct_answer: Optional[str] = Field(None, min_length=1, max_length=1, pattern="^[A-F]$")
    explanation: Optional[str] = None


class QuestionOut(QuestionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExerciseStartRequest(BaseModel):
    child_id: int
    bank_id: int
    count: int = Field(default=5, ge=1, le=20)
    knowledge_points: Optional[List[str]] = None  # None=随机
    difficulty: Optional[str] = Field(None, pattern="^(easy|normal|hard)$")
    mode: str = Field("manual", pattern="^(manual|recommend)$")
    wrong_question_ids: Optional[List[int]] = None


class ExerciseSubmitRequest(BaseModel):
    answers: List[dict]  # [{question_id, selected}]
    time_spent: Optional[int] = None  # 练习耗时(秒)


class ExerciseOut(BaseModel):
    id: int
    child_id: int
    bank_id: int
    bank_title: str = ""  # v1.8.0: 联表返回题库标题，看板直接用（避免 N+1：list 端点 selectinload）
    questions: List[dict]
    answers: List[dict]
    score: Optional[float]
    total_questions: int
    correct_count: int
    submitted_at: Optional[datetime]
    time_spent: Optional[int] = None
    created_at: datetime
    # v1.8.0 激励：本次练习获得的积分、今日累计、本次解锁的新成就
    points_earned: int = 0
    daily_points_total: int = 0
    daily_points_cap: int = 10
    new_achievements: List["ChildAchievementOut"] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ExerciseRecommendation(BaseModel):
    wrong_questions: List[dict]
    matched_questions: List[MatchedQuestionOut]
    suggestion: str
    # 兼容新体系：本次推荐命中的 KP 列表（带 Unit 信息），家长可一眼看到薄弱点
    recommended_kps: List[KPMatchCandidateOut] = Field(default_factory=list)



