"""Pydantic schemas — 按业务域拆分。

所有 schema 通过此 __init__.py 重新导出，保持 `from schemas import XxxCreate` 向后兼容。
"""
from schemas.ai_report import *  # noqa: F401,F403
from schemas.child import *  # noqa: F401,F403
from schemas.common import *  # noqa: F401,F403
from schemas.dashboard import (  # noqa: F401
    CompareData,
    DashboardData,
    SubjectStat,
)
from schemas.exam import *  # noqa: F401,F403
from schemas.growth import *  # noqa: F401,F403
from schemas.homework import *  # noqa: F401,F403
from schemas.interest import *  # noqa: F401,F403
from schemas.knowledge_point import *  # noqa: F401,F403
from schemas.kp_progress import *  # noqa: F401,F403
from schemas.kp_unit import *  # noqa: F401,F403
from schemas.question_bank import *  # noqa: F401,F403
from schemas.question_kp import *  # noqa: F401,F403
from schemas.rewards import *  # noqa: F401,F403
from schemas.social_emotional import *  # noqa: F401,F403
from schemas.textbook import *  # noqa: F401,F403
from schemas.timeline import *  # noqa: F401,F403
from schemas.wrong_question import *  # noqa: F401,F403
