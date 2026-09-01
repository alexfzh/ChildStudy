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
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from dependencies import get_current_user, require_parent
from models import Child, Family, User
from utils.security import create_jwt, hash_password, verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["认证"])


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

    class Config:
        from_attributes = True


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
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.username == req.username))).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(req.password, user.password_hash):
        # 统一返回模糊错误，避免暴露用户存在性
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
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
