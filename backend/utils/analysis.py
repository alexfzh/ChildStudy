"""统计与基础分析工具(不依赖 AI 的纯数学计算)"""
from collections import defaultdict
from statistics import mean
from typing import Any, Dict, List, Optional


def pct(score: float, full: float) -> float:
    """得分百分比"""
    if full <= 0:
        return 0.0
    return round(score / full * 100, 2)


def build_subject_stats(exams: List[Any]) -> List[Dict[str, Any]]:
    """按科目聚合统计：平均分、趋势等"""
    grouped: Dict[str, List[Any]] = defaultdict(list)
    for e in exams:
        grouped[e.subject].append(e)

    stats = []
    for subject, items in grouped.items():
        items_sorted = sorted(items, key=lambda x: x.exam_date)
        pcts = [pct(e.score, e.full_score) for e in items_sorted]
        if len(pcts) >= 2:
            recent = mean(pcts[-3:]) if len(pcts) >= 3 else mean(pcts[-2:])
            earlier = mean(pcts[:-3]) if len(pcts) > 3 else mean(pcts[: max(1, len(pcts) // 2)])
            delta = recent - earlier
            trend = "up" if delta > 2 else ("down" if delta < -2 else "flat")
        else:
            trend = "flat"
            delta = 0
        stats.append({
            "subject": subject,
            "avg_score": round(mean(pcts), 2),
            "max_score": max(pcts),
            "min_score": min(pcts),
            "exam_count": len(items_sorted),
            "trend": trend,
            "delta": round(delta, 2),
            "latest_score": pcts[-1] if pcts else 0,
        })
    return sorted(stats, key=lambda x: x["avg_score"], reverse=True)


def build_trend_data(exams: List[Any]) -> Dict[str, Any]:
    """构建按时间排序的科目趋势数据(给 ECharts 用)

    每个科目输出两个 series(同个 series 点之间用线连起来，跨日期自动平滑):
    - <科目>-分数 (实线，主色)
    - <科目>-班均 (虚线，灰色，有数据时才出)

    数据格式：每个 series.data 是 [[iso_date, value], ...] 二维数组，
    ECharts xAxis type='time' 会自动按时间顺序连成平滑折线。
    """
    by_subject: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in sorted(exams, key=lambda x: x.exam_date):
        by_subject[e.subject].append({
            "date": e.exam_date.isoformat(),
            "name": e.exam_name,
            "score": e.score,
            "full": e.full_score,
            "pct": pct(e.score, e.full_score),
            "class_average": e.class_average,
            "class_average_pct": (
                pct(e.class_average, e.full_score) if e.class_average is not None else None
            ),
        })

    series = []
    for subject, points in by_subject.items():
        # 1. 分数(实线)—— 按时间排序的二维数组
        score_pts = sorted([[p["date"], p["pct"]] for p in points], key=lambda x: x[0])
        series.append({
            "name": f"{subject}-分数",
            "type": "line",
            "smooth": True,
            "lineStyle": {"width": 2.5},
            "data": score_pts,
            "_kind": "score",
        })
        # 2. 班级平均分(虚线 + 灰色)—— 只取有班均的点
        avg_points = [p for p in points if p["class_average_pct"] is not None]
        if avg_points:
            avg_pts = sorted([[p["date"], p["class_average_pct"]] for p in avg_points], key=lambda x: x[0])
            series.append({
                "name": f"{subject}-班均",
                "type": "line",
                "smooth": True,
                "lineStyle": {"type": "dashed", "width": 1.5},
                "itemStyle": {"color": "#94a3b8"},
                "data": avg_pts,
                "_kind": "class_average",
            })
    # dates 保留为所有考试日期的有序列表(前端可用作 xAxis 标签或 tooltip 参考)
    all_dates = sorted({e.exam_date.isoformat() for e in exams})
    return {"dates": all_dates, "series": series}


def build_radar_data(subject_stats: List[Dict[str, Any]], focus_subjects: Optional[List[str]] = None) -> Dict[str, Any]:
    """构造雷达图：优先基于关注科目，无数据的关注科目补 0"""
    if not subject_stats and not focus_subjects:
        return {"indicators": [], "values": []}
    # 建立 stats lookup
    stats_map = {s["subject"]: s for s in subject_stats}
    # 决定显示哪些科目：focus_subjects 优先，否则全部有数据的科目
    if focus_subjects:
        subjects = focus_subjects
    else:
        subjects = list(stats_map.keys())
    if not subjects:
        return {"indicators": [], "values": []}
    indicators = [{"name": s, "max": 100} for s in subjects]
    values = [round(stats_map.get(s, {}).get("avg_score", 0), 1) for s in subjects]
    return {"indicators": indicators, "values": values}


def detect_weak_subjects(subject_stats: List[Dict[str, Any]], threshold: float = 75.0) -> List[str]:
    """识别薄弱科目：平均分低于阈值或最近下降明显"""
    weak = []
    for s in subject_stats:
        if s["avg_score"] < threshold:
            weak.append(s["subject"])
        elif s["trend"] == "down" and s["delta"] < -5:
            weak.append(s["subject"])
    return weak


def build_action_suggestions(exams: List[Any], stats: List[Dict[str, Any]], weak: List[str]) -> List[str]:
    """基于数据生成可执行的家辅导建议(2-3 条)"""
    suggestions: List[str] = []
    if not exams or not stats:
        return ["数据还不多，继续录入考试后我会给出更具体的建议。"]

    # 1. 薄弱科目建议
    for w in weak[:2]:
        s = next((x for x in stats if x["subject"] == w), None)
        if not s:
            continue
        if s["trend"] == "down":
            suggestions.append(f"📉 {w} 最近呈下降趋势(较前期 {s['delta']:+.1f}%)，建议重点复习近期错题，并每周增加 1-2 次专项练习。")
        else:
            suggestions.append(f"📊 {w} 平均 {s['avg_score']}%，低于警戒线。建议优先补基础，从课本例题和课后习题入手。")

    # 2. 强势科目保持
    if stats:
        best = stats[0]
        if best["avg_score"] >= 90:
            suggestions.append(f"🌟 {best['subject']} 表现优秀(平均 {best['avg_score']}%)，建议适当增加拓展题，保持优势。")

    # 3. 整体建议
    if len(suggestions) < 2:
        overall = sum(s["avg_score"] for s in stats) / len(stats)
        if overall >= 85:
            suggestions.append("✅ 整体表现良好，继续保持现有节奏，注意均衡各科时间分配。")
        else:
            suggestions.append("💪 整体还有提升空间，建议制定每周学习计划，重点攻克薄弱知识点。")

    return suggestions[:3]


def build_child_context(exams: List[Any], homeworks: List[Any]) -> Dict[str, Any]:
    """Prepare AI analysis context summary (save tokens)"""
    stats = build_subject_stats(exams)
    weak = detect_weak_subjects(stats)
    recent = sorted(exams, key=lambda x: x.exam_date, reverse=True)[:5]

    # 最近作业表现
    recent_hw = sorted(homeworks, key=lambda x: x.homework_date, reverse=True)[:10]
    hw_summary = []
    for h in recent_hw:
        if h.accuracy is not None:
            hw_summary.append(f"{h.subject}《{h.title}》正确率{h.accuracy}%")

    return {
        "subject_stats": stats,
        "weak_subjects": weak,
        "recent_exams": [
            {
                "subject": e.subject,
                "name": e.exam_name,
                "score": e.score,
                "full": e.full_score,
                "date": e.exam_date.isoformat(),
                "pct": pct(e.score, e.full_score),
                "class_average": e.class_average,
                "class_average_pct": (
                    pct(e.class_average, e.full_score) if e.class_average is not None else None
                ),
                "knowledge_points": e.knowledge_points or [],
                "wrong_questions": e.wrong_questions or "",
            }
            for e in recent
        ],
        "recent_homeworks": hw_summary,
        "total_exams": len(exams),
        "total_homeworks": len(homeworks),
    }


def build_child_context_markdown(child: Any, exams: List[Any], homeworks: List[Any], period_days: int = 90) -> str:
    """导出当前数据为 markdown 格式上下文(用户复制到外部 AI prompt)"""
    stats = build_subject_stats(exams)
    weak = detect_weak_subjects(stats)
    recent = sorted(exams, key=lambda x: x.exam_date, reverse=True)

    lines: List[str] = []
    lines.append(f"# 孩子学情数据快照 · {child.name}")
    lines.append("")
    lines.append(f"- 年级：{child.grade}")
    if child.school:
        lines.append(f"- 学校：{child.school}")
    lines.append(f"- 数据周期：最近 {period_days} 天")
    lines.append(f"- 考试总数：{len(exams)} 次")
    lines.append(f"- 作业记录：{len(homeworks)} 条")
    lines.append("")

    # 科目统计
    if stats:
        lines.append("## 📊 各科目表现统计")
        lines.append("")
        lines.append("| 科目 | 平均得分率 | 最高 | 最低 | 考试数 | 趋势 |")
        lines.append("|---|---|---|---|---|---|")
        for s in stats:
            trend_emoji = {"up": "📈 上升", "down": "📉 下降", "flat": "➡️ 持平"}.get(s["trend"], s["trend"])
            lines.append(f"| {s['subject']} | {s['avg_score']}% | {s['max_score']}% | {s['min_score']}% | {s['exam_count']} | {trend_emoji} |")
        lines.append("")

    # 薄弱科目
    if weak:
        lines.append("## 🎯 薄弱科目(需重点关注)")
        lines.append("")
        for w in weak:
            lines.append(f"- {w}")
        lines.append("")

    # 近期考试
    if recent:
        lines.append("## 📝 近期考试记录")
        lines.append("")
        lines.append("| 日期 | 科目 | 名称 | 得分 | 班级平均 | 差值 | 知识点 | 错题 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for e in recent[:15]:  # 最多列 15 条
            kp = "、".join(e.knowledge_points or []) if e.knowledge_points else "—"
            wrong = (e.wrong_questions or "—").replace("\n", " ").replace("|", "/")
            if len(wrong) > 50:
                wrong = wrong[:50] + "…"
            # 班级平均分(可选)+ 差值(个人 - 班均)
            ca = f"{e.class_average:.1f}/{e.full_score}" if e.class_average is not None else "—"
            if e.class_average is not None:
                diff = e.score - e.class_average
                diff_str = f"{diff:+.1f}" if diff != 0 else "0"
            else:
                diff_str = "—"
            lines.append(f"| {e.exam_date.isoformat()} | {e.subject} | {e.exam_name} | {e.score}/{e.full_score} | {ca} | {diff_str} | {kp} | {wrong} |")
        if len(recent) > 15:
            lines.append(f"\n*(还有 {len(recent) - 15} 条考试未列出)*")
        lines.append("")

    # 近期作业
    recent_hw = sorted(homeworks, key=lambda x: x.homework_date, reverse=True)[:10]
    if recent_hw:
        lines.append("## 📚 近期作业表现")
        lines.append("")
        for h in recent_hw:
            line = f"- {h.homework_date.isoformat()} · {h.subject}《{h.title}》"
            if h.accuracy is not None:
                line += f" · 正确率 {h.accuracy}%"
            if h.difficulty and h.difficulty != "normal":
                diff_map = {"easy": "简单", "normal": "中等", "hard": "困难"}
                line += f" · 难度 {diff_map.get(h.difficulty, h.difficulty)}"
            lines.append(line)
        lines.append("")

    # 底部提示
    lines.append("---")
    lines.append("")
    lines.append("**请基于以上数据，生成结构化学情报告**，包含：")
    lines.append("1. 整体评估(2-3 句)")
    lines.append("2. 优势(3-5 条)")
    lines.append("3. 薄弱点(3-5 条)")
    lines.append("4. 学习趋势观察(2-3 条)")
    lines.append("5. 知识盲点(按科目推断)")
    lines.append("6. 家庭辅导建议(每周 3-5 条，要具体可执行)")
    lines.append("")
    lines.append("语气：温和理性、鼓励为主、客观分析。建议要具体(在家就能做)。")

    return "\n".join(lines)

