"""Seed KnowledgePoint 官方标签库（英语四年级）+ Question ↔ KP 关联

  运行：python -m backend._seed_knowledge_points
  前置：先跑过 _seed_textbook_grade4a.py（确保 TextbookVersion/Unit 就绪）
"""
import asyncio

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import (
    KnowledgePoint,
    KnowledgePointUnit,
    Question,
    QuestionBank,
    QuestionKnowledgePoint,
    TextbookUnit,
    TextbookVersion,
)

# ============ 英语四年级 KP 定义 ============
# subject / name / category / grade_level
ENGLISH_KPS = [
    # ---- U2 My classmates ----
    ("英语", "形容词：描述人物性格", "词汇", "四年级",
     ["lovely", "different", "great", "polite", "interesting", "helpful"]),
    ("英语", "... help ... (do) ... 句型", "语法", "四年级", []),
    ("英语", "can / can't 表达能力", "语法", "四年级", []),

    # ---- U1 My school ----
    ("英语", "学校场所词汇", "词汇", "四年级",
     ["classroom", "sports field", "hall", "library", "computer room", "art room", "school building"]),
    ("英语", "have no = don't have any", "语法", "四年级", []),
    ("英语", "方位介词：in / on / near", "语法", "四年级", []),

    # ---- U3 Animals and their homes ----
    ("英语", "动物词汇", "词汇", "四年级",
     ["panda", "monkey", "elephant", "baby elephant", "polar bear", "hometown"]),
    ("英语", "... (doing) ... 进行时态", "语法", "四年级", []),
    ("英语", "动物栖息地表达", "词汇", "四年级", []),

    # ---- U4 Our birthday ----
    ("英语", "家庭成员称呼", "词汇", "四年级",
     ["mother", "father", "brother", "sister", "family"]),
    ("英语", "生日/派对词汇", "词汇", "四年级",
     ["invitation", "party", "activity", "share", "cake", "letter", "noodles", "egg"]),
    ("英语", "It's a tradition to (do) ...", "语法", "四年级", []),

    # ---- U5 Visiting places ----
    ("英语", "地点场所词汇", "词汇", "四年级",
     ["neighbourhood", "park", "bakery", "museum", "cinema", "supermarket", "bridge", "shop", "waterway"]),
    ("英语", "Is/Are there ...? there be 句型", "语法", "四年级", []),
    ("英语", "地点描述：next to / between / behind", "语法", "四年级", []),

    # ---- U6 It's autumn! ----
    ("英语", "季节/秋天词汇", "词汇", "四年级",
     ["autumn", "farm", "fall", "leaf", "fruit", "fly south", "apple"]),
    ("英语", "How ...! 感叹句", "语法", "四年级", []),
    ("英语", "自然拼读：字母 y 发音 /j/", "自然拼读", "四年级", []),

    # ---- U7 My healthy breakfast ----
    ("英语", "食物/早餐词汇", "词汇", "四年级",
     ["breakfast", "bread", "porridge", "juice", "milk", "banana"]),
    ("英语", "How often ...? 频率提问", "语法", "四年级", []),
    ("英语", "自然拼读：字母组合 sh /ʃ/", "自然拼读", "四年级", []),

    # ---- U8 Be honest ----
    ("英语", "品质/美德词汇", "词汇", "四年级",
     ["honest", "honesty", "tell the truth", "never tell a lie", "keep one's word", "give ... back", "trust each other"]),
    ("英语", "... should ... 义务表达", "语法", "四年级", []),

    # ---- U9 What time is it? ----
    ("英语", "时间表达词汇", "词汇", "四年级",
     ["time", "hour hand", "minute hand", "seven o'clock", "half past eleven", "ten to four"]),
    ("英语", "What time is it? It's ... 句型", "语法", "四年级", []),

    # ---- U10 Weather ----
    ("英语", "天气词汇", "词汇", "四年级",
     ["sunny", "rainy", "cloudy", "windy", "snowy", "weather", "weather report", "degree"]),
    ("英语", "How's the weather ...? 句型", "语法", "四年级", []),
    ("英语", "形容词比较级：-er / more", "语法", "四年级", []),

    # ---- Starter 准备单元 ----
    ("英语", "问候与自我介绍", "功能", "四年级",
     ["hello", "hi", "goodbye", "I'm ...", "What's your name?"]),
    ("英语", "数字 1-100", "词汇", "四年级", []),
    ("英语", "星期表达", "词汇", "四年级", []),
]

# ============ KP ↔ Unit 关联 ============
# 用 code 匹配（创建完 KP 后拿 id，此处是 name → unit_code 的映射）
# group: (kp_name, unit_code, relevance)
KP_UNIT_LINKS = [
    # U2
    ("形容词：描述人物性格", "U2", "primary"),
    ("... help ... (do) ... 句型", "U2", "primary"),
    ("can / can't 表达能力", "U2", "secondary"),
    # U1
    ("学校场所词汇", "U1", "primary"),
    ("have no = don't have any", "U1", "primary"),
    ("方位介词：in / on / near", "U1", "secondary"),
    # U3
    ("动物词汇", "U3", "primary"),
    ("... (doing) ... 进行时态", "U3", "primary"),
    ("动物栖息地表达", "U3", "secondary"),
    # U4
    ("家庭成员称呼", "U4", "primary"),
    ("生日/派对词汇", "U4", "primary"),
    ("It's a tradition to (do) ...", "U4", "primary"),
    # U5
    ("地点场所词汇", "U5", "primary"),
    ("Is/Are there ...? there be 句型", "U5", "primary"),
    ("地点描述：next to / between / behind", "U5", "secondary"),
    # U6
    ("季节/秋天词汇", "U6", "primary"),
    ("How ...! 感叹句", "U6", "primary"),
    ("自然拼读：字母 y 发音 /j/", "U6", "primary"),
    # U7
    ("食物/早餐词汇", "U7", "primary"),
    ("How often ...? 频率提问", "U7", "primary"),
    ("自然拼读：字母组合 sh /ʃ/", "U7", "primary"),
    # U8
    ("品质/美德词汇", "U8", "primary"),
    ("... should ... 义务表达", "U8", "primary"),
    # U9
    ("时间表达词汇", "U9", "primary"),
    ("What time is it? It's ... 句型", "U9", "primary"),
    # U10
    ("天气词汇", "U10", "primary"),
    ("How's the weather ...? 句型", "U10", "primary"),
    ("形容词比较级：-er / more", "U10", "primary"),
    # Starter
    ("问候与自我介绍", "Starter", "primary"),
    ("数字 1-100", "Starter", "primary"),
    ("星期表达", "Starter", "primary"),
    # cross-unit
    ("can / can't 表达能力", "U1", "cross"),
    ("地点场所词汇", "U1", "cross"),
    ("天气词汇", "U5", "cross"),
]

# ============ Question ↔ KP 关联 ============
# 用旧 knowledge_point 标签（"4A M1"等）匹配，映射到新 KP id
OLD_KP_TO_NEW_KP = {
    "4A M1": ["形容词：描述人物性格", "can / can't 表达能力"],
    "4A M2": ["家庭成员称呼", "生日/派对词汇"],
    "4A M3": ["学校场所词汇", "地点场所词汇", "方位介词：in / on / near"],
    "4A M4": ["天气词汇", "形容词比较级：-er / more"],
}


async def seed():
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # 1) 确保有版本 + Unit
        version = (await db.execute(
            select(TextbookVersion).where(TextbookVersion.code == "SH-5-4-2025A")
        )).scalars().first()
        if not version:
            print("[WARN] 找不到 TextbookVersion SH-5-4-2025A，先跑 _seed_textbook_grade4a.py")
            return

        units = (await db.execute(
            select(TextbookUnit).where(TextbookUnit.version_id == version.id)
        )).scalars().all()
        code_to_unit = {u.code: u for u in units}
        print(f"找到 {len(units)} 个 Units")

        # 2) 创建/更新 KP 记录（按 subject+name 去重）
        existing_kps = (await db.execute(
            select(KnowledgePoint).where(KnowledgePoint.subject == "英语")
        )).scalars().all()
        existing_names = {kp.name for kp in existing_kps}

        kp_map = {}  # name -> KnowledgePoint obj
        for subj, name, cat, grade, topic_words in ENGLISH_KPS:
            if name in existing_names:
                kp = next(k for k in existing_kps if k.name == name)
                kp.category = cat
                kp.grade_level = grade
                print(f"  更新 KP: {name}")
            else:
                kp = KnowledgePoint(
                    subject=subj, name=name, category=cat, grade_level=grade,
                    description=", ".join(topic_words) if topic_words else None,
                )
                db.add(kp)
                print(f"  创建 KP: {name}")
            kp_map[name] = kp

        await db.commit()
        # 刷新获取 id
        for kp in kp_map.values():
            await db.refresh(kp)
        print(f"KP 总数: {len(kp_map)}")

        # 3) KP ↔ Unit 关联
        for kp_name, unit_code, relevance in KP_UNIT_LINKS:
            kp = kp_map.get(kp_name)
            unit = code_to_unit.get(unit_code)
            if not kp or not unit:
                continue
            kp_id = kp.id
            unit_id = unit.id
            existing = (await db.execute(
                select(KnowledgePointUnit).where(
                    KnowledgePointUnit.knowledge_point_id == kp_id,
                    KnowledgePointUnit.unit_id == unit_id,
                )
            )).scalars().first()
            if not existing:
                db.add(KnowledgePointUnit(
                    knowledge_point_id=kp_id, unit_id=unit_id, relevance=relevance,
                ))
        await db.commit()
        print("KP ↔ Unit 关联完成")

        # 4) Question ↔ KP 关联（通过旧标签映射）
        target_bank = (await db.execute(
            select(QuestionBank).where(
                and_(QuestionBank.grade == "四年级", QuestionBank.subject == "英语",
                     QuestionBank.title.like("%沪教%"))
            )
        )).scalars().first()
        if not target_bank:
            print("[WARN] 找不到目标题库，跳过 Question-KP 关联")
            return

        questions = (await db.execute(
            select(Question).where(Question.bank_id == target_bank.id)
        )).scalars().all()

        linked = 0
        for q in questions:
            old_kp_tag = q.knowledge_point  # "4A M1"
            new_kp_names = OLD_KP_TO_NEW_KP.get(old_kp_tag, [])
            if not new_kp_names:
                continue
            for kp_name in new_kp_names:
                kp = kp_map.get(kp_name)
                if not kp:
                    continue
                existing = (await db.execute(
                    select(QuestionKnowledgePoint).where(
                        QuestionKnowledgePoint.question_id == q.id,
                        QuestionKnowledgePoint.knowledge_point_id == kp.id,
                    )
                )).scalars().first()
                if not existing:
                    db.add(QuestionKnowledgePoint(
                        question_id=q.id,
                        knowledge_point_id=kp.id,
                        is_primary=(kp_name == new_kp_names[0]),
                    ))
                    linked += 1
        await db.commit()
        print(f"Question ↔ KP 关联: {linked} 条")

        # 5) 打印汇总
        total_qkp = (await db.execute(select(func.count(QuestionKnowledgePoint.id)))).scalar_one()
        total_kpu = (await db.execute(select(func.count(KnowledgePointUnit.id)))).scalar_one()
        print("\n=== 完成 ===")
        print(f"  KP 记录: {len(kp_map)} 条")
        print(f"  KP ↔ Unit 关联: {total_kpu} 条")
        print(f"  Question ↔ KP 关联: {total_qkp} 条")


if __name__ == "__main__":
    from sqlalchemy import func
    asyncio.run(seed())
