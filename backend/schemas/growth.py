"""生长发育"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 生长发育 ============
class GrowthRecordBase(BaseModel):
    # child_id 由 router 从路径参数注入，不要求 body 传（前端表单无此字段）
    child_id: Optional[int] = None
    record_date: date
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    vision_left: Optional[float] = Field(None, description="左眼视力")
    vision_right: Optional[float] = Field(None, description="右眼视力")
    note: Optional[str] = None


class GrowthRecordCreate(GrowthRecordBase):
    pass


class GrowthRecordUpdate(BaseModel):
    record_date: Optional[date] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    vision_left: Optional[float] = None
    vision_right: Optional[float] = None
    note: Optional[str] = None


class GrowthRecordOut(GrowthRecordBase):
    id: int
    created_at: datetime
    bmi_assessment: dict | None = None
    height_assessment: dict | None = None
    weight_assessment: dict | None = None
    model_config = ConfigDict(from_attributes=True)




