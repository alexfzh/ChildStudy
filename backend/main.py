"""FastAPI 主入口"""
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db
from dependencies import get_current_user
from routers import (
    auth,
    children,
    config,
    dashboard,
    exams,
    exercises,
    growth,
    homework,
    import_export,
    interests,
    knowledge_points,
    kp_progress,
    kp_unit,
    project_works,
    question_banks,
    question_kp,
    quotes,
    reports,
    rewards,
    social_emotional,
    study_progress,
    system,
    textbook,
    timeline,
    wrong_questions,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("childstudy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库"""
    Path("./data").mkdir(exist_ok=True)
    Path("./uploads").mkdir(exist_ok=True)
    await init_db()
    logger.info("数据库初始化完成")
    yield


app = FastAPI(
    title="学业成长系统",
    description="为家长提供的孩子学习数据记录、AI 学情分析与可视化看板",
    version="1.8.1",
    lifespan=lifespan,
)

# 跨域：v1.6.0 起从 .env 的 ALLOWED_ORIGINS 读取（逗号分隔）
# 默认 *：家庭局域网环境，所有 origin 允许；如有外网暴露需求，请在 .env 里限制具体地址
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()] or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 简单 IP 限流中间件（防滥用；部署时由 .env 的 RATE_LIMIT_PER_MINUTE 启用）----
class RateLimitMiddleware:
    """基于来源 IP 的滑动窗口限流（单进程内有效，多 worker 需共享存储）。

    默认关闭（RATE_LIMIT_PER_MINUTE=0）。仅限制 /api/*，放开登录与健康检查。
    """

    def __init__(self, app, per_minute: int = 0):
        self.app = app
        self.per_minute = per_minute
        self._hits: dict[str, deque] = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if self.per_minute > 0 and scope.get("type") == "http":
            path = scope.get("path", "")
            if path.startswith("/api/") and path not in ("/api/auth/login", "/api/health"):
                ip = self._client_ip(scope)
                now = time.time()
                dq = self._hits[ip]
                while dq and dq[0] < now - 60:
                    dq.popleft()
                if len(dq) >= self.per_minute:
                    await self._send_429(send)
                    return
                dq.append(now)
        await self.app(scope, receive, send)

    @staticmethod
    def _client_ip(scope) -> str:
        for k, v in scope.get("headers", []):
            if k == b"x-forwarded-for":
                return v.decode().split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    @staticmethod
    async def _send_429(send):
        body = json.dumps({"detail": "请求过于频繁，请稍后再试"}).encode()
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [(b"content-type", b"application/json")],
        })
        await send({"type": "http.response.body", "body": body})


if settings.rate_limit_per_minute > 0:
    app.add_middleware(RateLimitMiddleware, per_minute=settings.rate_limit_per_minute)


# 健康检查（公开）
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "学业成长系统"}

# 生长发育标准数据（公开，不涉及隐私）
@app.get("/api/growth/standards")
async def public_growth_standards():
    from utils.growth_standards import (
        BMI_0_83, BMI_CUTOFFS_6_18, HEIGHT_0_83, HEIGHT_7_18, WEIGHT_0_83, WEIGHT_7_18,
    )
    from utils.growth_assessor import get_standard_description
    return {
        "schema_version": 1,
        "sources": [
            "WS/T 423-2022 (0-7 岁)",
            "WS/T 586-2018 (6-18 岁 BMI 切点)",
            "WS/T 611-2018 (7-18 岁身高)",
        ],
        "height_0_83_months": HEIGHT_0_83,
        "weight_0_83_months": WEIGHT_0_83,
        "bmi_0_83_months": BMI_0_83,
        "bmi_cutoffs_6_18": BMI_CUTOFFS_6_18,
        "height_7_18_years": HEIGHT_7_18,
        "weight_7_18_years": WEIGHT_7_18,
        "description": get_standard_description(),
    }


# 公开路由（无需认证）：auth、config、system、knowledge-points 只读参考
app.include_router(auth.router)
app.include_router(config.router)
app.include_router(system.router)
app.include_router(knowledge_points.router)

# 受保护路由（需登录）：依赖注入 get_current_user 会在所有端点上验证 Bearer token
# 数据隔离（家长只看自己家庭 / 孩子只看自己）在 router 内部通过 accessible_child_ids 实现
_PROTECTED = [
    children,
    exams,
    homework,
    timeline,
    dashboard,
    reports,
    import_export,
    wrong_questions,
    growth,
    social_emotional,
    interests,
    rewards,
    exercises,
    question_banks,
    textbook,
    study_progress,
    project_works,
    kp_unit,
    question_kp,
    kp_progress,
    quotes,
]
for r in _PROTECTED:
    app.include_router(r.router, dependencies=[Depends(get_current_user)])


# 用户上传文件（作品图片等）：独立静态目录，供前端 <img> 直接回取
# 注意：文件名由服务端生成（work_{id}_{ts}.ext），不可枚举；家庭局域网场景下可接受公开访问。
# 若需严格鉴权，应改为受保护端点 + 前端 fetch→blob 方式回取。
UPLOAD_DIR = Path("./uploads").resolve()
if UPLOAD_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# 静态资源（前端打包产物）
STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if STATIC_DIR.exists():
    # assets 目录可选（CDN 版前端不需要）
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """前端 SPA fallback"""
        # API 路径交给上方的路由处理
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file = STATIC_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )

