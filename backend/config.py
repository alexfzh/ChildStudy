"""应用配置：统一管理环境变量和默认值"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_debug: bool = True

    # 数据库
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'childstudy.db'}"

    # 多孩子上限（运行时可调 .env，配置项）
    max_children: int = 4

    # 上传
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 10

    # 多用户认证（v1.6.0）
    jwt_secret: str = "change-me-in-production-please-use-32-bytes-random"  # 生产必须改！
    jwt_expire_seconds: int = 86400  # 24h
    allowed_origins: str = "*"  # 逗号分隔，CORS 白名单；家庭局域网默认全允许，生产环境可限制具体 origin


settings = Settings()
