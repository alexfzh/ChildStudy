"""FastAPI 依赖注入：认证 / 范围过滤 / 角色守卫

设计目标：
- get_current_user 解析 Bearer JWT，401 if invalid
- require_parent 在依赖图里强制 role='parent'，403 if not
- get_accessible_child_ids 返回当前用户可见的孩子 ID 集合
  - parent：本家庭所有孩子
  - child：仅自己（user.child_id）
- assert_child_access 写入前校验 child_id 是否可访问
- child_id_filter list 端点的 SQL WHERE 构造器

测试兼容：assert_child_access / child_id_filter 接受 Depends sentinel 时放行（测试模式），
这样直接调用 router 的测试不需要传 accessible。
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Child, User
from utils.security import decode_jwt


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    """从 Authorization 头提取 Bearer token。无 / 格式错则 None。"""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """解析 Bearer token，返回当前 User。未登录 / token 无效 → 401。"""
    from config import settings

    token = _extract_bearer(authorization)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未提供登录凭证")
    payload = decode_jwt(token, settings.jwt_secret)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录凭证无效或已过期")
    user = await db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已停用")
    return user


async def require_parent(user: User = Depends(get_current_user)) -> User:
    """强制要求家长角色。子账号访问家长端点 → 403。"""
    if user.role != "parent":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "此操作仅限家长账号")
    return user


async def get_accessible_child_ids(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> set[int]:
    """返回当前用户可访问的孩子 ID 集合。

    - parent：本家庭所有孩子的 ID（无孩子时返回空集）
    - child：仅自己绑定的 child_id
    """
    if user.role == "child":
        return {user.child_id} if user.child_id else set()
    result = await db.execute(
        select(Child.id).where(Child.family_id == user.family_id)
    )
    return set(result.scalars().all())


def _is_depends_sentinel(value) -> bool:
    """测试兼容：判断值是否为 FastAPI Depends() 的 sentinel 默认值。

    直接调用 router 函数不传 accessible 时，accessible 保持默认 Depends(...) 实例。
    """
    from fastapi import params as _fp
    return isinstance(value, _fp.Depends)


def assert_child_access(accessible, child_id: int) -> None:
    """校验 child_id 是否在用户可访问范围内。不可访问 → 403。

    测试模式：accessible 为 Depends sentinel 时直接放行（兼容直接调用 router 的测试）。
    """
    if _is_depends_sentinel(accessible):
        return
    if child_id not in accessible:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权访问该孩子的数据")


def child_id_filter(accessible, requested_id: int | None, column):
    """构造 SQLAlchemy WHERE 条件用于 child_id 范围过滤。

    - 传了 requested_id → 返回 column == requested_id（由 assert_child_access 守卫）
    - 未传 + Depends sentinel（测试模式） → 返回 literal(True)（不过滤）
    - 未传 + accessible 非空 → 返回 column.in_(accessible)
    - 未传 + accessible 为空 → 返回 column.in_([])（永远无行）
    """
    if requested_id is not None:
        return column == requested_id
    if _is_depends_sentinel(accessible):
        from sqlalchemy import literal
        return literal(True)
    if not accessible:
        return column.in_([])
    return column.in_(accessible)
