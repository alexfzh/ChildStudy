"""应用配置：统一管理环境变量和默认值"""
import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("childstudy")

BASE_DIR = Path(__file__).resolve().parent

# 默认占位密钥。仅作兜底，部署时必须通过 .env 的 JWT_SECRET 覆盖，否则启动即拒绝。
DEFAULT_JWT_SECRET = "change-me-in-production-please-use-32-bytes-random"


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

    # CSV 导入行数上限（防止 10MB 大文件含数万行把进程卡死）
    max_import_rows: int = 5000

    # 多用户认证（v1.6.0）
    jwt_secret: str = "change-me-in-production-please-use-32-bytes-random"  # 生产必须改！
    jwt_expire_seconds: int = 86400  # 24h
    allowed_origins: str = "*"  # 逗号分隔，CORS 白名单；家庭局域网默认全允许，生产环境可限制具体 origin

    # 启动时校验 JWT secret 强度（防弱密钥被暴力破解 / 占位密钥被伪造任意角色 token）
    def model_post_init(self, __context):
        if self.jwt_secret == DEFAULT_JWT_SECRET:
            # 占位密钥等于公开字符串，任何人都可伪造任意角色 token → 直接 fail-fast 拒绝启动
            raise ValueError(
                "安全拦截：JWT_SECRET 仍为默认占位值，存在被伪造任意角色 token 的严重风险！"
                "请在 backend/.env 中设置强随机密钥（≥32 字符，例如 `openssl rand -hex 32`）后重启服务。"
            )
        if len(self.jwt_secret) < 32:
            logger.warning(
                "JWT_SECRET 长度仅 %d 字符（推荐 ≥32），请生成强随机密钥后重启服务",
                len(self.jwt_secret),
            )

    # 登录防爆破（v1.7.1）：窗口内连续失败达阈值则锁定来源 IP 一段时间
    login_max_failures: int = 5  # 阈值：连续失败次数
    login_lock_minutes: int = 15  # 锁定时长（分钟）

    # 通用接口限流（P2#9）：每 IP 每分钟请求上限；0 = 关闭（默认，开发/测试不干扰）
    rate_limit_per_minute: int = 0


settings = Settings()
