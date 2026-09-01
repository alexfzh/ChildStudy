"""考试记录路由"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, child_id_filter, get_accessible_child_ids
from models import Child, ChildAchievement, Exam, ExamQuestion, PointsLog, WrongQuestion
from routers.rewards import recalc_subject_rank
from schemas import (
    ExamAnalysis,
    ExamCreate,
    ExamHistoryAnalysis,
    ExamOut,
    ExamPaperAnalysis,
    ExamPaperIn,
    ExamQuestionOut,
    ExamUpdate,
    OkResponse,
)
from utils.exam_analyzer import (
    ExamLike,
    ExamQuestionLike,
    analyze_exam_history,
    analyze_exam_paper,
    analyze_single_exam,
)
from utils.grade import get_grade_at_date

router = APIRouter(prefix="/api/exams", tags=["考试记录"])


@router.get("", response_model=List[ExamOut])
async def list_exams(
    child_id: Optional[int] = None,
    subject: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(200, le=1000),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    # 如果显式传了 child_id，先校验访问权限
    if child_id is not None:
        assert_child_access(accessible, child_id)
    stmt = select(Exam).order_by(Exam.exam_date.desc(), Exam.id.desc())
    stmt = stmt.where(child_id_filter(accessible, child_id, Exam.child_id))
    if subject:
        stmt = stmt.where(Exam.subject == subject)
    if knowledge_point:
        stmt = stmt.where(Exam.knowledge_points.as_json().contains(knowledge_point))
    if start_date:
        stmt = stmt.where(Exam.exam_date >= start_date)
    if end_date:
        stmt = stmt.where(Exam.exam_date <= end_date)
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=ExamOut, status_code=201)
async def create_exam(
    payload: ExamCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, payload.child_id)
    child = await db.get(Child, payload.child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    data = payload.model_dump()
    # 自动补 grade_snapshot：若用户没传则按 GradeHistory 查询考试时的年级
    if not data.get("grade_snapshot"):
        snapshot = await get_grade_at_date(db, payload.child_id, payload.exam_date)
        data["grade_snapshot"] = snapshot
    exam = Exam(**data)
    db.add(exam)
    await db.commit()
    await db.refresh(exam)
    return exam


@router.get("/{exam_id}", response_model=ExamOut)
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)
    return exam


@router.put("/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: int,
    payload: ExamUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)
    update_data = payload.model_dump(exclude_unset=True)
    # 如果改了 exam_date 但没传新 snapshot，重查
    if "exam_date" in update_data and "grade_snapshot" not in update_data:
        update_data["grade_snapshot"] = await get_grade_at_date(db, exam.child_id, update_data["exam_date"])
    for k, v in update_data.items():
        setattr(exam, k, v)
    await db.commit()
    await db.refresh(exam)
    return exam


@router.delete("/{exam_id}", response_model=OkResponse)
async def delete_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)
    child_id = exam.child_id
    subject = exam.subject
    await db.delete(exam)
    # 级联清理关联数据（SQLite 无 FK 约束，需手动清理）
    await db.execute(
        delete(PointsLog).where(
            PointsLog.source == "exam_reward",
            PointsLog.source_id == exam_id,
        )
    )
    await db.execute(
        delete(ChildAchievement).where(ChildAchievement.exam_id == exam_id)
    )
    # DB-4：考试来源的错题（source_type="exam" 且 source_id 指向本考试）
    # 目前无 FK 且无级联，删考试后会变成"幽灵出处"错题，一并清理。
    await db.execute(
        delete(WrongQuestion).where(
            WrongQuestion.source_type == "exam",
            WrongQuestion.source_id == exam_id,
        )
    )
    # 重算该科目段位（基于剩余考试；统一入口，与 exam_reward / recalculate_ranks 同口径）
    await recalc_subject_rank(db, child_id, subject)
    await db.commit()
    return OkResponse(message="已删除考试记录")


# ============ 试卷纸面录入（AI 工具友好） ============
def _to_exam_like(exam: Exam) -> ExamLike:
    """ORM Exam → 算法 ExamLike（隔离 ORM）"""
    return ExamLike(
        id=exam.id, child_id=exam.child_id, subject=exam.subject,
        exam_name=exam.exam_name, score=exam.score, full_score=exam.full_score,
        target_score=exam.target_score, class_rank=exam.class_rank,
        grade_rank=exam.grade_rank, exam_date=exam.exam_date,
        knowledge_points=list(exam.knowledge_points or []),
        class_average=exam.class_average,
        paper_total_score=exam.paper_total_score,
        paper_actual_scored=exam.paper_actual_scored,
    )


@router.post("/{exam_id}/paper", response_model=List[ExamQuestionOut], status_code=201)
async def submit_paper(
    exam_id: int,
    payload: ExamPaperIn,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """整张试卷录入（替换式，AI 工具友好）

    - 接收整卷 sections → 逐题写入 exam_questions
    - paper_total_score 应等于 sum(max_score)，不一致返回 422
    - 同一试卷重复提交会先清空旧题再写新题
    """
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)

    # 校验：纸面满分应等于 sum(max_score)
    total_from_questions = sum(
        q.max_score for section in payload.sections for q in section.questions
    )
    if abs(total_from_questions - payload.paper_total_score) > 0.01:
        raise HTTPException(
            422,
            f"纸面满分不一致：payload.paper_total_score={payload.paper_total_score}, "
            f"实际 sum(max_score)={total_from_questions}",
        )

    # 替换式：清空旧题
    await db.execute(delete(ExamQuestion).where(ExamQuestion.exam_id == exam_id))

    # 写新题
    questions: list[ExamQuestion] = []
    for section in payload.sections:
        for q in section.questions:
            eq = ExamQuestion(
                exam_id=exam_id,
                section_name=section.section_name,
                number=q.number,
                type=q.type.value,
                max_score=q.max_score,
                scored=q.scored,
                is_correct=q.is_correct,
                knowledge_points=list(q.knowledge_points or []),
                content=q.content,
                note=q.note,
                source=payload.source,
                raw_payload=payload.raw_payload,
            )
            questions.append(eq)
            db.add(eq)

    # 更新 Exam 冗余字段（纸面聚合）
    actual_scored = sum(q.scored for q in questions)
    exam.paper_total_score = payload.paper_total_score
    exam.paper_actual_scored = actual_scored

    await db.commit()
    for q in questions:
        await db.refresh(q)
    return questions


@router.get("/{exam_id}/questions", response_model=List[ExamQuestionOut])
async def list_exam_questions(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """列出考试的所有题目（按 section_name, number 排序）"""
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)
    result = await db.execute(
        select(ExamQuestion)
        .where(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.section_name, ExamQuestion.number)
    )
    return result.scalars().all()


@router.delete("/{exam_id}/paper", response_model=OkResponse)
async def clear_paper(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """清空考试的全部题目（让 AI 重传用）"""
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)
    await db.execute(delete(ExamQuestion).where(ExamQuestion.exam_id == exam_id))
    exam.paper_total_score = None
    exam.paper_actual_scored = None
    await db.commit()
    return OkResponse(message="已清空试卷题目")


# ============ 考试分析 ============
@router.get("/analysis/history", response_model=ExamHistoryAnalysis)
async def get_exam_history_analysis(
    child_id: int = Query(...),
    subject: str = Query(...),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """历次考试趋势分析（总分维度）"""
    assert_child_access(accessible, child_id)
    result = await db.execute(
        select(Exam)
        .where(Exam.child_id == child_id, Exam.subject == subject)
        .order_by(Exam.exam_date.asc())
    )
    exams = result.scalars().all()
    history = analyze_exam_history(child_id, subject, [_to_exam_like(e) for e in exams])
    return history


@router.get("/{exam_id}/analysis", response_model=ExamAnalysis)
async def get_exam_analysis(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """单次考试总分分析"""
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)
    # 拉该孩子该科目的全部考试（含本场）作历史
    history_result = await db.execute(
        select(Exam)
        .where(Exam.child_id == exam.child_id, Exam.subject == exam.subject)
    )
    history = [_to_exam_like(e) for e in history_result.scalars().all()]
    return analyze_single_exam(_to_exam_like(exam), history)


@router.get("/{exam_id}/paper-analysis", response_model=ExamPaperAnalysis)
async def get_exam_paper_analysis(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """单次考试卷面分析（按大题/题型/KP 多维聚合）"""
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)
    result = await db.execute(
        select(ExamQuestion)
        .where(ExamQuestion.exam_id == exam_id)
        .order_by(ExamQuestion.section_name, ExamQuestion.number)
    )
    questions = [
        ExamQuestionLike(
            id=q.id, exam_id=q.exam_id, section_name=q.section_name,
            number=q.number, type=q.type, max_score=q.max_score,
            scored=q.scored, is_correct=q.is_correct,
            knowledge_points=list(q.knowledge_points or []),
            content=q.content,
        )
        for q in result.scalars().all()
    ]
    return analyze_exam_paper(exam_id, questions)
