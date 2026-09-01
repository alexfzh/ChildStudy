"""Pydantic 数据校验模式（API 进出结构）"""
from datetime import date, datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============ 通用 ============
class OkResponse(BaseModel):
    ok: bool = True
    message: str = "操作成功"


# ============ 孩子档案 ============
class ChildBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    grade: str = Field(..., min_length=1, max_length=32)
    school: Optional[str] = None
    avatar_color: str = "#6366f1"
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    subjects: List[str] = Field(default_factory=lambda: ["语文", "数学", "英语"])


class ChildCreate(ChildBase):
    pass


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    avatar_color: Optional[str] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    subjects: Optional[List[str]] = None


class ChildOut(ChildBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============ 年级历史 ============
class GradeHistoryCreate(BaseModel):
    grade: str = Field(..., min_length=1, max_length=32)
    effective_from: date
    note: Optional[str] = Field(None, max_length=256)


class GradeHistoryOut(BaseModel):
    id: int
    grade: str
    effective_from: date
    note: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


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


# ============ 作业记录 ============
class HomeworkBase(BaseModel):
    subject: str
    title: str
    homework_date: date
    duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    correct_questions: Optional[int] = None
    accuracy: Optional[float] = None
    completed: bool = True
    difficulty: str = "normal"
    note: Optional[str] = None
    grade_snapshot: Optional[str] = None  # 作业时的年级快照（服务端可自动补）


class HomeworkCreate(HomeworkBase):
    child_id: int


class HomeworkUpdate(BaseModel):
    subject: Optional[str] = None
    title: Optional[str] = None
    homework_date: Optional[date] = None
    duration_minutes: Optional[int] = None
    total_questions: Optional[int] = None
    correct_questions: Optional[int] = None
    accuracy: Optional[float] = None
    completed: Optional[bool] = None
    difficulty: Optional[str] = None
    note: Optional[str] = None


class HomeworkOut(HomeworkBase):
    id: int
    child_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============ 时间轴事件 ============
class TimelineBase(BaseModel):
    event_type: str = "note"
    title: str
    description: Optional[str] = None
    event_date: date
    attachments: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class TimelineCreate(TimelineBase):
    child_id: int


class TimelineUpdate(BaseModel):
    event_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    attachments: Optional[List[str]] = None
    tags: Optional[List[str]] = None


class TimelineOut(TimelineBase):
    id: int
    child_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


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


# ============ Dashboard ============
class SubjectStat(BaseModel):
    subject: str
    avg_score: float
    max_score: float
    min_score: float
    exam_count: int
    trend: str  # up/down/flat
    latest_score: float


class DashboardData(BaseModel):
    child_id: int
    child_name: str
    total_exams: int
    total_homeworks: int
    recent_exams: List[ExamOut]
    subject_stats: List[SubjectStat]
    weak_subjects: List[str]
    radar_data: dict
    trend_data: dict
    action_suggestions: List[str] = []


class CompareData(BaseModel):
    children: List[dict]  # 每个孩子的概况


# ============ 知识点标签库 ============
class KnowledgePointBase(BaseModel):
    subject: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    grade_level: Optional[str] = Field(None, max_length=32)


class KnowledgePointCreate(KnowledgePointBase):
    pass


class KnowledgePointUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=32)
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = None
    grade_level: Optional[str] = Field(None, max_length=32)


class KnowledgePointOut(KnowledgePointBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============ 设置（已废弃：保留 OkResponse 兼容） ============
# v1.x 的 SettingsPayload / SettingsStatus 已随 AI 模块下线。
# 设置页改为"工作流说明"，不再有 API endpoint。

# ============ 错题本 ============
class WrongQuestionBase(BaseModel):
    child_id: int
    source_type: str = "manual"  # manual/exam/homework/bank
    source_id: Optional[int] = None
    bank_question_id: Optional[int] = None  # 智能匹配到的题库题目 ID
    subject: str = Field(..., min_length=1, max_length=32)
    question_text: str = Field(..., min_length=1)
    question_image: Optional[str] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    error_reason: str = "other"  # knowledge_gap/misunderstanding/careless/incomplete/other
    knowledge_points: List[str] = Field(default_factory=list)
    difficulty: str = "normal"  # easy/normal/hard
    mastery_level: str = "new"  # new/learning/mastered
    wrong_count: int = 1
    last_wrong_date: date = Field(default_factory=date.today)
    next_review_date: Optional[date] = None
    review_count: int = 0
    status: str = "active"  # active/archived/mastered
    note: Optional[str] = None


class WrongQuestionCreate(WrongQuestionBase):
    pass


class WrongQuestionUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=32)
    question_text: Optional[str] = Field(None, min_length=1)
    question_image: Optional[str] = None
    user_answer: Optional[str] = None
    correct_answer: Optional[str] = None
    error_reason: Optional[str] = None
    knowledge_points: Optional[List[str]] = None
    difficulty: Optional[str] = None
    mastery_level: Optional[str] = None
    wrong_count: Optional[int] = None
    last_wrong_date: Optional[date] = None
    next_review_date: Optional[date] = None
    review_count: Optional[int] = None
    status: Optional[str] = None
    note: Optional[str] = None
    bank_question_id: Optional[int] = None


class WrongQuestionReviewCreate(BaseModel):
    result: str = Field(..., min_length=1)  # correct/partial/wrong
    note: Optional[str] = None


class WrongQuestionReviewOut(BaseModel):
    id: int
    wrong_question_id: int
    review_date: date
    result: str
    note: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WrongQuestionOut(WrongQuestionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    reviews: List[WrongQuestionReviewOut] = Field(default_factory=list)
    match_suggestions: Optional[dict] = None  # 智能匹配建议（创建/重新分析时返回）
    model_config = ConfigDict(from_attributes=True)


class WrongQuestionStats(BaseModel):
    total: int
    active: int
    mastered: int
    archived: int
    mastery_rate: float
    by_subject: List[dict]
    by_error_reason: List[dict]
    top_knowledge_points: List[dict]
    recent_trend: List[dict]


class BankMatchCandidateOut(BaseModel):
    question_id: int
    bank_id: int
    bank_title: str
    content: str
    knowledge_point: str
    score: float
    text_score: float
    fingerprint_score: float
    options_score: float
    match_reasons: List[str] = Field(default_factory=list)


class KPMatchCandidateOut(BaseModel):
    knowledge_point_id: int
    name: str
    subject: str
    score: float
    match_reasons: List[str] = Field(default_factory=list)
    # KP 是否能命中 KP 库（错题 KP 字符串 → KP id 解析用）
    matched: bool = True
    # 若已挂教材，附带 unit 标题（拼接 KP↔Unit 体系后输出）
    unit_code: Optional[str] = None
    unit_title_zh: Optional[str] = None


class MatchSuggestionsOut(BaseModel):
    bank_matches: List[BankMatchCandidateOut] = Field(default_factory=list)
    kp_matches: List[KPMatchCandidateOut] = Field(default_factory=list)


# KP 匹配来源（错题推荐时区分推荐路径）
KPMatchLevel = Literal["primary", "kp_name_fallback", "unit_extend"]


class MatchedQuestionOut(BaseModel):
    id: int
    bank_id: int
    knowledge_point: str
    difficulty: str
    content: str
    options: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    # 对接新 KP 体系的产物
    kp_match_level: str = "kp_name_fallback"  # primary / kp_name_fallback / unit_extend
    matched_kp_ids: List[int] = Field(default_factory=list)  # 命中的 KP id
    matched_kp_names: List[str] = Field(default_factory=list)
    unit_code: Optional[str] = None  # 来源 Unit（如 U3）
    unit_title_zh: Optional[str] = None  # 来源 Unit 标题


class AcceptMatchRequest(BaseModel):
    bank_question_id: Optional[int] = None
    knowledge_points: Optional[List[str]] = None


class TodayReviewItem(BaseModel):
    id: int
    subject: str
    question_text: str
    mastery_level: str
    wrong_count: int
    knowledge_points: List[str]


class TodayReviewResponse(BaseModel):
    total: int
    items: List[TodayReviewItem]


# ============ 生长发育 ============
class GrowthRecordBase(BaseModel):
    child_id: int
    record_date: date
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    vision_left: Optional[float] = Field(None, description="左眼视力")
    vision_right: Optional[float] = Field(None, description="右眼视力")
    note: Optional[str] = None


class GrowthRecordCreate(GrowthRecordBase):
    pass


class GrowthRecordUpdate(BaseModel):
    record_date: Optional[date] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    vision_left: Optional[float] = None
    vision_right: Optional[float] = None
    note: Optional[str] = None


class GrowthRecordOut(GrowthRecordBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============ 社交情感 ============
class SocialEmotionalBase(BaseModel):
    child_id: int
    record_date: date
    mood_score: Optional[int] = Field(None, ge=1, le=5, description="情绪指数 1-5")
    emotion_tags: List[str] = Field(default_factory=list)
    social_activity: Optional[str] = Field(None, max_length=256)
    confidence_level: Optional[int] = Field(None, ge=1, le=5, description="自信心 1-5")
    note: Optional[str] = None


class SocialEmotionalCreate(SocialEmotionalBase):
    pass


class SocialEmotionalUpdate(BaseModel):
    record_date: Optional[date] = None
    mood_score: Optional[int] = Field(None, ge=1, le=5)
    emotion_tags: Optional[List[str]] = None
    social_activity: Optional[str] = Field(None, max_length=256)
    confidence_level: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = None


class SocialEmotionalOut(SocialEmotionalBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============ 兴趣特长 ============
class InterestBase(BaseModel):
    child_id: int
    record_date: date
    activity_type: str = Field(..., min_length=1, max_length=32)  # 运动/音乐/美术/编程/阅读/其他
    activity_name: str = Field(..., min_length=1, max_length=128)
    duration_minutes: Optional[int] = None
    skill_level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    note: Optional[str] = None


class InterestCreate(InterestBase):
    pass


class InterestUpdate(BaseModel):
    record_date: Optional[date] = None
    activity_type: Optional[str] = Field(None, min_length=1, max_length=32)
    activity_name: Optional[str] = Field(None, min_length=1, max_length=128)
    duration_minutes: Optional[int] = None
    skill_level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced)$")
    note: Optional[str] = None


class InterestOut(InterestBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============ 奖励系统 ============

class RankInfo(BaseModel):
    subject: str
    tier: str
    stars: int
    avg_score: Optional[float]
    exam_count: int
    total_points: int
    color: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

    @property
    def display(self) -> str:
        if self.stars > 0:
            return f"{self.tier} {'⭐' * self.stars}"
        return self.tier


class RewardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    reward_type: str = Field("material", pattern="^(material|spiritual|privilege)$")
    cost_points: int = Field(0, ge=0)
    description: Optional[str] = None
    icon: str = Field("🎁", max_length=32)
    is_active: bool = True


class RewardCreate(RewardBase):
    pass


class RewardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    reward_type: Optional[str] = Field(None, pattern="^(material|spiritual|privilege)$")
    cost_points: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=32)
    is_active: Optional[bool] = None


class RewardOut(RewardBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChildRewardOut(BaseModel):
    id: int
    child_id: int
    reward_id: int
    points_spent: int
    source: str
    note: Optional[str]
    earned_date: date
    reward: Optional[RewardOut] = None
    model_config = ConfigDict(from_attributes=True)


class AchievementBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None
    icon: str = Field("🏆", max_length=32)
    condition_type: str = Field(..., min_length=1, max_length=32)
    condition_value: Optional[int] = None


# icon 白名单：仅放行 "svg:<key>" 命名空间引用、或单个/少数 emoji、或一般短字符串
# （防 AchIcon.vue 的 v-html 被恶意 SVG/HTML 标签注入；用 Pydantic 在写入侧拦下最稳）
_ICON_PATTERN = r'^(svg:[a-z][a-z0-9_-]{0,31}|[\U0001F300-\U0001FAFF\u2600-\u27BF]{1,4}|.{1,8})$'


class AchievementCreate(AchievementBase):
    icon: str = Field("🏆", max_length=32, pattern=_ICON_PATTERN)


class AchievementOut(AchievementBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChildAchievementOut(BaseModel):
    id: int
    child_id: int
    achievement_id: int
    exam_id: Optional[int]
    earned_date: date
    achievement: Optional[AchievementOut] = None
    model_config = ConfigDict(from_attributes=True)


class PointsLogOut(BaseModel):
    id: int
    child_id: int
    points: int
    source: str
    description: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PointsSummary(BaseModel):
    total: int
    earned: int
    spent: int
    recent_logs: List[PointsLogOut] = Field(default_factory=list)


class ExamRewardResponse(BaseModel):
    points_earned: int
    new_rank: Optional[RankInfo] = None
    new_achievements: List[ChildAchievementOut] = Field(default_factory=list)
    message: str


class RewardShopItem(BaseModel):
    reward: RewardOut
    can_afford: bool


# ============ 题库系统 ============

class QuestionBankBase(BaseModel):
    grade: str = Field(..., max_length=32)
    subject: str = Field(..., max_length=32)
    title: str = Field(..., max_length=128)
    description: Optional[str] = None
    is_active: bool = True


class QuestionBankCreate(QuestionBankBase):
    pass


class QuestionBankUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionBankOut(QuestionBankBase):
    id: int
    question_count: int = 0
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuestionBase(BaseModel):
    bank_id: int
    knowledge_point: str = Field(..., max_length=128)
    # single_choice: 4 选项单选; true_false: 对/错判断 (options=["正确","错误"], correct_answer=A/B)
    question_type: str = Field("single_choice", pattern="^(single_choice|true_false)$")
    difficulty: str = Field("normal", pattern="^(easy|normal|hard)$")
    content: str
    options: List[str] = Field(..., min_length=2, max_length=6)
    correct_answer: str = Field(..., min_length=1, max_length=1, pattern="^[A-F]$")
    explanation: Optional[str] = None


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    knowledge_point: Optional[str] = Field(None, max_length=128)
    question_type: Optional[str] = Field(None, pattern="^(single_choice|true_false)$")
    difficulty: Optional[str] = Field(None, pattern="^(easy|normal|hard)$")
    content: Optional[str] = None
    options: Optional[List[str]] = Field(None, min_length=2, max_length=6)
    correct_answer: Optional[str] = Field(None, min_length=1, max_length=1, pattern="^[A-F]$")
    explanation: Optional[str] = None


class QuestionOut(QuestionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExerciseStartRequest(BaseModel):
    child_id: int
    bank_id: int
    count: int = Field(default=5, ge=1, le=20)
    knowledge_points: Optional[List[str]] = None  # None=随机
    difficulty: Optional[str] = Field(None, pattern="^(easy|normal|hard)$")
    mode: str = Field("manual", pattern="^(manual|recommend)$")
    wrong_question_ids: Optional[List[int]] = None


class ExerciseSubmitRequest(BaseModel):
    answers: List[dict]  # [{question_id, selected}]
    time_spent: Optional[int] = None  # 练习耗时(秒)


class ExerciseOut(BaseModel):
    id: int
    child_id: int
    bank_id: int
    questions: List[dict]
    answers: List[dict]
    score: Optional[float]
    total_questions: int
    correct_count: int
    submitted_at: Optional[datetime]
    time_spent: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExerciseRecommendation(BaseModel):
    wrong_questions: List[dict]
    matched_questions: List[MatchedQuestionOut]
    suggestion: str
    # 兼容新体系：本次推荐命中的 KP 列表（带 Unit 信息），家长可一眼看到薄弱点
    recommended_kps: List[KPMatchCandidateOut] = Field(default_factory=list)

# ============ 教材版本 / 单元 / 学习进度 / Project 作品 ============

class TextbookVersionBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    publisher: str = Field(..., max_length=64)
    grade: str = Field(..., max_length=32)
    subject: str = Field(..., max_length=32)
    term: str = Field("A", max_length=8)
    is_active: bool = True
    description: Optional[str] = None


class TextbookVersionCreate(TextbookVersionBase):
    pass


class TextbookVersionOut(TextbookVersionBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TextbookUnitBase(BaseModel):
    version_id: int
    code: str = Field(..., max_length=16)
    unit_number: int
    title_en: Optional[str] = Field(None, max_length=128)
    title_zh: str = Field(..., max_length=128)
    topic_words: list = Field(default_factory=list)
    sound: Optional[str] = Field(None, max_length=32)
    sound_examples: list = Field(default_factory=list)
    structure: Optional[str] = Field(None, max_length=128)
    big_task: Optional[str] = Field(None, max_length=255)
    project_type: Optional[str] = Field(None, max_length=64)
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    is_project: bool = False


class TextbookUnitCreate(TextbookUnitBase):
    pass


class TextbookUnitOut(TextbookUnitBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QuestionUnitLink(BaseModel):
    unit_id: int
    relevance: str = Field("primary", pattern="^(primary|supplementary|cross)$")


class QuestionUnitBulkLink(BaseModel):
    question_id: int
    links: list[QuestionUnitLink]


class StudyProgressOut(BaseModel):
    id: int
    child_id: int
    unit_id: int
    status: str
    total_attempts: int
    total_correct: int
    accuracy: float
    completion_pct: float
    mastered_at: Optional[datetime] = None
    last_study_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ChildProgressSummary(BaseModel):
    """孩子在某教材版本下所有 Unit 的进度概览"""
    child_id: int
    version_id: int
    units: list[TextbookUnitOut]
    progress_map: dict
    mastery_pct: float
    streak_units: int
    total_points: int
    total_achievements: int


class ProjectWorkCreate(BaseModel):
    child_id: int
    unit_id: int
    work_type: str = Field("text", pattern="^(text|image|drawing|audio)$")
    title: Optional[str] = Field(None, max_length=128)
    content: Optional[str] = None
    image_path: Optional[str] = Field(None, max_length=255)


class ProjectWorkUpdate(BaseModel):
    content: Optional[str] = None
    image_path: Optional[str] = Field(None, max_length=255)
    parent_comment: Optional[str] = None
    teacher_comment: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(submitted|reviewed|approved|needs_revision)$")


class ProjectWorkOut(BaseModel):
    id: int
    child_id: int
    unit_id: int
    work_type: str
    title: Optional[str] = None
    content: Optional[str] = None
    image_path: Optional[str] = None
    ai_score: Optional[float] = None
    ai_comment: Optional[str] = None
    parent_comment: Optional[str] = None
    teacher_comment: Optional[str] = None
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ============ KnowledgePoint ↔ Unit 多对多关联 ============

class KnowledgePointUnitLink(BaseModel):
    unit_id: int
    relevance: str = Field("primary", pattern="^(primary|secondary|review)$")


class KnowledgePointUnitBulkLink(BaseModel):
    knowledge_point_id: int
    links: list[KnowledgePointUnitLink]


class KnowledgePointWithUnits(KnowledgePointBase):
    """KP 详情 + 关联 Unit 列表（id + code + title_en + relevance）"""
    id: int
    unit_links: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class UnitWithKnowledgePoints(BaseModel):
    """Unit 详情 + 关联 KP 列表"""
    unit_id: int
    knowledge_points: list[dict] = Field(default_factory=list)


# ============ Question ↔ KnowledgePoint 多对多关联 ============

class QuestionKPLink(BaseModel):
    knowledge_point_id: int
    is_primary: bool = True


class QuestionKPBulkLink(BaseModel):
    question_id: int
    links: list[QuestionKPLink]


class QuestionWithKPs(BaseModel):
    """Question 详情 + 关联 KP 列表"""
    id: int
    knowledge_point: str  # 保留旧字符串字段（兼容）
    kp_links: list[dict] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


# ============ KPStudyProgress（KP 级别掌握度） ============

class KPStudyProgressOut(BaseModel):
    id: int
    child_id: int
    knowledge_point_id: int
    unit_id: Optional[int] = None
    total_attempts: int
    total_correct: int
    accuracy: float
    mastery_level: str  # new/learning/strong/mastered
    last_study_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class KPProgressSummary(BaseModel):
    """某 Unit 内所有 KP 的掌握度汇总"""
    unit_id: int
    unit_code: str
    unit_title_zh: str
    total_kps: int
    mastered_kps: int
    learning_kps: int
    strong_kps: int
    new_kps: int
    mastery_pct: float  # 0-100
    kp_details: list[KPStudyProgressOut] = Field(default_factory=list)


class ChildKPProgressSummary(BaseModel):
    """孩子某教材版本下所有 Unit × KP 的掌握度矩阵"""
    child_id: int
    version_id: int
    total_kps: int
    overall_mastery_pct: float
    kp_summary_by_unit: list[KPProgressSummary] = Field(default_factory=list)
