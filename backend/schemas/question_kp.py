"""Question ↔ KnowledgePoint 多对多关联"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ Question ↔ KnowledgePoint 多对多关联 ============
class QuestionKPLink(BaseModel):
    knowledge_point_id: int
    is_primary: bool = True


class QuestionKPBulkLink(BaseModel):
    question_id: int
    links: list[QuestionKPLink]


class QuestionWithKPs(BaseModel):
    """Question 详情 + 关联 KP 列表"""
    id: int
    knowledge_point: str  # 保留旧字符串字段（兼容）
    kp_links: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)




