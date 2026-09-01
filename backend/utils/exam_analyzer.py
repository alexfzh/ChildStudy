"""考试分析算法（纯函数，可单测）

不依赖 DB / FastAPI，只接收 dataclass / dict 输入，返回分析结果。
所有 DB 查询在外面做完传进来（避免 ORM 在分析逻辑里做 N+1）。
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class ExamLike:
    """考试记录的最小视图（隔离 ORM）"""
    id: int
    child_id: int
    subject: str
    exam_name: str
    score: float
    full_score: float
    target_score: Optional[float]
    class_rank: Optional[int]
    grade_rank: Optional[int]
    exam_date: date
    knowledge_points: List[str]
    class_average: Optional[float]
    paper_total_score: Optional[float]
    paper_actual_scored: Optional[float]


@dataclass
class ExamQuestionLike:
    """考试题目的最小视图"""
    id: int
    exam_id: int
    section_name: str
    number: int
    type: str
    max_score: float
    scored: float
    is_correct: Optional[bool]
    knowledge_points: List[str]
    content: Optional[str] = None


# ============ 单次考试总分分析 ============

def _build_comparison(
    target: ExamLike,
    history: List[ExamLike],
) -> dict:
    """vs 历史 / 班级 / 目标的对比"""
    same_subject = [e for e in history if e.id != target.id and e.subject == target.subject]
    scores = [e.score for e in same_subject]
    result = {
        "vs_subject_mean": None,
        "vs_subject_best": None,
        "vs_subject_worst": None,
        "vs_class_average": None,
        "target_delta": None,
        "target_reached": None,
    }
    if scores:
        result["vs_subject_mean"] = round(target.score - statistics.mean(scores), 2)
        result["vs_subject_best"] = round(target.score - max(scores), 2)
        result["vs_subject_worst"] = round(target.score - min(scores), 2)
    if target.class_average is not None:
        result["vs_class_average"] = round(target.score - target.class_average, 2)
    if target.target_score is not None:
        result["target_delta"] = round(target.score - target.target_score, 2)
        result["target_reached"] = target.score >= target.target_score
    return result


def _trend_position(target: ExamLike, history: List[ExamLike]) -> dict:
    """本次在历史时间轴上的位置"""
    same_subject = sorted(
        [e for e in history if e.subject == target.subject],
        key=lambda e: e.exam_date,
    )
    total = len(same_subject)
    if total == 0:
        return {"position": "only", "rank_in_n": 1, "total_n": 1, "percentile": 100.0}
    if total == 1:
        return {"position": "only", "rank_in_n": 1, "total_n": 1, "percentile": 100.0}

    scores = [e.score for e in same_subject]
    # rank_in_n: 1=最高分
    sorted_desc = sorted(scores, reverse=True)
    rank_in_n = sorted_desc.index(target.score) + 1 if target.score in sorted_desc else None
    if rank_in_n is None:
        # 浮点比较兜底
        rank_in_n = sum(1 for s in scores if s > target.score) + 1

    if rank_in_n == 1:
        position = "best"
    elif rank_in_n <= max(2, total // 3):
        position = "near_best"
    elif rank_in_n >= total:
        position = "worst"
    elif rank_in_n >= total - max(1, total // 3):
        position = "near_worst"
    else:
        position = "middle"

    percentile = round((total - rank_in_n + 1) / total * 100, 1)
    return {"position": position, "rank_in_n": rank_in_n, "total_n": total, "percentile": percentile}


def _generate_insights(
    target: ExamLike,
    comparison: dict,
    trend: dict,
) -> List[str]:
    """规则生成洞察句（不调 AI）"""
    insights: List[str] = []

    # 1. 目标达成
    if comparison.get("target_reached") is True:
        delta = comparison["target_delta"]
        insights.append(f"达到目标分 {target.target_score}，超出 {delta} 分")
    elif comparison.get("target_reached") is False:
        delta = comparison["target_delta"]
        if delta < -10:
            insights.append(f"距目标分 {target.target_score} 还差 {abs(delta)} 分")
        else:
            insights.append(f"距目标分 {target.target_score} 还差 {abs(delta)} 分")

    # 2. 班级对比
    cls_delta = comparison.get("vs_class_average")
    if cls_delta is not None:
        if cls_delta >= 10:
            insights.append(f"超越班级平均分 {cls_delta} 分，处于班级上游")
        elif cls_delta >= 5:
            insights.append(f"高于班级平均分 {cls_delta} 分")
        elif cls_delta <= -10:
            insights.append(f"低于班级平均分 {abs(cls_delta)} 分，需要重点关注")
        elif cls_delta < 0:
            insights.append(f"低于班级平均分 {abs(cls_delta)} 分")

    # 3. 历史位置
    pos = trend.get("position")
    if pos == "best":
        insights.append(f"是该科目历史最高分（{trend['total_n']} 次考试中）")
    elif pos == "worst":
        insights.append(f"是该科目历史最低分（{trend['total_n']} 次考试中）")
    elif pos == "near_best" and comparison.get("vs_subject_mean") is not None:
        m = comparison["vs_subject_mean"]
        if m > 0:
            insights.append(f"高于该科目历史平均分 {m} 分")

    # 4. 排名
    if target.class_rank is not None and target.class_rank <= 3:
        insights.append(f"班级排名 {target.class_rank}，进入班级前三")

    # 5. 知识点覆盖
    if not target.knowledge_points:
        insights.append("本次考试未标注涉及知识点，建议补充以便后续分析")
    elif len(target.knowledge_points) > 8:
        insights.append(f"本次考试涉及 {len(target.knowledge_points)} 个知识点，覆盖面广")

    return insights


def analyze_single_exam(
    target: ExamLike,
    history: List[ExamLike],
) -> dict:
    """单次考试总分分析（返回 dict，路由层包成 Pydantic）"""
    percentage = round(target.score / target.full_score * 100, 1) if target.full_score else 0.0
    comparison = _build_comparison(target, history)
    trend = _trend_position(target, history)
    insights = _generate_insights(target, comparison, trend)

    rank_info = {
        "class_rank": target.class_rank,
        "grade_rank": target.grade_rank,
    }
    target_info = None
    if target.target_score is not None:
        target_info = {
            "target_score": target.target_score,
            "delta": comparison["target_delta"],
            "reached": comparison["target_reached"],
        }

    return {
        "exam_id": target.id,
        "exam_name": target.exam_name,
        "subject": target.subject,
        "exam_date": target.exam_date,
        "score": target.score,
        "full_score": target.full_score,
        "percentage": percentage,
        "rank_info": rank_info,
        "target_info": target_info,
        "comparison": comparison,
        "trend_position": trend,
        "knowledge_points": target.knowledge_points,
        "insights": insights,
    }


# ============ 历次考试趋势分析 ============

def _trend_direction(scores: List[float]) -> tuple[str, str]:
    """用简单线性回归判定方向 + 强度"""
    n = len(scores)
    if n < 2:
        return "stable", "flat"

    # 斜率 = cov(x, y) / var(x), x = 0..n-1
    xs = list(range(n))
    mean_x = (n - 1) / 2
    mean_y = statistics.mean(scores)
    cov = sum((xs[i] - mean_x) * (scores[i] - mean_y) for i in range(n))
    var_x = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = cov / var_x

    # 强度 = 斜率 / 平均分（相对变化率）
    if mean_y == 0:
        return "stable", "flat"
    relative = abs(slope) / mean_y

    direction = "rising" if slope > 0 else "falling" if slope < 0 else "stable"
    if relative < 0.005:
        strength = "flat"
    elif relative < 0.015:
        strength = "weak"
    elif relative < 0.04:
        strength = "moderate"
    else:
        strength = "significant"
    return direction, strength


def _build_volatility(scores: List[float]) -> dict:
    """波动性分析"""
    if len(scores) < 2:
        return {"std_dev": 0.0, "max_delta": 0.0, "min_delta": 0.0, "stability": "stable"}
    deltas = [scores[i] - scores[i - 1] for i in range(1, len(scores))]
    std_dev = round(statistics.stdev(scores), 2) if len(scores) >= 2 else 0.0
    max_delta = round(max(deltas), 2)
    min_delta = round(min(deltas), 2)
    if std_dev < 2:
        stability = "stable"
    elif std_dev < 5:
        stability = "fluctuating"
    else:
        stability = "volatile"
    return {
        "std_dev": std_dev,
        "max_delta": max_delta,
        "min_delta": min_delta,
        "stability": stability,
    }


def _kp_evolution(history: List[ExamLike]) -> List[dict]:
    """知识点历次出现次数 + 总失分（按 subject.knowledge_points 统计）"""
    kp_count: dict[str, int] = {}
    kp_loss: dict[str, float] = {}
    for e in history:
        for kp in e.knowledge_points:
            kp_count[kp] = kp_count.get(kp, 0) + 1
            kp_loss[kp] = kp_loss.get(kp, 0) + max(0.0, e.full_score - e.score)
    result = []
    for kp in kp_count:
        result.append({
            "knowledge_point": kp,
            "appearances": kp_count[kp],
            "lost_score_total": round(kp_loss.get(kp, 0), 1),
        })
    result.sort(key=lambda x: (-x["appearances"], -x["lost_score_total"]))
    return result


def analyze_exam_history(
    child_id: int,
    subject: str,
    exams: List[ExamLike],
) -> dict:
    """历次考试趋势分析（输入按 exam_date 升序）"""
    if not exams:
        return {
            "subject": subject,
            "child_id": child_id,
            "period": {"start_date": None, "end_date": None},
            "exam_count": 0,
            "score_trend": [],
            "rank_trend": [],
            "volatility": {"std_dev": 0.0, "max_delta": 0.0, "min_delta": 0.0, "stability": "stable"},
            "target_progression": [],
            "best_exam": None,
            "worst_exam": None,
            "trend_direction": "stable",
            "trend_strength": "flat",
            "knowledge_point_evolution": [],
            "insights": ["该科目暂无考试记录"],
        }

    sorted_e = sorted(exams, key=lambda e: e.exam_date)
    scores = [e.score for e in sorted_e]
    trend_direction, trend_strength = _trend_direction(scores)
    volatility = _build_volatility(scores)

    score_trend = [
        {
            "exam_id": e.id,
            "exam_name": e.exam_name,
            "date": e.exam_date.isoformat(),
            "score": e.score,
            "full_score": e.full_score,
            "percentage": round(e.score / e.full_score * 100, 1) if e.full_score else 0.0,
            "class_avg_delta": (
                round(e.score - e.class_average, 2) if e.class_average is not None else None
            ),
        }
        for e in sorted_e
    ]
    rank_trend = [
        {
            "exam_id": e.id,
            "date": e.exam_date.isoformat(),
            "class_rank": e.class_rank,
            "grade_rank": e.grade_rank,
        }
        for e in sorted_e
    ]
    target_progression = [
        {
            "exam_id": e.id,
            "date": e.exam_date.isoformat(),
            "target": e.target_score,
            "actual": e.score,
            "delta": (
                round(e.score - e.target_score, 2) if e.target_score is not None else None
            ),
            "reached": (
                e.score >= e.target_score if e.target_score is not None else None
            ),
        }
        for e in sorted_e
    ]

    best = max(sorted_e, key=lambda e: e.score)
    worst = min(sorted_e, key=lambda e: e.score)
    best_exam = {
        "exam_id": best.id, "exam_name": best.exam_name, "date": best.exam_date.isoformat(),
        "score": best.score,
    }
    if best.id != worst.id:
        worst_exam = {
            "exam_id": worst.id, "exam_name": worst.exam_name, "date": worst.exam_date.isoformat(),
            "score": worst.score,
        }
    else:
        worst_exam = None  # 只有一条时不算"最差"

    # 洞察生成
    insights: List[str] = []
    insights.append(
        f"该科目共 {len(sorted_e)} 次考试，"
        f"最高 {best.score}（{best.exam_date.isoformat()}），"
        f"最低 {worst.score if worst_exam else best.score}"
    )
    if trend_direction == "rising":
        if trend_strength == "significant":
            insights.append(f"成绩呈显著上升趋势（斜率 +{scores[-1] - scores[0]:.1f} 分）")
        elif trend_strength == "moderate":
            insights.append(f"成绩稳步上升（{scores[-1] - scores[0]:.1f} 分）")
        else:
            insights.append("成绩略有上升")
    elif trend_direction == "falling":
        if trend_strength in ("significant", "moderate"):
            insights.append(f"成绩出现下滑（{scores[0] - scores[-1]:.1f} 分），需要重点关注")
        else:
            insights.append("成绩略有下滑")
    if volatility["stability"] == "volatile":
        insights.append(f"成绩波动较大（标准差 {volatility['std_dev']}），稳定性待提升")
    if trend_strength == "flat" and volatility["stability"] == "stable":
        insights.append("成绩稳定，处于平台期")

    # 知识点出现频率
    kp_evo = _kp_evolution(sorted_e)
    if kp_evo:
        top_kp = kp_evo[0]
        if top_kp["appearances"] >= 2:
            insights.append(
                f"高频考点「{top_kp['knowledge_point']}」出现 {top_kp['appearances']} 次，"
                f"累计失分 {top_kp['lost_score_total']}"
            )

    # 目标达成率
    targets_set = [e for e in sorted_e if e.target_score is not None]
    if targets_set:
        reached = sum(1 for e in targets_set if e.score >= e.target_score)
        rate = round(reached / len(targets_set) * 100, 1)
        insights.append(f"目标达成率 {rate}%（{reached}/{len(targets_set)}）")

    return {
        "subject": subject,
        "child_id": child_id,
        "period": {
            "start_date": sorted_e[0].exam_date.isoformat(),
            "end_date": sorted_e[-1].exam_date.isoformat(),
        },
        "exam_count": len(sorted_e),
        "score_trend": score_trend,
        "rank_trend": rank_trend,
        "volatility": volatility,
        "target_progression": target_progression,
        "best_exam": best_exam,
        "worst_exam": worst_exam,
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "knowledge_point_evolution": kp_evo,
        "insights": insights,
    }


# ============ 试卷卷面分析 ============

def _build_section_stats(questions: List[ExamQuestionLike]) -> List[dict]:
    """按 section_name 分组统计（保持试卷顺序）"""
    section_map: dict[str, list[ExamQuestionLike]] = {}
    section_order: list[str] = []
    for q in questions:
        if q.section_name not in section_map:
            section_map[q.section_name] = []
            section_order.append(q.section_name)
        section_map[q.section_name].append(q)

    stats = []
    for name in section_order:
        qs = section_map[name]
        max_total = sum(q.max_score for q in qs)
        scored = sum(q.scored for q in qs)
        stats.append({
            "section_name": name,
            "question_type": qs[0].type,
            "question_count": len(qs),
            "max_score": round(max_total, 2),
            "scored": round(scored, 2),
            "accuracy": round(scored / max_total * 100, 1) if max_total else 0.0,
            "loss_score": round(max_total - scored, 2),
        })
    return stats


def _build_type_stats(questions: List[ExamQuestionLike]) -> List[dict]:
    """按题型聚合"""
    type_map: dict[str, list[ExamQuestionLike]] = {}
    for q in questions:
        type_map.setdefault(q.type, []).append(q)

    stats = []
    for qtype, qs in type_map.items():
        max_total = sum(q.max_score for q in qs)
        scored = sum(q.scored for q in qs)
        stats.append({
            "section_name": f"[{qtype}]",
            "question_type": qtype,
            "question_count": len(qs),
            "max_score": round(max_total, 2),
            "scored": round(scored, 2),
            "accuracy": round(scored / max_total * 100, 1) if max_total else 0.0,
            "loss_score": round(max_total - scored, 2),
        })
    stats.sort(key=lambda s: -s["loss_score"])
    return stats


def _kp_loss_breakdown(questions: List[ExamQuestionLike]) -> List[dict]:
    """知识点维度丢分（每题丢分按 KP 数均分）"""
    kp_loss: dict[str, float] = {}
    kp_count: dict[str, int] = {}
    for q in questions:
        loss = max(0.0, q.max_score - q.scored)
        if not q.knowledge_points or loss <= 0:
            continue
        share = loss / len(q.knowledge_points)
        for kp in q.knowledge_points:
            kp_loss[kp] = kp_loss.get(kp, 0.0) + share
            kp_count[kp] = kp_count.get(kp, 0) + 1
    result = []
    for kp, loss in kp_loss.items():
        if loss > 0:
            result.append({
                "knowledge_point": kp,
                "lost_score": round(loss, 2),
                "question_count": kp_count[kp],
            })
    result.sort(key=lambda x: -x["lost_score"])
    return result


def _classify_questions(questions: List[ExamQuestionLike]) -> tuple[list[dict], list[dict], list[dict]]:
    """分类：满分题 / 部分得分题 / 丢分题"""
    perfect: list[dict] = []
    partial: list[dict] = []
    lost: list[dict] = []
    for q in questions:
        loss = q.max_score - q.scored
        item = {
            "question_id": q.id,
            "number": q.number,
            "section_name": q.section_name,
            "type": q.type,
            "max_score": q.max_score,
            "scored": q.scored,
            "loss": round(loss, 2),
            "knowledge_points": list(q.knowledge_points or []),
        }
        if loss <= 0:
            perfect.append(item)
        elif q.scored > 0:
            partial.append(item)
        else:
            lost.append(item)
    lost.sort(key=lambda x: -x["loss"])
    return perfect, partial, lost


def _generate_paper_insights(
    questions: List[ExamQuestionLike],
    section_stats: List[dict],
    type_stats: List[dict],
    kp_loss: List[dict],
    total_loss: float,
) -> List[str]:
    """卷面洞察句生成"""
    insights: List[str] = []
    if not questions:
        return ["本次考试未录入卷面题目"]

    total_max = sum(q.max_score for q in questions)
    total_scored = sum(q.scored for q in questions)
    accuracy = total_scored / total_max * 100 if total_max else 0
    insights.append(
        f"卷面共 {len(questions)} 题，满分 {total_max:.0f} 分，"
        f"得分 {total_scored:.0f} 分（{accuracy:.1f}%）"
    )

    if len(type_stats) >= 2:
        worst_type = min(type_stats, key=lambda s: s["accuracy"])
        best_type = max(type_stats, key=lambda s: s["accuracy"])
        if worst_type["accuracy"] < best_type["accuracy"] - 15:
            type_label = {
                "single_choice": "选择题", "multi_choice": "多选题", "true_false": "判断题",
                "fill_blank": "填空题", "short_answer": "简答题", "calculation": "计算题",
                "application": "应用题", "essay": "作文", "other": "其他题",
            }.get(worst_type["question_type"], worst_type["question_type"])
            insights.append(
                f"{type_label}失分率最高（{100 - worst_type['accuracy']:.0f}%），是本次最大短板"
            )

    if kp_loss:
        top_kp = kp_loss[0]
        loss_ratio = top_kp["lost_score"] / total_loss * 100 if total_loss else 0
        if loss_ratio >= 40:
            insights.append(
                f"「{top_kp['knowledge_point']}」丢分 {top_kp['lost_score']:.0f} 分，"
                f"占总失分 {loss_ratio:.0f}%，需重点突破"
            )
        elif top_kp["lost_score"] >= 5:
            insights.append(
                f"「{top_kp['knowledge_point']}」丢分 {top_kp['lost_score']:.0f} 分"
            )

    if len(section_stats) >= 2:
        worst_section = min(section_stats, key=lambda s: s["accuracy"])
        if worst_section["accuracy"] < 70 and worst_section["loss_score"] >= 5:
            insights.append(
                f"「{worst_section['section_name']}」失分率 {100 - worst_section['accuracy']:.0f}%，"
                f"共失 {worst_section['loss_score']:.0f} 分"
            )

    perfect_count = sum(1 for q in questions if q.scored >= q.max_score)
    if perfect_count == len(questions):
        insights.append("所有题目满分，基础非常扎实")
    elif perfect_count >= len(questions) * 0.7:
        insights.append(f"满分题 {perfect_count}/{len(questions)}，基础掌握较好")

    return insights


def analyze_exam_paper(
    exam_id: int,
    questions: List[ExamQuestionLike],
) -> dict:
    """单次考试卷面分析（按大题/题型/KP 多维聚合）"""
    if not questions:
        return {
            "exam_id": exam_id,
            "paper_total_score": 0.0,
            "actual_scored": 0.0,
            "accuracy": 0.0,
            "section_stats": [],
            "question_type_stats": [],
            "knowledge_point_loss": [],
            "hardest_questions": [],
            "perfect_questions": [],
            "partial_questions": [],
            "insights": ["本次考试未录入卷面题目"],
        }

    section_stats = _build_section_stats(questions)
    type_stats = _build_type_stats(questions)
    kp_loss = _kp_loss_breakdown(questions)
    perfect, partial, lost = _classify_questions(questions)

    total_max = sum(q.max_score for q in questions)
    total_scored = sum(q.scored for q in questions)
    total_loss = total_max - total_scored
    insights = _generate_paper_insights(questions, section_stats, type_stats, kp_loss, total_loss)

    return {
        "exam_id": exam_id,
        "paper_total_score": round(total_max, 2),
        "actual_scored": round(total_scored, 2),
        "accuracy": round(total_scored / total_max * 100, 1) if total_max else 0.0,
        "section_stats": section_stats,
        "question_type_stats": type_stats,
        "knowledge_point_loss": kp_loss[:10],
        "hardest_questions": lost[:5],
        "perfect_questions": perfect,
        "partial_questions": partial,
        "insights": insights,
    }
