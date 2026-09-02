"""题库分组 + 题目 CRUD"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_parent
from models import (
    Question,
    QuestionBank,
)
from schemas import (
    OkResponse,
    QuestionBankCreate,
    QuestionBankOut,
    QuestionBankUpdate,
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
)

router = APIRouter(prefix="/api/question-banks", tags=["题库系统"])

logger = logging.getLogger("childstudy")


# ============ 题库分组 CRUD ============

@router.get("", response_model=List[QuestionBankOut])
async def list_banks(
    grade: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """列出题库分组，支持按年级/科目筛选"""
    stmt = select(QuestionBank).where(QuestionBank.is_active)
    if grade:
        stmt = stmt.where(QuestionBank.grade == grade)
    if subject:
        stmt = stmt.where(QuestionBank.subject == subject)
    stmt = stmt.order_by(QuestionBank.grade, QuestionBank.subject, QuestionBank.id)

    result = await db.execute(stmt)
    banks = result.scalars().unique().all()

    counts = {}
    if banks:
        count_stmt = (
            select(Question.bank_id, func.count(Question.id))
            .where(Question.bank_id.in_([b.id for b in banks]))
            .group_by(Question.bank_id)
        )
        count_result = await db.execute(count_stmt)
        counts = {row[0]: row[1] for row in count_result.all()}

    return [
        {
            "id": b.id,
            "grade": b.grade,
            "subject": b.subject,
            "title": b.title,
            "description": b.description,
            "is_active": b.is_active,
            "question_count": counts.get(b.id, 0),
            "created_at": b.created_at,
            "updated_at": b.updated_at,
        }
        for b in banks
    ]


@router.post("", response_model=QuestionBankOut)
async def create_bank(
    data: QuestionBankCreate,
    db: AsyncSession = Depends(get_db),
    _parent=Depends(require_parent),
):
    """创建题库分组"""
    bank = QuestionBank(**data.model_dump())
    db.add(bank)
    await db.commit()
    await db.refresh(bank)
    return {**bank.__dict__, "question_count": 0}


# ============ 题库分组 CRUD（/{bank_id} 路由，放在 exercises 之后） ============

@router.get("/{bank_id}", response_model=QuestionBankOut)
async def get_bank(bank_id: int, db: AsyncSession = Depends(get_db)):
    """获取题库分组详情"""
    bank = await db.get(QuestionBank, bank_id)
    if not bank:
        raise HTTPException(404, "题库分组不存在")
    count = (await db.execute(
        select(func.count(Question.id)).where(Question.bank_id == bank_id)
    )).scalar_one()
    return {**bank.__dict__, "question_count": count}


@router.put("/{bank_id}", response_model=QuestionBankOut)
async def update_bank(bank_id: int, data: QuestionBankUpdate, db: AsyncSession = Depends(get_db)):
    """更新题库分组"""
    bank = await db.get(QuestionBank, bank_id)
    if not bank:
        raise HTTPException(404, "题库分组不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(bank, k, v)
    await db.commit()
    await db.refresh(bank)
    count = (await db.execute(
        select(func.count(Question.id)).where(Question.bank_id == bank_id)
    )).scalar_one()
    return {**bank.__dict__, "question_count": count}


@router.delete("/{bank_id}", response_model=OkResponse)
async def delete_bank(bank_id: int, db: AsyncSession = Depends(get_db)):
    """删除题库分组（级联删除题目）"""
    bank = await db.get(QuestionBank, bank_id)
    if not bank:
        raise HTTPException(404, "题库分组不存在")
    await db.delete(bank)
    await db.commit()
    return OkResponse(message="删除成功")


# ============ 题目 CRUD ============

@router.get("/{bank_id}/questions", response_model=List[QuestionOut])
async def list_questions(
    bank_id: int,
    knowledge_point: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """列出题库中的题目"""
    bank = await db.get(QuestionBank, bank_id)
    if not bank:
        raise HTTPException(404, "题库分组不存在")

    stmt = select(Question).where(Question.bank_id == bank_id)
    if knowledge_point:
        stmt = stmt.where(Question.knowledge_point == knowledge_point)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    stmt = stmt.order_by(Question.id)

    result = await db.execute(stmt)
    return result.scalars().unique().all()


@router.post("/{bank_id}/questions", response_model=QuestionOut)
async def create_question(bank_id: int, data: QuestionCreate, db: AsyncSession = Depends(get_db)):
    """向题库添加题目"""
    bank = await db.get(QuestionBank, bank_id)
    if not bank:
        raise HTTPException(404, "题库分组不存在")

    q = Question(bank_id=bank_id, **data.model_dump(exclude={"bank_id"}))
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q


@router.put("/{bank_id}/questions/{question_id}", response_model=QuestionOut)
async def update_question(bank_id: int, question_id: int, data: QuestionUpdate, db: AsyncSession = Depends(get_db)):
    """更新题目"""
    q = await db.get(Question, question_id)
    if not q or q.bank_id != bank_id:
        raise HTTPException(404, "题目不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(q, k, v)
    await db.commit()
    await db.refresh(q)
    return q


@router.delete("/{bank_id}/questions/{question_id}", response_model=OkResponse)
async def delete_question(bank_id: int, question_id: int, db: AsyncSession = Depends(get_db)):
    """删除题目"""
    q = await db.get(Question, question_id)
    if not q or q.bank_id != bank_id:
        raise HTTPException(404, "题目不存在")
    await db.delete(q)
    await db.commit()
    return OkResponse(message="删除成功")
