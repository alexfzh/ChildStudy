"""考试记录 / 题目 / 分析"""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 考试记录 ============
class ExamBase(BaseModel):
    subject: str
    exam_name: str
    exam_type: str = "quiz"
    score: float
    full_score: float = 100.0
    target_score: Optional[float] = None  # 家长设定的目标分
    class_rank: Optional[int] = None
    grade_rank: Optional[int] = None
    exam_date: date
    knowledge_points: List[str] = Field(default_factory=list)
    wrong_questions: Optional[str] = None
    teacher_comment: Optional[str] = None
    note: Optional[str] = None
    grade_snapshot: Optional[str] = None  # 考试时的年级快照（服务端可自动补）
    class_average: Optional[float] = None  # 班级平均分（满分同 full_score，可选）
    # 纸面分析冗余字段（ExamQuestion 聚合时更新）
    paper_total_score: Optional[float] = None  # 纸面满分
    paper_actual_scored: Optional[float] = None  # 纸面实际得分


class ExamCreate(ExamBase):
    child_id: int


class ExamUpdate(BaseModel):
    subject: Optional[str] = None
    exam_name: Optional[str] = None
    exam_type: Optional[str] = None
    score: Optional[float] = None
    full_score: Optional[float] = None
    target_score: Optional[float] = None
    class_rank: Optional[int] = None
    grade_rank: Optional[int] = None
    exam_date: Optional[date] = None
    knowledge_points: Optional[List[str]] = None
    wrong_questions: Optional[str] = None
    teacher_comment: Optional[str] = None
    note: Optional[str] = None
    class_average: Optional[float] = None
    paper_total_score: Optional[float] = None
    paper_actual_scored: Optional[float] = None


class ExamOut(ExamBase):
    id: int
    child_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)




# ============ 考试题目 / 纸面录入（AI 工具友好） ============
class QuestionType(str, Enum):
    """考试题型枚举。AI 工具录入时强制用枚举，避免后续聚合 SQL 散落。"""
    SINGLE_CHOICE = "single_choice"   # 单选
    MULTI_CHOICE = "multi_choice"     # 多选
    TRUE_FALSE = "true_false"         # 判断
    FILL_BLANK = "fill_blank"         # 填空
    SHORT_ANSWER = "short_answer"     # 简答
    CALCULATION = "calculation"       # 计算
    APPLICATION = "application"       # 应用题
    ESSAY = "essay"                   # 作文/论述
    OTHER = "other"                   # 兜底


class ExamQuestionIn(BaseModel):
    """AI 工具录入的单题数据"""
    number: int                                 # 试卷上的题号
    type: QuestionType
    max_score: float                            # 满分
    scored: float                               # 实际得分
    is_correct: Optional[bool] = None           # True/False/None（解答题可能部分对）
    knowledge_points: List[str] = Field(default_factory=list)
    content: Optional[str] = None               # 题目文本（OCR 出来就填）
    note: Optional[str] = None


class ExamSectionIn(BaseModel):
    """一道大题（一组同题型题）"""
    section_name: str                           # "一、选择题"
    question_type: QuestionType
    questions: List[ExamQuestionIn]


class ExamPaperIn(BaseModel):
    """整张试卷录入（AI 工具友好：一次性 POST 替换）"""
    paper_total_score: float                    # 纸面满分（应等于 sum(max_score)）
    sections: List[ExamSectionIn]
    source: str = "manual"                      # manual / ocr_v1 / import 等
    raw_payload: Optional[dict] = None          # AI 原始返回，存根


class ExamQuestionOut(BaseModel):
    id: int
    exam_id: int
    section_name: str
    number: int
    type: str
    max_score: float
    scored: float
    is_correct: Optional[bool] = None
    knowledge_points: List[str] = Field(default_factory=list)
    content: Optional[str] = None
    note: Optional[str] = None
    source: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)




# ============ 考试分析 ============
class ExamAnalysisComparison(BaseModel):
    """vs 历史/班级/目标的对比分析"""
    vs_subject_mean: Optional[float] = None       # vs 该科目历史平均分（差值，正=高于均值）
    vs_subject_best: Optional[float] = None       # vs 该科目历史最高分
    vs_subject_worst: Optional[float] = None
    vs_class_average: Optional[float] = None      # vs 班级平均分（差值）
    target_delta: Optional[float] = None          # vs 目标分（差值，正=超过目标）
    target_reached: Optional[bool] = None         # 是否达到目标


class ExamAnalysis(BaseModel):
    """单次考试总分分析"""
    exam_id: int
    exam_name: str
    subject: str
    exam_date: date
    score: float
    full_score: float
    percentage: float                              # score / full_score * 100
    rank_info: dict                                # {class_rank, grade_rank}
    target_info: Optional[dict] = None             # {target_score, delta, reached}
    comparison: ExamAnalysisComparison
    trend_position: dict                           # {position, rank_in_n, total_n, percentile}
    knowledge_points: List[str]
    insights: List[str]                            # AI 式洞察句


class ExamHistoryAnalysis(BaseModel):
    """历次考试趋势分析"""
    subject: str
    child_id: int
    period: dict                                   # {start_date, end_date}
    exam_count: int
    score_trend: List[dict]                        # [{exam_id, date, score, full_score, percentage, class_avg_delta}]
    rank_trend: List[dict]                         # [{exam_id, class_rank, grade_rank}]
    volatility: dict                               # {std_dev, max_delta, stability}
    target_progression: List[dict]                 # [{exam_id, target, actual, delta, reached}]
    best_exam: Optional[dict] = None
    worst_exam: Optional[dict] = None
    trend_direction: str                           # rising / falling / stable
    trend_strength: str                            # significant / moderate / weak / flat
    knowledge_point_evolution: List[dict]          # [{kp, appearances, lost_score_total}]
    insights: List[str]


class PaperSectionStat(BaseModel):
    """试卷节（或题型聚合）统计"""
    section_name: str
    question_type: str
    question_count: int
    max_score: float
    scored: float
    accuracy: float
    loss_score: float


class ExamPaperAnalysis(BaseModel):
    """单次考试卷面分析（按大题/题型/KP 多维聚合）"""
    exam_id: int
    paper_total_score: float
    actual_scored: float
    accuracy: float
    section_stats: List[PaperSectionStat] = Field(default_factory=list)
    question_type_stats: List[PaperSectionStat] = Field(default_factory=list)
    knowledge_point_loss: List[dict] = Field(default_factory=list)
    hardest_questions: List[dict] = Field(default_factory=list)
    perfect_questions: List[dict] = Field(default_factory=list)
    partial_questions: List[dict] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)




