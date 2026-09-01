"""教材版本 / 教材单元路由"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Question, QuestionUnit, TextbookUnit, TextbookVersion
from schemas import (
    OkResponse,
    QuestionUnitLink,
    TextbookUnitOut,
    TextbookVersionOut,
)

router = APIRouter(prefix="/api/textbook", tags=["教材章节"])


# ============ 教材版本 CRUD ============

@router.get("/versions", response_model=List[TextbookVersionOut])
async def list_versions(
    grade: Optional[str] = None,
    subject: Optional[str] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TextbookVersion)
    if grade:
        stmt = stmt.where(TextbookVersion.grade == grade)
    if subject:
        stmt = stmt.where(TextbookVersion.subject == subject)
    if is_active is not None:
        stmt = stmt.where(TextbookVersion.is_active == is_active)
    stmt = stmt.order_by(TextbookVersion.grade, TextbookVersion.subject, TextbookVersion.id)
    result = await db.execute(stmt)
    return result.scalars().unique().all()


@router.get("/versions/{version_id}", response_model=TextbookVersionOut)
async def get_version(version_id: int, db: AsyncSession = Depends(get_db)):
    v = await db.get(TextbookVersion, version_id)
    if not v:
        raise HTTPException(404, "教材版本不存在")
    return v


@router.get("/versions/{version_id}/units", response_model=List[TextbookUnitOut])
async def list_units(version_id: int, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(TextbookUnit)
        .where(TextbookUnit.version_id == version_id)
        .order_by(TextbookUnit.unit_number)
    )
    result = await db.execute(stmt)
    return result.scalars().unique().all()


@router.get("/units/{unit_id}", response_model=TextbookUnitOut)
async def get_unit(unit_id: int, db: AsyncSession = Depends(get_db)):
    u = await db.get(TextbookUnit, unit_id)
    if not u:
        raise HTTPException(404, "教材单元不存在")
    return u


# ============ 题目 ↔ 单元 多对多关联 ============

@router.get("/questions/{question_id}/units")
async def get_question_units(question_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(QuestionUnit).where(QuestionUnit.question_id == question_id)
    result = await db.execute(stmt)
    links = result.scalars().unique().all()
    return [
        {"id": link.id, "unit_id": link.unit_id, "relevance": link.relevance, "created_at": link.created_at}
        for link in links
    ]


@router.post("/questions/{question_id}/units", response_model=OkResponse)
async def link_question_to_units(question_id: int, payload: list[QuestionUnitLink], db: AsyncSession = Depends(get_db)):
    q = await db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "题目不存在")
    # 删除已有，再插入（简单替换）
    existing = (await db.execute(
        select(QuestionUnit).where(QuestionUnit.question_id == question_id)
    )).scalars().all()
    for ex in existing:
        await db.delete(ex)
    for link in payload:
        qu = QuestionUnit(question_id=question_id, unit_id=link.unit_id, relevance=link.relevance)
        db.add(qu)
    await db.commit()
    return OkResponse(message=f"已为题目 {question_id} 关联 {len(payload)} 个单元")


@router.post("/units/{unit_id}/questions", response_model=List[int])
async def list_question_ids_for_unit(unit_id: int, db: AsyncSession = Depends(get_db)):
    """返回某单元关联的所有题目 id 列表（用于按单元练习组卷）"""
    stmt = select(QuestionUnit.question_id).where(QuestionUnit.unit_id == unit_id)
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]
