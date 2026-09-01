"""系统版本 + 升级管理"""
import os

from fastapi import APIRouter
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/api/system", tags=["系统"])


class VersionInfo(BaseModel):
    version: str
    build_time: str
    python_version: str
    backend_host: str
    backend_port: int
    database: str
    debug_mode: bool


class UpgradeLog(BaseModel):
    timestamp: str
    from_version: str
    to_version: str
    status: str
    detail: str = ""


# 当前版本（手动 bump，对应前端 package.json version）
CURRENT_VERSION = "1.6.0"
BUILD_TIME = "2026-09-01"


@router.get("/version", response_model=VersionInfo)
async def get_version():
    """返回当前系统版本信息"""
    return VersionInfo(
        version=CURRENT_VERSION,
        build_time=BUILD_TIME,
        python_version=f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        backend_host=settings.app_host,
        backend_port=settings.app_port,
        database=settings.database_url.split("///")[-1] if "///" in settings.database_url else settings.database_url,
        debug_mode=settings.app_debug,
    )


@router.get("/upgrade-log", response_model=list[UpgradeLog])
async def get_upgrade_log():
    """返回升级历史（当前仅返回模拟数据，后续接入真实 migration 日志）"""
    return [
        UpgradeLog(
            timestamp="2026-09-01T10:50:00",
            from_version="1.5.0",
            to_version="1.6.0",
            status="success",
            detail="新增: 家庭成员多用户登录 (家长/孩子账号 + JWT 认证 + 家庭数据隔离 + 孩子 scope 过滤 + LAN 访问).",
        ),
        UpgradeLog(
            timestamp="2026-08-31T14:30:00",
            from_version="1.4.0",
            to_version="1.5.0",
            status="success",
            detail="新增: exercises 练习耗时 time_spent 记录 + 练习页计时器 + 知识点筛选预加载 + 题目进度色块导航 + some/any 17 题入库并关联 U1 单元 + 修正 coffee 疑问句答案/解析 + 清理临时文件.",
        ),
        UpgradeLog(
            timestamp="2026-08-31T11:48:00",
            from_version="1.3.0",
            to_version="1.4.0",
            status="success",
            detail="新增: 考试分析模块 (单科单次总分分析 + 历次趋势 + 卷面分析). 新建 ExamQuestion 表 + 9 种题型枚举 + AI 整卷录入接口 (paper_total_score 校验). utils/exam_analyzer.py 单测 25 个全过.",
        ),
        UpgradeLog(
            timestamp="2026-08-31T11:23:00",
            from_version="1.2.0",
            to_version="1.3.0",
            status="success",
            detail="新增: 错题本智能关联题库与知识点（多信号匹配引擎）+ 答题自动归错题本 + python-multipart CVE-2026-24486 修复 + 后端依赖升级 (fastapi 0.115 → 0.141, starlette 1.6)",
        ),
        UpgradeLog(
            timestamp="2026-08-28T11:30:00",
            from_version="1.1.0",
            to_version="1.2.0",
            status="success",
            detail="新增: 教材章节系统 + Question-KP 关联 + KPStudyProgress",
        ),
    ]


@router.post("/upgrade")
async def trigger_upgrade():
    """触发版本升级（当前仅做版本检查，实际升级需手动执行 migration）"""
    return {
        "ok": True,
        "message": f"当前已是最新版本 {CURRENT_VERSION}，无需升级",
        "current_version": CURRENT_VERSION,
    }
