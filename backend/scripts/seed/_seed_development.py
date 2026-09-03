"""Seed 生长发育/社交情感/兴趣特长 demo 数据"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal

from database import AsyncSessionLocal, init_db
from models import GrowthRecord, InterestRecord, SocialEmotionalRecord


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        # 生长发育：大宝 (id=1)，6 条记录，3个月
        growth_rows = []
        base = date.today() - timedelta(days=90)
        height = Decimal("135.0")
        weight = Decimal("32.0")
        for i in range(6):
            d = base + timedelta(days=15 * i)
            height += Decimal("0.5")  # 每月长 0.5cm
            weight += Decimal("0.3")  # 每月重 0.3kg
            bmi = round(float(weight) / ((float(height) / 100) ** 2), 1)
            growth_rows.append(GrowthRecord(
                child_id=1,
                record_date=d,
                height_cm=float(height),
                weight_kg=float(weight),
                bmi=bmi,
                vision_left=5.0 - i * 0.1 if i < 3 else None,
                vision_right=5.0 - i * 0.1 if i < 3 else None,
                note="季度体检" if i % 3 == 0 else "",
            ))
        db.add_all(growth_rows)

        # 社交情感：大宝，8 条记录
        social_rows = []
        mood_cycle = [4, 5, 3, 4, 5, 4, 3, 5]
        emotions_cycle = [
            ["happy", "excited"],
            ["happy", "proud"],
            ["calm"],
            ["happy", "calm"],
            ["happy", "proud"],
            ["happy"],
            ["anxious", "calm"],
            ["happy", "proud"],
        ]
        social_activities = [
            "和同学打球",
            "班级演讲比赛",
            "",
            "周末家庭活动",
            "数学竞赛获奖",
            "",
            "期中考试前",
            "获得三好学生",
        ]
        for i in range(8):
            d = base + timedelta(days=10 * i)
            social_rows.append(SocialEmotionalRecord(
                child_id=1,
                record_date=d,
                mood_score=mood_cycle[i],
                emotion_tags=emotions_cycle[i],
                social_activity=social_activities[i],
                confidence_level=min(5, 3 + i // 3),
                note="",
            ))
        db.add_all(social_rows)

        # 兴趣特长：大宝，10 条记录
        interest_rows = []
        activities = [
            ("运动", "足球", 90, "intermediate"),
            ("运动", "游泳", 60, "beginner"),
            ("音乐", "钢琴", 45, "intermediate"),
            ("阅读", "科幻小说", 30, "advanced"),
            ("运动", "足球", 90, "intermediate"),
            ("美术", "素描", 60, "beginner"),
            ("音乐", "钢琴", 45, "intermediate"),
            ("编程", "Scratch", 60, "beginner"),
            ("运动", "游泳", 60, "intermediate"),
            ("阅读", "历史故事", 40, "intermediate"),
        ]
        for i, (atype, name, dur, skill) in enumerate(activities):
            d = base + timedelta(days=7 * i)
            interest_rows.append(InterestRecord(
                child_id=1,
                record_date=d,
                activity_type=atype,
                activity_name=name,
                duration_minutes=dur,
                skill_level=skill,
                note="",
            ))
        db.add_all(interest_rows)

        await db.commit()
        print(f"growth: {len(growth_rows)}, social: {len(social_rows)}, interests: {len(interest_rows)}")


if __name__ == "__main__":
    asyncio.run(main())
