"""错题本"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ 错题本 ============
class WrongQuestionBase(BaseModel):
    child_id: int
    source_type: str = "manual"  # manual/exam/homework/bank
    source_id: Optional[int] = None
    bank_question_id: Optional[int] = None  # 智能匹配到的题库题目 ID
    subject: str = Field(..., min_length=1, max_length=32)
    question_text: str = Field(..., min_length=1)
    question_image: Optional[str] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    error_reason: str = "other"  # knowledge_gap/misunderstanding/careless/incomplete/other
    knowledge_points: List[str] = Field(default_factory=list)
    difficulty: str = "normal"  # easy/normal/hard
    mastery_level: str = "new"  # new/learning/mastered
    wrong_count: int = 1
    last_wrong_date: date = Field(default_factory=date.today)
    next_review_date: Optional[date] = None
    review_count: int = 0
    status: str = "active"  # active/archived/mastered
    note: Optional[str] = None


class WrongQuestionCreate(WrongQuestionBase):
    pass


class WrongQuestionUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=32)
    question_text: Optional[str] = Field(None, min_length=1)
    question_image: Optional[str] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    error_reason: Optional[str] = None
    knowledge_points: Optional[List[str]] = None
    difficulty: Optional[str] = None
    mastery_level: Optional[str] = None
    wrong_count: Optional[int] = None
    last_wrong_date: Optional[date] = None
    next_review_date: Optional[date] = None
    review_count: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None
    bank_question_id: Optional[int] = None


class WrongQuestionReviewCreate(BaseModel):
    result: str = Field(..., min_length=1)  # correct/partial/wrong
    note: Optional[str] = None


class WrongQuestionReviewOut(BaseModel):
    id: int
    wrong_question_id: int
    review_date: date
    result: str
    note: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WrongQuestionOut(WrongQuestionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    reviews: List[WrongQuestionReviewOut] = Field(default_factory=list)
    match_suggestions: Optional[dict] = None  # 智能匹配建议（创建/重新分析时返回）
    model_config = ConfigDict(from_attributes=True)


class WrongQuestionStats(BaseModel):
    total: int
    active: int
    mastered: int
    archived: int
    mastery_rate: float
    by_subject: List[dict]
    by_error_reason: List[dict]
    top_knowledge_points: List[dict]
    recent_trend: List[dict]


class BankMatchCandidateOut(BaseModel):
    question_id: int
    bank_id: int
    bank_title: str
    content: str
    knowledge_point: str
    score: float
    text_score: float
    fingerprint_score: float
    options_score: float
    match_reasons: List[str] = Field(default_factory=list)


class KPMatchCandidateOut(BaseModel):
    knowledge_point_id: int
    name: str
    subject: str
    score: float
    match_reasons: List[str] = Field(default_factory=list)
    # KP 是否能命中 KP 库（错题 KP 字符串 → KP id 解析用）
    matched: bool = True
    # 若已挂教材，附带 unit 标题（拼接 KP↔Unit 体系后输出）
    unit_code: Optional[str] = None
    unit_title_zh: Optional[str] = None


class MatchSuggestionsOut(BaseModel):
    bank_matches: List[BankMatchCandidateOut] = Field(default_factory=list)
    kp_matches: List[KPMatchCandidateOut] = Field(default_factory=list)


# KP 匹配来源（错题推荐时区分推荐路径）
KPMatchLevel = Literal["primary", "kp_name_fallback", "unit_extend"]


class MatchedQuestionOut(BaseModel):
    id: int
    bank_id: int
    knowledge_point: str
    difficulty: str
    content: str
    options: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    # 对接新 KP 体系的产物
    kp_match_level: str = "kp_name_fallback"  # primary / kp_name_fallback / unit_extend
    matched_kp_ids: List[int] = Field(default_factory=list)  # 命中的 KP id
    matched_kp_names: List[str] = Field(default_factory=list)
    unit_code: Optional[str] = None  # 来源 Unit（如 U3）
    unit_title_zh: Optional[str] = None  # 来源 Unit 标题


class AcceptMatchRequest(BaseModel):
    bank_question_id: Optional[int] = None
    knowledge_points: Optional[List[str]] = None


class TodayReviewItem(BaseModel):
    id: int
    subject: str
    question_text: str
    mastery_level: str
    wrong_count: int
    knowledge_points: List[str]


class TodayReviewResponse(BaseModel):
    total: int
    items: List[TodayReviewItem]




