"""公开的系统配置（只暴露前端需要的非敏感字段）"""
from fastapi import APIRouter
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/api/config", tags=["系统配置"])


class PublicConfig(BaseModel):
    max_children: int


@router.get("", response_model=PublicConfig)
async def get_public_config():
    """返回前端可见的运行时配置（不含敏感信息）"""
    return PublicConfig(max_children=settings.max_children)
