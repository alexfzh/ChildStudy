"""homework.py 测试：删除作业时清理作业来源错题（DB-4）+ 复习记录级联"""
from datetime import date

from sqlalchemy import select

from models import Homework, WrongQuestion, WrongQuestionReview
from routers.homework import (
    create_homework,
    delete_homework,
    list_homeworks,
    update_homework,
)
from schemas import HomeworkCreate, HomeworkUpdate


class TestDeleteHomeworkCleansWrongQuestions:
    """DB-4：删除作业不得留下指向已删作业的幽灵错题"""

    async def _make_homework(self, db_session, child_id, title="练习一"):
        hw = Homework(
            child_id=child_id, subject="数学", title=title, homework_date=date.today()
        )
        db_session.add(hw)
        await db_session.flush()
        return hw

    async def _make_wrong_question(self, db_session, child_id, source_type, source_id, text):
        wq = WrongQuestion(
            child_id=child_id, subject="数学", question_text=text,
            source_type=source_type, source_id=source_id,
        )
        db_session.add(wq)
        await db_session.flush()
        return wq

    async def test_cleans_homework_sourced_only(self, db_session, make_child):
        """只清理指向本作业的错题，其他来源的错题不受影响"""
        child = await make_child()
        hw1 = await self._make_homework(db_session, child.id, "练习一")
        hw2 = await self._make_homework(db_session, child.id, "练习二")

        wq_hw1 = await self._make_wrong_question(
            db_session, child.id, "homework", hw1.id, "1+1=?")
        wq_hw2 = await self._make_wrong_question(
            db_session, child.id, "homework", hw2.id, "2+2=?")
        wq_manual = await self._make_wrong_question(
            db_session, child.id, "manual", None, "3+3=?")
        wq_exam = await self._make_wrong_question(
            db_session, child.id, "exam", 999, "4+4=?")

        await delete_homework(hw1.id, db_session)

        remaining = {
            q.id for q in
            (await db_session.execute(select(WrongQuestion))).scalars().all()
        }
        assert wq_hw1.id not in remaining, "指向已删作业的错题应被清理"
        assert wq_hw2.id in remaining, "其他作业的错题不应受影响"
        assert wq_manual.id in remaining, "手动录入错题不应受影响"
        assert wq_exam.id in remaining, "考试来源错题不应受影响"

    async def test_reviews_cascade_not_orphaned(self, db_session, make_child):
        """清理错题时，其复习记录由 DB 外键 ON DELETE CASCADE 连带删除，不留孤儿。

        这里用 Core 层 delete() 批量删除，会绕过 ORM 的 delete-orphan 级联，
        因此必须依赖数据库层的外键级联——本测试守护的就是这条链路。
        """
        child = await make_child()
        hw = await self._make_homework(db_session, child.id)
        wq = await self._make_wrong_question(
            db_session, child.id, "homework", hw.id, "1+1=?")
        review = WrongQuestionReview(
            wrong_question_id=wq.id, review_date=date.today(), result="wrong"
        )
        db_session.add(review)
        await db_session.flush()

        # 前置断言：复习记录确实已落库，否则后面的"无孤儿"断言会假通过
        assert (await db_session.execute(
            select(WrongQuestionReview).where(
                WrongQuestionReview.wrong_question_id == wq.id)
        )).scalars().all(), "前置条件失败：复习记录未落库"

        await delete_homework(hw.id, db_session)

        orphan_reviews = (await db_session.execute(
            select(WrongQuestionReview).where(
                WrongQuestionReview.wrong_question_id == wq.id)
        )).scalars().all()
        assert orphan_reviews == [], "错题被清理后不应残留孤儿复习记录"


class TestHomeworkCRUD:
    """作业 CRUD 端到端测试（v1.7.4 补全）"""

    async def _make_child(self, db_session, name="测试娃", grade="四年级"):
        from models import Family, User
        fam = Family(name=f"{name}的家")
        db_session.add(fam)
        await db_session.flush()
        user = User(
            family_id=fam.id, username=f"parent_{name}", password_hash="x",
            role="parent", display_name="Parent", is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        from models import Child
        child = Child(family_id=fam.id, name=name, grade=grade)
        db_session.add(child)
        await db_session.flush()
        return child

    def _acc(self, child):
        return {child.id}

    async def test_create_and_list(self, db_session, make_child):
        child = await make_child("hw_kid_1")
        hw = await create_homework(
            HomeworkCreate(
                child_id=child.id, subject="数学", title="练习一",
                homework_date=date.today(), duration_minutes=30,
            ),
            db=db_session, accessible=self._acc(child),
        )
        assert hw.id is not None
        items = await list_homeworks(
            child_id=child.id, subject=None, limit=200,
            db=db_session, accessible=self._acc(child),
        )
        assert any(h.id == hw.id for h in items)

    async def test_update_homework(self, db_session, make_child):
        child = await make_child("hw_kid_2")
        hw = await create_homework(
            HomeworkCreate(
                child_id=child.id, subject="语文", title="古诗背诵",
                homework_date=date.today(), duration_minutes=20,
            ),
            db=db_session, accessible=self._acc(child),
        )
        updated = await update_homework(
            hw.id,
            HomeworkUpdate(title="古诗背诵-已订正", is_completed=True),
            db=db_session, accessible=self._acc(child),
        )
        assert updated.title == "古诗背诵-已订正"
        assert updated.completed is True

    async def test_filter_by_subject(self, db_session, make_child):
        child = await make_child("hw_kid_3")
        await create_homework(
            HomeworkCreate(
                child_id=child.id, subject="数学", title="数学习题",
                homework_date=date.today(), duration_minutes=15,
            ),
            db=db_session, accessible=self._acc(child),
        )
        await create_homework(
            HomeworkCreate(
                child_id=child.id, subject="语文", title="语文习题",
                homework_date=date.today(), duration_minutes=15,
            ),
            db=db_session, accessible=self._acc(child),
        )
        math_items = await list_homeworks(
            child_id=child.id, subject="数学", limit=200,
            db=db_session, accessible=self._acc(child),
        )
        assert all(h.subject == "数学" for h in math_items)
        assert len(math_items) == 1

    async def test_delete_homework(self, db_session, make_child):
        child = await make_child("hw_kid_4")
        hw = await create_homework(
            HomeworkCreate(
                child_id=child.id, subject="英语", title="英语听写",
                homework_date=date.today(), duration_minutes=10,
            ),
            db=db_session, accessible=self._acc(child),
        )
        await delete_homework(
            hw.id, db=db_session, accessible=self._acc(child),
        )
        items = await list_homeworks(
            child_id=child.id, subject=None, limit=200,
            db=db_session, accessible=self._acc(child),
        )
        assert not any(h.id == hw.id for h in items)

    async def test_create_validates_accessible_child(self, db_session, make_child):
        """家长不能给不在自己家庭的孩子建作业（assert_child_access 守卫）"""
        child_a = await make_child("hw_a")
        # 用一个错误的 accessible 集合，期望触发 403
        import pytest
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as ei:
            await create_homework(
                HomeworkCreate(
                    child_id=child_a.id, subject="数学", title="应被拒",
                    homework_date=date.today(), duration_minutes=10,
                ),
                db=db_session, accessible={99999},  # 不包含 child_a.id
            )
        assert ei.value.status_code == 403
