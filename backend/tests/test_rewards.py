"""rewards.py 测试：积分计算 + 12 类成就判定 + 幂等性"""
import pytest
import pytest_asyncio
from pydantic import ValidationError
from sqlalchemy import select

from models import (
    Achievement,
    ChildAchievement,
    KnowledgePoint,
    KPStudyProgress,
    PointsLog,
)
from routers.rewards import calc_exam_points, exam_reward
from schemas import AchievementCreate

# ==================== 纯函数：calc_exam_points ====================

class TestCalcExamPoints:
    """考试积分分段计算"""

    def test_below_60_returns_zero(self):
        assert calc_exam_points(50, 100) == 0
        assert calc_exam_points(0, 100) == 0
        assert calc_exam_points(60, 100) == 0  # 恰好 60% 也是 0

    def test_zero_full_score_returns_zero(self):
        assert calc_exam_points(90, 0) == 0
        assert calc_exam_points(90, -10) == 0

    def test_60_to_70_range(self):
        # 65% → (65-60)*1 = 5
        assert calc_exam_points(65, 100) == 5

    def test_70_to_80_range(self):
        # 75% → 10*1 + (75-70)*1.2 = 10 + 6 = 16
        assert calc_exam_points(75, 100) == 16

    def test_80_to_85_range(self):
        # 82% → 10*1 + 10*1.2 + (82-80)*1.5 = 10 + 12 + 3 = 25
        assert calc_exam_points(82, 100) == 25

    def test_85_to_90_range(self):
        # 87% → 10 + 12 + 5*1.5 + (87-85)*1.8 = 10+12+7.5+3.6 = 33.1 → 33
        assert calc_exam_points(87, 100) == 33

    def test_90_to_95_range(self):
        # 92% → 10+12+7.5+5*1.8+(92-90)*2.3 = 10+12+7.5+9+4.6 = 43.1 → 43
        assert calc_exam_points(92, 100) == 43

    def test_95_to_100_range(self):
        # 97% → 10+12+7.5+9+5*2.3+(97-95)*3 = 10+12+7.5+9+11.5+6 = 56
        assert calc_exam_points(97, 100) == 56

    def test_perfect_score(self):
        # 100% → 10+12+7.5+9+11.5+5*3 = 65
        assert calc_exam_points(100, 100) == 65

    def test_non_100_full_score(self):
        # 45/50 = 90% → 同 90% 档位
        pts = calc_exam_points(45, 50)
        assert pts == calc_exam_points(90, 100)


# ==================== 集成测试：exam_reward ====================

class TestExamRewardIdempotency:
    """同一场考试多次调用只发一次积分"""

    async def test_same_exam_no_double_points(self, db_session, make_child, make_exam):
        child = await make_child()
        exam = await make_exam(child.id, score=90, full_score=100)

        # 第一次
        r1 = await exam_reward(exam.id, db_session)
        first_points = r1.points_earned
        assert first_points > 0
        assert "🎉" in r1.message

        # 第二次（幂等）
        r2 = await exam_reward(exam.id, db_session)
        assert r2.points_earned == first_points  # 计算值相同
        assert "已处理过" in r2.message  # 但文案不同

        # 实际只有一条积分日志
        from sqlalchemy import func, select
        count = (await db_session.execute(
            select(func.count(PointsLog.id)).where(
                PointsLog.child_id == child.id,
                PointsLog.source == "exam_reward",
                PointsLog.source_id == exam.id,
            )
        )).scalar()
        assert count == 1

    async def test_different_exams_both_grant(self, db_session, make_child, make_exam):
        child = await make_child()
        e1 = await make_exam(child.id, score=85, full_score=100, exam_name="测试1")
        e2 = await make_exam(child.id, score=90, full_score=100, exam_name="测试2")

        r1 = await exam_reward(e1.id, db_session)
        r2 = await exam_reward(e2.id, db_session)
        assert r1.points_earned > 0
        assert r2.points_earned > 0


class TestAchievements:
    """12 类成就触发条件"""

    async def test_first_exam(self, db_session, make_child, make_exam):
        """首次考试 → 🎯 入门学徒"""
        child = await make_child()
        exam = await make_exam(child.id, score=70, full_score=100)
        r = await exam_reward(exam.id, db_session)

        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "first_exam" in codes

    async def test_perfect_score(self, db_session, make_child, make_exam):
        """满分 → 💎 满分传说"""
        child = await make_child()
        exam = await make_exam(child.id, score=100, full_score=100)
        r = await exam_reward(exam.id, db_session)

        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "perfect_score" in codes
        assert "score_90" in codes  # 满分也 ≥90
        assert "score_95" in codes  # 满分也 ≥95

    async def test_score_90_and_95(self, db_session, make_child, make_exam):
        """单科 ≥90 / ≥95 分别触发"""
        child = await make_child()
        e90 = await make_exam(child.id, score=90, full_score=100, exam_name="A")
        r = await exam_reward(e90.id, db_session)
        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "score_90" in codes
        assert "score_95" not in codes

    async def test_improvement_10(self, db_session, make_child, make_exam):
        """单科比上次进步 ≥10 → 📈 进步之星"""
        child = await make_child()
        e1 = await make_exam(child.id, score=60, full_score=100, exam_name="第一次")
        await exam_reward(e1.id, db_session)

        e2 = await make_exam(child.id, score=75, full_score=100, exam_name="第二次")
        r = await exam_reward(e2.id, db_session)
        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "improvement_10" in codes

    async def test_improvement_less_than_10_no_trigger(self, db_session, make_child, make_exam):
        """进步 <10 不触发"""
        child = await make_child()
        e1 = await make_exam(child.id, score=70, full_score=100, exam_name="第一次")
        await exam_reward(e1.id, db_session)

        e2 = await make_exam(child.id, score=78, full_score=100, exam_name="第二次")
        r = await exam_reward(e2.id, db_session)
        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "improvement_10" not in codes

    async def test_streak_3(self, db_session, make_child, make_exam):
        """连续 3 次单科不下降 → 🔥 连胜王者"""
        child = await make_child()
        for i, sc in enumerate([80, 85, 90]):
            e = await make_exam(child.id, score=sc, full_score=100, exam_name=f"第{i+1}次")
            r = await exam_reward(e.id, db_session)

        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "streak_3" in codes

    async def test_subject_5_times(self, db_session, make_child, make_exam):
        """单科累计 5 次 → 📚 学科达人"""
        child = await make_child()
        for i in range(5):
            e = await make_exam(child.id, score=70, full_score=100, exam_name=f"第{i+1}次")
            r = await exam_reward(e.id, db_session)

        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "subject_5_times" in codes

    async def test_exam_10(self, db_session, make_child, make_exam):
        """累计 10 次考试 → 💪 坚持不懈"""
        child = await make_child()
        for i in range(10):
            e = await make_exam(child.id, score=70, full_score=100, exam_name=f"第{i+1}次")
            r = await exam_reward(e.id, db_session)

        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "exam_10" in codes

    async def test_no_achievement_for_low_score(self, db_session, make_child, make_exam):
        """低分考试（<60%）只触发 first_exam，不触发分数类成就"""
        child = await make_child()
        exam = await make_exam(child.id, score=30, full_score=100)
        r = await exam_reward(exam.id, db_session)

        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "first_exam" in codes
        assert "score_90" not in codes
        assert "perfect_score" not in codes
        # 积分应为 0
        assert r.points_earned == 0


# ==================== H-3：AchievementCreate.icon 白名单 ====================

class TestAchievementIconWhitelist:
    """防 AchIcon.vue 的 v-html 被恶意 SVG/HTML 注入（H-3 修复）。"""

    def _payload(self, icon: str) -> dict:
        return {
            "code": "xss_test",
            "name": "测试成就",
            "description": "测试",
            "icon": icon,
            "condition_type": "total_exams",
            "condition_value": 1,
        }

    @pytest.mark.parametrize("icon", [
        "🏆",                            # 单 emoji
        "🌟⭐✨🎯",                       # 多 emoji（4 个以内）
        "svg:gold-bucket",               # 自定义 SVG 命名空间
        "svg:my-icon-1",                 # 含数字
        "abc",                           # 短字符串
    ])
    def test_accepts_safe_icons(self, icon: str):
        """合法值应通过校验"""
        a = AchievementCreate(**self._payload(icon))
        assert a.icon == icon

    @pytest.mark.parametrize("icon", [
        "<img src=x onerror=alert(1)>",                      # 经典 XSS
        "<svg/onload=alert(1)>",                             # SVG onload
        "javascript:alert(1)",                               # javascript: URI
        "<script>alert(1)</script>",                         # script 标签
        "svg:<svg onload=alert(1)>",                         # svg: 命名空间被注入
        "A" * 40,                                            # 超长（>32）
    ])
    def test_rejects_dangerous_icons(self, icon: str):
        """危险/超长值应被 Pydantic 拒绝（422）"""
        with pytest.raises(ValidationError):
            AchievementCreate(**self._payload(icon))


# ==================== M-8：grant_achievement exam_id 防御 ====================

class TestGrantAchievementExamIdRequired:
    """可重复型成就必须传 exam_id，否则 AssertionError 提前失败（防双发）。"""

    async def test_repeatable_without_exam_id_asserts(self, db_session, make_child):
        """perfect_score 是可重复型，不传 exam_id 必须 AssertionError"""
        from routers.rewards import grant_achievement
        child = await make_child()
        ach = Achievement(
            code="perfect_score", name="完美", description="x",
            condition_type="score", condition_value=100, icon="💯",
        )
        db_session.add(ach)
        await db_session.flush()

        with pytest.raises(AssertionError):
            await grant_achievement(db_session, child.id, ach.id, exam_id=None)

    async def test_milestone_with_none_exam_id_works(self, db_session, make_child):
        """里程碑型（不在白名单里）允许 exam_id=None，去重按 child+ach"""
        from routers.rewards import grant_achievement
        child = await make_child()
        ach = Achievement(
            code="exam_10", name="十次", description="x",
            condition_type="total_exams", condition_value=10, icon="💪",
        )
        db_session.add(ach)
        await db_session.flush()

        ca, created = await grant_achievement(db_session, child.id, ach.id, exam_id=None)
        assert created is True
        assert ca.id is not None
        assert ca.exam_id is None


# ==================== 成就去重索引兜底（DB-2） ====================

class TestAchievementDedupGuard:
    """child_achievements 上的 IFNULL(exam_id,-1) 唯一索引兜底"""

    @pytest_asyncio.fixture
    async def make_achievement(self, db_session):
        async def _create(code, name="测试成就", condition_type="single_exam_score"):
            ach = Achievement(
                code=code, name=name, icon="🏆",
                condition_type=condition_type, condition_value=90,
            )
            db_session.add(ach)
            await db_session.flush()
            return ach
        return _create

    async def test_milestone_duplicate_null_exam_rejected(
        self, db_session, make_child, make_achievement
    ):
        """里程碑型（exam_id=NULL）同孩子同成就只允许一条"""
        from sqlalchemy.exc import IntegrityError
        child = await make_child()
        ach = await make_achievement("milestone_test")
        db_session.add(ChildAchievement(child_id=child.id, achievement_id=ach.id))
        await db_session.flush()
        db_session.add(ChildAchievement(child_id=child.id, achievement_id=ach.id))
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    async def test_repeatable_same_exam_rejected(
        self, db_session, make_child, make_achievement
    ):
        """可重复型：同孩子同成就同考试只允许一条"""
        from sqlalchemy.exc import IntegrityError
        child = await make_child()
        ach = await make_achievement("repeatable_test")
        db_session.add(ChildAchievement(
            child_id=child.id, achievement_id=ach.id, exam_id=101))
        await db_session.flush()
        db_session.add(ChildAchievement(
            child_id=child.id, achievement_id=ach.id, exam_id=101))
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    async def test_repeatable_different_exam_ok(
        self, db_session, make_child, make_achievement
    ):
        """可重复型：不同考试各一条是正常的"""
        child = await make_child()
        ach = await make_achievement("repeatable_test2")
        db_session.add(ChildAchievement(
            child_id=child.id, achievement_id=ach.id, exam_id=101))
        db_session.add(ChildAchievement(
            child_id=child.id, achievement_id=ach.id, exam_id=102))
        await db_session.flush()
        rows = (await db_session.execute(
            select(ChildAchievement).where(ChildAchievement.child_id == child.id)
        )).scalars().all()
        assert len(rows) == 2


# ==================== CQ-1：knowledge_50 按孩子统计知识点 ====================

class TestKnowledge50PerChild:
    """knowledge_50 应统计该孩子自己练习过的知识点（KPStudyProgress 去重），
    而非全库知识点总数（否则多孩家庭全员误解锁）。"""

    @pytest_asyncio.fixture
    async def make_kp_progress(self, db_session):
        """给指定孩子造 n 条知识点学习记录"""

        async def _create(child_id: int, n: int):
            for i in range(n):
                kp = KnowledgePoint(subject="数学", name=f"知识点{i}")
                db_session.add(kp)
                await db_session.flush()
                db_session.add(KPStudyProgress(
                    child_id=child_id, knowledge_point_id=kp.id,
                    total_attempts=1, total_correct=1,
                ))
            await db_session.flush()

        return _create

    async def test_other_childs_kps_dont_unlock(
        self, db_session, make_child, make_exam, make_kp_progress
    ):
        """大宝练了 55 个知识点；小宝考试后不应解锁 knowledge_50（修复前全库 55 个会误解锁）"""
        child_a = await make_child(name="大宝")
        child_b = await make_child(name="小宝")
        await make_kp_progress(child_a.id, 55)

        exam_b = await make_exam(child_b.id, score=90, full_score=100, exam_name="小宝考试")
        r = await exam_reward(exam_b.id, db_session)
        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "knowledge_50" not in codes

    async def test_own_50_kps_unlocks(
        self, db_session, make_child, make_exam, make_kp_progress
    ):
        """自己练满 50 个知识点 → 解锁 knowledge_50"""
        child = await make_child()
        await make_kp_progress(child.id, 50)

        exam = await make_exam(child.id, score=90, full_score=100)
        r = await exam_reward(exam.id, db_session)
        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "knowledge_50" in codes

    async def test_49_kps_no_unlock(
        self, db_session, make_child, make_exam, make_kp_progress
    ):
        """49 个知识点不触发（边界）"""
        child = await make_child()
        await make_kp_progress(child.id, 49)

        exam = await make_exam(child.id, score=90, full_score=100)
        r = await exam_reward(exam.id, db_session)
        codes = [a.achievement.code for a in r.new_achievements if a.achievement]
        assert "knowledge_50" not in codes


# ==================== CQ-2/CQ-11：段位统一重算 + 成就只报新授予 ====================

class TestExamRewardRankAndNewAchievements:
    """exam_reward 走统一段位重算入口；返回的 new_achievements 只含本次新授予的。"""

    async def test_first_exam_creates_rank(self, db_session, make_child, make_exam):
        """首场考试即创建段位（此前 exam_reward 只更新不创建，首考 new_rank 恒为 None）"""
        child = await make_child()
        exam = await make_exam(child.id, score=85, full_score=100)

        r = await exam_reward(exam.id, db_session)
        assert r.new_rank is not None
        assert r.new_rank.subject == "数学"
        assert r.new_rank.exam_count == 1
        assert r.new_rank.avg_score == 85.0
        assert r.new_rank.total_points == r.points_earned

    async def test_second_call_no_duplicate_achievements(
        self, db_session, make_child, make_exam
    ):
        """同一考试重复调用：new_achievements 不再包含已存在的记录（CQ-11）"""
        child = await make_child()
        exam = await make_exam(child.id, score=100, full_score=100)

        r1 = await exam_reward(exam.id, db_session)
        assert len(r1.new_achievements) > 0

        r2 = await exam_reward(exam.id, db_session)
        assert r2.new_achievements == []

    async def test_delete_exam_rank_total_points_from_remaining(
        self, db_session, make_child, make_exam
    ):
        """删考试后段位重算的 total_points 只统计剩余考试的积分（旧实现错误地统计全孩子所有正积分）"""
        from routers.exams import delete_exam

        child = await make_child()
        e1 = await make_exam(child.id, score=90, full_score=100, exam_name="第一次")
        e2 = await make_exam(child.id, score=90, full_score=100, exam_name="第二次")
        await exam_reward(e1.id, db_session)
        await exam_reward(e2.id, db_session)

        # 塞一条与考试无关的正积分（study_progress 来源），不应计入数学科目段位
        db_session.add(PointsLog(
            child_id=child.id, points=999, source="study_progress",
            description="教材学习成就：UNIT_MASTERED",
        ))
        await db_session.flush()

        await delete_exam(e1.id, db_session)

        from models import ChildRank as CR
        rank = (await db_session.execute(
            select(CR).where(CR.child_id == child.id, CR.subject == "数学")
        )).scalar_one_or_none()
        assert rank is not None
        assert rank.exam_count == 1
        # 只剩 e2 的积分：calc_exam_points(90,100) = 38（10+12+7.5+5*1.8）
        assert rank.total_points == 38
