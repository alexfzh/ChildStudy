"""Seed 奖励系统：段位初始化 + 奖励模板 + 成就定义"""
import asyncio

from sqlalchemy import select

from database import AsyncSessionLocal, init_db
from models import (
    RANK_TIERS,
    Achievement,
    Child,
    ChildRank,
    Exam,
    Reward,
)


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        # 确保有孩子
        child = (await db.execute(select(Child).limit(1))).scalar_one_or_none()
        if not child:
            print("no child found, skip reward seed")
            return

        # 段位（已有考试则重算）
        exams_result = await db.execute(
            select(Exam).where(Exam.child_id == child.id)
        )
        exams = exams_result.scalars().all()
        if exams:
            def calc_tier(avg):
                tier_name = "青铜"
                for threshold, name, _ in RANK_TIERS:
                    if avg >= threshold:
                        tier_name = name
                return tier_name, 0
            subject_scores: dict[str, list] = {}
            for e in exams:
                pct = (e.score / e.full_score * 100) if e.full_score else 0
                subject_scores.setdefault(e.subject, []).append(pct)
            for subject, scores in subject_scores.items():
                avg = round(sum(scores) / len(scores), 1)
                tier, stars = calc_tier(avg)
                rank = ChildRank(
                    child_id=child.id, subject=subject,
                    tier=tier, stars=stars, avg_score=avg,
                    exam_count=len(scores), total_points=0,
                )
                db.add(rank)
            print(f"initialized {len(subject_scores)} ranks")

        # 奖励模板
        rewards = [
            Reward(name="🍦 一次冰淇淋", reward_type="material", cost_points=50, icon="🍦"),
            Reward(name="🎮 30分钟游戏", reward_type="privilege", cost_points=100, icon="🎮"),
            Reward(name="🎬 选一部电影", reward_type="privilege", cost_points=200, icon="🎬"),
            Reward(name="🧸 一本书/玩具", reward_type="material", cost_points=300, icon="🧸"),
            Reward(name="✈️ 周末短途出游", reward_type="material", cost_points=500, icon="✈️"),
            Reward(name="⭐ 荣耀徽章", reward_type="spiritual", cost_points=0, icon="⭐"),
            Reward(name="🏅 家庭颁奖仪式", reward_type="spiritual", cost_points=0, icon="🏅"),
            Reward(name="📜 打印证书", reward_type="spiritual", cost_points=0, icon="📜"),
            Reward(name="🛏️ 晚睡1小时", reward_type="privilege", cost_points=80, icon="🛏️"),
            Reward(name="📱 多刷15分钟视频", reward_type="privilege", cost_points=60, icon="📱"),
            Reward(name="🍕 指定晚餐", reward_type="material", cost_points=100, icon="🍕"),
            Reward(name="🎵 家庭播放一首歌", reward_type="spiritual", cost_points=50, icon="🎵"),
        ]
        for r in rewards:
            db.add(r)
        print(f"seeded {len(rewards)} rewards")

        # 成就定义
        achievements = [
            # 单科类（每次考试可能同时获得多个）
            Achievement(code="first_exam", name="🎯 入门学徒", description="完成第一次考试", condition_type="first_exam", condition_value=1, icon="🎯"),
            Achievement(code="improvement_10", name="📈 进步之星", description="单科比上次进步10分以上", condition_type="improvement", condition_value=10, icon="📈"),
            Achievement(code="score_90", name="🥇 优秀学员", description="单科得分≥90", condition_type="score_above", condition_value=90, icon="🥇"),
            Achievement(code="score_95", name="🧠 卓越学者", description="单科得分≥95", condition_type="score_above", condition_value=95, icon="🧠"),
            Achievement(code="perfect_score", name="💎 满分传说", description="单科满分", condition_type="perfect_score", condition_value=1, icon="💎"),
            Achievement(code="streak_3", name="🔥 连胜王者", description="连续3次单科成绩不下降", condition_type="streak", condition_value=3, icon="🔥"),
            Achievement(code="subject_5_times", name="📚 学科达人", description="某科目累计5次考试", condition_type="exam_count", condition_value=5, icon="📚"),
            # 综合类（跨科目/累计）
            Achievement(code="exam_10", name="💪 坚持不懈", description="累计完成10次考试", condition_type="total_exams", condition_value=10, icon="💪"),
            Achievement(code="exam_20", name="🏅 小有成就", description="累计完成20次考试", condition_type="total_exams", condition_value=20, icon="🏅"),
            Achievement(code="exam_50", name="🎖️ 考者荣耀", description="累计完成50次考试", condition_type="total_exams", condition_value=50, icon="🎖️"),
            Achievement(code="exam_100", name="⛰️ 巅峰考者", description="累计完成100次考试", condition_type="total_exams", condition_value=100, icon="⛰️"),
            Achievement(code="knowledge_50", name="🧩 知识探索者", description="累计解锁50个知识点", condition_type="knowledge_count", condition_value=50, icon="🧩"),
            Achievement(code="rank_king", name="👑 终极王者", description="任意科目达到王者段位", condition_type="rank_tier", condition_value=95, icon="👑"),
            Achievement(code="all_above_80", name="🌟 全能选手", description="最近一次考试全部科目≥80分", condition_type="all_above", condition_value=80, icon="🌟"),
            Achievement(code="all_above_90", name="🌈 顶尖高手", description="最近一次考试全部科目≥90分", condition_type="all_above", condition_value=90, icon="🌈"),
            Achievement(code="pentagon_warrior", name="🌟 五边形战士", description="4 个月内 5 门不同科目达到 95% 以上", condition_type="subjects_95_4m", condition_value=5, icon="🌟"),
            # 积分里程碑（当前总积分首次达到阈值）
            Achievement(code="points_100", name="🪙 第一桶金", description="积分首次达到100分", condition_type="total_points", condition_value=100, icon="svg:gold-bucket"),
            Achievement(code="points_200", name="🐷 小财迷", description="积分首次达到200分", condition_type="total_points", condition_value=200, icon="🐷"),
            Achievement(code="points_500", name="🏦 积分大户", description="积分首次达到500分", condition_type="total_points", condition_value=500, icon="🏦"),
            Achievement(code="points_700", name="💰 富甲一方", description="积分首次达到700分", condition_type="total_points", condition_value=700, icon="💰"),
            Achievement(code="points_1000", name="🤑 腰缠万贯", description="积分首次达到1000分", condition_type="total_points", condition_value=1000, icon="🤑"),
        ]
        for a in achievements:
            db.add(a)
        print(f"seeded {len(achievements)} achievements")

        await db.commit()
        print("done")


if __name__ == "__main__":
    asyncio.run(main())
