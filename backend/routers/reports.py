"""AI 报告管理路由（手动导入外部 AI 的输出）"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids
from models import AIReport, Child, Exam, Homework
from schemas import (
    AIReportCreate,
    AIReportListItem,
    AIReportOut,
    AIReportUpdate,
    ContextExportResponse,
    OkResponse,
)
from utils.analysis import build_child_context_markdown

router = APIRouter(prefix="/api/reports", tags=["AI 报告"])


@router.get("", response_model=list[AIReportListItem])
async def list_reports(
    child_id: int = Query(..., description="孩子 ID"),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """列出某孩子的所有 AI 报告（按创建时间倒序）"""
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    q = await db.execute(
        select(AIReport).where(AIReport.child_id == child_id).order_by(desc(AIReport.created_at))
    )
    return list(q.scalars().all())


@router.post("", response_model=AIReportOut)
async def create_report(
    payload: AIReportCreate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """导入一条 AI 报告（用户从外部 AI 复制 markdown 后粘贴回来）"""
    assert_child_access(accessible, payload.child_id)
    child = await db.get(Child, payload.child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    report = AIReport(
        child_id=payload.child_id,
        title=payload.title,
        raw_markdown=payload.raw_markdown,
        summary=payload.summary,
        source=payload.source,
        period_start=payload.period_start,
        period_end=payload.period_end,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/{report_id}", response_model=AIReportOut)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """获取单条 AI 报告详情"""
    report = await db.get(AIReport, report_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    assert_child_access(accessible, report.child_id)
    return report


@router.put("/{report_id}", response_model=AIReportOut)
async def update_report(
    report_id: int,
    payload: AIReportUpdate,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """更新 AI 报告（用户修正标题 / 内容）"""
    report = await db.get(AIReport, report_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    assert_child_access(accessible, report.child_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(report, k, v)
    await db.commit()
    await db.refresh(report)
    return report


@router.delete("/{report_id}", response_model=OkResponse)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """删除 AI 报告"""
    report = await db.get(AIReport, report_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    assert_child_access(accessible, report.child_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    await db.delete(report)
    await db.commit()
    return OkResponse(message="报告已删除")


@router.get("/export/context", response_model=ContextExportResponse)
async def export_context(
    child_id: int = Query(..., description="孩子 ID"),
    period_days: int = Query(90, ge=1, le=3650, description="数据周期（天）"),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """导出当前孩子的学情数据为 markdown（用户复制到外部 AI prompt 用）"""
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    since = datetime.now().date() - timedelta(days=period_days)

    exams_q = await db.execute(
        select(Exam).where(Exam.child_id == child_id).where(Exam.exam_date >= since)
    )
    exams = list(exams_q.scalars().all())

    homeworks_q = await db.execute(
        select(Homework).where(Homework.child_id == child_id).where(Homework.homework_date >= since)
    )
    homeworks = list(homeworks_q.scalars().all())

    md = build_child_context_markdown(child, exams, homeworks, period_days)
    return ContextExportResponse(
        child_name=child.name,
        period_days=period_days,
        context_markdown=md,
    )
