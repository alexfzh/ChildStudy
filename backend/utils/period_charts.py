"""学情周报/月报图表生成（v1.7.0）

matplotlib 生成 PNG BytesIO → reportlab 直接嵌入 PDF。
中文：注册 Windows 系统 msyh.ttc（微软雅黑），无则回退到默认。
"""
from __future__ import annotations

import io
import os
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # 无 GUI
import matplotlib.pyplot as plt
from matplotlib import font_manager


# ============ 中文字体设置 ============
def _setup_chinese_font() -> Any:
    """注册中文字体（Windows msyh.ttc）；返回 FontProperties 实例"""
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",   # 微软雅黑（Windows 首选）
        "C:/Windows/Fonts/msyhbd.ttc",
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                font_manager.fontManager.addfont(p)
                # 返回的 FontProperties 复用
                return font_manager.FontProperties(fname=p)
            except Exception:
                continue
    # fallback: 不显式指定，让 matplotlib 走默认（可能中文方块）
    return None


_ZH_FONT = None
def _font():
    global _ZH_FONT
    if _ZH_FONT is None:
        _ZH_FONT = _setup_chinese_font()
    return _ZH_FONT


def _style():
    """设置全局 matplotlib rcParams（中文 sans-serif）"""
    fp = _font()
    if fp:
        plt.rcParams["font.sans-serif"] = [fp.get_name()]
    plt.rcParams["axes.unicode_minus"] = False


# ============ 图表函数 ============

def chart_score_trend(exams: List[Dict[str, Any]], subject_stats: List[Dict[str, Any]]) -> Optional[bytes]:
    """各科成绩趋势线（按时间排序）

    exams: [{date, name, subject, score, full_score, pct}, ...]
    返回 PNG bytes；数据不足返回 None
    """
    if not exams or len(exams) < 1:
        return None

    _style()

    # 按科目分组，按日期排序
    by_subj: Dict[str, List[tuple]] = {}
    for e in exams:
        by_subj.setdefault(e["subject"], []).append((e["date"], e["pct"]))
    for s in by_subj:
        by_subj[s].sort(key=lambda x: x[0])

    fig, ax = plt.subplots(figsize=(7, 3.2))
    colors = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]

    for i, (subj, points) in enumerate(by_subj.items()):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.plot(xs, ys, marker="o", linewidth=2, markersize=6,
                color=colors[i % len(colors)], label=subj)

    ax.set_title("各科成绩走势", fontproperties=_font(), fontsize=14)
    ax.set_xlabel("考试日期", fontproperties=_font())
    ax.set_ylabel("得分率 (%)", fontproperties=_font())
    ax.set_ylim(0, 105)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", prop=_font())
    fig.autofmt_xdate(rotation=30)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def chart_wrong_kp_distribution(wrong_kp_dist: List[Dict[str, Any]]) -> Optional[bytes]:
    """错题按 KP 分布（柱状图）"""
    if not wrong_kp_dist:
        return None

    _style()
    items = wrong_kp_dist[:10]  # 最多 10 个
    labels = [f"{x['kp_name']}" for x in items]
    counts = [x["count"] for x in items]

    fig, ax = plt.subplots(figsize=(7, max(2.5, 0.45 * len(items) + 1)))
    bars = ax.barh(range(len(items)), counts, color="#ef4444", alpha=0.85)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(labels, fontproperties=_font(), fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("错题数", fontproperties=_font())
    ax.set_title("错题按知识点分布（Top 10）", fontproperties=_font(), fontsize=14)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for bar, cnt in zip(bars, counts, strict=True):
        ax.text(cnt + 0.1, bar.get_y() + bar.get_height() / 2,
                str(cnt), va="center", fontsize=9)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def chart_kp_progress_pie(kp_progress: Dict[str, int]) -> Optional[bytes]:
    """KP 掌握度饼图（new / learning / strong / mastered）"""
    if not kp_progress or kp_progress.get("total", 0) == 0:
        return None

    _style()
    data = {
        "new": kp_progress.get("new", 0),
        "learning": kp_progress.get("learning", 0),
        "strong": kp_progress.get("strong", 0),
        "mastered": kp_progress.get("mastered", 0),
    }
    labels_zh = {"new": "未学", "learning": "学习中", "strong": "已掌握", "mastered": "精通"}
    colors = ["#94a3b8", "#f59e0b", "#10b981", "#6366f1"]
    sizes = [v for v in data.values()]
    _labels = [f"{labels_zh[k]} ({v})" for k, v in data.items() if v > 0]

    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    # 仅展示 >0 的扇区
    filtered = [(v, c, label) for v, c, label in zip(sizes, colors, [labels_zh[k] for k in data.keys()], strict=True) if v > 0]
    if not filtered:
        plt.close(fig)
        return None
    sizes_f = [x[0] for x in filtered]
    colors_f = [x[1] for x in filtered]
    labels_f = [f"{x[2]} ({x[0]})" for x in filtered]
    ax.pie(sizes_f, labels=labels_f, colors=colors_f, autopct="%1.0f%%",
           startangle=90, textprops={"fontproperties": _font(), "fontsize": 11})
    ax.set_title(f"知识点掌握度（共 {kp_progress['total']} 个 KP）", fontproperties=_font(), fontsize=14)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def chart_rank_radar(ranks: List[Dict[str, Any]]) -> Optional[bytes]:
    """段位雷达图（按科目段位星数 + 平均分）"""
    if not ranks or len(ranks) < 3:
        return None

    _style()
    import numpy as np
    subjects = [r["subject"] for r in ranks]
    # 用 avg_score 作为雷达值
    scores = [r["avg_score"] for r in ranks]
    # 闭环
    N = len(subjects)
    angles = [n / N * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    scores += scores[:1]

    fig, ax = plt.subplots(figsize=(5, 4), subplot_kw={"projection": "polar"})
    ax.plot(angles, scores, color="#6366f1", linewidth=2)
    ax.fill(angles, scores, color="#6366f1", alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(subjects, fontproperties=_font())
    ax.set_ylim(0, 100)
    ax.set_yticks([60, 75, 90, 100])
    ax.set_title("各科均分雷达图", fontproperties=_font(), fontsize=14, pad=15)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()
