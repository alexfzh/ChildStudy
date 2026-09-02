"""AI 报告管理路由（手动导入外部 AI 的输出）+ 学情周报/月报（v1.7.0）"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids, require_parent
from models import AIReport, Child, Exam, Homework, PeriodicReport
from schemas import (
    AIReportCreate,
    AIReportListItem,
    AIReportOut,
    AIReportUpdate,
    ContextExportResponse,
    OkResponse,
    PeriodicReportGenerateRequest,
    PeriodicReportOut,
)
from utils.analysis import build_child_context_markdown
from utils.pdf_builder import build_period_report_pdf
from utils.period_report import build_period_report

router = APIRouter(prefix="/api/reports", tags=["AI 报告 + 学情周/月报"])

# PDF 存储目录：backend 根目录下 ./reports/{child_id}/{report_id}.pdf
BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_ROOT / "reports"


def _pdf_path_for(child_id: int, report_id: int) -> Path:
    """获取 PDF 文件路径，自动创建目录"""
    p = REPORTS_DIR / str(child_id) / f"{report_id}.pdf"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


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


# ============ 学情周报/月报（v1.7.0）============

@router.post("/period/generate", response_model=PeriodicReportOut)
async def generate_period_report(
    child_id: int = Query(..., description="孩子 ID"),
    payload: PeriodicReportGenerateRequest = ...,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """生成学情周报/月报 PDF（v1.7.0）

    流程：聚合数据 → reportlab 渲染 PDF → 存到 reports/{child_id}/{id}.pdf → 写 PeriodicReport 记录。
    """
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")
    if payload.period_type not in ("weekly", "monthly"):
        raise HTTPException(400, "period_type 必须是 weekly 或 monthly")

    # 1. 聚合
    data = await build_period_report(
        db,
        child_id=child_id,
        period_type=payload.period_type,
        period_end=payload.period_end,
    )

    # 2. 渲染 PDF
    pdf_bytes = build_period_report_pdf(data)

    # 3. 先落 DB（拿到 id），再写文件
    report = PeriodicReport(
        child_id=child_id,
        period_type=payload.period_type,
        period_start=date.fromisoformat(data["period"]["start"]),
        period_end=date.fromisoformat(data["period"]["end"]),
        pdf_path="",  # 待填
        file_size=len(pdf_bytes),
        overview_json=json.dumps(
            {
                "overview": data["overview"],
                "subject_count": len(data["subject_stats"]),
                "wrong_kp_count": len(data["wrong_kp_distribution"]),
                "rank_count": len(data["ranks"]),
                "action_suggestion_count": len(data["action_suggestions"]),
            },
            ensure_ascii=False,
        ),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    pdf_path = _pdf_path_for(child_id, report.id)
    pdf_path.write_bytes(pdf_bytes)
    rel_path = pdf_path.relative_to(BACKEND_ROOT).as_posix()
    report.pdf_path = rel_path
    await db.commit()
    await db.refresh(report)

    return PeriodicReportOut(
        id=report.id,
        child_id=report.child_id,
        period_type=report.period_type,
        period_start=report.period_start,
        period_end=report.period_end,
        file_size=report.file_size,
        download_url=f"/api/reports/period/{report.id}/download",
        created_at=report.created_at,
    )


@router.get("/period/list", response_model=list[PeriodicReportOut])
async def list_period_reports(
    child_id: int = Query(..., description="孩子 ID"),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """列出孩子的所有周/月报（按创建时间倒序）"""
    assert_child_access(accessible, child_id)
    q = await db.execute(
        select(PeriodicReport)
        .where(PeriodicReport.child_id == child_id)
        .order_by(desc(PeriodicReport.created_at))
    )
    rows = list(q.scalars().all())
    return [
        PeriodicReportOut(
            id=r.id,
            child_id=r.child_id,
            period_type=r.period_type,
            period_start=r.period_start,
            period_end=r.period_end,
            file_size=r.file_size,
            download_url=f"/api/reports/period/{r.id}/download",
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/period/{report_id}/download")
async def download_period_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """下载 PDF 文件"""
    report = await db.get(PeriodicReport, report_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    assert_child_access(accessible, report.child_id)

    pdf_path = BACKEND_ROOT / report.pdf_path if report.pdf_path else _pdf_path_for(report.child_id, report.id)
    if not pdf_path.exists():
        raise HTTPException(404, "PDF 文件已丢失，请重新生成")
    period_zh = {"weekly": "周报", "monthly": "月报"}.get(report.period_type, "学情报告")
    filename = f"ChildStudy-{period_zh}-{report.child_id}-{report.period_start.isoformat()}.pdf"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.delete("/period/{report_id}", response_model=OkResponse)
async def delete_period_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
    _parent=Depends(require_parent),
):
    """删除一条周/月报（家长权限；同时删除 PDF 文件）"""
    report = await db.get(PeriodicReport, report_id)
    if not report:
        raise HTTPException(404, "报告不存在")
    assert_child_access(accessible, report.child_id)
    pdf_path = BACKEND_ROOT / report.pdf_path if report.pdf_path else _pdf_path_for(report.child_id, report.id)
    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception as e:
            # 文件删不掉不影响 DB 删除（孤儿文件可人工清理）
            print(f"⚠️ 删除 PDF 失败: {pdf_path} -> {e}")
    await db.delete(report)
    await db.commit()
    return OkResponse(message="报告已删除")
