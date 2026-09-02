"""教材版本 / 单元 / 学习进度 / Project 作品"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ 教材版本 / 单元 / 学习进度 / Project 作品 ============
class TextbookVersionBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    publisher: str = Field(..., max_length=64)
    grade: str = Field(..., max_length=32)
    subject: str = Field(..., max_length=32)
    term: str = Field("A", max_length=8)
    is_active: bool = True
    description: Optional[str] = None


class TextbookVersionCreate(TextbookVersionBase):
    pass


class TextbookVersionOut(TextbookVersionBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TextbookUnitBase(BaseModel):
    version_id: int
    code: str = Field(..., max_length=16)
    unit_number: int
    title_en: Optional[str] = Field(None, max_length=128)
    title_zh: str = Field(..., max_length=128)
    topic_words: list = Field(default_factory=list)
    sound: Optional[str] = Field(None, max_length=32)
    sound_examples: list = Field(default_factory=list)
    structure: Optional[str] = Field(None, max_length=128)
    big_task: Optional[str] = Field(None, max_length=255)
    project_type: Optional[str] = Field(None, max_length=64)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    is_project: bool = False


class TextbookUnitCreate(TextbookUnitBase):
    pass


class TextbookUnitOut(TextbookUnitBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuestionUnitLink(BaseModel):
    unit_id: int
    relevance: str = Field("primary", pattern="^(primary|supplementary|cross)$")


class QuestionUnitBulkLink(BaseModel):
    question_id: int
    links: list[QuestionUnitLink]


class StudyProgressOut(BaseModel):
    id: int
    child_id: int
    unit_id: int
    status: str
    total_attempts: int
    total_correct: int
    accuracy: float
    completion_pct: float
    mastered_at: Optional[datetime] = None
    last_study_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ChildProgressSummary(BaseModel):
    """孩子在某教材版本下所有 Unit 的进度概览"""
    child_id: int
    version_id: int
    units: list[TextbookUnitOut]
    progress_map: dict
    mastery_pct: float
    streak_units: int
    total_points: int
    total_achievements: int


class ProjectWorkCreate(BaseModel):
    child_id: int
    unit_id: int
    work_type: str = Field("text", pattern="^(text|image|drawing|audio)$")
    title: Optional[str] = Field(None, max_length=128)
    content: Optional[str] = None
    image_path: Optional[str] = Field(None, max_length=255)


class ProjectWorkUpdate(BaseModel):
    content: Optional[str] = None
    image_path: Optional[str] = Field(None, max_length=255)
    parent_comment: Optional[str] = None
    teacher_comment: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(submitted|reviewed|approved|needs_revision)$")


class ProjectWorkOut(BaseModel):
    id: int
    child_id: int
    unit_id: int
    work_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    image_path: Optional[str] = None
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None
    parent_comment: Optional[str] = None
    teacher_comment: Optional[str] = None
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)



