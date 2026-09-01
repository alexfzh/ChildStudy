"""wrong_questions.py 测试：艾宾浩斯复习调度 + 掌握度状态机"""
from datetime import date, timedelta

from models import WrongQuestion
from routers.wrong_questions import (
    REVIEW_INTERVALS,
    _next_interval,
    _recalc_next_review,
)

# ==================== 纯函数：_next_interval ====================

class TestNextInterval:
    """艾宾浩斯间隔查表"""

    def test_first_review(self):
        assert _next_interval(0) == 1

    def test_second_review(self):
        assert _next_interval(1) == 3

    def test_third_review(self):
        assert _next_interval(2) == 7

    def test_fourth_review(self):
        assert _next_interval(3) == 15

    def test_fifth_and_beyond(self):
        assert _next_interval(4) == 30
        assert _next_interval(100) == 30  # 超出上限也 clamp

    def test_negative_index_wraps(self):
        # _next_interval 用 min() 只限上界，负数走 Python 负索引
        assert _next_interval(-1) == REVIEW_INTERVALS[-1]  # 30


# ==================== 纯函数：_recalc_next_review ====================

class TestRecalcNextReview:
    """复习结果状态机"""

    def _make_wq(self, review_count=0, wrong_count=0, mastery_level="new", status="active"):
        """构造一个轻量 WrongQuestion mock（不需要 DB）"""
        class MockWQ:
            pass
        wq = MockWQ()
        wq.review_count = review_count
        wq.wrong_count = wrong_count
        wq.mastery_level = mastery_level
        wq.status = status
        return wq

    # --- correct 分支 ---

    def test_correct_decreases_wrong_count_and_schedules(self):
        wq = self._make_wq(review_count=1, wrong_count=2)
        result = _recalc_next_review(wq, "correct")
        assert wq.wrong_count == 1  # 减 1
        assert wq.review_count == 1  # _recalc 不改 review_count（调用方负责 +1）
        assert result == date.today() + timedelta(days=3)  # _next_interval(1) = 3

    def test_correct_at_mastery_threshold(self):
        """review_count >= 3 + correct → mastered，返回 None"""
        wq = self._make_wq(review_count=3, wrong_count=0)
        result = _recalc_next_review(wq, "correct")
        assert result is None
        assert wq.mastery_level == "mastered"
        assert wq.status == "mastered"

    def test_correct_beyond_mastery(self):
        wq = self._make_wq(review_count=5, wrong_count=0)
        result = _recalc_next_review(wq, "correct")
        assert result is None
        assert wq.mastery_level == "mastered"

    # --- wrong 分支 ---

    def test_wrong_resets_review_count(self):
        wq = self._make_wq(review_count=3, wrong_count=1, mastery_level="learning")
        result = _recalc_next_review(wq, "wrong")
        assert wq.review_count == 0
        assert wq.wrong_count == 2
        assert wq.mastery_level == "learning"
        assert wq.status == "active"
        assert result == date.today() + timedelta(days=1)

    def test_wrong_demotes_mastered_to_new(self):
        wq = self._make_wq(review_count=4, wrong_count=0, mastery_level="mastered", status="mastered")
        _recalc_next_review(wq, "wrong")
        assert wq.mastery_level == "new"
        assert wq.status == "active"
        assert wq.review_count == 0

    def test_wrong_demotes_learning_stays_learning(self):
        wq = self._make_wq(review_count=2, wrong_count=1, mastery_level="learning")
        _recalc_next_review(wq, "wrong")
        assert wq.mastery_level == "learning"

    # --- partial 分支 ---

    def test_partial_no_counter_change(self):
        wq = self._make_wq(review_count=2, wrong_count=3)
        result = _recalc_next_review(wq, "partial")
        assert wq.wrong_count == 3  # 不变
        assert wq.review_count == 2  # 不变
        assert result == date.today() + timedelta(days=7)  # _next_interval(2) = 7

    def test_partial_does_not_master(self):
        wq = self._make_wq(review_count=5, wrong_count=0)
        result = _recalc_next_review(wq, "partial")
        assert wq.mastery_level != "mastered"
        assert result is not None


# ==================== 集成测试：复习 endpoint 逻辑 ====================

class TestReviewIntegration:
    """通过 DB 验证复习流程"""

    async def test_create_wrong_question_sets_next_review(self, db_session, make_child):
        child = await make_child()
        wq = WrongQuestion(
            child_id=child.id,
            question_text="1+1=?",
            subject="数学",
            correct_answer="2",
            next_review_date=date.today() + timedelta(days=1),
        )
        db_session.add(wq)
        await db_session.flush()

        assert wq.status == "active"
        assert wq.review_count == 0
        assert wq.mastery_level == "new"

    async def test_full_mastery_path(self, db_session, make_child):
        """模拟：创建错题 → 连续 4 次 correct → mastered"""
        child = await make_child()
        wq = WrongQuestion(
            child_id=child.id,
            question_text="测试题",
            subject="数学",
            correct_answer="答案",
            next_review_date=date.today(),
        )
        db_session.add(wq)
        await db_session.flush()

        # 4 次 correct：review_count 0→1→2→3→4，第 3 次后 mastered
        for i in range(4):
            wq.review_count += 1
            result = _recalc_next_review(wq, "correct")
            if i < 2:
                assert result is not None  # 还没 mastered
                assert wq.status == "active"
            else:
                assert result is None  # mastered
                assert wq.mastery_level == "mastered"
                assert wq.status == "mastered"

    async def test_wrong_after_near_mastery_resets(self, db_session, make_child):
        """review_count=2 时答错 → 归零"""
        child = await make_child()
        wq = WrongQuestion(
            child_id=child.id,
            question_text="难题",
            subject="数学",
            correct_answer="答案",
            next_review_date=date.today(),
            review_count=2,
        )
        db_session.add(wq)
        await db_session.flush()

        wq.review_count += 1  # 模拟 review endpoint 的 +1
        result = _recalc_next_review(wq, "wrong")
        assert wq.review_count == 0
        assert result == date.today() + timedelta(days=1)
