"""通用响应 / 状态"""

from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ============ 通用 ============
class OkResponse(BaseModel):
    ok: bool = True
    message: str = "操作成功"




# ============ 设置（已废弃：保留 OkResponse 兼容） ============
# v1.x 的 SettingsPayload / SettingsStatus 已随 AI 模块下线。
# 设置页改为"工作流说明"，不再有 API endpoint。



