"""核心 CRUD smoke tests（覆盖高频路由）

使用直接调用 router 函数，复用 conftest.py 的 db_session。
调用约定：
- db: AsyncSession = Depends(get_db) 结尾 → 传 db=db_session 关键字
- db: AsyncSession 无默认 → 传 db_session 位置参数（第一）
- user: User = Depends(...) → 传 parent fixture
- accessible: set[int] = Depends(...) → 传 _accessible(child) 工厂
"""
from datetime import date

import pytest
import pytest_asyncio

from models import Child, Family, User
from routers.children import (
    create_child,
    create_grade_history,
    delete_child,
    delete_grade_history,
    get_child,
    list_children,
    list_grade_history,
    update_child,
)
from routers.exercises import (
    get_exercise,
    list_exercises,
    recommend_questions,
    start_exercise,
    submit_exercise,
)
from routers.homework import create_homework, delete_homework, list_homeworks, update_homework
from routers.interests import (
    create as create_interest,
)
from routers.interests import (
    delete as delete_interest,
)
from routers.interests import (
    list_by_child as list_interests,
)
from routers.interests import (
    update as update_interest,
)
from routers.knowledge_points import (
    create_knowledge_point,
    delete_knowledge_point,
    get_knowledge_point,
    list_grade_levels,
    list_knowledge_points,
    list_subjects_with_knowledge_points,
    update_knowledge_point,
)
from routers.question_banks import (
    create_bank,
    create_question,
    delete_bank,
    get_bank,
    list_banks,
    list_questions,
    update_bank,
)
from routers.rewards import (
    create_reward,
    delete_reward,
    get_total_points,
    list_rewards,
    update_reward,
)
from routers.social_emotional import (
    create as create_social_emotional,
)
from routers.social_emotional import (
    delete as delete_social_emotional,
)
from routers.social_emotional import (
    list_by_child as list_social_emotional,
)
from routers.social_emotional import (
    update as update_social_emotional,
)
from routers.textbook import (
    get_unit,
    list_units,
    list_versions,
)
from routers.timeline import create_event, delete_event, list_events, update_event
from schemas import (
    ChildCreate,
    ChildUpdate,
    ExerciseStartRequest,
    ExerciseSubmitRequest,
    GradeHistoryCreate,
    HomeworkCreate,
    HomeworkUpdate,
    InterestCreate,
    InterestUpdate,
    KnowledgePointCreate,
    KnowledgePointUpdate,
    QuestionBankCreate,
    QuestionBankUpdate,
    QuestionCreate,
    RewardCreate,
    RewardUpdate,
    SocialEmotionalCreate,
    SocialEmotionalUpdate,
    TimelineCreate,
    TimelineUpdate,
)

# ==================== Fixtures ====================

@pytest_asyncio.fixture
async def family(db_session):
    f = Family(name="测试家庭")
    db_session.add(f)
    await db_session.flush()
    return f


@pytest_asyncio.fixture
async def parent(db_session, family):
    u = User(username="parent1", password_hash="x", role="parent", family_id=family.id, display_name="Parent", is_active=True)
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def child_factory(db_session, family):
    counter = {"n": 0}

    async def _create(name="娃", grade="四年级", **kw):
        counter["n"] += 1
        c = Child(
            name=name or f"娃{counter['n']}",
            family_id=family.id,
            grade=grade,
            **kw,
        )
        db_session.add(c)
        await db_session.flush()
        return c

    return _create


def _acc(child):
    return {child.id}


# ==================== Children CRUD ====================

class TestChildrenCRUD:
    async def test_list_empty(self, db_session, family, parent):
        # list_children(user, db) — user from Depends(require_parent), db from Depends(get_db)
        result = await list_children(parent, db=db_session)
        assert result == []

    async def test_create_and_get(self, db_session, child_factory, parent):
        child = await child_factory(name="张三", grade="五年级")
        # create_child(payload, user, db)
        created = await create_child(ChildCreate(name="张三", grade="五年级"), parent, db=db_session)
        assert created.id is not None
        fetched = await get_child(child.id, _acc(child), db=db_session)
        assert fetched.id == child.id

    async def test_update_child(self, db_session, child_factory, parent):
        child = await child_factory(name="旧名", grade="三年级")
        updated = await update_child(child.id, ChildUpdate(name="新名", grade="四年级"), _acc(child), db=db_session)
        assert updated.name == "新名"

    async def test_delete_child(self, db_session, child_factory, parent):
        child = await child_factory()
        await delete_child(child.id, _acc(child), db=db_session)
        result = await list_children(parent, db=db_session)
        assert not any(c.id == child.id for c in result)


# ==================== Grade History CRUD ====================

class TestGradeHistoryCRUD:
    async def test_create_and_list(self, db_session, child_factory, parent):
        child = await child_factory()
        # create_grade_history(child_id, payload, accessible, db)
        gh = await create_grade_history(child.id, GradeHistoryCreate(grade="六年级", effective_from=date.today()), _acc(child), db=db_session)
        assert gh.id is not None
        histories = await list_grade_history(child.id, _acc(child), db=db_session)
        assert len(histories) == 1

    async def test_delete_grade_history(self, db_session, child_factory, parent):
        child = await child_factory()
        gh = await create_grade_history(child.id, GradeHistoryCreate(grade="六年级", effective_from=date.today()), _acc(child), db=db_session)
        await delete_grade_history(child.id, gh.id, _acc(child), db=db_session)
        histories = await list_grade_history(child.id, _acc(child), db=db_session)
        assert len(histories) == 0


# ==================== Homework CRUD ====================

class TestHomeworkCRUD:
    async def test_create_and_list(self, db_session, child_factory):
        child = await child_factory()
        hw = await create_homework(
            HomeworkCreate(child_id=child.id, subject="math", title="hw1", homework_date=date.today(), duration_minutes=30),
            db=db_session
        )
        assert hw.id is not None
        items = await list_homeworks(child_id=child.id, subject=None, limit=200, db=db_session)
        assert any(it.id == hw.id for it in items)

    async def test_update_homework(self, db_session, child_factory):
        child = await child_factory()
        hw = await create_homework(
            HomeworkCreate(child_id=child.id, subject="math", title="oldhw", homework_date=date.today(), duration_minutes=30),
            db=db_session
        )
        updated = await update_homework(hw.id, HomeworkUpdate(title="new", is_completed=True), db=db_session)
        assert updated.title == "new"

    async def test_delete_homework(self, db_session, child_factory):
        child = await child_factory()
        hw = await create_homework(
            HomeworkCreate(child_id=child.id, subject="math", title="delhw", homework_date=date.today(), duration_minutes=10),
            db=db_session
        )
        await delete_homework(hw.id, db=db_session)
        items = await list_homeworks(child_id=child.id, subject=None, limit=200, db=db_session)
        assert not any(it.id == hw.id for it in items)


# ==================== Timeline CRUD ====================

class TestTimelineCRUD:
    async def test_create_and_list(self, db_session, child_factory, parent):
        child = await child_factory()
        evt = await create_event(
            TimelineCreate(child_id=child.id, event_type="school", title="开学", event_date=date.today()),
            parent, db=db_session
        )
        assert evt.id is not None
        items = await list_events(child_id=child.id, event_type=None, keyword=None, limit=200, db=db_session)
        assert any(it.id == evt.id for it in items)

    async def test_update_event(self, db_session, child_factory, parent):
        child = await child_factory()
        evt = await create_event(
            TimelineCreate(child_id=child.id, event_type="school", title="旧", event_date=date.today()),
            parent, db=db_session
        )
        updated = await update_event(evt.id, TimelineUpdate(title="新"), parent, db=db_session)
        assert updated.title == "新"

    async def test_delete_event(self, db_session, child_factory, parent):
        child = await child_factory()
        evt = await create_event(
            TimelineCreate(child_id=child.id, event_type="school", title="x", event_date=date.today()),
            parent, db=db_session
        )
        await delete_event(evt.id, parent, db=db_session)
        items = await list_events(child_id=child.id, event_type=None, keyword=None, limit=200, db=db_session)
        assert not any(it.id == evt.id for it in items)


# ==================== Rewards CRUD ====================

class TestRewardsCRUD:
    async def test_create_and_list(self, db_session, child_factory, parent):
        child = await child_factory()
        reward = await create_reward(
            RewardCreate(child_id=child.id, name="star", points_required=10, icon="star"),
            parent, db=db_session
        )
        assert reward.id is not None
        rewards = await list_rewards(db=db_session)
        assert any(r.id == reward.id for r in rewards)

    async def test_update_reward(self, db_session, child_factory, parent):
        child = await child_factory()
        reward = await create_reward(
            RewardCreate(child_id=child.id, name="old", points_required=10, icon="star"),
            parent, db=db_session
        )
        updated = await update_reward(reward.id, RewardUpdate(name="new", points_required=20), parent, db=db_session)
        assert updated.name == "new"

    async def test_delete_reward(self, db_session, child_factory, parent):
        child = await child_factory()
        reward = await create_reward(
            RewardCreate(child_id=child.id, name="x", points_required=5, icon="star"),
            parent, db=db_session
        )
        await delete_reward(reward.id, parent, db=db_session)
        rewards = await list_rewards(db=db_session)
        assert not any(r.id == reward.id for r in rewards)

    async def test_zero_points(self, db_session, child_factory):
        child = await child_factory()
        pts = await get_total_points(db_session, child.id)
        assert pts == 0


# ==================== Knowledge Points CRUD ====================

class TestKnowledgePointsCRUD:
    async def test_list_grade_levels(self, db_session):
        grades = await list_grade_levels(db=db_session)
        assert isinstance(grades, list)

    async def test_list_subjects(self, db_session):
        subjects = await list_subjects_with_knowledge_points(db=db_session)
        assert isinstance(subjects, list)

    async def test_create_and_get(self, db_session, child_factory, parent):
        child = await child_factory()
        kp = await create_knowledge_point(
            KnowledgePointCreate(child_id=child.id, name="addition", subject="math", grade="4"),
            parent, db=db_session
        )
        kp_id = kp.id
        fetched = await get_knowledge_point(kp_id, db=db_session)
        assert fetched.name == "addition"

    async def test_update_kp(self, db_session, child_factory, parent):
        child = await child_factory()
        kp = await create_knowledge_point(
            KnowledgePointCreate(child_id=child.id, name="old", subject="math", grade="4"),
            parent, db=db_session
        )
        updated = await update_knowledge_point(kp.id, KnowledgePointUpdate(name="new"), parent, db=db_session)
        assert updated.name == "new"

    async def test_delete_kp(self, db_session, child_factory, parent):
        child = await child_factory()
        kp = await create_knowledge_point(
            KnowledgePointCreate(child_id=child.id, name="x", subject="math", grade="4"),
            parent, db=db_session
        )
        await delete_knowledge_point(kp.id, parent, db=db_session)
        kps = await list_knowledge_points(subject="math", db=db_session)
        assert not any(k.id == kp.id for k in kps)


# ==================== Question Banks CRUD ====================

class TestQuestionBanksCRUD:
    async def test_create_and_list(self, db_session):
        bank = await create_bank(
            QuestionBankCreate(grade="5", subject="math", title="bank1"),
            db=db_session
        )
        assert bank["id"] is not None
        banks = await list_banks(grade=None, subject=None, db=db_session)
        assert any(b["id"] == bank["id"] for b in banks)

    async def test_get_bank(self, db_session):
        bank = await create_bank(
            QuestionBankCreate(grade="5", subject="math", title="bankX"),
            db=db_session
        )
        fetched = await get_bank(bank["id"], db=db_session)
        assert fetched["id"] == bank["id"]

    async def test_bank_with_questions(self, db_session):
        bank = await create_bank(
            QuestionBankCreate(grade="5", subject="math", title="bankQ"),
            db=db_session
        )
        await create_question(bank["id"], QuestionCreate(bank_id=bank["id"], knowledge_point="kp1", content="1+1=?", options=["2","3","4","5"], correct_answer="A", difficulty="easy"), db=db_session)
        await create_question(bank["id"], QuestionCreate(bank_id=bank["id"], knowledge_point="kp1", content="2+2=?", options=["3","4","5","6"], correct_answer="D", difficulty="normal"), db=db_session)
        questions = await list_questions(bank["id"], knowledge_point=None, difficulty=None, db=db_session)
        assert len(questions) == 2

    async def test_update_bank(self, db_session):
        bank = await create_bank(
            QuestionBankCreate(grade="5", subject="math", title="old"),
            db=db_session
        )
        updated = await update_bank(bank["id"], QuestionBankUpdate(title="new"), db=db_session)
        assert updated["title"] == "new"

    async def test_delete_bank(self, db_session):
        bank = await create_bank(
            QuestionBankCreate(grade="5", subject="math", title="x"),
            db=db_session
        )
        await delete_bank(bank["id"], db=db_session)
        banks = await list_banks(grade=None, subject=None, db=db_session)
        assert not any(b["id"] == bank["id"] for b in banks)


# ==================== Textbook CRUD ====================

class TestTextbookCRUD:
    async def test_list_versions(self, db_session):
        versions = await list_versions(grade=None, subject=None, db=db_session)
        assert isinstance(versions, list)

    async def test_list_units(self, db_session):
        versions = await list_versions(grade=None, subject=None, db=db_session)
        if not versions:
            pytest.skip("no textbook versions")
        vid = versions[0]["id"]
        units = await list_units(vid, db=db_session)
        assert isinstance(units, list)

    async def test_get_unit(self, db_session):
        versions = await list_versions(grade=None, subject=None, db=db_session)
        if not versions:
            pytest.skip("no textbook versions")
        vid = versions[0]["id"]
        units = await list_units(vid, db=db_session)
        if not units:
            pytest.skip("no units")
        uid = units[0]["id"]
        fetched = await get_unit(uid, db=db_session)
        assert fetched["id"] == uid


# ==================== Social Emotional CRUD ====================

class TestSocialEmotionalCRUD:
    async def test_create_and_list(self, db_session, child_factory, parent):
        child = await child_factory()
        rec = await create_social_emotional(
            child.id,
            SocialEmotionalCreate(record_date=date.today(), mood_score=4, emotion_tags=["happy"]),
            db=db_session, accessible=_acc(child),
        )
        assert rec.id is not None
        items = await list_social_emotional(child.id, db=db_session, accessible=_acc(child))
        assert any(it.id == rec.id for it in items)

    async def test_update_social_emotional(self, db_session, child_factory, parent):
        child = await child_factory()
        rec = await create_social_emotional(
            child.id,
            SocialEmotionalCreate(record_date=date.today(), mood_score=3, emotion_tags=["ok"]),
            db=db_session, accessible=_acc(child),
        )
        updated = await update_social_emotional(
            rec.id, SocialEmotionalUpdate(mood_score=5), db=db_session, accessible=_acc(child),
        )
        assert updated.mood_score == 5

    async def test_delete_social_emotional(self, db_session, child_factory, parent):
        child = await child_factory()
        rec = await create_social_emotional(
            child.id,
            SocialEmotionalCreate(record_date=date.today(), mood_score=2, emotion_tags=["sad"]),
            db=db_session, accessible=_acc(child),
        )
        await delete_social_emotional(rec.id, db=db_session, accessible=_acc(child))
        items = await list_social_emotional(child.id, db=db_session, accessible=_acc(child))
        assert not any(it.id == rec.id for it in items)


# ==================== Interests CRUD ====================

class TestInterestsCRUD:
    async def test_create_and_list(self, db_session, child_factory, parent):
        child = await child_factory()
        rec = await create_interest(
            child.id,
            InterestCreate(record_date=date.today(), activity_type="运动", activity_name="游泳", duration_minutes=30),
            db=db_session, accessible=_acc(child),
        )
        assert rec.id is not None
        items = await list_interests(child.id, db=db_session, accessible=_acc(child))
        assert any(it.id == rec.id for it in items)

    async def test_update_interest(self, db_session, child_factory, parent):
        child = await child_factory()
        rec = await create_interest(
            child.id,
            InterestCreate(record_date=date.today(), activity_type="音乐", activity_name="钢琴", duration_minutes=20),
            db=db_session, accessible=_acc(child),
        )
        updated = await update_interest(
            rec.id, InterestUpdate(duration_minutes=45), db=db_session, accessible=_acc(child),
        )
        assert updated.duration_minutes == 45

    async def test_delete_interest(self, db_session, child_factory, parent):
        child = await child_factory()
        rec = await create_interest(
            child.id,
            InterestCreate(record_date=date.today(), activity_type="阅读", activity_name="绘本", duration_minutes=15),
            db=db_session, accessible=_acc(child),
        )
        await delete_interest(rec.id, db=db_session, accessible=_acc(child))
        items = await list_interests(child.id, db=db_session, accessible=_acc(child))
        assert not any(it.id == rec.id for it in items)


# ==================== Exercises CRUD ====================

class TestExercisesCRUD:
    async def test_start_and_list(self, db_session, child_factory):
        child = await child_factory()
        bank = await create_bank(
            QuestionBankCreate(grade="5", subject="math", title="bankEx"),
            db=db_session,
        )
        await create_question(
            bank["id"],
            QuestionCreate(bank_id=bank["id"], knowledge_point="kp1", content="1+1=?", options=["2","3","4","5"], correct_answer="A", difficulty="easy"),
            db=db_session,
        )
        ex = await start_exercise(
            ExerciseStartRequest(child_id=child.id, bank_id=bank["id"], count=1),
            db=db_session, accessible=_acc(child),
        )
        assert ex.id is not None
        items = await list_exercises(child_id=child.id, db=db_session, accessible=_acc(child))
        assert any(it.id == ex.id for it in items)

    async def test_submit_and_get(self, db_session, child_factory):
        child = await child_factory()
        bank = await create_bank(
            QuestionBankCreate(grade="5", subject="math", title="bankEx2"),
            db=db_session,
        )
        q = await create_question(
            bank["id"],
            QuestionCreate(bank_id=bank["id"], knowledge_point="kp1", content="2+2=?", options=["3","4","5","6"], correct_answer="D", difficulty="easy"),
            db=db_session,
        )
        ex = await start_exercise(
            ExerciseStartRequest(child_id=child.id, bank_id=bank["id"], count=1),
            db=db_session, accessible=_acc(child),
        )
        submitted = await submit_exercise(
            ex.id,
            ExerciseSubmitRequest(answers=[{"question_id": q.id, "selected": "D"}]),
            db=db_session, accessible=_acc(child),
        )
        assert submitted.score == 100.0
        fetched = await get_exercise(ex.id, db=db_session, accessible=_acc(child))
        assert fetched.id == ex.id

    async def test_recommend(self, db_session, child_factory):
        child = await child_factory()
        rec = await recommend_questions(child.id, db=db_session, accessible=_acc(child))
        assert rec.suggestion
