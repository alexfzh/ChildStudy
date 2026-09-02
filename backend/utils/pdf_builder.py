"""学情周报/月报 PDF 生成（v1.7.0）

基于 reportlab 拼装 PDF：
- 标题 / 概览数字 / 各科成绩表 / 趋势图 / 错题分布柱状图 / KP 掌握度饼图 / 段位榜 / 行动建议
- 中文：reportlab 内置 STSong-Light CID 字体
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.period_charts import (
    chart_kp_progress_pie,
    chart_rank_radar,
    chart_score_trend,
    chart_wrong_kp_distribution,
)

# ============ 字体注册 ============

_FONT_NAME = "STSong-Light"

def _ensure_font_registered() -> str:
    """注册 reportlab 内置中文 CID 字体（仅一次）"""
    try:
        pdfmetrics.getFont(_FONT_NAME)
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont(_FONT_NAME))
    return _FONT_NAME


# ============ 样式 ============

def _styles():
    base = getSampleStyleSheet()
    _ensure_font_registered()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName=_FONT_NAME, fontSize=20, leading=26, alignment=1),
        "h1": ParagraphStyle("H1", parent=base["Heading1"], fontName=_FONT_NAME, fontSize=15, leading=20, textColor=colors.HexColor("#1f2937"), spaceAfter=8),
        "h2": ParagraphStyle("H2", parent=base["Heading2"], fontName=_FONT_NAME, fontSize=12, leading=16, textColor=colors.HexColor("#4f46e5"), spaceAfter=6),
        "normal": ParagraphStyle("Normal", parent=base["Normal"], fontName=_FONT_NAME, fontSize=10, leading=14),
        "small": ParagraphStyle("Small", parent=base["Normal"], fontName=_FONT_NAME, fontSize=9, leading=12, textColor=colors.HexColor("#6b7280")),
        "tip": ParagraphStyle("Tip", parent=base["Normal"], fontName=_FONT_NAME, fontSize=10, leading=14, textColor=colors.HexColor("#059669"), leftIndent=8, spaceBefore=4),
    }


# ============ 文档构建 ============

def build_period_report_pdf(data: Dict[str, Any]) -> bytes:
    """根据 period_report 输出的 dict 渲染 PDF，返回二进制内容"""
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"学情报告-{data['child']['name']}-{data['period']['label']}",
        author="ChildStudy",
    )

    story = []

    # ── 1. 标题 ──
    period_type_zh = "周报" if data["period"]["type"] == "weekly" else "月报"
    story.append(Paragraph(f"{data['child']['name']} 的学情{period_type_zh}", st["title"]))
    story.append(Paragraph(data["period"]["label"], st["small"]))
    story.append(Paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", st["small"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── 2. 概览（数字 + 卡片）──
    story.append(Paragraph("📊 周期概览", st["h1"]))
    story.extend(_overview_block(data["overview"], st))
    story.append(Spacer(1, 0.5 * cm))

    # ── 3. 各科成绩统计表 ──
    story.append(Paragraph("📈 各科成绩统计", st["h1"]))
    if data["subject_stats"]:
        story.append(_subject_stats_table(data["subject_stats"]))
    else:
        story.append(Paragraph("本周无考试数据。", st["normal"]))
    story.append(Spacer(1, 0.4 * cm))

    # ── 4. 趋势图 ──
    trend_png = chart_score_trend(data["exams"], data["subject_stats"])
    if trend_png:
        story.append(Paragraph("📉 成绩走势", st["h1"]))
        story.append(Image(io.BytesIO(trend_png), width=16 * cm, height=7.4 * cm))
    else:
        story.append(Paragraph("📉 成绩走势：考试数据不足，无法绘图。", st["small"]))

    # ── 5. 错题按 KP 分布 ──
    wrong_png = chart_wrong_kp_distribution(data["wrong_kp_distribution"])
    if wrong_png:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("❌ 错题按知识点分布", st["h1"]))
        story.append(Image(io.BytesIO(wrong_png), width=15 * cm, height=5.5 * cm))
        if data["wrong_kp_distribution"]:
            story.append(_wrong_kp_top_table(data["wrong_kp_distribution"][:8]))

    # ── 6. KP 掌握度饼图 ──
    kp_pie = chart_kp_progress_pie(data["kp_progress"])
    if kp_pie:
        story.append(PageBreak())
        story.append(Paragraph("🎯 知识点掌握度", st["h1"]))
        story.append(Image(io.BytesIO(kp_pie), width=12 * cm, height=8 * cm))
        story.append(Paragraph(
            f"共 {data['kp_progress']['total']} 个知识点：未学 {data['kp_progress']['new']}、"
            f"学习中 {data['kp_progress']['learning']}、已掌握 {data['kp_progress']['strong']}、"
            f"精通 {data['kp_progress']['mastered']}。",
            st["normal"],
        ))

    # ── 7. 段位榜（雷达 + 表）──
    if data["ranks"]:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("🏆 各科段位榜", st["h1"]))
        radar = chart_rank_radar(data["ranks"])
        if radar:
            story.append(Image(io.BytesIO(radar), width=11 * cm, height=8 * cm))
        story.append(_ranks_table(data["ranks"]))

    # ── 8. 行动建议 ──
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("💡 行动建议", st["h1"]))
    if data["action_suggestions"]:
        for s in data["action_suggestions"]:
            story.append(Paragraph(f"• {s}", st["normal"]))
    else:
        story.append(Paragraph("暂无具体建议。", st["normal"]))

    # ── 9. 页脚 ──
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "本报告由 ChildStudy 系统自动生成 · 数据完全本地存储 · 隐私优先",
        st["small"],
    ))

    doc.build(story)
    return buf.getvalue()


# ============ 子组件 ============

def _overview_block(overview: Dict[str, Any], st) -> list:
    """概览数字（表格形式 4 列 × 2 行）"""
    cells = [
        ["考试数", "新增错题", "练习次数", "获得积分"],
        [str(overview["exam_count"]), str(overview["wrong_count"]),
         f"{overview['exercise_count']}（均分 {overview['exercise_avg_score']}）",
         f"+{overview['points_earned']} 分"],
        ["KP 总数", "未学/学习中", "已掌握", "精通"],
        [str(overview["kp_total"]),
         f"{overview['kp_new']} / {overview['kp_learning']}",
         str(overview["kp_strong"]),
         str(overview["kp_mastered"])],
    ]
    table = Table(
        [cells[0], cells[1], cells[2], cells[3]],
        colWidths=[4.2 * cm, 4.2 * cm, 4.2 * cm, 4.2 * cm],
    )
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f0fdf4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#059669")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 3), (-1, 3), colors.HexColor("#1f2937")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [table]


def _subject_stats_table(subject_stats: List[Dict[str, Any]]) -> Table:
    """各科统计表"""
    header = ["科目", "考试数", "平均分", "最高", "最低", "最新", "趋势", "Δ"]
    rows = [header]
    for s in subject_stats:
        rows.append([
            s["subject"],
            str(s["exam_count"]),
            f"{s['avg_score']:.1f}",
            f"{s['max_score']:.1f}",
            f"{s['min_score']:.1f}",
            f"{s['latest_score']:.1f}",
            {"up": "📈 上升", "down": "📉 下降", "flat": "➡️ 持平"}.get(s["trend"], s["trend"]),
            f"{s['delta']:+.1f}",
        ])

    t = Table(rows, colWidths=[2 * cm, 1.8 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm, 2.4 * cm, 1.6 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _wrong_kp_top_table(wrong_kp_dist: List[Dict[str, Any]]) -> Table:
    """错题按 KP 分布明细表"""
    header = ["知识点", "错题数"]
    rows = [header]
    for x in wrong_kp_dist:
        rows.append([x["kp_name"], str(x["count"])])
    t = Table(rows, colWidths=[12 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ef4444")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef2f2")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _ranks_table(ranks: List[Dict[str, Any]]) -> Table:
    """段位榜表"""
    header = ["科目", "段位", "★", "均分", "考试数", "累计积分"]
    rows = [header]
    for r in ranks:
        rows.append([
            r["subject"],
            r["tier"],
            str(r["stars"]),
            f"{r['avg_score']:.1f}",
            str(r["exam_count"]),
            str(r["total_points"]),
        ])
    t = Table(rows, colWidths=[2.4 * cm, 2 * cm, 1.2 * cm, 2 * cm, 2 * cm, 2.4 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t
