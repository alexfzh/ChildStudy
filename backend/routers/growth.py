"""生长发育记录路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids
from models import Child, GrowthRecord
from schemas import GrowthRecordCreate, GrowthRecordOut, GrowthRecordUpdate
from utils.growth_assessor import (
    assess_bmi,
    assess_height,
    assess_weight,
    compute_bmi,
    get_standard_description,
)
from utils.growth_standards import (
    BMI_CUTOFFS_6_18,
    HEIGHT_0_83,
    HEIGHT_7_18,
    WEIGHT_0_83,
    WEIGHT_7_18,
)

router = APIRouter(prefix="/api/growth", tags=["生长发育"])


# ---------- 标准数据（必须在 {child_id} 之前定义，否则会被截胡） ----------
@router.get("/standards")
def get_standards():
    """Return Chinese growth standards for frontend charts.

    Sources:
      - WS/T 423-2022 (0-7 岁 身高/体重/BMI 百分位)
      - WS/T 586-2018 (6-18 岁 BMI 切点)
      - WS/T 611-2018 (7-18 岁身高)
    Note: WHO data is not yet implemented (future enhancement).
    """
    return {
        "schema_version": 1,
        "sources": [
            "WS/T 423-2022 (0-7 岁)",
            "WS/T 586-2018 (6-18 岁 BMI 切点)",
            "WS/T 611-2018 (7-18 岁身高)",
        ],
        "height_0_83_months": HEIGHT_0_83,  # type: ignore[return-value]
        "weight_0_83_months": WEIGHT_0_83,  # type: ignore[return-value]
        "bmi_cutoffs_6_18": BMI_CUTOFFS_6_18,  # type: ignore[return-value]
        "height_7_18_years": HEIGHT_7_18,  # type: ignore[return-value]
        "weight_7_18_years": WEIGHT_7_18,  # type: ignore[return-value]
        "description": get_standard_description(),
    }


# ---------- 列表（含派生评估） ----------
@router.get("/{child_id}", response_model=List[GrowthRecordOut])
async def list_by_child(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    result = await db.execute(
        select(GrowthRecord)
        .where(GrowthRecord.child_id == child_id)
        .order_by(GrowthRecord.record_date.desc())
    )
    records = result.scalars().all()

    if not records:
        return []

    # Attach derived assessments (BMI auto-calc + percentile ratings)
    # NOTE: Child model doesn't have a gender field yet (deferred).
    # Default to "male" for now; future enhancement: add Child.gender column.
    child = await db.get(Child, child_id)
    gender = "male"

    enriched = []
    for r in records:
        age_months = None
        if child and child.birth_date and r.record_date:
            try:
                from datetime import date

                from dateutil.relativedelta import relativedelta
                rd = date.fromisoformat(r.record_date.isoformat())
                bd = child.birth_date
                rd_ = relativedelta(rd, bd)
                age_months = rd_.years * 12 + rd_.months
            except Exception:
                pass

        bmi = compute_bmi(r.height_cm, r.weight_kg)
        enriched.append(
            GrowthRecordOut(
                id=r.id,
                record_date=r.record_date,
                height_cm=r.height_cm,
                weight_kg=r.weight_kg,
                vision_left=r.vision_left,
                vision_right=r.vision_right,
                note=r.note,
                created_at=r.created_at,
                bmi=bmi,
                bmi_assessment=assess_bmi(bmi, gender, age_months),
                height_assessment=assess_height(r.height_cm, gender, age_months),
                weight_assessment=assess_weight(r.weight_kg, gender, age_months),
            )
        )
    return enriched


# ---------- 创建 ----------
@router.post("/{child_id}", response_model=GrowthRecordOut, status_code=201)
async def create(
    child_id: int,
    payload: GrowthRecordCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    data = payload.model_dump()
    data["child_id"] = child_id
    record = GrowthRecord(**data)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


# ---------- 更新 ----------
@router.put("/{record_id}", response_model=GrowthRecordOut)
async def update(
    record_id: int,
    payload: GrowthRecordUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    record = await db.get(GrowthRecord, record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    assert_child_access(accessible, record.child_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    await db.commit()
    await db.refresh(record)
    return record


# ---------- 删除 ----------
@router.delete("/{record_id}")
async def delete(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    record = await db.get(GrowthRecord, record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    assert_child_access(accessible, record.child_id)
    await db.delete(record)
    await db.commit()
    return {"ok": True, "message": "已删除"}
