"""SQLAlchemy 数据模型定义"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Child(Base):
    """孩子档案"""
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    grade: Mapped[str] = mapped_column(String(32))  # 例如：三年级、初二
    school: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avatar_color: Mapped[str] = mapped_column(String(16), default="#6366f1")  # 头像颜色
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subjects: Mapped[list] = mapped_column(JSON, default=list)  # 关注的科目列表
    family_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=True, index=True
    )  # 多用户隔离：孩子归属的家庭（迁移期允许 NULL，启动迁移会 backfill 到默认家庭）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    exams: Mapped[list["Exam"]] = relationship(back_populates="child", cascade="all, delete-orphan")
    homeworks: Mapped[list["Homework"]] = relationship(back_populates="child", cascade="all, delete-orphan")
    timelines: Mapped[list["Timeline"]] = relationship(back_populates="child", cascade="all, delete-orphan")
    grade_history: Mapped[list["GradeHistory"]] = relationship(
        back_populates="child", cascade="all, delete-orphan", order_by="GradeHistory.effective_from.desc()"
    )
    family: Mapped[Optional["Family"]] = relationship(back_populates="children", foreign_keys=[family_id])


class Exam(Base):
    """考试/测验记录"""
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)  # 语文/数学/英语...
    exam_name: Mapped[str] = mapped_column(String(128))  # 期中/单元测验/随堂测
    exam_type: Mapped[str] = mapped_column(String(32), default="quiz")  # exam/quiz/homework
    score: Mapped[float] = mapped_column(Float)
    full_score: Mapped[float] = mapped_column(Float, default=100.0)
    target_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 家长设定的目标分
    class_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grade_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exam_date: Mapped[date] = mapped_column(Date, index=True)
    knowledge_points: Mapped[list] = mapped_column(JSON, default=list)  # 涉及知识点标签
    wrong_questions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 错题简述
    teacher_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grade_snapshot: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # 考试时的年级快照
    class_average: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 班级平均分（满分同 full_score）
    # 纸面分析（冗余字段，存 ExamQuestion 聚合，避免每次分析都 JOIN）
    paper_total_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 纸面满分
    paper_actual_scored: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 纸面实际得分
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship(back_populates="exams")
    questions: Mapped[list["ExamQuestion"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan",
        order_by="ExamQuestion.section_name, ExamQuestion.number"
    )


class ExamQuestion(Base):
    """单次考试的单题记录（AI 工具录入的最小单位）

    设计原则：
    - 每场考试的每题一条记录，AI 工具逐题识别后批量 POST 进来
    - paper_analysis / history_analysis 按题型/KP 聚合都走 GROUP BY，性能好
    - raw_payload 保留 AI 原始返回，schema 变了能回溯/调试
    """
    __tablename__ = "exam_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exams.id", ondelete="CASCADE"), index=True
    )
    section_name: Mapped[str] = mapped_column(String(64))  # "一、选择题"
    number: Mapped[int] = mapped_column(Integer)  # 试卷上的题号
    type: Mapped[str] = mapped_column(String(32), index=True)  # 题型枚举
    max_score: Mapped[float] = mapped_column(Float)  # 满分
    scored: Mapped[float] = mapped_column(Float)  # 实际得分
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # True/False/None（部分对）
    knowledge_points: Mapped[list] = mapped_column(JSON, default=list)  # 涉及的 KP 标签
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 题目文本（OCR 出来就填）
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="manual")  # manual / ocr_v1 / import
    raw_payload: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # AI 原始返回存根
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    exam: Mapped["Exam"] = relationship(back_populates="questions")


class Homework(Base):
    """日常作业/练习记录"""
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(128))
    homework_date: Mapped[date] = mapped_column(Date, index=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_questions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    correct_questions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    completed: Mapped[bool] = mapped_column(Boolean, default=True)
    difficulty: Mapped[str] = mapped_column(String(16), default="normal")  # easy/normal/hard
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grade_snapshot: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # 作业时的年级快照
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship(back_populates="homeworks")


class KnowledgePoint(Base):
    """知识点标签库（按科目分类）"""
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 大类，如：代数/几何
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grade_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


class Timeline(Base):
    """成长时间轴事件"""
    __tablename__ = "timelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)  # exam/award/milestone/note
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    attachments: Mapped[list] = mapped_column(JSON, default=list)  # 图片/文件路径
    tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship(back_populates="timelines")


class GradeHistory(Base):
    """升年级时间线：每个孩子的每次升年级一条记录"""
    __tablename__ = "grade_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    grade: Mapped[str] = mapped_column(String(32))  # 年级，如"四年级"
    effective_from: Mapped[date] = mapped_column(Date, index=True)  # 生效日期
    note: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # 可选备注
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship(back_populates="grade_history")


class AIReport(Base):
    """外部 AI 报告（手动导入，不持久化由系统生成的报告）"""
    __tablename__ = "ai_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    raw_markdown: Mapped[str] = mapped_column(Text)  # 用户粘回来的 AI 报告原文
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # 摘要（可选）
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 来源标识：deepseek / kimi / gpt-4o / 自定义
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # 报告覆盖的时间段起
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)  # 报告覆盖的时间段止
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()

class WrongQuestion(Base):
    """错题本记录"""
    __tablename__ = "wrong_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(16), default="manual")  # manual/exam/homework/bank
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bank_question_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True
    )  # 智能匹配到的题库题目
    subject: Mapped[str] = mapped_column(String(32), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    question_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correct_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_reason: Mapped[str] = mapped_column(String(32), default="other")  # knowledge_gap/misunderstanding/careless/incomplete/other
    knowledge_points: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(16), default="normal")  # easy/normal/hard
    mastery_level: Mapped[str] = mapped_column(String(16), default="new")  # new/learning/mastered
    wrong_count: Mapped[int] = mapped_column(Integer, default=1)
    last_wrong_date: Mapped[date] = mapped_column(Date, default=date.today)
    next_review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active/archived/mastered
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()
    bank_question: Mapped[Optional["Question"]] = relationship()
    reviews: Mapped[list["WrongQuestionReview"]] = relationship(back_populates="wrong_question", cascade="all, delete-orphan")


class WrongQuestionReview(Base):
    """错题复习记录"""
    __tablename__ = "wrong_question_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wrong_question_id: Mapped[int] = mapped_column(ForeignKey("wrong_questions.id", ondelete="CASCADE"), index=True)
    review_date: Mapped[date] = mapped_column(Date, default=date.today)
    result: Mapped[str] = mapped_column(String(16))  # correct/partial/wrong
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    wrong_question: Mapped["WrongQuestion"] = relationship(back_populates="reviews")


class GrowthRecord(Base):
    """生长发育记录"""
    __tablename__ = "growth_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True)
    height_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bmi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vision_left: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vision_right: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()


class SocialEmotionalRecord(Base):
    """社交情感记录"""
    __tablename__ = "social_emotional_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True)
    mood_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    emotion_tags: Mapped[list] = mapped_column(JSON, default=list)  # ["happy", "anxious", ...]
    social_activity: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    confidence_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()


class InterestRecord(Base):
    """兴趣特长记录"""
    __tablename__ = "interest_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True)
    activity_type: Mapped[str] = mapped_column(String(32))  # 运动/音乐/美术/编程/阅读/其他
    activity_name: Mapped[str] = mapped_column(String(128))
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skill_level: Mapped[str] = mapped_column(String(16), default="beginner")  # beginner/intermediate/advanced
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()


# ============ 奖励系统模型 ============

# 王者荣耀段位枚举
RANK_TIERS = [
    (0, "青铜", "#8B7355"),
    (60, "白银", "#C0C0C0"),
    (70, "黄金", "#FFD700"),
    (80, "铂金", "#00BFFF"),
    (85, "钻石", "#B9F2FF"),
    (90, "星耀", "#FF6B9D"),
    (95, "王者", "#FF4500"),
]

RANK_COLORS = {t[1]: t[2] for t in RANK_TIERS}


class ChildRank(Base):
    """孩子各科目段位（基于历史均分，自动计算）"""
    __tablename__ = "child_ranks"
    # DB-1：一个孩子一个科目只允许一行段位（upsert 竞态防护）
    __table_args__ = (
        Index("ux_child_ranks_child_subject", "child_id", "subject", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    subject: Mapped[str] = mapped_column(String(32), index=True)
    tier: Mapped[str] = mapped_column(String(16), default="青铜")  # 段位名称
    stars: Mapped[int] = mapped_column(Integer, default=0)  # 0-3 颗星
    avg_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 当前均分
    exam_count: Mapped[int] = mapped_column(Integer, default=0)  # 累计考试次数
    total_points: Mapped[int] = mapped_column(Integer, default=0)  # 累计获得积分
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()


class Reward(Base):
    """奖励池定义（家长配置）"""
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    reward_type: Mapped[str] = mapped_column(String(16), default="material")  # material/spiritual/privilege
    cost_points: Mapped[int] = mapped_column(Integer, default=0)  # 0 表示免费/自动发放
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(32), default="🎁")  # emoji
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


class ChildReward(Base):
    """孩子兑换/获得奖励记录"""
    __tablename__ = "child_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    reward_id: Mapped[int] = mapped_column(ForeignKey("rewards.id", ondelete="CASCADE"))
    points_spent: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(16), default="shop")  # shop/auto/event
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    earned_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()
    reward: Mapped["Reward"] = relationship()


class Achievement(Base):
    """成就定义（自动检测，无需积分）"""
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # first_exam / perfect_score / improvement_streak_3
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(32), default="🏆")
    condition_type: Mapped[str] = mapped_column(String(32))  # first_exam / perfect_score / improvement / streak
    condition_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


class ChildAchievement(Base):
    """孩子获得的成就"""
    __tablename__ = "child_achievements"
    # DB-2：防重复授予的数据库级兜底。exam_id 可为 NULL（里程碑型成就），
    # 而 SQL 标准中 NULL 之间互不相等，普通唯一索引拦不住多条 NULL 记录，
    # 因此用表达式索引把 NULL 归一为 -1 参与唯一性判定。
    # 用 COALESCE 而非 IFNULL：前者是 SQL 标准函数（SQLite/MySQL/PostgreSQL 均支持），
    # 后者仅 SQLite/MySQL 有，未来换数据库时不必改索引定义。
    # 应用层去重见 routers/rewards.py grant_achievement；此处是最后防线。
    __table_args__ = (
        Index(
            "ux_child_achievements_dedup",
            "child_id", "achievement_id", text("COALESCE(exam_id, -1)"),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"))
    exam_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 触发这次考试的ID
    earned_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()
    achievement: Mapped["Achievement"] = relationship(lazy="joined")


class PointsLog(Base):
    """积分变动日志"""
    __tablename__ = "points_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    points: Mapped[int] = mapped_column(Integer)  # 正数=获得，负数=消费
    source: Mapped[str] = mapped_column(String(32))  # exam_reward / redemption / bonus / manual
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()


# ============ 题库系统模型 ============

class QuestionBank(Base):
    """题库分组（按年级+科目）"""
    __tablename__ = "question_banks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    grade: Mapped[str] = mapped_column(String(32), index=True)  # 四年级/五年级
    subject: Mapped[str] = mapped_column(String(32), index=True)  # 英语/数学
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    questions: Mapped[list["Question"]] = relationship(back_populates="bank", cascade="all, delete-orphan")
    exercises: Mapped[list["Exercise"]] = relationship(back_populates="bank", cascade="all, delete-orphan")


class Question(Base):
    """题目（当前支持单选题）"""
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id", ondelete="CASCADE"), index=True)
    knowledge_point: Mapped[str] = mapped_column(String(128), index=True)  # 知识点标签
    question_type: Mapped[str] = mapped_column(String(16), default="single_choice")  # 当前只做单选题
    difficulty: Mapped[str] = mapped_column(String(16), default="normal")  # easy/normal/hard
    content: Mapped[str] = mapped_column(Text)  # 题干
    options: Mapped[list] = mapped_column(JSON, default=list)  # ["A. xxx", "B. xxx", ...]
    correct_answer: Mapped[str] = mapped_column(String(8))  # "A" / "B" / "C" / "D"
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 解析
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    bank: Mapped["QuestionBank"] = relationship(back_populates="questions")


class Exercise(Base):
    """练习记录（学生答题会话）"""
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id", ondelete="CASCADE"), index=True)
    questions: Mapped[list] = mapped_column(JSON)  # 快照: [{id, content, options, correct_answer, explanation, knowledge_point, difficulty}]
    answers: Mapped[list] = mapped_column(JSON, default=list)  # [{question_id, selected, is_correct}]
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    time_spent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 练习耗时(秒)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    child: Mapped["Child"] = relationship()
    bank: Mapped["QuestionBank"] = relationship(back_populates="exercises")


# ============ 教材版本 / 单元系统（与题库对接） ============

class TextbookVersion(Base):
    """教材版本：按出版社/学制区分"""
    __tablename__ = "textbook_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # SH-5-4-2025A / SH-MODULE-2025A / PEP-2025A
    name: Mapped[str] = mapped_column(String(128))  # 沪教版五四学制 2025 秋四年级上册
    publisher: Mapped[str] = mapped_column(String(64))  # 上海教育出版社
    grade: Mapped[str] = mapped_column(String(32), index=True)  # 四年级
    subject: Mapped[str] = mapped_column(String(32), index=True)  # 英语
    term: Mapped[str] = mapped_column(String(8), default="A")  # A 上册 / B 下册 / FULL 全一册
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    units: Mapped[list["TextbookUnit"]] = relationship(back_populates="version", cascade="all, delete-orphan", order_by="TextbookUnit.unit_number")


class TextbookUnit(Base):
    """教材单元（Module/Unit/Starter 任一）"""
    __tablename__ = "textbook_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("textbook_versions.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(16), index=True)  # U1, U2.../ Starter/ Project1
    unit_number: Mapped[int] = mapped_column(Integer)  # 排序用
    title_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title_zh: Mapped[str] = mapped_column(String(128))  # My school / 我的学校
    topic_words: Mapped[list] = mapped_column(JSON, default=list)  # 主题词列表
    sound: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # 自然拼读焦点: w / x / y / sh
    sound_examples: Mapped[list] = mapped_column(JSON, default=list)  # 例词: ["wall", "water"]
    structure: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # 语法结构: have no = don't have any
    big_task: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 综合任务
    project_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 作品类型: poem/profile/photo
    page_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_project: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    version: Mapped["TextbookVersion"] = relationship(back_populates="units")
    study_progresses: Mapped[list["StudyProgress"]] = relationship(back_populates="unit", cascade="all, delete-orphan")
    project_works: Mapped[list["ProjectWork"]] = relationship(back_populates="unit", cascade="all, delete-orphan")


class QuestionUnit(Base):
    """题目与教材单元的多对多关联"""
    __tablename__ = "question_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("textbook_units.id", ondelete="CASCADE"), index=True)
    relevance: Mapped[str] = mapped_column(String(16), default="primary")  # primary / supplementary / cross
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


class StudyProgress(Base):
    """孩子对每个教材单元的掌握进度"""
    __tablename__ = "study_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("textbook_units.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="not_started")  # not_started/in_progress/mastered
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)  # 累计练习题数
    total_correct: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    completion_pct: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100, 按题库中本 Unit 题目的完成率
    mastered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_study_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    unit: Mapped["TextbookUnit"] = relationship(back_populates="study_progresses")


class ProjectWork(Base):
    """教材 Big Task / Project 活动提交的作品"""
    __tablename__ = "project_works"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("textbook_units.id", ondelete="CASCADE"), index=True)
    work_type: Mapped[str] = mapped_column(String(32), default="text")  # text / image / drawing / audio
    title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 文本作业
    image_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 上传图片路径
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100 AI 评分
    ai_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI 评语
    parent_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 家长点评
    teacher_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 教师点评
    status: Mapped[str] = mapped_column(String(16), default="submitted")  # submitted / reviewed / approved / needs_revision
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    unit: Mapped["TextbookUnit"] = relationship(back_populates="project_works")


class UnitAchievementLog(Base):
    """Unit 成就解锁日志（防重复触发）"""
    __tablename__ = "unit_achievement_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("textbook_units.id", ondelete="CASCADE"), index=True)
    achievement_code: Mapped[str] = mapped_column(String(64), index=True)  # UNIT_MASTERED / STREAK_3
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    awarded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


# ============ 知识点 ↔ 教材单元 多对多关联 ============

class KnowledgePointUnit(Base):
    """KnowledgePoint 与 TextbookUnit 的多对多关联"""
    __tablename__ = "knowledge_point_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), index=True
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("textbook_units.id", ondelete="CASCADE"), index=True
    )
    relevance: Mapped[str] = mapped_column(String(16), default="primary")  # primary/secondary/review
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


class QuestionKnowledgePoint(Base):
    """Question 与 KnowledgePoint 的多对多关联（官方标签）"""
    __tablename__ = "question_knowledge_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)  # True=主要考察该KP, False=次要涉及
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))


class KPStudyProgress(Base):
    """孩子对每个知识点（KP）的掌握进度（Unit 内细粒度）"""
    __tablename__ = "kp_study_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("children.id", ondelete="CASCADE"), index=True)
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id", ondelete="CASCADE"), index=True
    )
    unit_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("textbook_units.id", ondelete="CASCADE"), nullable=True, index=True
    )
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    total_correct: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    mastery_level: Mapped[str] = mapped_column(String(16), default="new")  # new/learning/strong/mastered
    last_study_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))



# ============ 多用户认证（v1.6.0）============

class Family(Base):
    """家庭（数据隔离单元）

    同一家庭内的家长和孩子共享数据；不同家庭之间完全隔离。
    本期家庭只有一个，多家庭是未来 schema 演进方向，Family 表先建好。
    """
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))  # 例：'李老师家'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    users: Mapped[list["User"]] = relationship(back_populates="family", cascade="all, delete-orphan")
    children: Mapped[list["Child"]] = relationship(back_populates="family")


class User(Base):
    """登录账号（家长或孩子）

    - role='parent'：可见本家庭所有孩子的数据；可以创建/管理子账号
    - role='child'：仅可见 child_id 对应孩子的数据
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"), index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # 登录名（全局唯一）
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), index=True)  # 'parent' | 'child'
    child_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=True, unique=True, index=True
    )  # 仅 role='child' 时使用：账号绑定的孩子档案
    display_name: Mapped[str] = mapped_column(String(64))  # 显示名（中文姓名/昵称）
    avatar_color: Mapped[str] = mapped_column(String(16), default="#6366f1")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    family: Mapped["Family"] = relationship(back_populates="users")
    child: Mapped[Optional["Child"]] = relationship(foreign_keys=[child_id])

    __table_args__ = (
        # role 限定值（SQLite CHECK 约束靠 enum 不强，靠应用层校验）
        Index("ix_users_family_role", "family_id", "role"),
    )
