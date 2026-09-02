"""测试 growth/social_emotional/interests 三条路由的 422 bug fix

Bug 历史：v1.7.2 之前，schemas.py 中三个 Base schema 要求 body 传 child_id，
但 router 从路径参数注入 child_id，前端表单不传 child_id → POST 422。

修复：Base schema 中 child_id 改为 Optional[int] = None（router 仍从 path 注入）。

测试覆盖：
- 不传 child_id → 201/200（修复后）
- 显式传 child_id → 仍然接受（兼容客户端）
- 校验其他字段（GrowthRecord 的 record_date 必填等）
"""
from datetime import date

import pytest
import pytest_asyncio
from fastapi import HTTPException

from routers.growth import create as growth_create
from routers.interests import create as interest_create
from routers.social_emotional import create as social_create
from schemas import GrowthRecordCreate, InterestCreate, SocialEmotionalCreate

# ============== fixtures (assumes existing conftest.py) ==============

async def _make_family_with(db_session, name="测试家"):
    from models import Family
    fam = Family(name=name)
    db_session.add(fam)
    await db_session.commit()
    await db_session.refresh(fam)
    return fam


async def _make_child(db_session, family_id, name="娃"):
    from models import Child
    c = Child(name=name, grade="三年级", family_id=family_id)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest_asyncio.fixture
async def child_with_access(db_session):
    """一个 child + 它对应的 accessible set。"""
    fam = await _make_family_with(db_session)
    c = await _make_child(db_session, fam.id)
    return c, {c.id}


# ============== Growth ==============

@pytest.mark.asyncio
async def test_growth_create_without_child_id_succeeds(db_session, child_with_access):
    """核心 fix：不传 child_id（前端实际场景） → 成功"""
    child, accessible = child_with_access
    payload = GrowthRecordCreate(
        record_date=date(2026, 9, 1),
        height_cm=125.5,
        weight_kg=27.0,
    )
    out = await growth_create(child.id, payload, db_session, accessible)
    assert out.id is not None
    assert out.child_id == child.id  # 由 router 注入
    assert out.height_cm == 125.5
    assert out.weight_kg == 27.0


@pytest.mark.asyncio
async def test_growth_create_with_explicit_child_id_still_works(db_session, child_with_access):
    """兼容：客户端显式传 child_id（哪怕和 path 不同，行为是 path 胜）"""
    child, accessible = child_with_access
    payload = GrowthRecordCreate(
        child_id=999,  # 显式但错，router 会覆盖
        record_date=date(2026, 9, 1),
        height_cm=130.0,
    )
    out = await growth_create(child.id, payload, db_session, accessible)
    # router 用 path 覆盖 → 永远是 child.id
    assert out.child_id == child.id


@pytest.mark.asyncio
async def test_growth_create_requires_record_date(db_session, child_with_access):
    """其他必填字段仍然校验：record_date 必填"""
    _child, _accessible = child_with_access
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as ei:
        GrowthRecordCreate(height_cm=125.0)  # 缺 record_date
    assert "record_date" in str(ei.value)


# ============== SocialEmotional ==============

@pytest.mark.asyncio
async def test_social_emotional_create_without_child_id_succeeds(db_session, child_with_access):
    child, accessible = child_with_access
    payload = SocialEmotionalCreate(
        record_date=date(2026, 9, 1),
        mood_score=4,
        emotion_tags=["happy", "proud"],
    )
    out = await social_create(child.id, payload, db_session, accessible)
    assert out.id is not None
    assert out.child_id == child.id
    assert out.mood_score == 4


@pytest.mark.asyncio
async def test_social_emotional_create_validates_mood_range(db_session, child_with_access):
    """其他校验仍然生效：mood_score 1-5"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as ei:
        SocialEmotionalCreate(record_date=date(2026, 9, 1), mood_score=10)
    assert "mood_score" in str(ei.value)


# ============== Interests ==============

@pytest.mark.asyncio
async def test_interest_create_without_child_id_succeeds(db_session, child_with_access):
    child, accessible = child_with_access
    payload = InterestCreate(
        record_date=date(2026, 9, 1),
        activity_type="运动",
        activity_name="游泳",
        duration_minutes=60,
    )
    out = await interest_create(child.id, payload, db_session, accessible)
    assert out.id is not None
    assert out.child_id == child.id
    assert out.activity_type == "运动"
    assert out.activity_name == "游泳"


@pytest.mark.asyncio
async def test_interest_create_validates_skill_level(db_session, child_with_access):
    from pydantic import ValidationError
    with pytest.raises(ValidationError) as ei:
        InterestCreate(
            record_date=date(2026, 9, 1),
            activity_type="运动",
            activity_name="跑步",
            skill_level="expert",  # 不在合法枚举
        )
    assert "skill_level" in str(ei.value)


# ============== 仍然守住的范围 ==============

@pytest.mark.asyncio
async def test_growth_create_rejects_other_child(db_session, child_with_access):
    """安全：accessible 不包含的 child_id → 403"""
    from routers.growth import create as growth_create
    _child, accessible = child_with_access
    payload = GrowthRecordCreate(
        record_date=date(2026, 9, 1),
        height_cm=125.0,
    )
    with pytest.raises(HTTPException) as ei:
        # 路径参数传别人的 child.id
        await growth_create(9999, payload, db_session, accessible)
    assert ei.value.status_code == 403
