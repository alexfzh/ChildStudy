"""FastAPI 主入口"""
import logging
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
    version="1.6.0",
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


# 健康检查（公开）
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "学业成长系统"}


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
    question_banks,
    textbook,
    study_progress,
    project_works,
    kp_unit,
    question_kp,
    kp_progress,
]
for r in _PROTECTED:
    app.include_router(r.router, dependencies=[Depends(get_current_user)])


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

