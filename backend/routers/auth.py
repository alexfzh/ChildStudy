"""认证路由：登录 / 登出 / 当前用户 / 首次启动引导

POST /api/auth/setup  — 首次启动无 user 时调用，建家庭 + 建第一个家长账号
POST /api/auth/login  — 用户名 + 密码 → 返回 JWT
POST /api/auth/logout — 客户端清 token，服务端 noop（JWT 是 stateless）
GET  /api/auth/me     — 返回当前 user + 可访问孩子列表
GET  /api/auth/users  — 家长查询本家庭所有用户
POST /api/auth/users  — 家长建子账号（家长或孩子）

设计上：登出不做服务端 blacklist（增加 DB 表 + 复杂度，本地家庭工具不值得）；
JWT 24h 过期 + 客户端清 token 足够。
"""
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from dependencies import get_current_user, require_parent
from models import Child, Family, User
from utils.security import create_jwt, hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["认证"])

# ============ 登录防爆破（v1.7.1，内存方案） ============
# 单进程 uvicorn 内可靠；key = 来源 IP。连续失败达阈值 → 锁定 lock_seconds。
# 线程安全用锁保护；并发极低，粗粒度足够。
_login_lock = threading.Lock()
_login_fail = {}  # {ip: [fail_timestamps...]}
_login_locked = {}  # {ip: unlock_timestamp}
_login_max_failures = max(settings.login_max_failures, 1)
_login_lock_seconds = max(settings.login_lock_minutes * 60, 1)


def _record_login_fail(ip: str) -> bool:
    """记录一次失败；返回 True 表示本次失败后已触发锁定。"""
    now = time.time()
    with _login_lock:
        _prune_login_state(now)
        lst = _login_fail.setdefault(ip, [])
        lst.append(now)
        # 只保留最近一段窗口内的失败，避免字典无限膨胀
        cutoff = now - max(_login_lock_seconds, 3600)
        _login_fail[ip] = [t for t in lst if t > cutoff]
        if len(_login_fail[ip]) >= _login_max_failures:
            _login_locked[ip] = now + _login_lock_seconds
            _login_fail.pop(ip, None)
            logger.warning("登录防爆破：来源 %s 连续失败 %d 次，锁定 %d 分钟", ip, _login_max_failures, _login_lock_seconds // 60)
            return True
    return False


def _is_login_locked(ip: str) -> Optional[float]:
    """若 IP 被锁定返回还需等待秒数（约数），否则返回 None。"""
    with _login_lock:
        _prune_login_state(time.time())
        unlock = _login_locked.get(ip)
        if unlock:
            wait = unlock - time.time()
            if wait > 0:
                return wait
            _login_locked.pop(ip, None)
    return None


def _clear_login_fail(ip: str) -> None:
    """登录成功后清空该 IP 的失败记录。"""
    with _login_lock:
        _login_fail.pop(ip, None)
        _login_locked.pop(ip, None)


def _prune_login_state(now: float) -> None:
    """清掉已过期/超龄条目，防止内存泄漏。"""
    for k in [k for k, u in _login_locked.items() if u <= now]:
        _login_locked.pop(k, None)
    cutoff = now - 86400
    for k in [k for k, lst in _login_fail.items() if not lst or lst[-1] < cutoff]:
        _login_fail.pop(k, None)


def _client_ip(request: Request) -> str:
    """取真实客户端 IP（无反向代理时为直连地址）。"""
    # 若有反代可在此读取 X-Forwarded-For；当前直连场景 client.host 即真实 IP
    return request.client.host if request.client else "unknown"


# ============ Pydantic Schemas ============

class SetupRequest(BaseModel):
    """首次启动引导"""
    family_name: str = Field(min_length=1, max_length=64, default="我的家")
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    avatar_color: str
    family_id: int
    child_id: Optional[int] = None
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AccessibleChildrenOut(BaseModel):
    accessible_child_ids: list[int]


class MeResponse(BaseModel):
    user: UserOut
    accessible_child_ids: list[int]


class CreateUserRequest(BaseModel):
    """家长建子账号"""
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)
    role: str = Field(pattern="^(parent|child)$")
    child_id: Optional[int] = None  # role=child 时必填
    avatar_color: str = Field(default="#6366f1", max_length=16)


# ============ 端点 ============

@router.get("/setup-status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    """前端启动时查：是否需要走 setup wizard。无 user → 返回 needs_setup=True。"""
    result = await db.execute(select(User.id).limit(1))
    has_users = result.first() is not None
    return {"needs_setup": not has_users}


@router.post("/setup", response_model=TokenResponse)
async def setup(req: SetupRequest, db: AsyncSession = Depends(get_db)):
    """首次启动建家庭 + 建第一个家长账号。

    仅在系统无 user 时可调用，否则 409。

    现有数据迁移场景：如果 families 表已存在（init_db 迁移会建一个默认 '我的家'），
    则将第一个家长账号加入该默认家庭，避免新建家庭和已有孩子隔离。
    """
    existing = (await db.execute(select(User.id).limit(1))).first()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "系统已初始化，请用登录接口")

    # 检查 username 全局唯一（DB UNIQUE 约束兜底，应用层先查一次给友好提示）
    dup = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已被占用")

    # 选择家庭：复用默认家庭（migration 建）还是新建？
    existing_family = (await db.execute(select(Family).order_by(Family.id).limit(1))).scalar_one_or_none()
    if existing_family:
        family = existing_family  # 复用默认家庭，孩子数据已在里面
        logger.info("setup: 复用现有默认家庭 %s (id=%d)", family.name, family.id)
    else:
        family = Family(name=req.family_name)
        db.add(family)
        await db.flush()
        logger.info("setup: 新建家庭 %s (id=%d)", family.name, family.id)

    user = User(
        family_id=family.id,
        username=req.username,
        password_hash=hash_password(req.password),
        role="parent",
        display_name=req.display_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 自动签发 token 让用户立即进入系统
    token = create_jwt(
        {"sub": user.id, "role": user.role, "family_id": user.family_id},
        settings.jwt_secret,
        settings.jwt_expire_seconds,
    )
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_seconds,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    # 防爆破：该 IP 已被锁定 → 直接 429
    wait = _is_login_locked(ip)
    if wait is not None:
        logger.warning("登录被拒（限流）：来源 %s 处于锁定期，尚需约 %ds", ip, int(wait))
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "尝试过于频繁，请稍后再试")

    user = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
    ok = bool(user and user.is_active and verify_password(req.password, user.password_hash))
    if not ok:
        triggered = _record_login_fail(ip)
        logger.warning("登录失败：来源 %s，用户名 %r", ip, req.username)
        if triggered:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "尝试过于频繁，账号已临时锁定，请稍后再试")
        # 统一返回模糊错误，避免暴露用户存在性
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")

    # 登录成功：清失败记录 + 日志留痕
    _clear_login_fail(ip)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    token = create_jwt(
        {"sub": user.id, "role": user.role, "family_id": user.family_id},
        settings.jwt_secret,
        settings.jwt_expire_seconds,
    )
    logger.info("登录成功：来源 %s，用户 %s (id=%s, role=%s)", ip, user.username, user.id, user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expire_seconds,
        user=UserOut.model_validate(user),
    )


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """已登录用户修改自己的密码：校验原密码后更新哈希。"""
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "原密码错误")
    user.password_hash = hash_password(req.new_password)
    await db.commit()
    await db.refresh(user)
    return {"ok": True, "msg": "密码修改成功"}


@router.post("/logout")
async def logout(_user: User = Depends(get_current_user)):
    """服务端 noop，前端清 token 即可。"""
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
async def me(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if user.role == "parent":
        result = await db.execute(select(Child.id).where(Child.family_id == user.family_id))
        ids = sorted(result.scalars().all())
    else:
        ids = [user.child_id] if user.child_id else []
    return MeResponse(
        user=UserOut.model_validate(user),
        accessible_child_ids=ids,
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """家长查询本家庭所有账号（含其他家长和孩子）。"""
    user = await db.get(User, _parent.id)  # 拿到 family_id
    result = await db.execute(
        select(User).where(User.family_id == user.family_id).order_by(User.role, User.id)
    )
    return [UserOut.model_validate(u) for u in result.scalars().all()]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    req: CreateUserRequest,
    parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    """家长创建本家庭新账号（另一个家长，或孩子账号）。"""
    # username 唯一性
    dup = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已被占用")

    if req.role == "child":
        if req.child_id is None:
            raise HTTPException(422, "孩子账号必须绑定 child_id")
        # 校验 child 必须在本家庭
        child = await db.get(Child, req.child_id)
        if not child or child.family_id != parent.family_id:
            raise HTTPException(404, "孩子不存在或不属于本家庭")
        # 一个孩子一个账号：检查是否已被绑定
        bound = (await db.execute(
            select(User).where(User.child_id == req.child_id)
        )).scalar_one_or_none()
        if bound:
            raise HTTPException(status.HTTP_409_CONFLICT, f"该孩子已绑定账号：{bound.username}")
        user = User(
            family_id=parent.family_id,
            username=req.username,
            password_hash=hash_password(req.password),
            role="child",
            display_name=req.display_name,
            avatar_color=req.avatar_color,
            child_id=req.child_id,
        )
    else:
        user = User(
            family_id=parent.family_id,
            username=req.username,
            password_hash=hash_password(req.password),
            role="parent",
            display_name=req.display_name,
            avatar_color=req.avatar_color,
        )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("家长 %s 建账号：%s (%s)", parent.username, user.username, user.role)
    return UserOut.model_validate(user)


TokenResponse.model_rebuild()
