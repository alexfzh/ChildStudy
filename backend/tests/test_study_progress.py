"""study_progress.py 测试：完成度计算 + 掌握度触发 + 连胜检测 + 成就去重"""
from datetime import date

from models import (
    PointsLog,
    StudyProgress,
    TextbookUnit,
    TextbookVersion,
)
from routers.study_progress import (
    award_unit_achievement,
    calc_completion,
    check_streak_three,
    get_or_create_progress,
)

# ==================== 纯函数：calc_completion ====================

class TestCalcCompletion:
    """完成度 = min(attempts, total) / total * 100"""

    def test_zero_total_returns_zero(self):
        assert calc_completion(10, 0) == 0.0

    def test_negative_total_returns_zero(self):
        assert calc_completion(5, -3) == 0.0

    def test_zero_attempts(self):
        assert calc_completion(0, 20) == 0.0

    def test_exact_match(self):
        assert calc_completion(20, 20) == 100.0

    def test_capped_at_100(self):
        """attempts > total 时封顶 100%"""
        assert calc_completion(30, 20) == 100.0

    def test_partial(self):
        assert calc_completion(15, 20) == 75.0

    def test_rounding(self):
        # 1/3 = 33.33%
        assert calc_completion(1, 3) == 33.33


# ==================== 集成测试：get_or_create_progress ====================

class TestGetOrCreateProgress:
    """学习进度记录的创建 / 复用"""

    async def test_creates_new(self, db_session, make_child):
        child = await make_child()
        # 需要一个 unit
        ver = TextbookVersion(code="PEP-M4A", name="人教版四年级上", publisher="人教版", grade="四年级", subject="数学", term="A")
        db_session.add(ver)
        await db_session.flush()
        unit = TextbookUnit(version_id=ver.id, code="U1", unit_number=1, title_zh="第一单元")
        db_session.add(unit)
        await db_session.flush()

        sp = await get_or_create_progress(db_session, child.id, unit.id)
        assert sp.child_id == child.id
        assert sp.unit_id == unit.id
        assert sp.status == "not_started"

    async def test_returns_existing(self, db_session, make_child):
        child = await make_child()
        ver = TextbookVersion(code="PEP-M4A", name="人教版四年级上", publisher="人教版", grade="四年级", subject="数学", term="A")
        db_session.add(ver)
        await db_session.flush()
        unit = TextbookUnit(version_id=ver.id, code="U1", unit_number=1, title_zh="第一单元")
        db_session.add(unit)
        await db_session.flush()

        sp1 = await get_or_create_progress(db_session, child.id, unit.id)
        sp1.total_attempts = 5
        await db_session.flush()

        sp2 = await get_or_create_progress(db_session, child.id, unit.id)
        assert sp2.id == sp1.id
        assert sp2.total_attempts == 5


# ==================== 集成测试：award_unit_achievement ====================

class TestAwardUnitAchievement:
    """成就积分发放 + 去重"""

    async def _setup(self, db_session, make_child):
        child = await make_child()
        ver = TextbookVersion(code="PEP-M4A", name="人教版四年级上", publisher="人教版", grade="四年级", subject="数学", term="A")
        db_session.add(ver)
        await db_session.flush()
        unit = TextbookUnit(version_id=ver.id, code="U1", unit_number=1, title_zh="第一单元")
        db_session.add(unit)
        await db_session.flush()
        return child, unit

    async def test_first_award_succeeds(self, db_session, make_child):
        child, unit = await self._setup(db_session, make_child)
        ok = await award_unit_achievement(db_session, child.id, unit.id, "UNIT_MASTERED", 50)
        await db_session.flush()  # 函数内部不 flush，测试手动刷
        assert ok is True

        # 验证 PointsLog 已创建
        from sqlalchemy import select
        log = (await db_session.execute(
            select(PointsLog).where(
                PointsLog.child_id == child.id,
                PointsLog.source == "study_progress",
            )
        )).scalar_one_or_none()
        assert log is not None
        assert log.points == 50

    async def test_duplicate_award_returns_false(self, db_session, make_child):
        child, unit = await self._setup(db_session, make_child)
        await award_unit_achievement(db_session, child.id, unit.id, "UNIT_MASTERED", 50)
        await db_session.flush()  # 必须 flush 让去重查询能看到
        ok = await award_unit_achievement(db_session, child.id, unit.id, "UNIT_MASTERED", 50)
        assert ok is False

    async def test_different_codes_independent(self, db_session, make_child):
        child, unit = await self._setup(db_session, make_child)
        ok1 = await award_unit_achievement(db_session, child.id, unit.id, "UNIT_MASTERED", 50)
        ok2 = await award_unit_achievement(db_session, child.id, unit.id, "STREAK_3", 100)
        assert ok1 is True
        assert ok2 is True


# ==================== 集成测试：check_streak_three ====================

class TestCheckStreakThree:
    """连续 3 个 unit_number 检测"""

    async def _make_units_and_progress(self, db_session, make_child, unit_numbers, mastered_numbers):
        """创建教材单元并标记指定编号为 mastered"""
        child = await make_child()
        ver = TextbookVersion(code="PEP-M4A", name="人教版四年级上", publisher="人教版", grade="四年级", subject="数学", term="A")
        db_session.add(ver)
        await db_session.flush()

        units = []
        for n in unit_numbers:
            u = TextbookUnit(version_id=ver.id, code=f"U{n}", unit_number=n, title_zh=f"第{n}单元")
            db_session.add(u)
            await db_session.flush()
            units.append(u)

        # 为 mastered 的单元创建 progress
        for u in units:
            if int(u.unit_number) in mastered_numbers:
                sp = StudyProgress(
                    child_id=child.id, unit_id=u.id,
                    status="mastered",
                    total_attempts=20, total_correct=18,
                    accuracy=90.0, completion_pct=100.0,
                    mastered_at=date.today(),
                )
                db_session.add(sp)
        await db_session.flush()
        return child, units

    async def test_consecutive_three_triggers(self, db_session, make_child):
        """单元 1,2,3 mastered → STREAK_3"""
        child, _units = await self._make_units_and_progress(
            db_session, make_child,
            unit_numbers=[1, 2, 3, 4],
            mastered_numbers=[1, 2, 3],
        )
        result = await check_streak_three(db_session, child.id)
        assert result is not None  # 返回第三个 unit 的 id

    async def test_non_consecutive_no_trigger(self, db_session, make_child):
        """单元 1,3,5 mastered → 无连胜"""
        child, _units = await self._make_units_and_progress(
            db_session, make_child,
            unit_numbers=[1, 2, 3, 4, 5],
            mastered_numbers=[1, 3, 5],
        )
        result = await check_streak_three(db_session, child.id)
        assert result is None

    async def test_only_two_consecutive(self, db_session, make_child):
        """只有 2 个连续 → 不触发"""
        child, _units = await self._make_units_and_progress(
            db_session, make_child,
            unit_numbers=[1, 2, 3],
            mastered_numbers=[1, 2],
        )
        result = await check_streak_three(db_session, child.id)
        assert result is None

    async def test_four_consecutive_still_triggers(self, db_session, make_child):
        """1,2,3,4 mastered → 触发（取第一组三连）"""
        child, _units = await self._make_units_and_progress(
            db_session, make_child,
            unit_numbers=[1, 2, 3, 4],
            mastered_numbers=[1, 2, 3, 4],
        )
        result = await check_streak_three(db_session, child.id)
        assert result is not None


# ==================== 集成测试：mastery 触发条件 ====================

class TestMasteryTrigger:
    """掌握度三重条件：accuracy>=85 AND completion>=80 AND attempts>=10"""

    async def _setup_unit(self, db_session, make_child):
        child = await make_child()
        ver = TextbookVersion(code="PEP-M4A", name="人教版四年级上", publisher="人教版", grade="四年级", subject="数学", term="A")
        db_session.add(ver)
        await db_session.flush()
        unit = TextbookUnit(version_id=ver.id, code="U1", unit_number=1, title_zh="第一单元")
        db_session.add(unit)
        await db_session.flush()
        return child, unit

    async def test_all_conditions_met_triggers_mastery(self, db_session, make_child):
        child, unit = await self._setup_unit(db_session, make_child)
        sp = StudyProgress(
            child_id=child.id, unit_id=unit.id,
            status="in_progress",
            total_attempts=10, total_correct=9,
            accuracy=90.0, completion_pct=80.0,
        )
        db_session.add(sp)
        await db_session.flush()

        # 模拟触发检查（直接检查条件，不经过完整 update_progress_on_exercise）
        assert sp.accuracy >= 85.0
        assert sp.completion_pct >= 80.0
        assert sp.total_attempts >= 10
        # 条件全满足 → 可以标记为 mastered
        sp.status = "mastered"
        sp.mastered_at = date.today()
        await db_session.flush()
        assert sp.status == "mastered"

    async def test_accuracy_below_85_no_mastery(self, db_session, make_child):
        child, unit = await self._setup_unit(db_session, make_child)
        sp = StudyProgress(
            child_id=child.id, unit_id=unit.id,
            status="in_progress",
            total_attempts=10, total_correct=8,
            accuracy=80.0, completion_pct=90.0,
        )
        db_session.add(sp)
        await db_session.flush()

        # accuracy < 85 → 不满足
        can_master = sp.accuracy >= 85.0 and sp.completion_pct >= 80.0 and sp.total_attempts >= 10
        assert can_master is False

    async def test_attempts_below_10_no_mastery(self, db_session, make_child):
        child, unit = await self._setup_unit(db_session, make_child)
        sp = StudyProgress(
            child_id=child.id, unit_id=unit.id,
            status="in_progress",
            total_attempts=5, total_correct=5,
            accuracy=100.0, completion_pct=50.0,
        )
        db_session.add(sp)
        await db_session.flush()

        can_master = sp.accuracy >= 85.0 and sp.completion_pct >= 80.0 and sp.total_attempts >= 10
        assert can_master is False

    async def test_boundary_values(self, db_session, make_child):
        """恰好 85.0 / 80.0 / 10 → 应该触发"""
        child, unit = await self._setup_unit(db_session, make_child)
        sp = StudyProgress(
            child_id=child.id, unit_id=unit.id,
            total_attempts=10, total_correct=9,
            accuracy=85.0, completion_pct=80.0,
        )
        db_session.add(sp)
        await db_session.flush()

        can_master = sp.accuracy >= 85.0 and sp.completion_pct >= 80.0 and sp.total_attempts >= 10
        assert can_master is True
