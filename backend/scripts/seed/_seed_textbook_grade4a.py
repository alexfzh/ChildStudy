"""Seed 教材版本 + 教材单元（沪教版 5·4 学制四年级上册），并把现有题库的题目映射到教材 Unit。"""
import asyncio

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import (
    Question,
    QuestionBank,
    QuestionUnit,
    TextbookUnit,
    TextbookVersion,
)

# 教材版本数据
VERSION = dict(
    code="SH-5-4-2025A",
    name="沪教版（5·4 学制）2025 秋四年级上册",
    publisher="上海教育出版社",
    grade="四年级",
    subject="英语",
    term="A",
    is_active=True,
    description="配套本地 PDF：C:\\Users\\feizhonghua\\.openclaw\\workspace-musk\\projects\\ChildStudy\\docs\\上海新版四上英语教材.pdf",
)

# Unit 数据（按 PDF 实际页码顺序）
UNITS = [
    dict(code="Starter", unit_number=0,
         title_en="Starter", title_zh="准备单元",
         topic_words=["Shenshen", "Minmin", "Xiaopu", "Xiaojiang", "James", "Yaoyao"],
         sound=None, sound_examples=[],
         structure="基础问候与介绍",
         big_task="认识本册人物 + 20-100 数词 + 星期",
         project_type=None, page_start=2, page_end=6, is_project=False),
    dict(code="U1", unit_number=1,
         title_en="My school", title_zh="我的学校",
         topic_words=["classroom", "sports field", "hall", "library", "computer room", "art room", "school building"],
         sound="w", sound_examples=["wall", "water", "window", "Wednesday"],
         structure="have no = don't have any",
         big_task="Presenting my favourite place in the school",
         project_type="presentation", page_start=7, page_end=14, is_project=True),
    dict(code="U2", unit_number=2,
         title_en="My classmates", title_zh="我的同学们",
         topic_words=["lovely", "different", "great", "polite", "interesting", "helpful"],
         sound="x", sound_examples=["excited", "exam", "expensive", "fox"],
         structure="... help ... (do) ...",
         big_task="Playing a guessing game",
         project_type="guessing game", page_start=15, page_end=22, is_project=True),
    dict(code="U3", unit_number=3,
         title_en="Animals and their homes", title_zh="动物和它们的家",
         topic_words=["panda", "hometown", "monkey", "elephant", "family", "baby elephant", "polar bear"],
         sound=None, sound_examples=[],
         structure="... (doing) ...",
         big_task="Making an animal profile",
         project_type="profile", page_start=23, page_end=30, is_project=True),
    dict(code="U4", unit_number=4,
         title_en="Our birthday", title_zh="我们的生日",
         topic_words=["invitation", "party", "activity", "share", "cake", "letter", "noodles", "egg"],
         sound=None, sound_examples=[],
         structure="It's a tradition to (do) ...",
         big_task="Making a plan for our group birthday",
         project_type="plan", page_start=31, page_end=38, is_project=True),
    dict(code="U5", unit_number=5,
         title_en="Visiting places", title_zh="参观景点",
         topic_words=["neighbourhood", "park", "bakery", "museum", "cinema", "supermarket", "bridge", "shop", "waterway"],
         sound=None, sound_examples=[],
         structure="Is/Are there ...? Yes, there is/are. No, there isn't/aren't.",
         big_task="Presenting a photo of my favourite place",
         project_type="photo", page_start=39, page_end=46, is_project=True),
    dict(code="U6", unit_number=6,
         title_en="It's autumn!", title_zh="秋天来了",
         topic_words=["autumn", "farm", "fall", "leaf", "fruit", "fly south", "apple"],
         sound="y", sound_examples=["year", "yellow", "yes", "young"],
         structure="How ...!",
         big_task="Writing a poem for autumn",
         project_type="poem", page_start=47, page_end=54, is_project=True),
    dict(code="U7", unit_number=7,
         title_en="My healthy breakfast", title_zh="我的健康早餐",
         topic_words=["breakfast", "bread", "porridge", "juice", "milk", "banana"],
         sound="sh", sound_examples=["shout", "ship", "sheep", "shirt"],
         structure="How often ...? Once/Twice/... times a week.",
         big_task="Doing a survey about a healthy breakfast",
         project_type="survey", page_start=55, page_end=62, is_project=True),
    dict(code="U8", unit_number=8,
         title_en="Be honest", title_zh="做个诚实的孩子",
         topic_words=["keep one's word", "give ... back", "trust each other", "honest", "honesty", "tell the truth", "never tell a lie"],
         sound=None, sound_examples=[],
         structure="... should ...",
         big_task="Writing tips for being an honest child",
         project_type="tips", page_start=63, page_end=70, is_project=True),
    dict(code="U9", unit_number=9,
         title_en="What time is it?", title_zh="现在几点？",
         topic_words=["time", "hour hand", "minute hand", "seven o'clock", "half past eleven", "ten to four"],
         sound=None, sound_examples=[],
         structure="What time is it? It's ...",
         big_task="Playing a board game about time",
         project_type="board game", page_start=71, page_end=78, is_project=True),
    dict(code="U10", unit_number=10,
         title_en="Weather", title_zh="天气",
         topic_words=["sunny", "rainy", "cloudy", "windy", "snowy", "weather", "weather report", "degree"],
         sound=None, sound_examples=[],
         structure="How's the weather ...? It's ...",
         big_task="Giving a weather report",
         project_type="weather report", page_start=79, page_end=86, is_project=True),
]


# 现有 200 题 knowledge_point 标签 → Unit 映射表
# 旧标签: 4A M1 (人/can/doing)
#         4A M2 (family/物主)
#         4A M3 (places/进行时)
#         4A M4 (world around/there be/比较级)
#         4B M5-M8 (下册 — 暂不映射，标记 cross)
KP_TO_UNIT = {
    # 4A M1: "Getting to know you" / can / 自我介绍 / 形容词
    "4A M1": "U2",  # 同学特质（friendly/lovely/polite） ~ M1 形容词
    # 4A M2: Me, my family, my friends — 物主/家人 — 跨越 ~ 不严格贴合 U1/U4
    # M2 包含家人、朋友、jobs，更接近 U4 our birthday 语境
    "4A M2": "U4",  # 家庭成员 + birthday 语境（家庭场景）
    # 4A M3: Places and activities — places 主题强关联 U1（school places）
    "4A M3": "U1",  # Places 主题
    # 4A M4: The world around — 形状/天气/比较级 — 部分主题对应 U10 (weather)
    "4A M4": "U10",  # 主题词比较级也有天气词汇
    # 4B M5-M8: 下册 — 不映射，标记 cross
}


async def seed():
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # 1) 版本：已存在则更新，否则创建
        existing_v = (await db.execute(
            select(TextbookVersion).where(TextbookVersion.code == VERSION["code"])
        )).scalars().first()

        if existing_v:
            print(f"更新教材版本：{existing_v.name}")
            for k, v in VERSION.items():
                setattr(existing_v, k, v)
            version = existing_v
        else:
            print(f"创建教材版本：{VERSION['name']}")
            version = TextbookVersion(**VERSION)
            db.add(version)
            await db.commit()
            await db.refresh(version)

        print(f"  version_id = {version.id}")

        # 2) Units：按 code 去重重建
        existing_units = (await db.execute(
            select(TextbookUnit).where(TextbookUnit.version_id == version.id)
        )).scalars().all()
        existing_codes = {u.code for u in existing_units}

        for u in UNITS:
            if u["code"] in existing_codes:
                old = next(x for x in existing_units if x.code == u["code"])
                for k, v in u.items():
                    setattr(old, k, v)
            else:
                new = TextbookUnit(version_id=version.id, **u)
                db.add(new)
        await db.commit()

        # 拉回最新
        units = (await db.execute(
            select(TextbookUnit).where(TextbookUnit.version_id == version.id).order_by(TextbookUnit.unit_number)
        )).scalars().all()
        code_to_id = {u.code: u.id for u in units}
        print(f"  Units: {list(code_to_id.keys())}")

        # 3) 题目映射：把现有"沪教版四年级英语（2025-2026 新版）"题库的所有题映射到 Unit
        target_bank = (await db.execute(
            select(QuestionBank).where(
                and_(QuestionBank.grade == "四年级", QuestionBank.subject == "英语",
                     QuestionBank.title.like("%沪教版四年级英语%2025%"))
            )
        )).scalars().first()
        if not target_bank:
            # fallback: 任何 grade=四年级 subject=英语 title 含"沪教"
            target_bank = (await db.execute(
                select(QuestionBank).where(
                    and_(QuestionBank.grade == "四年级", QuestionBank.subject == "英语",
                         QuestionBank.title.like("%沪教%"))
                )
            )).scalars().first()

        if not target_bank:
            print("[WARN] 找不到目标题库，跳过题目映射")
            return

        questions = (await db.execute(
            select(Question).where(Question.bank_id == target_bank.id)
        )).scalars().all()

        # 删掉该题库下所有旧关联，重新建
        old_links = (await db.execute(
            select(QuestionUnit).where(
                QuestionUnit.question_id.in_([q.id for q in questions])
            )
        )).scalars().all()
        for l in old_links:
            await db.delete(l)
        await db.flush()

        n_mapped = 0
        n_skipped = 0
        for q in questions:
            kp = q.knowledge_point  # 形如 "4A M1"
            unit_code = KP_TO_UNIT.get(kp)
            if unit_code and unit_code in code_to_id:
                qu = QuestionUnit(question_id=q.id, unit_id=code_to_id[unit_code], relevance="primary")
                db.add(qu)
                n_mapped += 1
            else:
                # 下册题目（4B M5-M8）暂不映射
                n_skipped += 1

        await db.commit()
        print(f"  映射: {n_mapped} 条 Primary 关联（4A 题目）")
        print(f"  跳过: {n_skipped} 条（4B 下册题目，无对应教材 Unit）")

        # 4) 顺手给题库加上 description 提示（让 UI 显示教材版本信息）
        if target_bank and "（2025-2026 新版）" in target_bank.title:
            old_desc = target_bank.description or ""
            tag = "已映射教材 Unit (沪教版 5·4 学制 4A 上册)"
            if tag not in old_desc:
                target_bank.description = old_desc + f"\n\n📘 {tag}"
                await db.commit()

        print("\n=== 完成 ===")
        print(f"  教材版本: {VERSION['name']} (id={version.id})")
        print(f"  Units: {len(units)} 个")
        print(f"  题目关联: {n_mapped} 道题 → 4A 上册 Unit")


if __name__ == "__main__":
    asyncio.run(seed())
