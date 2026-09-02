"""KnowledgePoint ↔ Unit 多对多关联"""


from pydantic import BaseModel, ConfigDict, Field

from schemas.knowledge_point import KnowledgePointBase


# ============ KnowledgePoint ↔ Unit 多对多关联 ============
class KnowledgePointUnitLink(BaseModel):
    unit_id: int
    relevance: str = Field("primary", pattern="^(primary|secondary|review)$")


class KnowledgePointUnitBulkLink(BaseModel):
    knowledge_point_id: int
    links: list[KnowledgePointUnitLink]


class KnowledgePointWithUnits(KnowledgePointBase):
    """KP 详情 + 关联 Unit 列表（id + code + title_en + relevance）"""
    id: int
    unit_links: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class UnitWithKnowledgePoints(BaseModel):
    """Unit 详情 + 关联 KP 列表"""
    unit_id: int
    knowledge_points: list[dict] = Field(default_factory=list)




