"""Question ↔ KnowledgePoint 多对多关联路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import require_parent
from models import KnowledgePoint, Question, QuestionKnowledgePoint
from schemas import (
    OkResponse,
    QuestionKPBulkLink,
    QuestionKPLink,
)

router = APIRouter(prefix="/api/question-knowledge-points", tags=["题目-知识点关联"])


@router.get("/question/{question_id}", response_model=List[dict])
async def list_kps_for_question(question_id: int, db: AsyncSession = Depends(get_db)):
    """返回某题目关联的所有官方 KP"""
    stmt = (
        select(QuestionKnowledgePoint, KnowledgePoint)
        .join(KnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
        .where(QuestionKnowledgePoint.question_id == question_id)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "link_id": qkp.id,
            "knowledge_point_id": kp.id,
            "subject": kp.subject,
            "name": kp.name,
            "category": kp.category,
            "is_primary": qkp.is_primary,
        }
        for qkp, kp in rows
    ]


@router.get("/knowledge-point/{kp_id}", response_model=List[dict])
async def list_questions_for_kp(kp_id: int, db: AsyncSession = Depends(get_db)):
    """返回某 KP 关联的所有题目"""
    stmt = (
        select(QuestionKnowledgePoint, Question)
        .join(Question, Question.id == QuestionKnowledgePoint.question_id)
        .where(QuestionKnowledgePoint.knowledge_point_id == kp_id)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "link_id": qkp.id,
            "question_id": q.id,
            "bank_id": q.bank_id,
            "content": q.content[:120],
            "difficulty": q.difficulty,
            "is_primary": qkp.is_primary,
        }
        for qkp, q in rows
    ]


@router.post("/question/{question_id}", response_model=OkResponse)
async def link_kps_to_question(question_id: int, payload: List[QuestionKPLink], db: AsyncSession = Depends(get_db), _parent=Depends(require_parent)):
    """为题目关联 KP 标签（覆盖模式：删旧 → 插新）"""
    q = await db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "题目不存在")

    # 删旧关联
    existing = (await db.execute(
        select(QuestionKnowledgePoint).where(QuestionKnowledgePoint.question_id == question_id)
    )).scalars().all()
    for ex in existing:
        await db.delete(ex)

    # 插入新关联 —— 批量预取（修复 N+1）：一次校验全部 kp_id 存在性
    kp_ids = [link.knowledge_point_id for link in payload]
    valid_kp_ids = set((await db.execute(
        select(KnowledgePoint.id).where(KnowledgePoint.id.in_(kp_ids))
    )).scalars().all()) if kp_ids else set()
    for link in payload:
        if link.knowledge_point_id not in valid_kp_ids:
            continue
        db.add(QuestionKnowledgePoint(
            question_id=question_id,
            knowledge_point_id=link.knowledge_point_id,
            is_primary=link.is_primary,
        ))
    await db.commit()
    return OkResponse(message=f"已为题目 {question_id} 关联 {len(payload)} 个知识点")


@router.post("/bulk", response_model=OkResponse)
async def bulk_link(payload: List[QuestionKPBulkLink], db: AsyncSession = Depends(get_db), _parent=Depends(require_parent)):
    """批量关联 Question ↔ KP（覆盖模式）"""
    from sqlalchemy import delete as sa_delete

    if not payload:
        return OkResponse(message="已批量关联 0 条 Question-KP")
    # 批量预取（修复 N+1）：Question/KP 存在性 + 批量删旧，全部一次完成
    question_ids = [item.question_id for item in payload]
    valid_qids = set((await db.execute(
        select(Question.id).where(Question.id.in_(question_ids))
    )).scalars().all())
    kp_ids = list({link.knowledge_point_id for item in payload for link in item.links})
    valid_kp_ids = set((await db.execute(
        select(KnowledgePoint.id).where(KnowledgePoint.id.in_(kp_ids))
    )).scalars().all()) if kp_ids else set()
    # 批量删旧（覆盖模式；仅限存在的 Question，与原逐条语义一致）
    await db.execute(sa_delete(QuestionKnowledgePoint).where(
        QuestionKnowledgePoint.question_id.in_(list(valid_qids))
    ))

    total = 0
    for item in payload:
        if item.question_id not in valid_qids:
            continue
        for link in item.links:
            if link.knowledge_point_id not in valid_kp_ids:
                continue
            db.add(QuestionKnowledgePoint(
                question_id=item.question_id,
                knowledge_point_id=link.knowledge_point_id,
                is_primary=link.is_primary,
            ))
            total += 1
    await db.commit()
    return OkResponse(message=f"已批量关联 {total} 条 Question-KP")


@router.get("/bank/{bank_id}/summary")
async def bank_kp_summary(bank_id: int, db: AsyncSession = Depends(get_db)):
    """返回某题库的 KP 覆盖概况（每个 KP 有多少题）"""
    # 用两段查询避免 in-subquery 兼容问题
    qids_stmt = select(Question.id).where(Question.bank_id == bank_id)
    qids = [r[0] for r in (await db.execute(qids_stmt)).all()]
    if not qids:
        return []

    stmt = (
        select(KnowledgePoint.id, KnowledgePoint.name, KnowledgePoint.category, func.count(QuestionKnowledgePoint.id))
        .join(QuestionKnowledgePoint, QuestionKnowledgePoint.knowledge_point_id == KnowledgePoint.id)
        .where(QuestionKnowledgePoint.question_id.in_(qids))
        .group_by(KnowledgePoint.id, KnowledgePoint.name, KnowledgePoint.category)
        .order_by(KnowledgePoint.category, KnowledgePoint.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"knowledge_point_id": r[0], "name": r[1], "category": r[2], "question_count": r[3]}
        for r in rows
    ]
