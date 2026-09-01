"""KnowledgePoint ↔ TextbookUnit 多对多关联路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import KnowledgePoint, KnowledgePointUnit, TextbookUnit
from schemas import (
    KnowledgePointUnitBulkLink,
    KnowledgePointUnitLink,
    OkResponse,
)

router = APIRouter(prefix="/api/knowledge-point-units", tags=["知识点-单元关联"])


@router.get("/point/{point_id}")
async def list_units_for_point(point_id: int, db: AsyncSession = Depends(get_db)):
    """返回某 KP 关联的所有 Unit"""
    stmt = (
        select(KnowledgePointUnit, TextbookUnit)
        .join(TextbookUnit, TextbookUnit.id == KnowledgePointUnit.unit_id)
        .where(KnowledgePointUnit.knowledge_point_id == point_id)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "link_id": kpu.id,
            "unit_id": u.id,
            "version_id": u.version_id,
            "code": u.code,
            "title_en": u.title_en,
            "title_zh": u.title_zh,
            "relevance": kpu.relevance,
        }
        for kpu, u in rows
    ]


@router.get("/unit/{unit_id}")
async def list_points_for_unit(unit_id: int, db: AsyncSession = Depends(get_db)):
    """返回某 Unit 关联的所有 KP"""
    stmt = (
        select(KnowledgePointUnit, KnowledgePoint)
        .join(KnowledgePoint, KnowledgePoint.id == KnowledgePointUnit.knowledge_point_id)
        .where(KnowledgePointUnit.unit_id == unit_id)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "link_id": kpu.id,
            "knowledge_point_id": kp.id,
            "subject": kp.subject,
            "name": kp.name,
            "category": kp.category,
            "grade_level": kp.grade_level,
            "relevance": kpu.relevance,
        }
        for kpu, kp in rows
    ]


@router.post("/point/{point_id}", response_model=OkResponse)
async def link_point_to_units(point_id: int, payload: List[KnowledgePointUnitLink], db: AsyncSession = Depends(get_db)):
    p = await db.get(KnowledgePoint, point_id)
    if not p:
        raise HTTPException(404, "知识点不存在")
    # 删旧再插入（简单替换）
    existing = (await db.execute(
        select(KnowledgePointUnit).where(KnowledgePointUnit.knowledge_point_id == point_id)
    )).scalars().all()
    for ex in existing:
        await db.delete(ex)
    for link in payload:
        unit = await db.get(TextbookUnit, link.unit_id)
        if not unit:
            continue
        kpu = KnowledgePointUnit(
            knowledge_point_id=point_id,
            unit_id=link.unit_id,
            relevance=link.relevance,
        )
        db.add(kpu)
    await db.commit()
    return OkResponse(message=f"已为知识点 {point_id} 关联 {len(payload)} 个 Unit")


@router.post("/bulk", response_model=OkResponse)
async def bulk_link(payload: List[KnowledgePointUnitBulkLink], db: AsyncSession = Depends(get_db)):
    """批量关联 KP ↔ Unit（覆盖模式：删旧 → 插新）"""
    total = 0
    for item in payload:
        p = await db.get(KnowledgePoint, item.knowledge_point_id)
        if not p:
            continue
        existing = (await db.execute(
            select(KnowledgePointUnit).where(KnowledgePointUnit.knowledge_point_id == item.knowledge_point_id)
        )).scalars().all()
        for ex in existing:
            await db.delete(ex)
        for link in item.links:
            unit = await db.get(TextbookUnit, link.unit_id)
            if not unit:
                continue
            db.add(KnowledgePointUnit(
                knowledge_point_id=item.knowledge_point_id,
                unit_id=link.unit_id,
                relevance=link.relevance,
            ))
            total += 1
    await db.commit()
    return OkResponse(message=f"已批量关联 {total} 条 KP-Unit")
