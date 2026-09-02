"""奖励系统路由：段位 / 奖励商城 / 成就 / 积分"""
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import assert_child_access, get_accessible_child_ids, require_parent
from models import (
    RANK_COLORS,
    RANK_TIERS,
    Achievement,
    Child,
    ChildAchievement,
    ChildRank,
    ChildReward,
    Exam,
    KPStudyProgress,
    PointsLog,
    Reward,
    User,
)
from schemas import (
    AchievementCreate,
    AchievementOut,
    ChildAchievementOut,
    ChildRewardOut,
    ExamRewardResponse,
    PointsLogOut,
    PointsSummary,
    RankInfo,
    RewardCreate,
    RewardOut,
    RewardShopItem,
    RewardUpdate,
)

router = APIRouter(prefix="/api/rewards", tags=["奖励系统"])

logger = logging.getLogger("childstudy")


# ============ 段位 ============

def calc_tier(avg: Optional[float]) -> tuple[str, int]:
    """根据均分计算段位和星星数"""
    if avg is None:
        return "青铜", 0
    tier_name = "青铜"
    stars = 0
    for threshold, name, _ in RANK_TIERS:
        if avg >= threshold:
            tier_name = name
    # 星星：在当前段位内的精细度（0-3星）
    idx = next((i for i, t in enumerate(RANK_TIERS) if t[1] == tier_name), 0)
    low = RANK_TIERS[idx][0]
    high = RANK_TIERS[idx + 1][0] if idx + 1 < len(RANK_TIERS) else 100
    span = high - low
    if span > 0:
        frac = (avg - low) / span
        stars = min(3, max(0, int(frac * 4)))
    return tier_name, stars


async def recalc_subject_rank(db: AsyncSession, child_id: int, subject: str) -> Optional[ChildRank]:
    """重算某孩子某科目的段位记录（唯一入口，三处调用方共用，勿再内联复制）。

    调用方：exam_reward（录入后）/ recalculate_ranks（全量重算）/ delete_exam（删后重算）。

    口径：
      - 均分/段位/星数/场次：基于该科目当前全部考试重算，多次调用结果一致（幂等）。
      - total_points：从积分流水恢复（source=exam_reward 且 source_id ∈ 该科目考试），
        与发放口径严格一致，天然幂等，顺带修复历史漂移。
      - 该科目已无任何考试时删除段位记录，避免幽灵段位。

    注意：session autoflush=False，先 flush 保证 pending 的 Exam/PointsLog 变更对查询可见。
    """
    await db.flush()

    exams = (await db.execute(
        select(Exam).where(Exam.child_id == child_id, Exam.subject == subject)
    )).scalars().all()

    rank = (await db.execute(
        select(ChildRank).where(ChildRank.child_id == child_id, ChildRank.subject == subject)
    )).scalar_one_or_none()

    if not exams:
        if rank:
            await db.delete(rank)
        return None

    scores = [(e.score / e.full_score * 100) for e in exams if e.full_score]
    avg = round(sum(scores) / len(scores), 1) if scores else None
    tier, stars = calc_tier(avg)

    exam_ids = [e.id for e in exams]
    total_points = (await db.execute(
        select(func.coalesce(func.sum(PointsLog.points), 0)).where(
            PointsLog.child_id == child_id,
            PointsLog.source == "exam_reward",
            PointsLog.source_id.in_(exam_ids),
        )
    )).scalar() or 0

    if not rank:
        rank = ChildRank(child_id=child_id, subject=subject)
        db.add(rank)
    rank.avg_score = avg
    rank.tier = tier
    rank.stars = stars
    rank.exam_count = len(scores)
    rank.total_points = int(total_points)
    await db.flush()
    return rank


@router.get("/ranks/{child_id}", response_model=List[RankInfo])
async def get_ranks(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    result = await db.execute(
        select(ChildRank).where(ChildRank.child_id == child_id)
    )
    ranks = result.scalars().all()
    out = []
    for r in ranks:
        color = RANK_COLORS.get(r.tier)
        out.append(RankInfo(
            subject=r.subject, tier=r.tier, stars=r.stars,
            avg_score=r.avg_score, exam_count=r.exam_count,
            total_points=r.total_points, color=color,
        ))
    return out


@router.post("/ranks/{child_id}/recalculate", response_model=List[RankInfo])
async def recalculate_ranks(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """根据所有考试重新计算段位（统一走 recalc_subject_rank，与 exam_reward / delete_exam 同口径）"""
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    # 需要处理的科目 = 有考试的科目 ∪ 已有段位记录的科目（后者可能因考试删空而需清理）
    subjects = set((await db.execute(
        select(Exam.subject).where(Exam.child_id == child_id).distinct()
    )).scalars().all())
    subjects.update(r.subject for r in (await db.execute(
        select(ChildRank).where(ChildRank.child_id == child_id)
    )).scalars().all())

    ranks: List[ChildRank] = []
    for subject in sorted(subjects):
        rank = await recalc_subject_rank(db, child_id, subject)
        if rank:
            ranks.append(rank)

    # expire_on_commit=False，但仍在 commit 前构建响应，避免任何过期访问
    out = [
        RankInfo(subject=r.subject, tier=r.tier, stars=r.stars,
                 avg_score=r.avg_score, exam_count=r.exam_count,
                 total_points=r.total_points,
                 color=RANK_COLORS.get(r.tier))
        for r in ranks
    ]
    await db.commit()
    return out


# ============ 积分 ============

def calc_exam_points(score: float, full_score: float) -> int:
    """考试积分：累计累进制（低于60分为0）

    分数段:
      60-70 : 每分 1 积分
      70-80 : 每分 1.2 积分
      80-85 : 每分 1.5 积分
      85-90 : 每分 1.8 积分
      90-95 : 每分 2.3 积分
      95-100: 每分 3 积分
    """
    if not full_score or full_score <= 0:
        return 0
    pct = min((score / full_score) * 100, 100.0)
    if pct <= 60:
        return 0
    pts = 0.0
    # 60-70 : ×1
    if pct > 70:
        pts += 10 * 1
    elif pct > 60:
        pts += (pct - 60) * 1
    # 70-80 : ×1.2
    if pct > 80:
        pts += 10 * 1.2
    elif pct > 70:
        pts += (pct - 70) * 1.2
    # 80-85 : ×1.5
    if pct > 85:
        pts += 5 * 1.5
    elif pct > 80:
        pts += (pct - 80) * 1.5
    # 85-90 : ×1.8
    if pct > 90:
        pts += 5 * 1.8
    elif pct > 85:
        pts += (pct - 85) * 1.8
    # 90-95 : ×2.3
    if pct > 95:
        pts += 5 * 2.3
    elif pct > 90:
        pts += (pct - 90) * 2.3
    # 95-100: ×3
    if pct > 100:
        pts += 5 * 3  # 保险上限
    elif pct > 95:
        pts += (pct - 95) * 3
    return round(pts)


async def get_total_points(db: AsyncSession, child_id: int) -> int:
    """当前可用总积分（累计 - 消费）。

    shop / redeem 等只需要总数的场景请用这个，
    不要调 get_points（它会额外取 20 条日志再丢弃）。
    """
    return (await db.execute(
        select(func.coalesce(func.sum(PointsLog.points), 0))
        .where(PointsLog.child_id == child_id)
    )).scalar() or 0


@router.get("/points/{child_id}", response_model=PointsSummary)
async def get_points(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    earned = (await db.execute(
        select(func.coalesce(func.sum(PointsLog.points), 0))
        .where(PointsLog.child_id == child_id, PointsLog.points > 0)
    )).scalar() or 0
    spent = (await db.execute(
        select(func.coalesce(func.sum(PointsLog.points), 0))
        .where(PointsLog.child_id == child_id, PointsLog.points < 0)
    )).scalar() or 0
    total = earned + spent  # spent is negative
    logs_result = await db.execute(
        select(PointsLog)
        .where(PointsLog.child_id == child_id)
        .order_by(desc(PointsLog.created_at))
        .limit(20)
    )
    logs = logs_result.scalars().all()
    return PointsSummary(
        total=total, earned=earned, spent=abs(spent),
        recent_logs=[PointsLogOut.model_validate(log) for log in logs],
    )


# ============ 考试奖励（编排层） ============

@router.post("/exam-reward/{exam_id}", response_model=ExamRewardResponse)
async def exam_reward(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """考试录入后调用：发放积分 + 检查成就 + 更新段位（幂等）

    Idempotency:
      - 积分：同一 exam 只发一次。backfill 不会双倍发分。
      - 成就：grant_achievement 内部检查 existing 防重。
      - 段位：recalc_subject_rank 按当前考试列表+积分流水重算，多次调用结果一致。
    """
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, "考试记录不存在")
    assert_child_access(accessible, exam.child_id)

    child = await db.get(Child, exam.child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    points = calc_exam_points(exam.score, exam.full_score)

    # 积分幂等：同一 exam 只发一次积分（防 backfill 重复发分）
    existing_log = (await db.execute(
        select(PointsLog).where(
            PointsLog.child_id == exam.child_id,
            PointsLog.source == "exam_reward",
            PointsLog.source_id == exam_id,
        )
    )).scalar_one_or_none()
    points_already_granted = existing_log is not None

    if not existing_log:
        log = PointsLog(
            child_id=exam.child_id, points=points,
            source="exam_reward", source_id=exam_id,
            description=f"{exam.exam_name} {exam.subject} +{points}分",
        )
        db.add(log)

    # 段位重算（统一入口；内部先 flush，使上面新加的积分日志对统计可见）
    rank = await recalc_subject_rank(db, exam.child_id, exam.subject)

    # 成就判定（单科类 + 综合类，可同时获得多个；只返回本次新授予的）
    new_achievements = await _grant_exam_achievements(db, exam, rank)

    await db.commit()

    # 构建响应
    new_rank = None
    if rank:
        new_rank = RankInfo(
            subject=rank.subject, tier=rank.tier, stars=rank.stars,
            avg_score=rank.avg_score, exam_count=rank.exam_count,
            total_points=rank.total_points,
            color=RANK_COLORS.get(rank.tier),
        )

    return ExamRewardResponse(
        points_earned=points,
        new_rank=new_rank,
        new_achievements=[
            ChildAchievementOut(
                id=a.id, child_id=a.child_id, achievement_id=a.achievement_id,
                exam_id=a.exam_id, earned_date=a.earned_date,
                achievement=AchievementOut.model_validate(a.achievement) if a.achievement else None,
            )
            for a in new_achievements
        ],
        message=f"🎉 +{points} 积分！继续加油！" if not points_already_granted else f"✅ 已处理过，本次未重复发放积分（应得 {points}）",
    )


# 累计考试次数里程碑（综合）
_EXAM_COUNT_MILESTONES = [
    ("exam_10", "💪 坚持不懈", "累计完成10次考试", 10),
    ("exam_20", "🏅 小有成就", "累计完成20次考试", 20),
    ("exam_50", "🎖️ 考者荣耀", "累计完成50次考试", 50),
    ("exam_100", "⛰️ 巅峰考者", "累计完成100次考试", 100),
]


async def _grant_exam_achievements(
    db: AsyncSession, exam: Exam, rank: Optional[ChildRank],
) -> List[ChildAchievement]:
    """考试后成就判定：单科类 + 综合类。只返回本次新授予的成就记录。"""
    granted: List[ChildAchievement] = []
    pct = (exam.score / exam.full_score * 100) if exam.full_score else 0

    async def _grant(code: str, name: str, desc: str, cond_type: str, cond_val: int) -> None:
        ach = await get_or_create_achievement(db, code, name, desc, cond_type, cond_val)
        ca, created = await grant_achievement(db, exam.child_id, ach.id, exam.id)
        if created:
            granted.append(ca)

    # ---- 单科：分数类 ----
    if exam.full_score and exam.score >= exam.full_score:
        await _grant("perfect_score", "💎 满分传说", "单科满分", "perfect_score", 1)
    if pct >= 90:
        await _grant("score_90", "🥇 优秀学员", "单科得分≥90", "score_above", 90)
    if pct >= 95:
        await _grant("score_95", "🧠 卓越学者", "单科得分≥95", "score_above", 95)

    # ---- 单科：趋势类（取最近 2 次同科目历史，同时服务"进步"与"连胜"判定）----
    prev_exams = (await db.execute(
        select(Exam)
        .where(Exam.child_id == exam.child_id, Exam.subject == exam.subject, Exam.id != exam.id)
        .order_by(Exam.exam_date.desc(), Exam.id.desc())
        .limit(2)
    )).scalars().all()
    if prev_exams and prev_exams[0].full_score:
        prev_pct = prev_exams[0].score / prev_exams[0].full_score * 100
        if pct - prev_pct >= 10:
            await _grant("improvement_10", "📈 进步之星", "单科比上次进步10分以上", "improvement", 10)
    if len(prev_exams) >= 2 and all(
        e.full_score and (e.score / e.full_score * 100) <= pct for e in prev_exams
    ):
        await _grant("streak_3", "🔥 连胜王者", "连续3次单科成绩不下降", "streak", 3)

    # ---- 次数里程碑（综合）----
    child_total_exams = (await db.execute(
        select(func.count(Exam.id)).where(Exam.child_id == exam.child_id)
    )).scalar() or 0
    if child_total_exams == 1:
        await _grant("first_exam", "🎯 入门学徒", "完成第一次考试", "first_exam", 1)

    subject_count = (await db.execute(
        select(func.count(Exam.id)).where(Exam.child_id == exam.child_id, Exam.subject == exam.subject)
    )).scalar() or 0
    if subject_count >= 5:
        await _grant("subject_5_times", "📚 学科达人", "某科目累计5次考试", "exam_count", 5)

    for _code, _name, _desc, _th in _EXAM_COUNT_MILESTONES:
        if child_total_exams >= _th:
            await _grant(_code, _name, _desc, "total_exams", _th)

    # ---- 综合状态类 ----
    # CQ-1 修复：按该孩子实际练习过的知识点统计（KPStudyProgress 去重），
    # 不再统计全库 KnowledgePoint 总数（那会让所有孩子一起解锁）。
    kp_count = (await db.execute(
        select(func.count(func.distinct(KPStudyProgress.knowledge_point_id)))
        .where(KPStudyProgress.child_id == exam.child_id)
    )).scalar() or 0
    if kp_count >= 50:
        await _grant("knowledge_50", "🧩 知识探索者", "累计解锁50个知识点", "knowledge_count", 50)

    if rank and rank.tier == "王者":
        await _grant("rank_king", "👑 终极王者", "任意科目达到王者段位", "rank_tier", 95)

    # 最近一次各科成绩 → 全能选手 / 顶尖高手
    latest_scores = {}
    all_subjects = (await db.execute(
        select(Exam.subject).where(Exam.child_id == exam.child_id).distinct()
    )).scalars().all()
    for subj in all_subjects:
        latest = (await db.execute(
            select(Exam).where(Exam.child_id == exam.child_id, Exam.subject == subj)
            .order_by(Exam.exam_date.desc(), Exam.id.desc()).limit(1)
        )).scalar_one_or_none()
        if latest and latest.full_score:
            latest_scores[subj] = latest.score / latest.full_score * 100
    if latest_scores and all(v >= 80 for v in latest_scores.values()):
        await _grant("all_above_80", "🌟 全能选手", "最近一次考试全部科目≥80分", "all_above", 80)
    if latest_scores and all(v >= 90 for v in latest_scores.values()):
        await _grant("all_above_90", "🌈 顶尖高手", "最近一次考试全部科目≥90分", "all_above", 90)

    # 五边形战士：4 个月内 5 门不同科目达到 95% 以上
    four_months_ago = date.today() - timedelta(days=120)
    high_subjects = (await db.execute(
        select(Exam.subject).distinct()
        .where(
            Exam.child_id == exam.child_id,
            Exam.exam_date >= four_months_ago,
            Exam.full_score.isnot(None),
            Exam.score * 100 >= Exam.full_score * 95,  # score/full_score >= 0.95
        )
    )).scalars().all()
    if len(high_subjects) >= 5:
        await _grant("pentagon_warrior", "🌟 五边形战士",
                     "4 个月内 5 门不同科目达到 95% 以上", "subjects_95_4m", 5)

    # ---- 积分里程碑（一次型）----
    # 注意：session autoflush=False，先把本次新加的 PointsLog 落库，否则求和会漏算当前考试的积分
    await db.flush()
    granted.extend(await check_points_milestones(db, exam.child_id, exam.id))

    return granted


# 积分里程碑（一次型）：当前总积分（累计-消费）首次达到阈值时授予
POINTS_MILESTONES = [
    ("points_100", "🪙 第一桶金", "积分首次达到100分", 100, "svg:gold-bucket"),
    ("points_200", "🐷 小财迷", "积分首次达到200分", 200, "🐷"),
    ("points_500", "🏦 积分大户", "积分首次达到500分", 500, "🏦"),
    ("points_700", "💰 富甲一方", "积分首次达到700分", 700, "💰"),
    ("points_1000", "🤑 腰缠万贯", "积分首次达到1000分", 1000, "🤑"),
]


async def check_points_milestones(db: AsyncSession, child_id: int, exam_id: Optional[int] = None) -> List[ChildAchievement]:
    """检查积分里程碑成就。grant_achievement 自带去重，可安全重复调用。

    只返回本次新授予的记录（已拥有但未达到更高阈值的不重复出现）。
    """
    total = (await db.execute(
        select(func.coalesce(func.sum(PointsLog.points), 0))
        .where(PointsLog.child_id == child_id)
    )).scalar() or 0
    granted: List[ChildAchievement] = []
    for code, name, description, threshold, icon in POINTS_MILESTONES:
        if total >= threshold:
            ach = await get_or_create_achievement(db, code, name, description, "total_points", threshold, icon)
            ca, created = await grant_achievement(db, child_id, ach.id, exam_id)
            if created:
                granted.append(ca)
    return granted


async def get_or_create_achievement(db: AsyncSession, code: str, name: str, desc: str, cond_type: str, cond_val: int, icon: Optional[str] = None) -> Achievement:
    """获取或创建成就定义。

    icon 参数：若为 None，默认从 name 提取开头的 emoji（成就墙卡片主图标），
    避免 seed 错过 icon 字段。提取不到时退回到默认 🏆。
    """
    ach = (await db.execute(
        select(Achievement).where(Achievement.code == code)
    )).scalar_one_or_none()
    if not ach:
        if icon is None:
            m = re.match(r'^([\U0001F300-\U0001FAFF\U00002600-\U000027BF]+)', name)
            icon = m.group(1) if m else "🏆"
        ach = Achievement(
            code=code, name=name, description=desc,
            condition_type=cond_type, condition_value=cond_val, icon=icon,
        )
        db.add(ach)
        await db.flush()
    return ach


# 可重复获得的成就（每次考试达成都算一次获得）；其余为里程碑/累计型，仅获得一次
# 注意：全科类（all_above_*）只看"各科最近一次考试"的全局状态，与当前考试无关，属状态型成就，不重复计
REPEATABLE_ACHIEVEMENT_CODES = {
    "perfect_score",   # 单科满分：每考一次满分算一次
    "score_90",        # 单科≥90：每次达成都算
    "score_95",        # 单科≥95：每次达成都算
    "improvement_10",  # 进步之星：每次进步≥10 都算
    "streak_3",        # 连胜王者：每达成一轮连胜都算
}


async def grant_achievement(db: AsyncSession, child_id: int, achievement_id: int, exam_id: Optional[int]) -> Tuple[ChildAchievement, bool]:
    """授予成就。返回 (成就记录, 是否本次新授予)。

    - 里程碑型成就按 child+achievement 去重，仅获得一次。
    - 可重复型成就（REPEATABLE_ACHIEVEMENT_CODES）每次达成新增一条记录，
      幂等键为 child+achievement+exam：同一场考试对同一成就只发一次，backfill 重跑不会重复。

    注意：可重复型成就的幂等键含 exam_id，调用方必须传 exam_id；否则会因为 NULL 匹配行为
    在不同方言下行为不一致（SQLite 的 `NULL = NULL` 不为真，可能双发）。Assertion 仅作
    早期防线，真实幂等仍依赖应用层正确传参。
    """
    ach = await db.get(Achievement, achievement_id)
    repeatable = bool(ach and ach.code in REPEATABLE_ACHIEVEMENT_CODES)

    if repeatable:
        assert exam_id is not None, (
            f"grant_achievement: 可重复型成就 {ach.code!r} 必须传 exam_id 以保证幂等"
        )
        existing = (await db.execute(
            select(ChildAchievement).where(
                ChildAchievement.child_id == child_id,
                ChildAchievement.achievement_id == achievement_id,
                ChildAchievement.exam_id == exam_id,
            )
        )).scalars().first()
    else:
        # 防止重复授予
        existing = (await db.execute(
            select(ChildAchievement).where(
                ChildAchievement.child_id == child_id,
                ChildAchievement.achievement_id == achievement_id,
            )
        )).scalar_one_or_none()
    if existing:
        return existing, False
    ca = ChildAchievement(child_id=child_id, achievement_id=achievement_id, exam_id=exam_id)
    db.add(ca)
    await db.flush()
    # eager-load achievement relationship，避免 commit 后访问触发 lazy load 报 greenlet 错误
    await db.refresh(ca, ['achievement'])
    return ca, True


@router.post("/backfill/{child_id}")
async def backfill_rewards(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """按时间顺序遍历该 child 所有考试，重新跑 exam_reward 逻辑（幂等）。

    用途:
      - 历史数据补全：之前直接 SQL 插入的考试不会触发成就/积分
      - 修复：任何原因造成 child_achievements / ranks 不一致的情况

    实现说明:
      - 调用 exam_reward() 复用幂等逻辑
      - 按 exam_date asc 顺序处理，后期考试能引用前期的成累计（例 subject_5_times）
    """
    assert_child_access(accessible, child_id)
    child = await db.get(Child, child_id)
    if not child:
        raise HTTPException(404, "孩子档案不存在")

    exams_result = await db.execute(
        select(Exam)
        .where(Exam.child_id == child_id)
        .order_by(Exam.exam_date.asc(), Exam.id.asc())
    )
    exams = exams_result.scalars().all()

    processed = 0
    # 用前后总数差统计"实际新增"的成就记录（exam_reward 返回的只含新授予的，
    # 但直接累加会受其他写入方干扰，前后差是最终事实）
    count_before = (await db.execute(
        select(func.count(ChildAchievement.id)).where(ChildAchievement.child_id == child_id)
    )).scalar() or 0
    for exam in exams:
        await exam_reward(exam.id, db)
        processed += 1
    count_after = (await db.execute(
        select(func.count(ChildAchievement.id)).where(ChildAchievement.child_id == child_id)
    )).scalar() or 0
    new_achievements_total = max(count_after - count_before, 0)

    return {
        "ok": True,
        "exams_processed": processed,
        "new_achievements_total": new_achievements_total,
        "message": f"已处理 {processed} 场考试，新增解锁 {new_achievements_total} 个成就",
    }


# ============ 奖励池 CRUD ============

@router.get("/rewards", response_model=List[RewardOut])
async def list_rewards(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Reward).order_by(Reward.cost_points, Reward.id))
    return result.scalars().all()


@router.post("/rewards", response_model=RewardOut)
async def create_reward(
    payload: RewardCreate,
    _parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    r = Reward(**payload.model_dump())
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


@router.put("/rewards/{reward_id}", response_model=RewardOut)
async def update_reward(
    reward_id: int,
    payload: RewardUpdate,
    _parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    r = await db.get(Reward, reward_id)
    if not r:
        raise HTTPException(404, "奖励不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    await db.commit()
    await db.refresh(r)
    return r


@router.delete("/rewards/{reward_id}")
async def delete_reward(
    reward_id: int,
    _parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    r = await db.get(Reward, reward_id)
    if not r:
        raise HTTPException(404, "奖励不存在")
    await db.delete(r)
    await db.commit()
    return {"ok": True}


# ============ 兑换商城 ============

@router.get("/shop/{child_id}", response_model=List[RewardShopItem])
async def shop(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    points = await get_total_points(db, child_id)
    rewards_result = await db.execute(
        select(Reward).where(Reward.is_active).order_by(Reward.cost_points, Reward.id)
    )
    rewards = rewards_result.scalars().all()
    return [
        RewardShopItem(reward=RewardOut.model_validate(r), can_afford=points >= r.cost_points)
        for r in rewards
    ]


@router.post("/redeem/{child_id}/{reward_id}", response_model=ChildRewardOut)
async def redeem(
    child_id: int,
    reward_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    reward = await db.get(Reward, reward_id)
    if not reward or not reward.is_active:
        raise HTTPException(404, "奖励不存在")

    points = await get_total_points(db, child_id)
    if points < reward.cost_points:
        raise HTTPException(400, f"积分不足，需要 {reward.cost_points} 积分")

    # 扣积分
    log = PointsLog(
        child_id=child_id, points=-reward.cost_points,
        source="redemption", source_id=reward_id,
        description=f"兑换：{reward.name}",
    )
    db.add(log)

    cr = ChildReward(
        child_id=child_id, reward_id=reward_id,
        points_spent=reward.cost_points, source="shop",
    )
    db.add(cr)
    await db.commit()
    await db.refresh(cr)
    # 手动构造返回，避免异步上下文 lazy load cr.reward 报错
    return ChildRewardOut(
        id=cr.id, child_id=cr.child_id, reward_id=cr.reward_id,
        points_spent=cr.points_spent, source=cr.source, note=cr.note,
        earned_date=cr.earned_date,
        status=cr.status, used_at=cr.used_at, used_by=cr.used_by,
        reward=RewardOut.model_validate(reward),
    )


@router.get("/history/{child_id}", response_model=List[ChildRewardOut])
async def redemption_history(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    result = await db.execute(
        select(ChildReward)
        .options(selectinload(ChildReward.reward))
        .where(ChildReward.child_id == child_id)
        .order_by(desc(ChildReward.created_at))
        .limit(50)
    )
    rows = result.scalars().all()
    out = []
    for cr in rows:
        out.append(ChildRewardOut(
            id=cr.id, child_id=cr.child_id, reward_id=cr.reward_id,
            points_spent=cr.points_spent, source=cr.source, note=cr.note,
            earned_date=cr.earned_date,
            status=cr.status, used_at=cr.used_at, used_by=cr.used_by,
            reward=RewardOut.model_validate(cr.reward) if cr.reward else None,
        ))
    return out


@router.post("/history/{cr_id}/mark-used", response_model=ChildRewardOut)
async def mark_reward_used(
    cr_id: int,
    parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    """家长核销：把孩子已兑换的奖励标记为已使用（实物/权益已交付）。"""
    result = await db.execute(
        select(ChildReward)
        .options(selectinload(ChildReward.reward))
        .where(ChildReward.id == cr_id)
    )
    cr = result.scalars().first()
    if not cr:
        raise HTTPException(404, "兑换记录不存在")
    assert_child_access(accessible, cr.child_id)
    if cr.status == "used":
        raise HTTPException(400, "该奖励已核销过")

    cr.status = "used"
    cr.used_at = datetime.now(timezone.utc)
    cr.used_by = parent.id
    await db.commit()
    return ChildRewardOut(
        id=cr.id, child_id=cr.child_id, reward_id=cr.reward_id,
        points_spent=cr.points_spent, source=cr.source, note=cr.note,
        earned_date=cr.earned_date,
        status=cr.status, used_at=cr.used_at, used_by=cr.used_by,
        reward=RewardOut.model_validate(cr.reward) if cr.reward else None,
    )


# ============ 成就 CRUD ============

@router.get("/achievements", response_model=List[AchievementOut])
async def list_achievements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Achievement).order_by(Achievement.id))
    return result.scalars().all()


@router.post("/achievements", response_model=AchievementOut)
async def create_achievement(
    payload: AchievementCreate,
    _parent: User = Depends(require_parent),
    db: AsyncSession = Depends(get_db),
):
    a = Achievement(**payload.model_dump())
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


@router.get("/achievements/{child_id}", response_model=List[ChildAchievementOut])
async def child_achievements(
    child_id: int,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    result = await db.execute(
        select(ChildAchievement)
        .where(ChildAchievement.child_id == child_id)
        .order_by(desc(ChildAchievement.created_at))
    )
    rows = result.scalars().all()
    out = []
    for ca in rows:
        out.append(ChildAchievementOut(
            id=ca.id, child_id=ca.child_id, achievement_id=ca.achievement_id,
            exam_id=ca.exam_id, earned_date=ca.earned_date,
            achievement=AchievementOut.model_validate(ca.achievement) if ca.achievement else None,
        ))
    return out


# ============ 积分日志 ============

@router.get("/points-log/{child_id}", response_model=List[PointsLogOut])
async def points_log(
    child_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    accessible: set[int] = Depends(get_accessible_child_ids),
):
    assert_child_access(accessible, child_id)
    result = await db.execute(
        select(PointsLog)
        .where(PointsLog.child_id == child_id)
        .order_by(desc(PointsLog.created_at))
        .limit(min(limit, 100))
    )
    return result.scalars().all()
