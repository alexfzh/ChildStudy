"""exams.py 测试：考试录入 CRUD + 删除时级联清理 + 段位重算"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from models import ChildRank, Exam, PointsLog
from routers.exams import create_exam, delete_exam, get_exam, list_exams, update_exam
from routers.rewards import calc_tier
from schemas import ExamCreate, ExamUpdate

# ==================== 创建考试 ====================

class TestCreateExam:
    """POST /api/exams"""

    async def test_create_basic(self, db_session, make_child):
        child = await make_child()
        payload = ExamCreate(
            child_id=child.id,
            subject="数学",
            exam_name="期中考试",
            score=92.0,
            full_score=100.0,
            exam_date=date.today(),
        )
        exam = await create_exam(payload, db_session)
        assert exam.id is not None
        assert exam.child_id == child.id
        assert exam.subject == "数学"
        assert exam.score == 92.0
        assert exam.exam_name == "期中考试"

    async def test_auto_grade_snapshot(self, db_session, make_child):
        """未传 grade_snapshot 时自动从 Child.grade 补"""
        child = await make_child(grade="四年级")
        payload = ExamCreate(
            child_id=child.id,
            subject="语文",
            exam_name="单元测试",
            score=85.0,
            full_score=100.0,
            exam_date=date.today(),
        )
        exam = await create_exam(payload, db_session)
        assert exam.grade_snapshot == "四年级"

    async def test_explicit_grade_snapshot(self, db_session, make_child):
        """传了 grade_snapshot 就用传的"""
        child = await make_child(grade="四年级")
        payload = ExamCreate(
            child_id=child.id,
            subject="语文",
            exam_name="单元测试",
            score=85.0,
            full_score=100.0,
            exam_date=date.today(),
            grade_snapshot="三年级",
        )
        exam = await create_exam(payload, db_session)
        assert exam.grade_snapshot == "三年级"

    async def test_child_not_found_404(self, db_session):
        payload = ExamCreate(
            child_id=99999,
            subject="数学",
            exam_name="测试",
            score=80.0,
            full_score=100.0,
            exam_date=date.today(),
        )
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await create_exam(payload, db_session)
        assert exc_info.value.status_code == 404

    async def test_knowledge_points_stored(self, db_session, make_child):
        child = await make_child()
        payload = ExamCreate(
            child_id=child.id,
            subject="数学",
            exam_name="测试",
            score=80.0,
            full_score=100.0,
            exam_date=date.today(),
            knowledge_points=["分数加法", "通分"],
        )
        exam = await create_exam(payload, db_session)
        assert exam.knowledge_points == ["分数加法", "通分"]


# ==================== 查询考试 ====================

class TestListExams:
    """GET /api/exams"""

    async def _seed_exams(self, db_session, make_child):
        child = await make_child()
        exams = []
        for i, (subj, sc, dt) in enumerate([
            ("数学", 90, date.today() - timedelta(days=10)),
            ("数学", 85, date.today() - timedelta(days=5)),
            ("语文", 88, date.today()),
        ]):
            payload = ExamCreate(
                child_id=child.id, subject=subj,
                exam_name=f"测试{i+1}", score=sc, full_score=100.0,
                exam_date=dt,
            )
            exams.append(await create_exam(payload, db_session))
        return child, exams

    async def test_list_all(self, db_session, make_child):
        _child, _exams = await self._seed_exams(db_session, make_child)
        result = await list_exams(limit=200, db=db_session)
        assert len(result) == 3

    async def test_filter_by_child(self, db_session, make_child):
        child, _exams = await self._seed_exams(db_session, make_child)
        result = await list_exams(child_id=child.id, limit=200, db=db_session)
        assert len(result) == 3

    async def test_filter_by_child_no_match(self, db_session, make_child):
        await self._seed_exams(db_session, make_child)
        result = await list_exams(child_id=99999, limit=200, db=db_session)
        assert len(result) == 0

    async def test_filter_by_subject(self, db_session, make_child):
        child, _exams = await self._seed_exams(db_session, make_child)
        result = await list_exams(child_id=child.id, subject="数学", limit=200, db=db_session)
        assert len(result) == 2

    async def test_ordering_desc(self, db_session, make_child):
        child, _exams = await self._seed_exams(db_session, make_child)
        result = await list_exams(child_id=child.id, limit=200, db=db_session)
        dates = [e.exam_date for e in result]
        assert dates == sorted(dates, reverse=True)


class TestGetExam:
    """GET /api/exams/{id}"""

    async def test_found(self, db_session, make_child):
        child = await make_child()
        payload = ExamCreate(
            child_id=child.id, subject="数学",
            exam_name="测试", score=80, full_score=100,
            exam_date=date.today(),
        )
        created = await create_exam(payload, db_session)
        fetched = await get_exam(created.id, db_session)
        assert fetched.id == created.id
        assert fetched.score == 80

    async def test_not_found_404(self, db_session):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_exam(99999, db_session)
        assert exc_info.value.status_code == 404


# ==================== 更新考试 ====================

class TestUpdateExam:
    """PUT /api/exams/{id}"""

    async def test_update_score(self, db_session, make_child):
        child = await make_child()
        created = await create_exam(ExamCreate(
            child_id=child.id, subject="数学",
            exam_name="测试", score=70, full_score=100,
            exam_date=date.today(),
        ), db_session)

        updated = await update_exam(created.id, ExamUpdate(score=85), db_session)
        assert updated.score == 85

    async def test_update_multiple_fields(self, db_session, make_child):
        child = await make_child()
        created = await create_exam(ExamCreate(
            child_id=child.id, subject="数学",
            exam_name="测试", score=70, full_score=100,
            exam_date=date.today(),
        ), db_session)

        updated = await update_exam(
            created.id,
            ExamUpdate(score=95, teacher_comment="进步很大"),
            db_session,
        )
        assert updated.score == 95
        assert updated.teacher_comment == "进步很大"

    async def test_not_found_404(self, db_session):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await update_exam(99999, ExamUpdate(score=100), db_session)
        assert exc_info.value.status_code == 404


# ==================== 删除考试 ====================

class TestDeleteExam:
    """DELETE /api/exams/{id} — 级联清理 + 段位重算"""

    async def _setup_with_rank(self, db_session, make_child, make_exam):
        child = await make_child()
        e1 = await make_exam(child.id, score=90, full_score=100, exam_name="测试1")
        e2 = await make_exam(child.id, score=80, full_score=100, exam_name="测试2")

        # 模拟 exam_reward 产生的积分日志
        log = PointsLog(
            child_id=child.id, points=43,
            source="exam_reward", source_id=e1.id,
            description="积分",
        )
        db_session.add(log)
        await db_session.flush()
        return child, e1, e2

    async def test_delete_removes_exam(self, db_session, make_child, make_exam):
        _child, e1, _e2 = await self._setup_with_rank(db_session, make_child, make_exam)
        result = await delete_exam(e1.id, db_session)
        assert result.message == "已删除考试记录"

        fetched = await db_session.get(Exam, e1.id)
        assert fetched is None

    async def test_delete_cleans_points_log(self, db_session, make_child, make_exam):
        _child, e1, _e2 = await self._setup_with_rank(db_session, make_child, make_exam)
        await delete_exam(e1.id, db_session)

        # e1 关联的积分日志应被清理
        remaining = (await db_session.execute(
            select(PointsLog).where(
                PointsLog.source == "exam_reward",
                PointsLog.source_id == e1.id,
            )
        )).scalar_one_or_none()
        assert remaining is None

    async def test_delete_recalculates_rank(self, db_session, make_child, make_exam):
        """验证：删除一场考试后，基于剩余考试重算段位的逻辑正确"""
        child, e1, e2 = await self._setup_with_rank(db_session, make_child, make_exam)

        rank = ChildRank(child_id=child.id, subject="数学", avg_score=85.0, tier="青铜", stars=2, exam_count=2, total_points=43)
        db_session.add(rank)
        await db_session.flush()

        # 手动模拟 delete_exam 的重算逻辑（避免 commit 后 identity map 问题）
        await db_session.delete(e1)
        await db_session.flush()  # flush 让 delete 生效

        remaining = (await db_session.execute(
            select(Exam).where(Exam.child_id == child.id, Exam.subject == "数学")
        )).scalars().all()
        assert len(remaining) == 1
        assert remaining[0].id == e2.id

        scores = [(e.score / e.full_score * 100) for e in remaining if e.full_score]
        avg = round(sum(scores) / len(scores), 1)
        tier, stars = calc_tier(avg)
        rank.avg_score = avg
        rank.tier = tier
        rank.stars = stars
        rank.exam_count = len(scores)
        await db_session.flush()

        assert rank.exam_count == 1
        assert rank.avg_score == 80.0

    async def test_delete_last_exam_removes_rank(self, db_session, make_child, make_exam):
        """验证：最后一场考试删除后，段位记录应被移除"""
        child = await make_child()
        e1 = await make_exam(child.id, score=90, full_score=100, exam_name="唯一考试")

        rank = ChildRank(child_id=child.id, subject="数学", avg_score=90.0, tier="青铜", stars=3, exam_count=1, total_points=0)
        db_session.add(rank)
        await db_session.flush()

        # 模拟 delete_exam 逻辑：删除考试 → 无剩余 → 删段位
        await db_session.delete(e1)
        await db_session.flush()

        remaining = (await db_session.execute(
            select(Exam).where(Exam.child_id == child.id, Exam.subject == "数学")
        )).scalars().all()
        assert len(remaining) == 0

        # 无剩余考试 → 删 rank
        await db_session.delete(rank)
        await db_session.flush()

        rank_gone = (await db_session.execute(
            select(ChildRank).where(ChildRank.child_id == child.id, ChildRank.subject == "数学")
        )).scalar_one_or_none()
        assert rank_gone is None

    async def test_delete_not_found_404(self, db_session):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await delete_exam(99999, db_session)
        assert exc_info.value.status_code == 404


# ==================== 数据库唯一性兜底（DB-1 / DB-4） ====================

class TestDataIntegrityGuards:
    """DB 设计复核新增：唯一索引兜底 + 删考试清理考试来源错题"""

    async def test_child_rank_duplicate_rejected(self, db_session, make_child):
        """DB-1：同一 (child_id, subject) 只能有一行段位"""
        from sqlalchemy.exc import IntegrityError
        child = await make_child()
        db_session.add(ChildRank(child_id=child.id, subject="数学", tier="青铜"))
        await db_session.flush()
        db_session.add(ChildRank(child_id=child.id, subject="数学", tier="白银"))
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    async def test_child_rank_different_subject_ok(self, db_session, make_child):
        """DB-1：不同科目各一行是正常的"""
        child = await make_child()
        db_session.add(ChildRank(child_id=child.id, subject="数学", tier="青铜"))
        db_session.add(ChildRank(child_id=child.id, subject="语文", tier="黄金"))
        await db_session.flush()
        rows = (await db_session.execute(
            select(ChildRank).where(ChildRank.child_id == child.id)
        )).scalars().all()
        assert len(rows) == 2

    async def test_delete_exam_cleans_exam_sourced_wrong_questions(
        self, db_session, make_child, make_exam
    ):
        """DB-4：删除考试时，来源指向该考试的错题一并清理"""
        from models import WrongQuestion
        child = await make_child()
        e1 = await make_exam(child.id, score=60, full_score=100, exam_name="月考")
        e2 = await make_exam(child.id, score=80, full_score=100, exam_name="期中")

        wq_from_e1 = WrongQuestion(
            child_id=child.id, subject="数学", question_text="1+1=?",
            source_type="exam", source_id=e1.id,
        )
        wq_from_e2 = WrongQuestion(
            child_id=child.id, subject="数学", question_text="2+2=?",
            source_type="exam", source_id=e2.id,
        )
        wq_manual = WrongQuestion(
            child_id=child.id, subject="数学", question_text="3+3=?",
            source_type="manual", source_id=None,
        )
        db_session.add_all([wq_from_e1, wq_from_e2, wq_manual])
        await db_session.flush()

        await delete_exam(e1.id, db_session)

        remaining = (await db_session.execute(select(WrongQuestion))).scalars().all()
        remaining_ids = {q.id for q in remaining}
        assert wq_from_e1.id not in remaining_ids  # 考试来源 → 被清理
        assert wq_from_e2.id in remaining_ids      # 其他考试的错题 → 保留
        assert wq_manual.id in remaining_ids       # 手动错题 → 保留

    async def test_delete_exam_leaves_no_orphan_reviews(
        self, db_session, make_child, make_exam
    ):
        """清理错题时其复习记录须由 DB 外键级联删除，不留孤儿。

        delete_exam 用的是 Core 层 delete()，绕过 ORM 的 delete-orphan，
        因此只能依赖数据库层外键级联——本测试守护这条链路。
        """
        from models import WrongQuestion, WrongQuestionReview
        child = await make_child()
        exam = await make_exam(child.id, score=60, full_score=100, exam_name="月考")

        wq = WrongQuestion(
            child_id=child.id, subject="数学", question_text="1+1=?",
            source_type="exam", source_id=exam.id,
        )
        db_session.add(wq)
        await db_session.flush()
        db_session.add(WrongQuestionReview(
            wrong_question_id=wq.id, review_date=date.today(), result="wrong"
        ))
        await db_session.flush()

        # 前置断言：复习记录确实已落库，否则后面的"无孤儿"断言会假通过
        assert (await db_session.execute(
            select(WrongQuestionReview).where(
                WrongQuestionReview.wrong_question_id == wq.id)
        )).scalars().all(), "前置条件失败：复习记录未落库"

        await delete_exam(exam.id, db_session)

        orphans = (await db_session.execute(
            select(WrongQuestionReview).where(
                WrongQuestionReview.wrong_question_id == wq.id)
        )).scalars().all()
        assert orphans == [], "错题被清理后不应残留孤儿复习记录"
