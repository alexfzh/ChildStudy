"""知识点标签库"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ 知识点标签库 ============
class KnowledgePointBase(BaseModel):
    subject: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    grade_level: Optional[str] = Field(None, max_length=32)


class KnowledgePointCreate(KnowledgePointBase):
    pass


class KnowledgePointUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=32)
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    grade_level: Optional[str] = Field(None, max_length=32)


class KnowledgePointOut(KnowledgePointBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




