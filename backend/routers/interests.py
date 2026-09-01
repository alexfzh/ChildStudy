"""兴趣特长记录路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids
from models import InterestRecord
from schemas import InterestCreate, InterestOut, InterestUpdate

router = APIRouter(prefix="/api/interests", tags=["兴趣特长"])


@router.get("/{child_id}", response_model=List[InterestOut])
async def list_by_child(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    result = await db.execute(
        select(InterestRecord)
        .where(InterestRecord.child_id == child_id)
        .order_by(InterestRecord.record_date.desc())
    )
    return result.scalars().all()


@router.post("/{child_id}", response_model=InterestOut, status_code=201)
async def create(
    child_id: int,
    payload: InterestCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    data = payload.model_dump()
    data["child_id"] = child_id
    record = InterestRecord(**data)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


@router.put("/{record_id}", response_model=InterestOut)
async def update(
    record_id: int,
    payload: InterestUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    record = await db.get(InterestRecord, record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    assert_child_access(accessible, record.child_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{record_id}")
async def delete(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    record = await db.get(InterestRecord, record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    assert_child_access(accessible, record.child_id)
    await db.delete(record)
    await db.commit()
    return {"ok": True, "message": "已删除"}
