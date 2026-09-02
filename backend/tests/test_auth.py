"""认证路由测试（v1.7.1）：登录 / 改密 / 防爆破 / JWT / 范围过滤

覆盖关键安全路径：
- 登录成功 + 失败 + 用户不存在
- 防爆破锁定（5次失败 → 429）
- 改密：原密码错误拒绝、成功更新
- JWT 无效/过期/伪造 → 401
- 范围过滤：孩子账号访问家长端点 → 403
- 多孩子 scope 隔离
"""
import time
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

from config import settings
from dependencies import get_current_user, require_parent
from models import Child, Family, User
from routers.auth import (
    _is_login_locked,
    _login_fail,
    _login_locked,
    _record_login_fail,
)
from utils.security import create_jwt, hash_password, verify_password


# ============== 工具 ==============

async def _make_family_with(db_session, name="测试家"):
    fam = Family(name=name)
    db_session.add(fam)
    await db_session.commit()
    await db_session.refresh(fam)
    return fam


async def _make_user(db_session, family_id, username, password="pw123456", role="parent", child_id=None):
    user = User(
        family_id=family_id,
        username=username,
        password_hash=hash_password(password),
        role=role,
        display_name=username,
        child_id=child_id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_child(db_session, family_id, name="娃"):
    c = Child(name=name, grade="三年级", family_id=family_id)
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


# ============== LoginRequest 直接调用测试 ==============

@pytest.mark.asyncio
async def test_login_success(db_session):
    """正确用户名+密码 → 200 + token + 用户对象"""
    from routers.auth import LoginRequest, login
    fam = await _make_family_with(db_session)
    user = await _make_user(db_session, fam.id, "alice", "secret123", role="parent")

    class _FakeReq:
        client = type("C", (), {"host": "127.0.0.1"})()
    resp = await login(LoginRequest(username="alice", password="secret123"), _FakeReq(), db_session)

    assert resp.token_type == "bearer"
    assert resp.expires_in == settings.jwt_expire_seconds
    assert resp.user.id == user.id
    assert resp.user.username == "alice"
    assert resp.user.role == "parent"


@pytest.mark.asyncio
async def test_login_wrong_password(db_session):
    """密码错误 → 401 + 模糊错误（不暴露用户是否存在）"""
    from fastapi import HTTPException
    from routers.auth import LoginRequest, login
    fam = await _make_family_with(db_session)
    await _make_user(db_session, fam.id, "alice", "correct_pw")

    class _FakeReq:
        client = type("C", (), {"host": "10.0.0.1"})()
    with pytest.raises(HTTPException) as ei:
        await login(LoginRequest(username="alice", password="wrong_pw"), _FakeReq(), db_session)
    assert ei.value.status_code == 401
    assert "用户名或密码错误" in ei.value.detail


@pytest.mark.asyncio
async def test_login_nonexistent_user(db_session):
    """不存在的用户 → 同样模糊错误（不区分 vs 错误密码）"""
    from fastapi import HTTPException
    from routers.auth import LoginRequest, login

    class _FakeReq:
        client = type("C", (), {"host": "10.0.0.2"})()
    with pytest.raises(HTTPException) as ei:
        await login(LoginRequest(username="nobody", password="whatever"), _FakeReq(), db_session)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(db_session):
    """is_active=False 的账号 → 401（即使密码对）"""
    from fastapi import HTTPException
    from routers.auth import LoginRequest, login
    fam = await _make_family_with(db_session)
    user = await _make_user(db_session, fam.id, "alice", "secret")
    user.is_active = False
    await db_session.commit()

    class _FakeReq:
        client = type("C", (), {"host": "10.0.0.3"})()
    with pytest.raises(HTTPException) as ei:
        await login(LoginRequest(username="alice", password="secret"), _FakeReq(), db_session)
    assert ei.value.status_code == 401


# ============== 防爆破 ==============

@pytest.mark.asyncio
async def test_login_lockout_after_max_failures(db_session):
    """连续 login_max_failures 次失败 → 第 N+1 次请求 429"""
    from fastapi import HTTPException
    from routers.auth import LoginRequest, login
    # 清掉其它测试残留
    _login_fail.clear()
    _login_locked.clear()

    fam = await _make_family_with(db_session)
    await _make_user(db_session, fam.id, "alice", "right_pw")

    class _FakeReq:
        client = type("C", (), {"host": "10.1.1.1"})()

    # 前 N-1 次失败 = 401；第 N 次失败时记录已达阈值，触发 429
    for i in range(settings.login_max_failures - 1):
        with pytest.raises(HTTPException) as ei:
            await login(LoginRequest(username="alice", password="wrong"), _FakeReq(), db_session)
        assert ei.value.status_code == 401, f"iter {i}: 应该是 401"

    # 第 5 次失败 → 触发锁定（429）
    with pytest.raises(HTTPException) as ei:
        await login(LoginRequest(username="alice", password="wrong"), _FakeReq(), db_session)
    assert ei.value.status_code == 429
    assert "锁定" in ei.value.detail or "频繁" in ei.value.detail

    # 下一次直接被锁
    with pytest.raises(HTTPException) as ei:
        await login(LoginRequest(username="alice", password="wrong"), _FakeReq(), db_session)
    assert ei.value.status_code == 429
    assert "锁定" in ei.value.detail or "频繁" in ei.value.detail

    # 即便这次密码对了，也还是 429
    with pytest.raises(HTTPException) as ei:
        await login(LoginRequest(username="alice", password="right_pw"), _FakeReq(), db_session)
    assert ei.value.status_code == 429

    _login_fail.clear()
    _login_locked.clear()


@pytest.mark.asyncio
async def test_successful_login_clears_failure_count(db_session):
    """登录成功后清空该 IP 的失败计数 → 不会被前一次失败拖到锁定"""
    from routers.auth import LoginRequest, login
    _login_fail.clear()
    _login_locked.clear()
    fam = await _make_family_with(db_session)
    await _make_user(db_session, fam.id, "alice", "right_pw")

    class _FakeReq:
        client = type("C", (), {"host": "10.2.2.2"})()

    # 3 次失败（不到阈值）
    for _ in range(3):
        with pytest.raises(HTTPException):
            await login(LoginRequest(username="alice", password="wrong"), _FakeReq(), db_session)
    assert "10.2.2.2" in _login_fail
    assert len(_login_fail["10.2.2.2"]) == 3

    # 登录成功 → 清空
    resp = await login(LoginRequest(username="alice", password="right_pw"), _FakeReq(), db_session)
    assert resp.token_type == "bearer"
    assert "10.2.2.2" not in _login_fail
    assert "10.2.2.2" not in _login_locked
    _login_fail.clear()
    _login_locked.clear()


# ============== 改密 ==============

@pytest.mark.asyncio
async def test_change_password_success(db_session):
    """改密：原密码对 → 200，hash 真的被更新"""
    from routers.auth import ChangePasswordRequest, change_password
    fam = await _make_family_with(db_session)
    user = await _make_user(db_session, fam.id, "alice", "old_pass")
    old_hash = user.password_hash

    req = ChangePasswordRequest(old_password="old_pass", new_password="new_pass")
    resp = await change_password(req, user, db_session)
    assert resp["ok"] is True

    await db_session.refresh(user)
    assert user.password_hash != old_hash
    assert verify_password("new_pass", user.password_hash)
    assert not verify_password("old_pass", user.password_hash)


@pytest.mark.asyncio
async def test_change_password_wrong_old(db_session):
    """改密：原密码错 → 401，hash 不变"""
    from fastapi import HTTPException
    from routers.auth import ChangePasswordRequest, change_password
    fam = await _make_family_with(db_session)
    user = await _make_user(db_session, fam.id, "alice", "old_pass")
    old_hash = user.password_hash

    req = ChangePasswordRequest(old_password="WRONG_PW", new_password="new_pass")
    with pytest.raises(HTTPException) as ei:
        await change_password(req, user, db_session)
    assert ei.value.status_code == 401
    assert "原密码" in ei.value.detail

    await db_session.refresh(user)
    assert user.password_hash == old_hash


# ============== JWT / 依赖注入 ==============

@pytest.mark.asyncio
async def test_get_current_user_no_token(db_session):
    """无 Authorization header → 401"""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await get_current_user(None, db_session)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_malformed(db_session):
    """Authorization 不是 Bearer 格式 → 401"""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await get_current_user("Basic abc", db_session)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_signature(db_session):
    """伪造 token（错 secret 签的） → 401"""
    from fastapi import HTTPException
    bad_token = create_jwt({"sub": 1}, "WRONG-SECRET", 3600)
    with pytest.raises(HTTPException) as ei:
        await get_current_user(f"Bearer {bad_token}", db_session)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_expired(db_session):
    """过期 token → 401"""
    from fastapi import HTTPException
    fam = await _make_family_with(db_session)
    user = await _make_user(db_session, fam.id, "alice")
    expired = create_jwt(
        {"sub": user.id, "role": user.role, "family_id": user.family_id},
        settings.jwt_secret,
        -10,  # 10 秒前已过期
    )
    with pytest.raises(HTTPException) as ei:
        await get_current_user(f"Bearer {expired}", db_session)
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_valid(db_session):
    """合法 token → 返回 user 对象"""
    fam = await _make_family_with(db_session)
    user = await _make_user(db_session, fam.id, "alice")
    token = create_jwt(
        {"sub": user.id, "role": user.role, "family_id": user.family_id},
        settings.jwt_secret,
        3600,
    )
    got = await get_current_user(f"Bearer {token}", db_session)
    assert got.id == user.id
    assert got.username == "alice"


@pytest.mark.asyncio
async def test_get_current_user_inactive(db_session):
    """is_active=False 的用户拿到合法 token → 401（防止停用后还能用）"""
    from fastapi import HTTPException
    fam = await _make_family_with(db_session)
    user = await _make_user(db_session, fam.id, "alice")
    user.is_active = False
    await db_session.commit()
    token = create_jwt(
        {"sub": user.id, "role": user.role, "family_id": user.family_id},
        settings.jwt_secret,
        3600,
    )
    with pytest.raises(HTTPException) as ei:
        await get_current_user(f"Bearer {token}", db_session)
    assert ei.value.status_code == 401


# ============== 角色守卫 ==============

@pytest.mark.asyncio
async def test_require_parent_child_rejected(db_session):
    """孩子账号访问家长端点 → 403"""
    from fastapi import HTTPException
    fam = await _make_family_with(db_session)
    child = await _make_child(db_session, fam.id)
    child_user = await _make_user(db_session, fam.id, "kiddo", role="child", child_id=child.id)
    with pytest.raises(HTTPException) as ei:
        await require_parent(child_user)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_require_parent_allowed(db_session):
    fam = await _make_family_with(db_session)
    p = await _make_user(db_session, fam.id, "p1", role="parent")
    out = await require_parent(p)
    assert out.id == p.id


# ============== setup 端点 ==============

@pytest.mark.asyncio
async def test_setup_creates_default_family_and_user(db_session):
    """首次启动：无 user 时建家庭 + 家长 → 立即签 token"""
    from routers.auth import SetupRequest, setup, setup_status

    # 初始：默认家庭已由 conftest 引擎创建（_make_family_with 不需要再调）
    # 但要确保 families 表里至少有一条
    fam_count = (await db_session.execute(select(Family.id))).scalars().all()
    # 复用现有默认家庭
    if not fam_count:
        await _make_family_with(db_session)

    # 二次 setup → 409
    req = SetupRequest(family_name="新家", username="admin", password="abcdef", display_name="管理员")
    resp = await setup(req, db_session)
    assert resp.token_type == "bearer"
    assert resp.user.username == "admin"
    assert resp.user.role == "parent"

    # 此时再调一次 setup → 409
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        await setup(req, db_session)
    assert ei.value.status_code == 409


@pytest.mark.asyncio
async def test_setup_status(db_session):
    """无 user → needs_setup=True；有 user → False"""
    from routers.auth import setup_status
    # db_session 默认空 user
    resp = await setup_status(db_session)
    assert resp["needs_setup"] is True

    fam = await _make_family_with(db_session)
    await _make_user(db_session, fam.id, "p1")
    resp2 = await setup_status(db_session)
    assert resp2["needs_setup"] is False


# ============== Scope 隔离 ==============

@pytest.mark.asyncio
async def test_get_accessible_child_ids_parent_sees_all(db_session):
    """家长：可访问 = 本家庭所有孩子"""
    from dependencies import get_accessible_child_ids
    fam = await _make_family_with(db_session)
    c1 = await _make_child(db_session, fam.id, "娃1")
    c2 = await _make_child(db_session, fam.id, "娃2")
    p = await _make_user(db_session, fam.id, "parent", role="parent")

    ids = await get_accessible_child_ids(p, db_session)
    assert ids == {c1.id, c2.id}


@pytest.mark.asyncio
async def test_get_accessible_child_ids_child_sees_only_self(db_session):
    """孩子：仅自己 child_id"""
    from dependencies import get_accessible_child_ids
    fam = await _make_family_with(db_session)
    c1 = await _make_child(db_session, fam.id, "娃1")
    c2 = await _make_child(db_session, fam.id, "娃2")
    child_user = await _make_user(db_session, fam.id, "kiddo", role="child", child_id=c1.id)

    ids = await get_accessible_child_ids(child_user, db_session)
    assert ids == {c1.id}
    assert c2.id not in ids


@pytest.mark.asyncio
async def test_assert_child_access_blocks_other(db_session):
    """assert_child_access 校验：不是自己/本家庭的 → 403"""
    from fastapi import HTTPException
    from dependencies import assert_child_access
    fam = await _make_family_with(db_session)
    c1 = await _make_child(db_session, fam.id, "娃1")
    c2 = await _make_child(db_session, fam.id, "娃2")
    p = await _make_user(db_session, fam.id, "p", role="parent")

    # 家长只能访问本家庭
    accessible = {c1.id}
    assert_child_access(accessible, c1.id)  # OK 不抛

    with pytest.raises(HTTPException) as ei:
        assert_child_access(accessible, c2.id)
    assert ei.value.status_code == 403


# ============== /me 端点 ==============

@pytest.mark.asyncio
async def test_me_endpoint_returns_user_and_accessible(db_session):
    """/me 返回 user + accessible_child_ids"""
    from routers.auth import me
    fam = await _make_family_with(db_session)
    c1 = await _make_child(db_session, fam.id)
    p = await _make_user(db_session, fam.id, "p", role="parent")

    resp = await me(p, db_session)
    assert resp.user.id == p.id
    assert resp.accessible_child_ids == [c1.id]


@pytest.mark.asyncio
async def test_me_endpoint_child_only_sees_self(db_session):
    """/me 孩子端点：仅返回自己 child_id"""
    from routers.auth import me
    fam = await _make_family_with(db_session)
    c1 = await _make_child(db_session, fam.id)
    c2 = await _make_child(db_session, fam.id)
    kid = await _make_user(db_session, fam.id, "kid", role="child", child_id=c1.id)

    resp = await me(kid, db_session)
    assert resp.user.role == "child"
    assert resp.accessible_child_ids == [c1.id]


# ============== 安全工具单元测试 ==============

def test_hash_password_format_and_verifies():
    """hash 输出格式正确，能 verify"""
    h = hash_password("hello world")
    parts = h.split("$")
    assert len(parts) == 4
    assert parts[0] == "pbkdf2_sha256"
    assert parts[1] == "600000"
    assert verify_password("hello world", h) is True
    assert verify_password("wrong", h) is False


def test_hash_password_unique_salt():
    """相同密码两次哈希不同（salt 随机）"""
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
    assert verify_password("same", a)
    assert verify_password("same", b)


def test_verify_password_malformed_returns_false():
    """存储格式坏 → False（不抛）"""
    assert verify_password("anything", "garbage$") is False
    assert verify_password("anything", "") is False
    assert verify_password("anything", "alg$bad") is False


def test_jwt_roundtrip_and_expiry():
    """JWT 签发 + 验证，过期后失效"""
    payload = {"sub": 42, "role": "parent"}
    tok = create_jwt(payload, "secret", 3600)
    decoded = __import__("utils.security", fromlist=["decode_jwt"]).decode_jwt(tok, "secret")
    assert decoded["sub"] == 42
    assert decoded["role"] == "parent"
    assert decoded["exp"] > int(time.time())

    # 过期
    expired = create_jwt(payload, "secret", -10)
    assert __import__("utils.security", fromlist=["decode_jwt"]).decode_jwt(expired, "secret") is None

    # 错 secret
    bad = create_jwt(payload, "secret", 3600)
    assert __import__("utils.security", fromlist=["decode_jwt"]).decode_jwt(bad, "other-secret") is None


# ============== 登录失败计数清理（单元） ==============

def test_record_login_fail_triggers_lock_after_threshold():
    """_record_login_fail 调用 N 次后第 N 次返回 True"""
    _login_fail.clear()
    _login_locked.clear()
    ip = "9.9.9.9"
    for i in range(settings.login_max_failures - 1):
        assert _record_login_fail(ip) is False
    # 第 N 次触发
    assert _record_login_fail(ip) is True
    assert ip in _login_locked
    _login_fail.clear()
    _login_locked.clear()


def test_is_login_locked_returns_none_when_not_locked():
    _login_fail.clear()
    _login_locked.clear()
    assert _is_login_locked("1.2.3.4") is None