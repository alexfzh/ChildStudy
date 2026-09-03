"""Seed 沪教版 4A 英语知识点 ↔ 教材 Unit 关联：
  - 补全缺失的 KP
  - 把现有+新增 KP 关联到 TextbookUnit
"""
import asyncio

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import KnowledgePoint, KnowledgePointUnit, TextbookUnit, TextbookVersion

# 要补充的新 KP（小学四年级英语核心）
NEW_KP = [
    # (name, category, description, 关联 unit_codes)
    ("情态动词 can", "语法", "情态动词 can 表示能力/许可：can swim, can play", ["U1", "U2", "U6"]),
    ("现在进行时", "语法", "be + doing 表示正在进行的动作：is running, are playing", ["U3", "U7"]),
    ("一般现在时(第三人称单数)", "语法", "主语三单 + 动词+s/es：he has, she likes", ["U1", "U2", "U7"]),
    ("一般将来时 (be going to)", "语法", "be going to + 动词原形：I am going to visit", ["U6", "U10"]),
    ("There be 句型", "语法", "There is / There are 表示某地有某物", ["U1", "U5", "U7"]),
    ("物主代词", "语法", "形容词性 my/your/his/her + 名词性 mine/yours/his/hers", ["U1", "U2", "U4"]),
    ("介词 in/on/at", "语法", "地点/时间介词 in / on / at 的基本用法", ["U1", "U5", "U9"]),
    ("一般疑问句", "语法", "Yes/No 问句用 be / do / does 开头", ["U2", "U7"]),
    ("感叹句 (How ...!)", "语法", "How + 形容词/副词 + ! 表感叹：How beautiful!", ["U6"]),
    ("be 动词", "语法", "am/is/are 表示身份/状态/位置", ["U1", "U2", "U8"]),
    ("自然拼读 /w/", "语音", "字母 w 发 /w/ 音：wall, Wednesday, water, window", ["U1"]),
    ("自然拼读 /x/", "语音", "x 在词首发 /gz/（excited, exam），词尾发 /ks/（box, six）", ["U2"]),
    ("自然拼读 /j/", "语音", "字母 y 在词首发 /j/：yes, year, yellow, young", ["U6"]),
    ("自然拼读 /ʃ/", "语音", "字母组合 sh 发 /ʃ/ 音：shout, ship, sheep, shirt", ["U7"]),
    ("自然拼读 /kw/", "语音", "字母组合 qu 发 /kw/ 音：question, queen, quiet", ["U9"]),
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        from models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 加载教材版本 + Units
        version = (await db.execute(
            select(TextbookVersion).where(TextbookVersion.code == "SH-5-4-2025A")
        )).scalars().first()
        if not version:
            print("[ERROR] 教材版本不存在，先跑 _seed_textbook_grade4a.py")
            return
        units = (await db.execute(
            select(TextbookUnit).where(TextbookUnit.version_id == version.id)
        )).scalars().all()
        code_to_unit = {u.code: u for u in units}
        print(f"加载 {len(units)} 个 Unit")

        # ── 1) 创建新 KP（不存在则建）──
        new_kp_ids = []
        for name, cat, desc, units_list in NEW_KP:
            existing = (await db.execute(
                select(KnowledgePoint).where(
                    and_(
                        KnowledgePoint.subject == "英语",
                        KnowledgePoint.grade_level == "四年级",
                        KnowledgePoint.name == name,
                    )
                )
            )).scalars().first()
            if existing:
                new_kp_ids.append((existing.id, units_list))
                print(f"  KP 存在：{name} (id={existing.id})")
            else:
                kp = KnowledgePoint(
                    subject="英语",
                    grade_level="四年级",
                    category=cat,
                    name=name,
                    description=desc,
                )
                db.add(kp)
                await db.flush()
                new_kp_ids.append((kp.id, units_list))
                print(f"  KP 新建：{name} (id={kp.id})")

        await db.commit()

        # ── 2) 把现有四年级 KP（id 144-150）也加入映射 ──
        existing_grade4a = (await db.execute(
            select(KnowledgePoint).where(
                and_(KnowledgePoint.subject == "英语", KnowledgePoint.grade_level == "四年级")
            )
        )).scalars().all()

        EXISTING_KP_MAP = {
            144: ["U2", "U4"],  # 名词所有格
            145: ["U7"],  # 频度副词
            146: ["U6", "U10"],  # 形容词比较级
            147: ["U8"],  # 一般过去时
            148: ["U1", "U2"],  # 祈使句
            149: ["U5"],  # 交通方式
            150: ["U5"],  # 问路与指路
        }

        # ── 3) 批量建关联（先清空旧 KP-Unit 关联，再插入）──
        # 先按版本清空
        unit_ids_in_version = [u.id for u in units]
        old_links = (await db.execute(
            select(KnowledgePointUnit).where(
                KnowledgePointUnit.unit_id.in_(unit_ids_in_version)
            )
        )).scalars().all()
        for l in old_links:
            await db.delete(l)
        await db.flush()

        # 收集所有要关联的 (kp_id, unit_code)
        all_links = []
        for kp_id, units_list in new_kp_ids:
            for unit_code in units_list:
                all_links.append((kp_id, unit_code, "primary"))
        for kp in existing_grade4a:
            units_list = EXISTING_KP_MAP.get(kp.id, [])
            for unit_code in units_list:
                all_links.append((kp.id, unit_code, "primary"))

        n_created = 0
        for kp_id, unit_code, relevance in all_links:
            unit = code_to_unit.get(unit_code)
            if not unit:
                continue
            db.add(KnowledgePointUnit(
                knowledge_point_id=kp_id,
                unit_id=unit.id,
                relevance=relevance,
            ))
            n_created += 1

        await db.commit()
        print("\n=== 完成 ===")
        print(f"  新建 KP: {len([x for x in new_kp_ids if x not in [(e.id, None) for e in existing_grade4a]])}")
        print(f"  KP ↔ Unit 关联: {n_created} 条")

        # 验证分布
        for u in units:
            kps = (await db.execute(
                select(KnowledgePoint, KnowledgePointUnit)
                .join(KnowledgePointUnit, KnowledgePointUnit.knowledge_point_id == KnowledgePoint.id)
                .where(KnowledgePointUnit.unit_id == u.id)
            )).all()
            if kps:
                names = [kp.name for kp, _ in kps]
                print(f"  {u.code:8s} ({u.title_en:25s}): {len(names)} KP - {', '.join(names[:3])}{'...' if len(names) > 3 else ''}")


if __name__ == "__main__":
    asyncio.run(seed())
