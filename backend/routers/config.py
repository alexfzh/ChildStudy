"""公开的系统配置（只暴露前端需要的非敏感字段）"""
from fastapi import APIRouter
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/api/config", tags=["系统配置"])


class PublicConfig(BaseModel):
    max_children: int
    server_host: str
    server_port: int
    lan_url: str


@router.get("", response_model=PublicConfig)
async def get_public_config():
    """返回前端可见的运行时配置（不含敏感信息）"""
    import socket
    lan_ip = "127.0.0.1"
    try:
        # 获取本机局域网 IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    return PublicConfig(
        max_children=settings.max_children,
        server_host=settings.app_host,
        server_port=settings.app_port,
        lan_url=f"http://{lan_ip}:{settings.app_port}",
    )
