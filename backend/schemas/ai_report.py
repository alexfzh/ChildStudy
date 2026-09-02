"""AI 报告（手动导入）"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ AI 报告（手动导入） ============
class AIReportCreate(BaseModel):
    """用户从外部 AI 粘贴回来的分析报告"""
    child_id: int
    title: str = Field(..., min_length=1, max_length=128)
    raw_markdown: str = Field(..., min_length=1)
    summary: Optional[str] = Field(None, max_length=500)
    source: Optional[str] = Field(None, max_length=64, description="来源：deepseek / kimi / gpt-4o / 自定义")
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class AIReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=128)
    raw_markdown: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = Field(None, max_length=500)
    source: Optional[str] = Field(None, max_length=64)


class AIReportOut(BaseModel):
    id: int
    child_id: int
    title: str
    raw_markdown: str
    summary: Optional[str]
    source: Optional[str]
    period_start: Optional[date]
    period_end: Optional[date]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AIReportListItem(BaseModel):
    """列表用的精简版"""
    id: int
    child_id: int
    title: str
    summary: Optional[str]
    source: Optional[str]
    period_start: Optional[date]
    period_end: Optional[date]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ContextExportResponse(BaseModel):
    """导出当前数据为 markdown 上下文（给外部 AI）"""
    child_name: str
    period_days: int
    context_markdown: str


# ============ 学情周报/月报（v1.7.0）============

class PeriodicReportOut(BaseModel):
    """学情周报/月报（列表项）"""
    id: int
    child_id: int
    period_type: str
    period_start: date
    period_end: date
    file_size: int
    download_url: str  # 相对路径：/api/reports/{id}/download
    created_at: datetime


class PeriodicReportGenerateRequest(BaseModel):
    """生成周报/月报请求"""
    period_type: str = "weekly"  # weekly / monthly
    period_end: Optional[date] = None  # 默认今天；可指定过去某天




