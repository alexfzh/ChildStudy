"""KnowledgePoint ↔ TextbookUnit 多对多关联路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_parent
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
async def link_point_to_units(point_id: int, payload: List[KnowledgePointUnitLink], db: AsyncSession = Depends(get_db), _parent=Depends(require_parent)):
    p = await db.get(KnowledgePoint, point_id)
    if not p:
        raise HTTPException(404, "知识点不存在")
    # 删旧再插入（简单替换）
    existing = (await db.execute(
        select(KnowledgePointUnit).where(KnowledgePointUnit.knowledge_point_id == point_id)
    )).scalars().all()
    for ex in existing:
        await db.delete(ex)
    # 批量预取（修复 N+1）：一次校验全部 unit_id 存在性
    unit_ids = [link.unit_id for link in payload]
    valid_unit_ids = set((await db.execute(
        select(TextbookUnit.id).where(TextbookUnit.id.in_(unit_ids))
    )).scalars().all()) if unit_ids else set()
    for link in payload:
        if link.unit_id not in valid_unit_ids:
            continue
        db.add(KnowledgePointUnit(
            knowledge_point_id=point_id,
            unit_id=link.unit_id,
            relevance=link.relevance,
        ))
    await db.commit()
    return OkResponse(message=f"已为知识点 {point_id} 关联 {len(payload)} 个 Unit")


@router.post("/bulk", response_model=OkResponse)
async def bulk_link(payload: List[KnowledgePointUnitBulkLink], db: AsyncSession = Depends(get_db), _parent=Depends(require_parent)):
    """批量关联 KP ↔ Unit（覆盖模式：删旧 → 插新）"""
    from sqlalchemy import delete as sa_delete

    if not payload:
        return OkResponse(message="已批量关联 0 条 KP-Unit")
    # 批量预取（修复 N+1）：KP/Unit 存在性 + 旧关联，全部一次查出
    kp_ids = [item.knowledge_point_id for item in payload]
    valid_kp_ids = set((await db.execute(
        select(KnowledgePoint.id).where(KnowledgePoint.id.in_(kp_ids))
    )).scalars().all())
    unit_ids = list({link.unit_id for item in payload for link in item.links})
    valid_unit_ids = set((await db.execute(
        select(TextbookUnit.id).where(TextbookUnit.id.in_(unit_ids))
    )).scalars().all()) if unit_ids else set()
    # 批量删旧（覆盖模式；仅限存在的 KP，与原逐条语义一致）
    await db.execute(sa_delete(KnowledgePointUnit).where(
        KnowledgePointUnit.knowledge_point_id.in_(list(valid_kp_ids))
    ))

    total = 0
    for item in payload:
        if item.knowledge_point_id not in valid_kp_ids:
            continue
        for link in item.links:
            if link.unit_id not in valid_unit_ids:
                continue
            db.add(KnowledgePointUnit(
                knowledge_point_id=item.knowledge_point_id,
                unit_id=link.unit_id,
                relevance=link.relevance,
            ))
            total += 1
    await db.commit()
    return OkResponse(message=f"已批量关联 {total} 条 KP-Unit")
