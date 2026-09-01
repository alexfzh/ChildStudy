"""考试分析算法单测（纯函数，无 DB）"""
from datetime import date
from typing import List, Optional

from utils.exam_analyzer import (
    ExamLike,
    ExamQuestionLike,
    analyze_exam_history,
    analyze_exam_paper,
    analyze_single_exam,
)


def make_exam(
    id: int,
    child_id: int = 1,
    subject: str = "数学",
    score: float = 90.0,
    full_score: float = 100.0,
    target_score: Optional[float] = None,
    class_rank: Optional[int] = None,
    grade_rank: Optional[int] = None,
    exam_date: Optional[date] = None,
    knowledge_points: Optional[List[str]] = None,
    class_average: Optional[float] = None,
    exam_name: str = "测试",
) -> ExamLike:
    return ExamLike(
        id=id, child_id=child_id, subject=subject, exam_name=exam_name,
        score=score, full_score=full_score, target_score=target_score,
        class_rank=class_rank, grade_rank=grade_rank,
        exam_date=exam_date or date(2026, 6, 1),
        knowledge_points=knowledge_points or [],
        class_average=class_average,
        paper_total_score=None, paper_actual_scored=None,
    )


# ============ analyze_single_exam ============

def test_single_exam_only_one_in_history():
    """只有一条考试 → trend_position 应是 only"""
    e = make_exam(1, score=85, exam_date=date(2026, 6, 1))
    result = analyze_single_exam(e, [e])
    assert result["trend_position"]["position"] == "only"
    assert result["trend_position"]["rank_in_n"] == 1
    assert result["trend_position"]["total_n"] == 1
    assert result["percentage"] == 85.0
    assert "本次考试未标注涉及知识点" in result["insights"][0]


def test_single_exam_best_among_many():
    """本次是历史最高分"""
    history = [
        make_exam(1, score=80, exam_date=date(2026, 1, 1)),
        make_exam(2, score=85, exam_date=date(2026, 3, 1)),
        make_exam(3, score=90, exam_date=date(2026, 5, 1)),
    ]
    target = make_exam(4, score=95, exam_date=date(2026, 6, 1))
    result = analyze_single_exam(target, [*history, target])
    assert result["trend_position"]["position"] == "best"
    assert any("历史最高分" in i for i in result["insights"])


def test_single_exam_target_reached():
    """超过目标分"""
    target = make_exam(1, score=95, target_score=90)
    result = analyze_single_exam(target, [target])
    assert result["comparison"]["target_reached"] is True
    assert result["comparison"]["target_delta"] == 5.0
    assert result["target_info"]["reached"] is True
    assert any("达到目标分" in i for i in result["insights"])


def test_single_exam_target_missed():
    """未达目标分"""
    target = make_exam(1, score=80, target_score=90)
    result = analyze_single_exam(target, [target])
    assert result["comparison"]["target_reached"] is False
    assert result["comparison"]["target_delta"] == -10.0
    assert any("距目标分" in i for i in result["insights"])


def test_single_exam_class_average_high():
    """远超班级平均"""
    target = make_exam(1, score=95, class_average=80)
    result = analyze_single_exam(target, [target])
    assert result["comparison"]["vs_class_average"] == 15.0
    assert any("超越班级平均" in i for i in result["insights"])


def test_single_exam_top_rank_insight():
    """班级前 3 触发洞察"""
    target = make_exam(1, score=95, class_rank=2)
    result = analyze_single_exam(target, [target])
    assert any("班级前三" in i for i in result["insights"])


# ============ analyze_exam_history ============

def test_history_empty():
    """无考试记录"""
    result = analyze_exam_history(1, "数学", [])
    assert result["exam_count"] == 0
    assert any("暂无考试记录" in i for i in result["insights"])


def test_history_only_one_insight():
    """只有一条考试时，insights 里有'平台期'洞察"""
    result = analyze_exam_history(1, "数学", [
        make_exam(1, score=88, exam_date=date(2026, 6, 1)),
    ])
    assert result["exam_count"] == 1


def test_history_rising_trend():
    """成绩上升趋势"""
    exams = [
        make_exam(1, score=80, exam_date=date(2026, 1, 1)),
        make_exam(2, score=85, exam_date=date(2026, 3, 1)),
        make_exam(3, score=92, exam_date=date(2026, 5, 1)),
    ]
    result = analyze_exam_history(1, "数学", exams)
    assert result["trend_direction"] == "rising"
    assert result["exam_count"] == 3
    assert result["best_exam"]["exam_id"] == 3
    assert any("上升" in i for i in result["insights"])


def test_history_falling_trend():
    """成绩下降趋势"""
    exams = [
        make_exam(1, score=95, exam_date=date(2026, 1, 1)),
        make_exam(2, score=85, exam_date=date(2026, 3, 1)),
        make_exam(3, score=75, exam_date=date(2026, 5, 1)),
    ]
    result = analyze_exam_history(1, "数学", exams)
    assert result["trend_direction"] == "falling"
    assert any("下滑" in i for i in result["insights"])


def test_history_stable_trend():
    """成绩平稳"""
    exams = [
        make_exam(1, score=88, exam_date=date(2026, 1, 1)),
        make_exam(2, score=89, exam_date=date(2026, 3, 1)),
        make_exam(3, score=88, exam_date=date(2026, 5, 1)),
    ]
    result = analyze_exam_history(1, "数学", exams)
    assert result["trend_direction"] in ("stable", "rising", "falling")
    assert result["volatility"]["stability"] == "stable"


def test_history_volatile():
    """成绩波动大"""
    exams = [
        make_exam(1, score=60, exam_date=date(2026, 1, 1)),
        make_exam(2, score=95, exam_date=date(2026, 3, 1)),
        make_exam(3, score=70, exam_date=date(2026, 5, 1)),
    ]
    result = analyze_exam_history(1, "数学", exams)
    assert result["volatility"]["stability"] in ("volatile", "fluctuating")


def test_history_kp_evolution():
    """知识点历次出现 + 失分"""
    exams = [
        make_exam(1, score=80, knowledge_points=["分数乘法", "异分母"], exam_date=date(2026, 1, 1)),
        make_exam(2, score=70, knowledge_points=["分数乘法"], exam_date=date(2026, 3, 1)),
        make_exam(3, score=85, knowledge_points=["异分母", "通分"], exam_date=date(2026, 5, 1)),
    ]
    result = analyze_exam_history(1, "数学", exams)
    kp_map = {k["knowledge_point"]: k for k in result["knowledge_point_evolution"]}
    assert kp_map["分数乘法"]["appearances"] == 2
    assert kp_map["异分母"]["appearances"] == 2
    assert kp_map["分数乘法"]["lost_score_total"] == 50.0  # 20 + 30
    assert any("分数乘法" in i for i in result["insights"])


def test_history_target_progression_rate():
    """目标达成率"""
    exams = [
        make_exam(1, score=95, target_score=90, exam_date=date(2026, 1, 1)),
        make_exam(2, score=92, target_score=90, exam_date=date(2026, 3, 1)),
        make_exam(3, score=88, target_score=90, exam_date=date(2026, 5, 1)),
    ]
    result = analyze_exam_history(1, "数学", exams)
    # 95>=90 达到, 92>=90 达到, 88<90 未达 → 2/3 = 66.7%
    assert any("目标达成率 66.7%" in i for i in result["insights"])


def test_history_single_exam_no_worst():
    """只有一条考试时不输出 worst_exam"""
    exams = [make_exam(1, score=88, exam_date=date(2026, 6, 1))]
    result = analyze_exam_history(1, "数学", exams)
    assert result["best_exam"]["exam_id"] == 1
    assert result["worst_exam"] is None


def test_history_score_trend_has_class_avg_delta():
    """score_trend 含 class_avg_delta"""
    exams = [
        make_exam(1, score=85, class_average=80, exam_date=date(2026, 1, 1)),
        make_exam(2, score=92, class_average=85, exam_date=date(2026, 3, 1)),
    ]
    result = analyze_exam_history(1, "数学", exams)
    assert result["score_trend"][0]["class_avg_delta"] == 5.0
    assert result["score_trend"][1]["class_avg_delta"] == 7.0


def test_trend_strength_classification():
    """斜率大 → significant，平 → flat"""
    from utils.exam_analyzer import _trend_direction

    # 显著上升
    assert _trend_direction([80, 82, 95])[0] == "rising"
    # 平稳
    assert _trend_direction([90, 90, 90])[0] == "stable"
    # 略上升
    assert _trend_direction([90, 91, 92])[1] in ("weak", "moderate")


# ============ analyze_exam_paper ============

def make_q(
    id: int,
    section: str = "一、单选",
    number: int = 1,
    type_: str = "single_choice",
    max_score: float = 3,
    scored: float = 3,
    is_correct: Optional[bool] = None,
    kps: Optional[List[str]] = None,
) -> ExamQuestionLike:
    return ExamQuestionLike(
        id=id, exam_id=1, section_name=section, number=number, type=type_,
        max_score=max_score, scored=scored, is_correct=is_correct,
        knowledge_points=kps or [], content=None,
    )


def test_paper_empty():
    """空数据"""
    r = analyze_exam_paper(1, [])
    assert r["exam_id"] == 1
    assert r["paper_total_score"] == 0.0
    assert any("未录入卷面题目" in i for i in r["insights"])


def test_paper_section_stats():
    """按大题分组统计"""
    questions = [
        make_q(1, "一、单选", 1, scored=3),
        make_q(2, "一、单选", 2, scored=2),
        make_q(3, "二、应用", 3, "application", 20, 10, kps=["异分母分数加减"]),
    ]
    r = analyze_exam_paper(1, questions)
    assert len(r["section_stats"]) == 2
    assert r["section_stats"][0]["section_name"] == "一、单选"
    assert r["section_stats"][0]["max_score"] == 6  # 3+3
    assert r["section_stats"][0]["scored"] == 5
    assert r["section_stats"][0]["loss_score"] == 1
    assert r["section_stats"][1]["section_name"] == "二、应用"
    assert r["section_stats"][1]["accuracy"] == 50.0


def test_paper_type_stats():
    """按题型聚合，按失分排序"""
    questions = [
        make_q(1, "一、单选", 1, scored=3),
        make_q(2, "一、单选", 2, scored=3),
        make_q(3, "二、应用", 3, "application", 20, 10),
        make_q(4, "二、应用", 4, "application", 20, 0),
    ]
    r = analyze_exam_paper(1, questions)
    assert len(r["question_type_stats"]) == 2
    # application 失分多，应排前
    assert r["question_type_stats"][0]["question_type"] == "application"
    assert r["question_type_stats"][0]["loss_score"] == 30  # 10+20
    assert r["question_type_stats"][1]["loss_score"] == 0  # single_choice 全对


def test_paper_kp_loss_breakdown():
    """KP 维度丢分，按 KP 数均分"""
    questions = [
        make_q(1, "", 1, "application", 20, 10, kps=["异分母分数加减", "通分"]),
        make_q(2, "", 2, "application", 20, 5, kps=["异分母分数加减"]),
    ]
    r = analyze_exam_paper(1, questions)
    kp_map = {k["knowledge_point"]: k for k in r["knowledge_point_loss"]}
    assert "异分母分数加减" in kp_map
    # Q1 丢 10 分，2 个 KP 各分 5；Q2 丢 15 分，1 个 KP 全拿 → 5 + 15 = 20
    assert kp_map["异分母分数加减"]["lost_score"] == 20.0
    assert "通分" in kp_map
    assert kp_map["通分"]["lost_score"] == 5.0


def test_paper_classify_questions():
    """满分 / 部分 / 全丢三类"""
    questions = [
        make_q(1, "", 1, scored=3),       # perfect
        make_q(2, "", 2, scored=2),       # partial (max=3, lost=1)
        make_q(3, "", 3, scored=0),       # lost
    ]
    r = analyze_exam_paper(1, questions)
    assert len(r["perfect_questions"]) == 1
    assert len(r["partial_questions"]) == 1
    assert len(r["hardest_questions"]) == 1
    assert r["hardest_questions"][0]["number"] == 3
    assert r["partial_questions"][0]["number"] == 2


def test_paper_insights_shortest_board():
    """洞察句应包含题型短板 + KP 重点"""
    questions = [
        make_q(1, "一、单选", 1, scored=3),  # perfect
        make_q(2, "二、应用", 2, "application", 30, 5, kps=["异分母分数加减"]),
    ]
    r = analyze_exam_paper(1, questions)
    insights_text = " ".join(r["insights"])
    assert "应用题" in insights_text
    assert "异分母分数加减" in insights_text


def test_paper_insights_all_perfect():
    """全卷满分"""
    questions = [make_q(i, "", i, scored=3) for i in range(1, 6)]
    r = analyze_exam_paper(1, questions)
    assert any("所有题目满分" in i for i in r["insights"])


def test_paper_accuracy():
    """卷面正确率"""
    questions = [
        make_q(1, "", 1, max_score=10, scored=10),
        make_q(2, "", 2, max_score=10, scored=5),
        make_q(3, "", 3, max_score=10, scored=0),
    ]
    r = analyze_exam_paper(1, questions)
    # total_max=30, total_scored=15, accuracy=50%
    assert r["paper_total_score"] == 30
    assert r["actual_scored"] == 15
    assert r["accuracy"] == 50.0
