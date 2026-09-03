"""Router 级 CRUD 测试：children / timeline / project_works / question_banks / dashboard

覆盖 v3 审计 P1#4 指出的覆盖空白：此前这 5 个 router 仅靠 test_crud_smoke.py 兜底。
风格与 test_exams.py 一致：直调 router 函数，Depends 参数显式传入。
"""
from datetime import date

import pytest
from fastapi import HTTPException

from models import Child, Exam, Family, TextbookUnit, TextbookVersion, User
from routers.children import (
    create_child,
    delete_child,
    get_child,
    list_grade_history,
    update_child,
)
from routers.dashboard import compare_children, get_dashboard, invalidate_dashboard_cache
from routers.project_works import (
    get_work_image,
    review_work,
    submit_work,
)
from routers.question_banks import (
    create_bank,
    create_question,
    delete_bank,
    delete_question,
    get_bank,
    list_questions,
    update_bank,
    update_question,
)
from routers.timeline import create_event, delete_event, list_events, update_event
from schemas import (
    ChildCreate,
    ChildUpdate,
    ProjectWorkCreate,
    ProjectWorkUpdate,
    QuestionBankCreate,
    QuestionBankUpdate,
    QuestionCreate,
    QuestionUpdate,
    TimelineCreate,
    TimelineUpdate,
)

pytestmark = pytest.mark.asyncio


# ---------- 公共 fixtures ----------

async def _make_family_user(db_session, username="crud_parent") -> User:
    fam = Family(name=f"{username}家")
    db_session.add(fam)
    await db_session.flush()
    user = User(
        username=username, password_hash="x", display_name=username,
        role="parent", family_id=fam.id, is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_child(db_session, family_id: int, name="测试宝") -> Child:
    child = Child(family_id=family_id, name=name, grade="四年级")
    db_session.add(child)
    await db_session.flush()
    return child


# ---------- children ----------

async def test_create_child_writes_initial_grade_history(db_session):
    user = await _make_family_user(db_session, "p_children")
    child = await create_child(
        ChildCreate(name="大宝", grade="四年级"), user=user, db=db_session,
    )
    assert child.id and child.family_id == user.family_id
    rows = await list_grade_history(child.id, accessible={child.id}, db=db_session)
    assert len(rows) == 1 and rows[0].grade == "四年级"


async def test_get_child_denies_out_of_scope(db_session):
    user = await _make_family_user(db_session, "p_children2")
    child = await _make_child(db_session, user.family_id)
    with pytest.raises(HTTPException) as ei:
        await get_child(child.id, accessible=set(), db=db_session)
    assert ei.value.status_code == 403


async def test_update_and_delete_child(db_session):
    user = await _make_family_user(db_session, "p_children3")
    child = await _make_child(db_session, user.family_id)

    updated = await update_child(
        child.id, ChildUpdate(notes="数学需加强"), accessible={child.id}, db=db_session,
    )
    assert updated.notes == "数学需加强"

    resp = await delete_child(child.id, accessible={child.id}, db=db_session)
    assert resp.ok is True
    with pytest.raises(HTTPException) as ei:
        await get_child(child.id, accessible={child.id}, db=db_session)
    assert ei.value.status_code == 404


# ---------- timeline ----------

async def test_timeline_crud_and_scope(db_session):
    user = await _make_family_user(db_session, "p_timeline")
    child = await _make_child(db_session, user.family_id)
    accessible = {child.id}

    ev = await create_event(
        TimelineCreate(child_id=child.id, title="第一次口算比赛", event_date=date.today()),
        _parent=user, db=db_session, accessible=accessible,
    )
    assert ev.id and ev.title == "第一次口算比赛"

    rows = await list_events(child_id=child.id, limit=10, offset=0,
                             db=db_session, accessible=accessible)
    assert any(r.id == ev.id for r in rows)

    ev2 = await update_event(
        ev.id, TimelineUpdate(title="口算比赛一等奖"),
        _parent=user, db=db_session, accessible=accessible,
    )
    assert ev2.title == "口算比赛一等奖"

    resp = await delete_event(ev.id, _parent=user, db=db_session, accessible=accessible)
    assert resp.ok is True
    with pytest.raises(HTTPException) as ei:
        await update_event(ev.id, TimelineUpdate(title="x"),
                           _parent=user, db=db_session, accessible=accessible)
    assert ei.value.status_code == 404


async def test_create_event_rejects_other_family_child(db_session):
    user = await _make_family_user(db_session, "p_timeline2")
    other = await _make_child(db_session, user.family_id)  # 同家庭但不在可访问集合内
    # 空可访问集 → assert_child_access 必然 403（避免 id 数值巧合碰撞）
    with pytest.raises(HTTPException) as ei:
        await create_event(
            TimelineCreate(child_id=other.id, title="越权", event_date=date.today()),
            _parent=user, db=db_session, accessible=set(),
        )
    assert ei.value.status_code == 403


# ---------- project_works ----------

async def _make_unit(db_session) -> TextbookUnit:
    ver = TextbookVersion(code=f"PW-{id(db_session)}", name="沪教版五四制",
                          publisher="上海教育出版社", grade="四年级", subject="数学")
    db_session.add(ver)
    await db_session.flush()
    unit = TextbookUnit(version_id=ver.id, code="U1", unit_number=1, title_zh="第一章")
    db_session.add(unit)
    await db_session.flush()
    return unit


async def test_submit_and_review_work(db_session):
    user = await _make_family_user(db_session, "p_works")
    child = await _make_child(db_session, user.family_id)
    unit = await _make_unit(db_session)
    accessible = {child.id}

    pw = await submit_work(
        ProjectWorkCreate(child_id=child.id, unit_id=unit.id,
                          work_type="text", title="口算练习", content="10 道口算"),
        db=db_session, accessible=accessible,
    )
    assert pw.id and pw.status == "submitted"

    reviewed = await review_work(
        pw.id, ProjectWorkUpdate(parent_comment="很棒", status="reviewed"),
        db=db_session, accessible=accessible,
    )
    assert reviewed.status == "reviewed" and reviewed.parent_comment == "很棒"


async def test_get_work_image_404_when_no_image(db_session):
    user = await _make_family_user(db_session, "p_works2")
    child = await _make_child(db_session, user.family_id)
    unit = await _make_unit(db_session)
    pw = await submit_work(
        ProjectWorkCreate(child_id=child.id, unit_id=unit.id, work_type="text"),
        db=db_session, accessible={child.id},
    )
    with pytest.raises(HTTPException) as ei:
        await get_work_image(pw.id, db=db_session, accessible={child.id})
    assert ei.value.status_code == 404


async def test_submit_work_rejects_unknown_unit(db_session):
    user = await _make_family_user(db_session, "p_works3")
    child = await _make_child(db_session, user.family_id)
    with pytest.raises(HTTPException) as ei:
        await submit_work(
            ProjectWorkCreate(child_id=child.id, unit_id=99999, work_type="text"),
            db=db_session, accessible={child.id},
        )
    assert ei.value.status_code == 404


# ---------- question_banks ----------

async def test_bank_and_question_crud(db_session):
    user = await _make_family_user(db_session, "p_banks")

    bank = await create_bank(
        QuestionBankCreate(grade="四年级", subject="数学", title="口算题库"),
        db=db_session, _parent=user,
    )
    bank_id = bank["id"] if isinstance(bank, dict) else bank.id

    got = await get_bank(bank_id, db=db_session)
    got_title = got["title"] if isinstance(got, dict) else got.title
    assert got_title == "口算题库"

    updated = await update_bank(
        bank_id, QuestionBankUpdate(title="口算精选"), db=db_session, _parent=user,
    )
    updated_title = updated["title"] if isinstance(updated, dict) else updated.title
    assert updated_title == "口算精选"

    q = await create_question(
        bank_id,
        QuestionCreate(bank_id=bank_id, knowledge_point="加法", content="1+1=?",
                       options=["A", "B"], correct_answer="A"),
        db=db_session, _parent=user,
    )
    assert q.id and q.bank_id == bank_id

    rows = await list_questions(bank_id, knowledge_point=None, difficulty=None,
                                db=db_session)
    assert len(rows) == 1

    q2 = await update_question(
        bank_id, q.id, QuestionUpdate(difficulty="hard"), db=db_session, _parent=user,
    )
    assert q2.difficulty == "hard"

    resp = await delete_question(bank_id, q.id, db=db_session, _parent=user)
    assert resp.ok is True
    resp = await delete_bank(bank_id, db=db_session, _parent=user)
    assert resp.ok is True
    with pytest.raises(HTTPException) as ei:
        await get_bank(bank_id, db=db_session)
    assert ei.value.status_code == 404


async def test_get_bank_404(db_session):
    with pytest.raises(HTTPException) as ei:
        await get_bank(99999, db=db_session)
    assert ei.value.status_code == 404


# ---------- dashboard ----------

async def test_get_dashboard_aggregates(db_session):
    user = await _make_family_user(db_session, "p_dash")
    child = await _make_child(db_session, user.family_id)
    db_session.add_all([
        Exam(child_id=child.id, exam_name="期中", subject="数学",
             exam_date=date(2026, 6, 1), score=90, full_score=100),
        Exam(child_id=child.id, exam_name="期中", subject="语文",
             exam_date=date(2026, 6, 1), score=85, full_score=100),
    ])
    await db_session.flush()
    invalidate_dashboard_cache(child.id)

    data = await get_dashboard(child.id, accessible={child.id}, db=db_session)
    assert data is not None
    invalidate_dashboard_cache(child.id)


async def test_get_dashboard_404_for_missing_child(db_session):
    with pytest.raises(HTTPException) as ei:
        await get_dashboard(99999, accessible={99999}, db=db_session)
    assert ei.value.status_code == 404


async def test_compare_children_counts_exams(db_session):
    user = await _make_family_user(db_session, "p_compare")
    child = await _make_child(db_session, user.family_id)
    db_session.add_all([
        Exam(child_id=child.id, exam_name="期中", subject="数学",
             exam_date=date(2026, 6, 1), score=90, full_score=100),
        Exam(child_id=child.id, exam_name="期中", subject="语文",
             exam_date=date(2026, 6, 2), score=85, full_score=100),
    ])
    await db_session.flush()

    result = await compare_children(user=user, accessible={child.id}, db=db_session)
    assert len(result.children) == 1
    item = result.children[0]
    item = item if isinstance(item, dict) else item.model_dump()
    assert item["total_exams"] == 2
    assert item["average_score"] == 87.5
