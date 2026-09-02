"""题库系统路由：题库管理 + 题目管理 + 练习流程 + 错题推荐"""
import logging
import random
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids, require_parent
from models import (
    Child,
    Exercise,
    KnowledgePoint,
    KnowledgePointUnit,
    PointsLog,
    Question,
    QuestionBank,
    QuestionKnowledgePoint,
    TextbookUnit,
    WrongQuestion,
)
from schemas import (
    ExerciseOut,
    ExerciseRecommendation,
    ExerciseStartRequest,
    ExerciseSubmitRequest,
    KPMatchCandidateOut,
    MatchedQuestionOut,
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


# ============ KP 解析工具：错题 KP 字符串 → 新知识点体系 ============

async def _resolve_kps_by_names(
    db: AsyncSession,
    kp_names: List[str],
    subject: str,
) -> List[KnowledgePoint]:
    """把错题本里的 KP 字符串集合（同一科目）解析为 KP 对象。

    匹配策略（按优先级）：
    1) name 精确匹配
    2) name 包含/被包含的模糊匹配（处理「运算定律」vs「运算律」、「声音的高低」vs「声音的产生」等命名差异）
    3) 找不到则丢弃（不强加，避免误关联）
    """
    if not kp_names:
        return []

    # 第一轮：精确匹配
    name_set = list({n for n in kp_names if n})
    exact_stmt = select(KnowledgePoint).where(
        and_(KnowledgePoint.subject == subject, KnowledgePoint.name.in_(name_set))
    )
    kps = list((await db.execute(exact_stmt)).scalars().unique().all())

    matched_names = {kp.name for kp in kps}
    leftover = [n for n in name_set if n not in matched_names]
    if not leftover:
        return kps

    # 第二轮：模糊匹配（LIKE 包含/被包含）
    fuzzy_kps: List[KnowledgePoint] = []
    for n in leftover:
        like_stmt = select(KnowledgePoint).where(
            and_(
                KnowledgePoint.subject == subject,
                KnowledgePoint.name.like(f"%{n}%"),
            )
        )
        cands = list((await db.execute(like_stmt)).scalars().unique().all())
        if cands:
            # 优先挑名字最短的（最贴合）
            cands.sort(key=lambda k: len(k.name))
            best = cands[0]
            if best.id not in {k.id for k in kps}:
                fuzzy_kps.append(best)
    kps.extend(fuzzy_kps)
    return kps


async def _attach_unit_info(
    db: AsyncSession,
    kps: List[KnowledgePoint],
) -> dict:
    """给一批 KP 挂上 Unit 信息（code + title_zh）。

    返回 {kp_id: {"unit_code": "U3", "unit_title_zh": "..."}, ...}
    如果某个 KP 挂多个 Unit，取第一个（primary 优先）。
    """
    if not kps:
        return {}
    kp_ids = [k.id for k in kps]
    stmt = (
        select(KnowledgePointUnit.knowledge_point_id, TextbookUnit.code, TextbookUnit.title_zh, KnowledgePointUnit.relevance)
        .join(TextbookUnit, TextbookUnit.id == KnowledgePointUnit.unit_id)
        .where(KnowledgePointUnit.knowledge_point_id.in_(kp_ids))
        .order_by(KnowledgePointUnit.knowledge_point_id, KnowledgePointUnit.relevance.asc())
    )
    rows = (await db.execute(stmt)).all()
    info = {}
    for kp_id, code, title_zh, _relevance in rows:
        if kp_id not in info:  # 第一个出现的（已按 primary 排前）
            info[kp_id] = {"unit_code": code, "unit_title_zh": title_zh}
    return info


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

    # 幂等保护：同一 child + bank 若有未提交练习，直接复用，避免快速连点创建多条记录
    existing_stmt = select(Exercise).where(
        and_(
            Exercise.child_id == data.child_id,
            Exercise.bank_id == data.bank_id,
            Exercise.submitted_at.is_(None),
        )
    ).order_by(Exercise.created_at.desc())
    existing_result = await db.execute(existing_stmt)
    existing_exercise = existing_result.scalars().first()
    if existing_exercise:
        await db.refresh(existing_exercise)
        if existing_exercise.bank is None:
            existing_exercise.bank = bank
        return existing_exercise

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

        # 取主要科目
        from collections import Counter
        subj_counter = Counter(wq.subject for wq in matched_wqs)
        primary_subject = subj_counter.most_common(1)[0][0]

        # 收集错题 KP 字符串（按主科目过滤）
        kp_names = set()
        for wq in matched_wqs:
            if wq.subject == primary_subject:
                kp_names.update(wq.knowledge_points or [])

        if kp_names:
            # 第一路径：QKP 多对多 → KP id → 题目（最精准）
            resolved_kps = await _resolve_kps_by_names(db, list(kp_names), primary_subject)
            qkp_qids: List[int] = []
            if resolved_kps:
                qkp_rows = (await db.execute(
                    select(QuestionKnowledgePoint.question_id)
                    .join(KnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
                    .where(
                        and_(
                            QuestionKnowledgePoint.knowledge_point_id.in_([k.id for k in resolved_kps]),
                            KnowledgePoint.subject == primary_subject,
                        )
                    )
                )).all()
                qkp_qids = list({row[0] for row in qkp_rows})

            # 兜底：字符串字段（兼容 QKP 没覆盖的老题）
            fb_stmt = select(Question).where(
                and_(
                    Question.bank_id == data.bank_id,
                    Question.knowledge_point.in_(list(kp_names)),
                    ~Question.id.in_(qkp_qids) if qkp_qids else True,
                )
            )
            fb_qs = list((await db.execute(fb_stmt)).scalars().unique().all())
            fb_qids = [q.id for q in fb_qs]

            all_qids = list({*qkp_qids, *fb_qids})
            if all_qids:
                stmt = stmt.where(Question.id.in_(all_qids))
            else:
                # 兜底也找不到，回退到全题库随机
                pass
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
    # 显式赋值 bank 关系，避免响应序列化时 bank_title 触发 lazy load 报 greenlet 错误
    exercise.bank = bank

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

    # ====== 激励联动：积分 + 首次通关成就 ======
    # 与主提交分离：练习记录已落库，即使激励计算出错也不应回滚已提交的练习。
    # 每日上限 10 分，同一孩子同一自然日最多只能得到 10 个 practice_perfect 积分。
    points_earned = 0
    daily_points_total = 0
    daily_points_cap = 10
    new_achievements = []

    if correct_count == total and total > 0:
        try:
            today_start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
            today_logs = (await db.execute(
                select(func.coalesce(func.sum(PointsLog.points), 0)).where(
                    PointsLog.child_id == exercise.child_id,
                    PointsLog.source == "practice_perfect",
                    PointsLog.created_at >= today_start,
                )
            )).scalar_one()
            daily_points_total = int(today_logs or 0)
            logger.info("积分判定 child_id=%s today=%s cap=%s score=%s/%s",
                        exercise.child_id, daily_points_total, daily_points_cap, correct_count, total)
            if daily_points_total < daily_points_cap:
                points_earned = 1
                # 访问 bank 标题可能会触发 lazy load，提前单独查
                bank = await db.get(QuestionBank, exercise.bank_id)
                bank_title = bank.title if bank else f"题库#{exercise.bank_id}"
                db.add(PointsLog(
                    child_id=exercise.child_id,
                    points=1,
                    source="practice_perfect",
                    source_id=exercise.id,
                    description=f"练习《{bank_title}》全对 +1",
                ))
                daily_points_total += 1
                await db.commit()
                logger.info("积分发放成功 child_id=%s daily_total=%s", exercise.child_id, daily_points_total)
        except Exception as e:
            logger.warning("积分发放失败（不影响主提交）: %s", e, exc_info=True)

    # 首次通关题库：得分 ≥80% 且此前未得过同一题库的通关成就
    if score >= 80:
        try:
            from routers.rewards import get_or_create_achievement, grant_achievement
            bank = await db.get(QuestionBank, exercise.bank_id)
            bank_title = bank.title if bank else f"题库#{exercise.bank_id}"
            ach = await get_or_create_achievement(
                db,
                code=f"bank_clear_{exercise.bank_id}",
                name=f"🎯 征服《{bank_title}》",
                desc=f"首次在《{bank_title}》得分达到 80% 以上",
                cond_type="bank_clear",
                cond_val=exercise.bank_id,
            )
            ca, created = await grant_achievement(
                db, exercise.child_id, ach.id, exam_id=None
            )
            logger.info("成就判定 child_id=%s bank=%s score=%s ach_id=%s created=%s",
                        exercise.child_id, exercise.bank_id, score, ach.id, created)
            if created:
                new_achievements.append(ca)
                await db.commit()
        except Exception as e:
            logger.warning("成就解锁失败（不影响主提交）: %s", e, exc_info=True)

    # 构造响应：动 ORM 字段会被 Pydantic from_attributes 读到
    exercise.points_earned = points_earned
    exercise.daily_points_total = daily_points_total
    exercise.daily_points_cap = daily_points_cap
    exercise.new_achievements = new_achievements
    # 显式赋值 bank 关系，避免响应序列化时 bank_title 触发 lazy load 报 greenlet 错误
    if exercise.bank is None:
        exercise.bank = await db.get(QuestionBank, exercise.bank_id)
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
    # 显式 load bank 关系，避免响应序列化时 bank_title 触发 lazy load
    if exercise.bank is None:
        exercise.bank = await db.get(QuestionBank, exercise.bank_id)
    return exercise


@router.get("/exercises", response_model=List[ExerciseOut])
async def list_exercises(
    child_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """获取孩子的练习历史（含题库标题，方便看板直接用）

    排序：按交卷时间 submitted_at 倒序（未交卷的排最后，id 倒序兜底）。
    不能用 created_at：批量创建的练习 created_at 相同，会导致顺序错乱，
    且前端 dashboard 的「最近得分」取列表第一条，顺序错就会显示错分。
    """
    result = await db.execute(
        select(Exercise)
        .where(Exercise.child_id == child_id)
        .options(selectinload(Exercise.bank))
        .order_by(Exercise.submitted_at.desc().nullslast(), Exercise.id.desc())
    )
    return result.scalars().unique().all()


@router.get("/recommend/{child_id}", response_model=ExerciseRecommendation)
async def recommend_questions(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """根据错题本推荐练习题（新知识点体系版）。

    推荐三层去重合并（按优先级）：
    1) primary —— 错题 KP 字符串 → KP id → QuestionKnowledgePoint 主关联（is_primary=True 优先）
    2) kp_name_fallback —— 兜底查 Question.knowledge_point 字符串字段（兼容未建 QKP 关联的老题）
    3) unit_extend —— 错题 KP 关联的同 Unit 其他 KP 的题（同单元横向拓展）

    返回每道题带 kp_match_level / matched_kp_ids / unit_code，方便前端区分推荐来源。
    """
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
            recommended_kps=[],
            suggestion="目前错题本中没有未掌握的错题，继续保持！可以主动去题库做题来巩固。",
        )

    # 取主要科目（按错题出现次数）
    from collections import Counter
    subj_counter = Counter(wq.subject for wq in wrong_questions)
    primary_subject = subj_counter.most_common(1)[0][0]

    # 收集错题 KP 字符串集合（按主科目过滤）
    wq_kp_names = set()
    for wq in wrong_questions:
        if wq.subject == primary_subject:
            wq_kp_names.update(wq.knowledge_points or [])

    # 字符串 → KP id（同时挂 Unit 信息）
    matched_kps = await _resolve_kps_by_names(db, list(wq_kp_names), primary_subject)
    unit_info = await _attach_unit_info(db, matched_kps)

    # 同 Unit 拓展：拿到这些 KP 关联的所有 Unit 的其他 KP
    if unit_info:
        # 拿到错题 KP 关联的所有 unit_id
        unit_ids_rows = (await db.execute(
            select(KnowledgePointUnit.unit_id)
            .where(KnowledgePointUnit.knowledge_point_id.in_(list(unit_info.keys())))
        )).all()
        unit_ids = list({row[0] for row in unit_ids_rows})
        # 同 Unit 其他 KP（排除自身）
        if unit_ids:
            extend_kp_stmt = (
                select(KnowledgePoint)
                .join(KnowledgePointUnit, KnowledgePointUnit.knowledge_point_id == KnowledgePoint.id)
                .where(
                    and_(
                        KnowledgePointUnit.unit_id.in_(unit_ids),
                        KnowledgePoint.subject == primary_subject,
                        ~KnowledgePoint.id.in_(list(unit_info.keys())),
                    )
                )
                .limit(10)
            )
            extend_kps = list((await db.execute(extend_kp_stmt)).scalars().unique().all())
            extend_unit_info = await _attach_unit_info(db, extend_kps)
        else:
            extend_kps = []
            extend_unit_info = {}
    else:
        extend_kps = []
        extend_unit_info = {}

    # ── 第一层：primary（QKP 主关联）──
    primary_qids: List[int] = []
    primary_qid_to_meta: dict = {}  # qid -> {matched_kp_ids, matched_kp_names, unit_code, unit_title_zh}
    if matched_kps:
        primary_stmt = (
            select(
                QuestionKnowledgePoint.question_id,
                QuestionKnowledgePoint.knowledge_point_id,
                QuestionKnowledgePoint.is_primary,
                KnowledgePoint.name,
            )
            .join(KnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
            .where(
                and_(
                    QuestionKnowledgePoint.knowledge_point_id.in_([k.id for k in matched_kps]),
                    KnowledgePoint.subject == primary_subject,
                )
            )
            .order_by(QuestionKnowledgePoint.is_primary.desc())
        )
        rows = (await db.execute(primary_stmt)).all()
        for qid, kp_id, _is_primary, kp_name in rows:
            if qid not in primary_qid_to_meta:
                primary_qid_to_meta[qid] = {
                    "matched_kp_ids": [kp_id],
                    "matched_kp_names": [kp_name],
                    "unit_code": (unit_info.get(kp_id) or {}).get("unit_code"),
                    "unit_title_zh": (unit_info.get(kp_id) or {}).get("unit_title_zh"),
                }
                primary_qids.append(qid)
            else:
                # 同一题关联多 KP：累加
                meta = primary_qid_to_meta[qid]
                if kp_id not in meta["matched_kp_ids"]:
                    meta["matched_kp_ids"].append(kp_id)
                    meta["matched_kp_names"].append(kp_name)

    # ── 第二层：unit_extend（拓展 KP 的 QKP 题）──
    extend_qids: List[int] = []
    extend_qid_to_meta: dict = {}
    if extend_kps:
        extend_stmt = (
            select(
                QuestionKnowledgePoint.question_id,
                QuestionKnowledgePoint.knowledge_point_id,
                KnowledgePoint.name,
            )
            .join(KnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
            .where(
                and_(
                    QuestionKnowledgePoint.knowledge_point_id.in_([k.id for k in extend_kps]),
                    KnowledgePoint.subject == primary_subject,
                )
            )
            .limit(15)
        )
        rows = (await db.execute(extend_stmt)).all()
        for qid, kp_id, kp_name in rows:
            if qid in primary_qid_to_meta:
                continue  # 已 primary 覆盖
            if qid not in extend_qid_to_meta:
                extend_qid_to_meta[qid] = {
                    "matched_kp_ids": [kp_id],
                    "matched_kp_names": [kp_name],
                    "unit_code": (extend_unit_info.get(kp_id) or {}).get("unit_code"),
                    "unit_title_zh": (extend_unit_info.get(kp_id) or {}).get("unit_title_zh"),
                }
                extend_qids.append(qid)

    # ── 第三层：kp_name_fallback（兜底查 Question.knowledge_point 字符串字段）──
    fallback_qids: List[int] = []
    fallback_qid_to_meta: dict = {}
    if wq_kp_names:
        fb_stmt = select(Question).where(
            and_(
                Question.knowledge_point.in_(list(wq_kp_names)),
                ~Question.id.in_(primary_qids + extend_qids),
            )
        ).limit(10)
        fb_qs = list((await db.execute(fb_stmt)).scalars().unique().all())
        for q in fb_qs:
            # 用字符串本身匹配 KP（取第一个匹配的 KP id）
            kp_name = q.knowledge_point
            kp_id_match = next((k.id for k in matched_kps if k.name == kp_name), None)
            fallback_qids.append(q.id)
            fallback_qid_to_meta[q.id] = {
                "matched_kp_ids": [kp_id_match] if kp_id_match else [],
                "matched_kp_names": [kp_name] if kp_name else [],
                "unit_code": (unit_info.get(kp_id_match) or {}).get("unit_code") if kp_id_match else None,
                "unit_title_zh": (unit_info.get(kp_id_match) or {}).get("unit_title_zh") if kp_id_match else None,
            }

    # ── 拼装 MatchedQuestionOut ──
    all_qids = primary_qids + extend_qids + fallback_qids
    if not all_qids:
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
            matched_questions=[],
            recommended_kps=[
                KPMatchCandidateOut(
                    knowledge_point_id=k.id,
                    name=k.name,
                    subject=k.subject,
                    score=0.0,
                    matched=True,
                    unit_code=(unit_info.get(k.id) or {}).get("unit_code"),
                    unit_title_zh=(unit_info.get(k.id) or {}).get("unit_title_zh"),
                )
                for k in matched_kps
            ],
            suggestion=f"识别到错题 KP：{'、'.join(k.name for k in matched_kps[:5])}，但题库里暂无对应的练习题，可先去录入题目。",
        )

    q_meta_map = {q.id: q for q in (await db.execute(
        select(Question).where(Question.id.in_(all_qids))
    )).scalars().unique().all()}

    def _to_out(qid: int, level: str, meta: dict) -> MatchedQuestionOut:
        q = q_meta_map.get(qid)
        if not q:
            return None
        return MatchedQuestionOut(
            id=q.id,
            bank_id=q.bank_id,
            knowledge_point=q.knowledge_point,
            difficulty=q.difficulty,
            content=q.content,
            options=q.options or [],
            explanation=q.explanation,
            kp_match_level=level,
            matched_kp_ids=meta["matched_kp_ids"],
            matched_kp_names=meta["matched_kp_names"],
            unit_code=meta["unit_code"],
            unit_title_zh=meta["unit_title_zh"],
        )

    matched = []
    for qid in primary_qids:
        out = _to_out(qid, "primary", primary_qid_to_meta[qid])
        if out:
            matched.append(out)
    for qid in extend_qids:
        out = _to_out(qid, "unit_extend", extend_qid_to_meta[qid])
        if out:
            matched.append(out)
    for qid in fallback_qids:
        out = _to_out(qid, "kp_name_fallback", fallback_qid_to_meta[qid])
        if out:
            matched.append(out)

    # 截断到 20 条
    matched = matched[:20]

    # ── 建议文案 ──
    primary_kp_str = "、".join(k.name for k in matched_kps[:3])
    unit_codes = sorted({(unit_info.get(k.id) or {}).get("unit_code") for k in matched_kps if (unit_info.get(k.id) or {}).get("unit_code")})
    unit_hint = f"（涉及单元：{'、'.join(unit_codes)}）" if unit_codes else ""
    suggestion = (
        f"你最近在「{primary_kp_str}」等知识点还有薄弱，"
        f"已用 QKP 多对多表定位 {len(primary_qids)} 道主 KP 题、"
        f"{len(extend_qids)} 道同 Unit 拓展题、{len(fallback_qids)} 道兜底题"
        f"{unit_hint}，推荐做 {min(len(matched), 5)} 道巩固。"
    )

    recommended_kps = [
        KPMatchCandidateOut(
            knowledge_point_id=k.id,
            name=k.name,
            subject=k.subject,
            score=0.0,
            matched=True,
            unit_code=(unit_info.get(k.id) or {}).get("unit_code"),
            unit_title_zh=(unit_info.get(k.id) or {}).get("unit_title_zh"),
        )
        for k in matched_kps
    ]

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
        recommended_kps=recommended_kps,
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
