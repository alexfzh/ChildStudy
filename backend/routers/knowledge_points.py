"""知识点标签库路由"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_parent
from models import KnowledgePoint
from schemas import KnowledgePointCreate, KnowledgePointOut, KnowledgePointUpdate, OkResponse

router = APIRouter(prefix="/api/knowledge-points", tags=["知识点标签库"])


@router.get("", response_model=List[KnowledgePointOut])
async def list_knowledge_points(
    subject: Optional[str] = None,
    category: Optional[str] = None,
    grade_level: Optional[str] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """知识点列表，支持按科目/分类/年级/关键词过滤"""
    stmt = select(KnowledgePoint).order_by(KnowledgePoint.subject.asc(), KnowledgePoint.name.asc())
    if subject:
        stmt = stmt.where(KnowledgePoint.subject == subject)
    if category:
        stmt = stmt.where(KnowledgePoint.category == category)
    if grade_level:
        stmt = stmt.where(KnowledgePoint.grade_level == grade_level)
    if keyword:
        stmt = stmt.where(
            (KnowledgePoint.name.ilike(f"%{keyword}%"))
            | (KnowledgePoint.description.ilike(f"%{keyword}%"))
        )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/subjects", response_model=List[str])
async def list_subjects_with_knowledge_points(db: AsyncSession = Depends(get_db)):
    """获取已有知识点的科目列表（去重）"""
    stmt = select(KnowledgePoint.subject).distinct().order_by(KnowledgePoint.subject.asc())
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


@router.get("/categories", response_model=List[str])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """获取已有知识点的分类列表（去重，非空）"""
    stmt = (
        select(KnowledgePoint.category)
        .where(KnowledgePoint.category.is_not(None))
        .where(KnowledgePoint.category != "")
        .distinct()
        .order_by(KnowledgePoint.category.asc())
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


@router.get("/grade-levels", response_model=List[str])
async def list_grade_levels(db: AsyncSession = Depends(get_db)):
    """获取已有知识点的年级列表（去重，非空）"""
    stmt = (
        select(KnowledgePoint.grade_level)
        .where(KnowledgePoint.grade_level.is_not(None))
        .where(KnowledgePoint.grade_level != "")
        .distinct()
        .order_by(KnowledgePoint.grade_level.asc())
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]


@router.get("/{point_id}", response_model=KnowledgePointOut)
async def get_knowledge_point(point_id: int, db: AsyncSession = Depends(get_db)):
    point = await db.get(KnowledgePoint, point_id)
    if not point:
        raise HTTPException(404, "知识点不存在")
    return point


@router.post("", response_model=KnowledgePointOut, status_code=201)
async def create_knowledge_point(
    payload: KnowledgePointCreate,
    _parent=Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    point = KnowledgePoint(**payload.model_dump())
    db.add(point)
    await db.commit()
    await db.refresh(point)
    return point


@router.put("/{point_id}", response_model=KnowledgePointOut)
async def update_knowledge_point(
    point_id: int,
    payload: KnowledgePointUpdate,
    _parent=Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    point = await db.get(KnowledgePoint, point_id)
    if not point:
        raise HTTPException(404, "知识点不存在")
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(point, k, v)
    await db.commit()
    await db.refresh(point)
    return point


@router.delete("/{point_id}", response_model=OkResponse)
async def delete_knowledge_point(
    point_id: int,
    _parent=Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    point = await db.get(KnowledgePoint, point_id)
    if not point:
        raise HTTPException(404, "知识点不存在")
    await db.delete(point)
    await db.commit()
    return OkResponse(message="已删除知识点")
