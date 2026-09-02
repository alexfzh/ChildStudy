"""系统版本 + 升级管理"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

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
CURRENT_VERSION = "1.7.2"
BUILD_TIME = "2026-09-02"

# 全量升级历史存在 data/upgrade_log.json（不提交 git，部署端自动积累）
_LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "upgrade_log.json"

# 首次启动种子数据（仅当文件不存在时写入）
_SEED_LOG = [
    {
        "timestamp": "2026-08-28T11:30:00",
        "from_version": "1.1.0",
        "to_version": "1.2.0",
        "status": "success",
        "detail": "新增: 教材章节系统 + Question-KP 关联 + KPStudyProgress",
    },
    {
        "timestamp": "2026-08-31T11:23:00",
        "from_version": "1.2.0",
        "to_version": "1.3.0",
        "status": "success",
        "detail": "新增: 错题本智能关联题库与知识点（多信号匹配引擎）+ 答题自动归错题本 + python-multipart CVE-2026-24486 修复 + 后端依赖升级 (fastapi 0.115 → 0.141, starlette 1.6)",
    },
    {
        "timestamp": "2026-08-31T11:48:00",
        "from_version": "1.3.0",
        "to_version": "1.4.0",
        "status": "success",
        "detail": "新增: 考试分析模块 (单科单次总分分析 + 历次趋势 + 卷面分析). 新建 ExamQuestion 表 + 9 种题型枚举 + AI 整卷录入接口 (paper_total_score 校验). utils/exam_analyzer.py 单测 25 个全过.",
    },
    {
        "timestamp": "2026-08-31T14:30:00",
        "from_version": "1.4.0",
        "to_version": "1.5.0",
        "status": "success",
        "detail": "新增: exercises 练习耗时 time_spent 记录 + 练习页计时器 + 知识点筛选预加载 + 题目进度色块导航 + some/any 17 题入库并关联 U1 单元 + 修正 coffee 疑问句答案/解析 + 清理临时文件.",
    },
    {
        "timestamp": "2026-09-01T10:50:00",
        "from_version": "1.5.0",
        "to_version": "1.6.0",
        "status": "success",
        "detail": "新增: 家庭成员多用户登录 (家长/孩子账号 + JWT 认证 + 家庭数据隔离 + 孩子 scope 过滤 + LAN 访问).",
    },
    {
        "timestamp": "2026-09-01T16:50:00",
        "from_version": "1.6.0",
        "to_version": "1.7.0",
        "status": "success",
        "detail": "新增: 错题推荐对接新知识点体系(QuestionKnowledgePoint多对多 + KP↔Unit 三层去重: primary主KP / unit_extend同Unit拓展 / kp_name_fallback字符串兜底). 孩子端看板(ChildDashboard)+ bootstrapChild自举 + 修改密码(/api/auth/change-password + Settings) + 路由守卫tokenValidated校验 + 全局错误兜底(errorHandler + unhandledrejection) + JWT_SECRET轮换 + 端口8000回归修复 + 匿名写knowledge-points/rewards补require_parent + vite build配置修复(v1.7.0).",
    },
    {
        "timestamp": "2026-09-02T15:00:00",
        "from_version": "1.7.0",
        "to_version": "1.7.1",
        "status": "success",
        "detail": "安全加固: 登录防爆破限流(来源IP连续失败N次临时锁定返回429, 默认5次/15分钟, .env 可配 LOGIN_MAX_FAILURES/LOGIN_LOCK_MINUTES) + 登录成功/失败/锁定日志留痕(含来源IP). 面向公网无 HTTPS 部署的安全增强(v1.7.1).",
    },
    {
        "timestamp": "2026-09-02T21:00:00",
        "from_version": "1.7.1",
        "to_version": "1.7.2",
        "status": "success",
        "detail": "hotfix + 审计加固: dependencies.py B904 修复 (raise ... from err) + auth.py/rewards.py import sort + test_auth.py 新增 29 个用例 (登录/防爆破/改密/JWT/角色守卫/范围隔离/setup/安全工具) 覆盖 v1.7.0-v1.7.1 安全关键路径 + frontend audit:routes 脚本 (路由 meta 校验) + README 新增部署安全须知章节 (单 worker / JWT secret rotation / CORS 不要 credentials / 端口暴露策略) + ruff check 全过 (v1.7.2).",
    },
]


def _load_log() -> list[dict]:
    """从文件加载全量升级历史，文件不存在则写入种子数据。"""
    try:
        if _LOG_FILE.exists():
            with open(_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass
    # 首次：写入种子数据
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(_SEED_LOG, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return list(_SEED_LOG)


def _save_log(log: list[dict]) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def add_upgrade(from_version: str, to_version: str, status: str = "success", detail: str = "") -> None:
    """版本升级时调用：追加一条记录，按时间倒序，最多保留 50 条。"""
    log = _load_log()
    log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_version": from_version,
        "to_version": to_version,
        "status": status,
        "detail": detail,
    })
    # 按 timestamp 倒序
    log.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    # 保留最近 50 条全量历史
    log = log[:50]
    _save_log(log)


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
    """返回最近 3 条升级历史（全量日志存在 data/upgrade_log.json）。"""
    log = _load_log()
    # 按时间倒序取前 3
    log.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return [UpgradeLog(**entry) for entry in log[:3]]


@router.post("/upgrade")
async def trigger_upgrade():
    """触发版本升级（当前仅做版本检查，实际升级需手动执行 migration）"""
    return {
        "ok": True,
        "message": f"当前已是最新版本 {CURRENT_VERSION}，无需升级",
        "current_version": CURRENT_VERSION,
    }
