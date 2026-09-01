"""错题本路由"""
from collections import defaultdict
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids
from models import Child, KnowledgePoint, Question, QuestionBank, WrongQuestion, WrongQuestionReview
from schemas import (
    AcceptMatchRequest,
    BankMatchCandidateOut,
    KPMatchCandidateOut,
    MatchSuggestionsOut,
    OkResponse,
    TodayReviewItem,
    TodayReviewResponse,
    WrongQuestionCreate,
    WrongQuestionOut,
    WrongQuestionReviewCreate,
    WrongQuestionStats,
    WrongQuestionUpdate,
)
from utils.text_matcher import match_knowledge_points, match_question_bank

router = APIRouter(prefix="/api/wrong-questions", tags=["错题本"])


# ============ 艾宾浩斯间隔 ============
REVIEW_INTERVALS = [1, 3, 7, 15, 30]  # 第 N 次复习间隔天数


def _next_interval(review_count: int) -> int:
    """根据已复习次数返回下次间隔天数"""
    idx = min(review_count, len(REVIEW_INTERVALS) - 1)
    return REVIEW_INTERVALS[idx]


def _recalc_next_review(q: WrongQuestion, last_result: str) -> date:
    """根据复习结果计算下次复习日期"""
    if last_result == "correct":
        q.wrong_count = max(0, q.wrong_count - 1)
        if q.review_count >= 3:
            q.mastery_level = "mastered"
            q.status = "mastered"
            return None  # mastered 不再安排
        interval = _next_interval(q.review_count)
    elif last_result == "partial":
        interval = REVIEW_INTERVALS[max(0, min(q.review_count, len(REVIEW_INTERVALS) - 1))]
    else:  # wrong
        q.wrong_count += 1
        q.review_count = 0
        q.mastery_level = "new" if q.mastery_level == "mastered" else "learning"
        q.status = "active"
        interval = 1
    return date.today() + timedelta(days=interval)


# ============ CRUD ============
@router.get("", response_model=List[WrongQuestionOut])
async def list_wrong_questions(
    child_id: int = Query(...),
    subject: Optional[str] = None,
    error_reason: Optional[str] = None,
    mastery_level: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    stmt = select(WrongQuestion).where(WrongQuestion.child_id == child_id)
    if subject:
        stmt = stmt.where(WrongQuestion.subject == subject)
    if error_reason:
        stmt = stmt.where(WrongQuestion.error_reason == error_reason)
    if mastery_level:
        stmt = stmt.where(WrongQuestion.mastery_level == mastery_level)
    if status:
        stmt = stmt.where(WrongQuestion.status == status)
    if keyword:
        stmt = stmt.where(
            (WrongQuestion.question_text.ilike(f"%{keyword}%"))
            | (WrongQuestion.knowledge_points.as_json().ilike(f"%{keyword}%"))
        )
    stmt = stmt.options(selectinload(WrongQuestion.reviews)).order_by(WrongQuestion.updated_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=WrongQuestionOut, status_code=201)
async def create_wrong_question(
    payload: WrongQuestionCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, payload.child_id)
    child = await db.get(Child, payload.child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    q = WrongQuestion(**payload.model_dump())
    # 初始化艾宾浩斯：第一次复习在 1 天后（调用方已指定复习日期时尊重原值，如历史数据导入）
    if q.next_review_date is None:
        q.next_review_date = date.today() + timedelta(days=1)
    db.add(q)
    await db.commit()
    await db.refresh(q)
    # reload with reviews for response serialization
    result = await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == q.id).options(selectinload(WrongQuestion.reviews))
    )
    q = result.scalar_one()

    # 智能匹配建议（不写入 DB，随响应返回，前端可采纳）
    suggestions = await _run_smart_match(db, q.question_text, q.subject, q.child_id)
    out = WrongQuestionOut.model_validate(q)
    out.match_suggestions = suggestions.model_dump(mode="json")
    return out


@router.get("/{qid}", response_model=WrongQuestionOut)
async def get_wrong_question(
    qid: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    stmt = select(WrongQuestion).where(WrongQuestion.id == qid).options(selectinload(WrongQuestion.reviews))
    result = await db.execute(stmt)
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "错题不存在")
    assert_child_access(accessible, q.child_id)
    return q


@router.put("/{qid}", response_model=WrongQuestionOut)
async def update_wrong_question(
    qid: int,
    payload: WrongQuestionUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    q = await db.get(WrongQuestion, qid)
    if not q:
        raise HTTPException(404, "错题不存在")
    assert_child_access(accessible, q.child_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(q, k, v)
    await db.commit()
    await db.refresh(q)
    # reload with reviews for response serialization
    result = await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == qid).options(selectinload(WrongQuestion.reviews))
    )
    q = result.scalar_one()
    return q


@router.delete("/{qid}", response_model=OkResponse)
async def delete_wrong_question(
    qid: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    q = await db.get(WrongQuestion, qid)
    if not q:
        raise HTTPException(404, "错题不存在")
    assert_child_access(accessible, q.child_id)
    await db.delete(q)
    await db.commit()
    return OkResponse(message="已删除错题")


# ============ 智能匹配引擎 ============
async def _run_smart_match(
    db: AsyncSession,
    text: str,
    subject: str,
    child_id: int,
) -> MatchSuggestionsOut:
    """对一段错题文本运行智能匹配，返回题库 + 知识点建议。"""
    # 候选题库题目（同科目，上限 200 控制性能）
    q_stmt = (
        select(Question.id, Question.bank_id, QuestionBank.title, Question.content, Question.knowledge_point)
        .join(QuestionBank, Question.bank_id == QuestionBank.id)
        .where(QuestionBank.subject == subject)
        .limit(200)
    )
    q_result = await db.execute(q_stmt)
    bank_candidates = [tuple(row) for row in q_result.all()]

    bank_matches = match_question_bank(text, subject, bank_candidates, top_k=3)

    # 候选知识点（同科目，上限 200）
    kp_stmt = (
        select(KnowledgePoint.id, KnowledgePoint.name, KnowledgePoint.subject)
        .where(KnowledgePoint.subject == subject)
        .limit(200)
    )
    kp_result = await db.execute(kp_stmt)
    kp_candidates = [tuple(row) for row in kp_result.all()]

    kp_matches = match_knowledge_points(text, subject, kp_candidates, top_k=5)

    # 给候选 KP 挂上 Unit 信息（教材对接新 KP 体系）
    kp_ids = [m.knowledge_point_id for m in kp_matches]
    unit_info: dict = {}
    if kp_ids:
        from models import KnowledgePointUnit, TextbookUnit
        unit_rows = (await db.execute(
            select(KnowledgePointUnit.knowledge_point_id, TextbookUnit.code, TextbookUnit.title_zh)
            .join(TextbookUnit, TextbookUnit.id == KnowledgePointUnit.unit_id)
            .where(KnowledgePointUnit.knowledge_point_id.in_(kp_ids))
            .order_by(KnowledgePointUnit.knowledge_point_id)
        )).all()
        for kp_id, code, title_zh in unit_rows:
            if kp_id not in unit_info:
                unit_info[kp_id] = (code, title_zh)

    return MatchSuggestionsOut(
        bank_matches=[BankMatchCandidateOut(**m.__dict__) for m in bank_matches],
        kp_matches=[
            KPMatchCandidateOut(
                knowledge_point_id=m.knowledge_point_id,
                name=m.name,
                subject=m.subject,
                score=m.score,
                match_reasons=m.match_reasons,
                matched=True,
                unit_code=unit_info.get(m.knowledge_point_id, (None, None))[0],
                unit_title_zh=unit_info.get(m.knowledge_point_id, (None, None))[1],
            )
            for m in kp_matches
        ],
    )


@router.post("/{qid}/match", response_model=MatchSuggestionsOut)
async def reanalyze_wrong_question(
    qid: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """手动重新分析某道错题的智能匹配建议"""
    q = await db.get(WrongQuestion, qid)
    if not q:
        raise HTTPException(404, "错题不存在")
    assert_child_access(accessible, q.child_id)
    return await _run_smart_match(db, q.question_text, q.subject, q.child_id)


@router.post("/{qid}/apply-match", response_model=WrongQuestionOut)
async def apply_match(
    qid: int,
    payload: AcceptMatchRequest,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """采纳智能匹配建议：关联题库题目 + 补全知识点"""
    q = await db.get(WrongQuestion, qid)
    if not q:
        raise HTTPException(404, "错题不存在")
    assert_child_access(accessible, q.child_id)

    if payload.bank_question_id is not None:
        q.bank_question_id = payload.bank_question_id
        # 题库题的知识点自动并入错题 KP（去重）
        bank_q = await db.get(Question, payload.bank_question_id)
        if bank_q and bank_q.knowledge_point:
            kps = list(q.knowledge_points or [])
            if bank_q.knowledge_point not in kps:
                kps.append(bank_q.knowledge_point)
            q.knowledge_points = kps

    if payload.knowledge_points is not None:
        q.knowledge_points = payload.knowledge_points

    await db.commit()
    await db.refresh(q)
    result = await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == qid).options(selectinload(WrongQuestion.reviews))
    )
    q = result.scalar_one()
    return q


# ============ 统计 ============
@router.get("/stats/{child_id}", response_model=WrongQuestionStats)
async def get_stats(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    base_q = select(WrongQuestion).where(WrongQuestion.child_id == child_id)
    all_q = (await db.execute(base_q)).scalars().all()

    total = len(all_q)
    active = sum(1 for q in all_q if q.status == "active")
    mastered = sum(1 for q in all_q if q.status == "mastered")
    archived = sum(1 for q in all_q if q.status == "archived")
    mastery_rate = round(mastered / total * 100, 1) if total else 0.0

    # 按科目
    by_subject_map = defaultdict(int)
    for q in all_q:
        by_subject_map[q.subject] += 1
    by_subject = [{"subject": k, "count": v} for k, v in sorted(by_subject_map.items(), key=lambda x: -x[1])]

    # 按错因
    reason_map = {
        # 与前端表单枚举一致（WrongQuestions.vue）
        "careless": "粗心大意",
        "concept": "概念不清",
        "calculation": "计算错误",
        "reasoning": "推理错误",
        "unfamiliar": "题型陌生",
        # 兼容历史数据
        "knowledge_gap": "知识盲区",
        "misunderstanding": "理解偏差",
        "incomplete": "掌握不全",
        "other": "其他",
    }
    by_reason_map = defaultdict(int)
    for q in all_q:
        by_reason_map[q.error_reason] += 1
    by_error_reason = [
        {"reason": k, "label": reason_map.get(k, k), "count": v}
        for k, v in sorted(by_reason_map.items(), key=lambda x: -x[1])
    ]

    # 高频知识点 TOP10
    kp_map = defaultdict(int)
    for q in all_q:
        for kp in (q.knowledge_points or []):
            kp_map[kp] += 1
    top_knowledge_points = [{"knowledge_point": k, "count": v} for k, v in sorted(kp_map.items(), key=lambda x: -x[1])[:10]]

    # 近 30 天趋势
    cutoff = date.today() - timedelta(days=30)
    trend_map = defaultdict(int)
    for q in all_q:
        if q.created_at.date() >= cutoff:
            trend_map[q.created_at.date().isoformat()] += 1
    recent_trend = [
        {"date": k, "count": v}
        for k, v in sorted(trend_map.items())
    ]

    return WrongQuestionStats(
        total=total,
        active=active,
        mastered=mastered,
        archived=archived,
        mastery_rate=mastery_rate,
        by_subject=by_subject,
        by_error_reason=by_error_reason,
        top_knowledge_points=top_knowledge_points,
        recent_trend=recent_trend,
    )


# ============ 今日复习 ============
@router.get("/today/{child_id}", response_model=TodayReviewResponse)
async def get_today_reviews(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    today = date.today()
    stmt = select(WrongQuestion).where(
        WrongQuestion.child_id == child_id,
        WrongQuestion.status == "active",
        WrongQuestion.next_review_date <= today,
    ).order_by(WrongQuestion.next_review_date.asc())
    result = await db.execute(stmt)
    items = result.scalars().all()

    return TodayReviewResponse(
        total=len(items),
        items=[
            TodayReviewItem(
                id=q.id,
                subject=q.subject,
                question_text=q.question_text[:120],
                mastery_level=q.mastery_level,
                wrong_count=q.wrong_count,
                knowledge_points=q.knowledge_points or [],
            )
            for q in items
        ],
    )


@router.post("/{qid}/review", response_model=WrongQuestionOut)
async def review_wrong_question(
    qid: int,
    payload: WrongQuestionReviewCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    q = await db.get(WrongQuestion, qid)
    if not q:
        raise HTTPException(404, "错题不存在")
    assert_child_access(accessible, q.child_id)

    # 记录复习
    review = WrongQuestionReview(
        wrong_question_id=qid,
        result=payload.result,
        note=payload.note,
    )
    db.add(review)

    # 更新错题状态
    q.review_count += 1
    q.last_wrong_date = date.today()
    next_date = _recalc_next_review(q, payload.result)
    q.next_review_date = next_date

    await db.commit()
    await db.refresh(q)
    # reload with reviews for response serialization
    result = await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == qid).options(selectinload(WrongQuestion.reviews))
    )
    q = result.scalar_one()
    return q
