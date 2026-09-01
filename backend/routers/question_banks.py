"""题库系统路由：题库管理 + 题目管理 + 练习流程 + 错题推荐"""
import logging
import random
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids, require_parent
from models import Child, Exercise, Question, QuestionBank, WrongQuestion
from schemas import (
    ExerciseOut,
    ExerciseRecommendation,
    ExerciseStartRequest,
    ExerciseSubmitRequest,
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


# ============ 练习流程（放在 /{bank_id} 之前，避免路由冲突） ============

@router.post("/exercises/start", response_model=ExerciseOut)
async def start_exercise(
    data: ExerciseStartRequest,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """开始一次练习（手动组卷 或 错题推荐）"""
    assert_child_access(accessible, data.child_id)
    bank = await db.get(QuestionBank, data.bank_id)
    if not bank:
        raise HTTPException(404, "题库分组不存在")

    child = await db.get(Child, data.child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    stmt = select(Question).where(Question.bank_id == data.bank_id)

    if data.mode == "recommend" and data.wrong_question_ids:
        wqs = await db.execute(
            select(WrongQuestion).where(
                and_(
                    WrongQuestion.id.in_(data.wrong_question_ids),
                    WrongQuestion.child_id == data.child_id,
                )
            )
        )
        matched_wqs = wqs.scalars().unique().all()
        if not matched_wqs:
            raise HTTPException(400, "没有匹配的错题记录")

        kps = set()
        for wq in matched_wqs:
            kps.update(wq.knowledge_points or [])

        if kps:
            conditions = [Question.knowledge_point.in_(list(kps))]
            stmt = stmt.where(*conditions)
    else:
        if data.knowledge_points:
            stmt = stmt.where(Question.knowledge_point.in_(data.knowledge_points))
        if data.difficulty:
            stmt = stmt.where(Question.difficulty == data.difficulty)

    result = await db.execute(stmt)
    all_questions = result.scalars().unique().all()

    if not all_questions:
        raise HTTPException(404, "题库中暂无符合条件的题目，请先添加题目")

    count = min(data.count, len(all_questions))
    selected = random.sample(all_questions, count)

    questions_snapshot = [
        {
            "id": q.id,
            "knowledge_point": q.knowledge_point,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "content": q.content,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
        }
        for q in selected
    ]

    exercise = Exercise(
        child_id=data.child_id,
        bank_id=data.bank_id,
        questions=questions_snapshot,
        answers=[],
        total_questions=count,
        correct_count=0,
        score=None,
        submitted_at=None,
    )
    db.add(exercise)
    await db.commit()
    await db.refresh(exercise)

    return exercise


@router.post("/exercises/{exercise_id}/submit", response_model=ExerciseOut)
async def submit_exercise(
    exercise_id: int,
    data: ExerciseSubmitRequest,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """提交练习答案，自动批改"""
    exercise = await db.get(Exercise, exercise_id)
    if not exercise:
        raise HTTPException(404, "练习记录不存在")
    assert_child_access(accessible, exercise.child_id)
    if exercise.submitted_at:
        raise HTTPException(400, "练习已提交")

    correct_map = {q["id"]: q["correct_answer"] for q in exercise.questions}

    answers = []
    correct_count = 0
    for ans in data.answers:
        qid = ans.get("question_id")
        selected = ans.get("selected", "")
        is_correct = (selected == correct_map.get(qid))
        if is_correct:
            correct_count += 1
        answers.append({
            "question_id": qid,
            "selected": selected,
            "is_correct": is_correct,
        })

    total = exercise.total_questions
    score = round(correct_count / total * 100, 1) if total > 0 else 0.0

    exercise.answers = answers
    exercise.correct_count = correct_count
    exercise.score = score
    exercise.submitted_at = datetime.now(timezone.utc)
    if data.time_spent is not None:
        exercise.time_spent = data.time_spent

    question_map = {q["id"]: q for q in exercise.questions}

    # 练习结果与联动更新放同一事务：任一失败整体回滚并显式报错，
    # 避免"练习已提交但进度/积分静默丢失"的假性成功（CQ-4 修复）。
    try:
        from routers.study_progress import update_progress_on_exercise
        await update_progress_on_exercise(db, exercise.child_id, exercise)
        from routers.kp_progress import update_kp_progress_on_exercise
        await update_kp_progress_on_exercise(db, exercise.child_id, exercise)
        # 自动归错题本：答错的题自动创建/更新错题记录（"有智慧"的联动）
        for ans in answers:
            if not ans["is_correct"]:
                qid = ans.get("question_id")
                q_info = question_map.get(qid)
                if not q_info:
                    continue
                # 查是否已有关联该题库题的错题记录
                existing = (await db.execute(
                    select(WrongQuestion).where(
                        WrongQuestion.child_id == exercise.child_id,
                        WrongQuestion.bank_question_id == qid,
                        WrongQuestion.status != "archived",
                    )
                )).scalar_one_or_none()
                if existing:
                    existing.wrong_count += 1
                    existing.review_count = 0
                    existing.mastery_level = (
                        "new" if existing.mastery_level == "mastered" else "learning"
                    )
                    existing.status = "active"
                    existing.last_wrong_date = date.today()
                    existing.next_review_date = date.today() + timedelta(days=1)
                    kp = q_info.get("knowledge_point")
                    if kp:
                        kps = list(existing.knowledge_points or [])
                        if kp not in kps:
                            kps.append(kp)
                        existing.knowledge_points = kps
                else:
                    bank = await db.get(QuestionBank, exercise.bank_id)
                    subject = bank.subject if bank else "unknown"
                    kp = q_info.get("knowledge_point")
                    kps = [kp] if kp else []
                    db.add(WrongQuestion(
                        child_id=exercise.child_id,
                        source_type="bank",
                        source_id=exercise.id,
                        bank_question_id=qid,
                        subject=subject,
                        question_text=q_info.get("content", ""),
                        correct_answer=q_info.get("correct_answer", ""),
                        knowledge_points=kps,
                        difficulty=q_info.get("difficulty", "normal"),
                        wrong_count=1,
                        last_wrong_date=date.today(),
                        next_review_date=date.today() + timedelta(days=1),
                        status="active",
                        mastery_level="new",
                    ))
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("练习提交联动失败，已整体回滚: exercise_id=%s", exercise_id)
        await db.rollback()
        raise HTTPException(500, "练习提交失败（进度联动异常），请重试") from e

    await db.refresh(exercise)
    return exercise


@router.get("/exercises/{exercise_id}", response_model=ExerciseOut)
async def get_exercise(
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """获取练习结果"""
    exercise = await db.get(Exercise, exercise_id)
    if not exercise:
        raise HTTPException(404, "练习记录不存在")
    assert_child_access(accessible, exercise.child_id)
    return exercise


@router.get("/exercises", response_model=List[ExerciseOut])
async def list_exercises(
    child_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """获取孩子的练习历史"""
    result = await db.execute(
        select(Exercise)
        .where(Exercise.child_id == child_id)
        .order_by(Exercise.created_at.desc())
    )
    return result.scalars().unique().all()


@router.get("/recommend/{child_id}", response_model=ExerciseRecommendation)
async def recommend_questions(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """根据错题本推荐练习题"""
    assert_child_access(accessible, child_id)
    wq_stmt = (
        select(WrongQuestion)
        .where(
            and_(
                WrongQuestion.child_id == child_id,
                WrongQuestion.status.in_(["active", "learning"]),
            )
        )
        .order_by(WrongQuestion.updated_at.desc())
        .limit(10)
    )
    wq_result = await db.execute(wq_stmt)
    wrong_questions = wq_result.scalars().unique().all()

    if not wrong_questions:
        return ExerciseRecommendation(
            wrong_questions=[],
            matched_questions=[],
            suggestion="目前错题本中没有未掌握的错题，继续保持！可以主动去题库做题来巩固。",
        )

    kp_set = set()
    for wq in wrong_questions:
        kp_set.update(wq.knowledge_points or [])

    matched = []
    if kp_set:
        q_stmt = select(Question).where(Question.knowledge_point.in_(list(kp_set))).limit(20)
        q_result = await db.execute(q_stmt)
        matched = [
            {
                "id": q.id,
                "bank_id": q.bank_id,
                "knowledge_point": q.knowledge_point,
                "difficulty": q.difficulty,
                "content": q.content,
                "options": q.options,
                "explanation": q.explanation,
            }
            for q in q_result.scalars().unique().all()
        ]

    kp_str = "、".join(list(kp_set)[:3])
    suggestion = f"你最近在「{kp_str}」等知识点上还有错题，推荐做 {min(len(matched), 5)} 道相关练习巩固。"

    return ExerciseRecommendation(
        wrong_questions=[
            {
                "id": wq.id,
                "subject": wq.subject,
                "question_text": wq.question_text,
                "knowledge_points": wq.knowledge_points,
                "mastery_level": wq.mastery_level,
            }
            for wq in wrong_questions
        ],
        matched_questions=matched,
        suggestion=suggestion,
    )


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
