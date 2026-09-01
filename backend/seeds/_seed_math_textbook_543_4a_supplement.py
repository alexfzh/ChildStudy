"""沪教版五四制数学四上·配套题库补充题目（U8 数学广场 + U9 复习）。

背景：首轮造数后 U8 只有 2 题、U9 只有 1 题，且部分知识点题量单薄。
本脚本通过 API 建题 + 直连数据库建单元/知识点关联（与 _seed_math_textbook_543_4a.py 一致）。

运行方式（在 backend 目录下）：
    PYTHONPATH=. ./.venv/Scripts/python.exe seeds/_seed_math_textbook_543_4a_supplement.py
"""
import json
import urllib.request

BASE = "http://127.0.0.1:8000/api"
BANK_ID = 5  # 沪教版（五四制）数学四年级上册·配套练习
VERSION = 2
U8_UNIT = 8  # unit_number
U9_UNIT = 9


def api_post(path, payload):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ---- 题目定义：(unit, kp, difficulty, content, options, answer, explanation) ----
QUESTIONS = [
    # ================= U8 数学广场（等量代换专题，补 4 题至共 6 题）=================
    (U8_UNIT, "等量代换", "easy",
     "1 个梨的重量 = 3 个橘子的重量，2 个梨的重量 =（　）个橘子的重量。",
     ["A. 3", "B. 5", "C. 6", "D. 9"], "C",
     "1 个梨 = 3 个橘子，2 个梨 = 3×2 = 6 个橘子。"),
    (U8_UNIT, "等量代换", "normal",
     "天平平衡时，左边放 1 个正方体，右边放 3 个圆柱；另一个天平左边放 1 个圆柱，右边放 2 个球。那么 1 个正方体 =（　）个球的重量。",
     ["A. 3", "B. 5", "C. 6", "D. 8"], "C",
     "1 正方体 = 3 圆柱 = 3×2 = 6 球。"),
    (U8_UNIT, "等量代换", "normal",
     "□+□+△=30，△+△+□=24，那么 □=（　）。",
     ["A. 6", "B. 8", "C. 12", "D. 10"], "C",
     "两式相加得 3(□+△)=54，□+△=18；由第二式 △=24-□-□，代入解得 □=12。"),
    (U8_UNIT, "等量代换", "hard",
     "8 支铅笔的价钱 = 2 支钢笔的价钱，3 支钢笔的价钱 = 1 个文具盒的价钱。买 1 个文具盒的钱可以买（　）支铅笔。",
     ["A. 8", "B. 12", "C. 16", "D. 24"], "B",
     "1 钢笔 = 4 铅笔，1 文具盒 = 3 钢笔 = 12 铅笔。"),

    # ================= U9 复习（全书综合，补 5 题至共 6 题，覆盖薄弱知识点）=================
    (U9_UNIT, "近似数与四舍五入", "normal",
     "把 39□5000000 四舍五入到亿位约等于 40 亿，□ 里最小可以填（　）。",
     ["A. 4", "B. 5", "C. 6", "D. 9"], "B",
     "千万位上满 5 向亿位进 1，□ 最小填 5。"),
    (U9_UNIT, "亿以内数的读写", "normal",
     "下面各数中，只读一个零的数是（　）。",
     ["A. 5005500", "B. 5500000", "C. 5050005", "D. 5000500"], "D",
     "5000500 读作五百万零五百：万级末尾的三个 0 只读一个零，个级末尾的 0 不读。A 读五百万五千五百（不读零），B 读五百五十万（不读零），C 读五百零五万零五（读两个零）。"),
    (U9_UNIT, "乘除法各部分关系", "easy",
     "在除法算式中，被除数 = 除数 × 商 +（　）。",
     ["A. 余数", "B. 被除数", "C. 除数", "D. 积"], "A",
     "有余数除法中：被除数 = 除数 × 商 + 余数。"),
    (U9_UNIT, "四则混合运算", "normal",
     "计算 480 ÷ (24 - 16) × 5，正确的结果是（　）。",
     ["A. 10", "B. 300", "C. 60", "D. 120"], "B",
     "先算括号：24-16=8，再按从左到右：480÷8=60，60×5=300。"),
    (U9_UNIT, "运算定律", "hard",
     "下面算式中，运用了乘法分配律的是（　）。",
     ["A. 25×44 = 25×4×11", "B. 36×101 = 36×100+36",
      "C. 125×8×7 = 125×(8×7)", "D. 56+37+44 = 37+(56+44)"], "B",
     "36×101 = 36×(100+1) = 36×100+36，是乘法分配律；A 是乘法结合律拆分，C 是结合律，D 是交换律与结合律。"),
]


def main():
    created = []
    for unit, kp, diff, content, options, answer, expl in QUESTIONS:
        q = api_post(f"/question-banks/{BANK_ID}/questions", {
            "bank_id": BANK_ID,
            "knowledge_point": kp,
            "question_type": "single_choice",
            "difficulty": diff,
            "content": content,
            "options": options,
            "correct_answer": answer,
            "explanation": expl,
        })
        created.append((q["id"], unit, kp))
        print(f"  + 题目 #{q['id']} U{unit} [{diff}] {content[:30]}")

    # ---- 建关联（单元 + 知识点），与主造数脚本同法 ----
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from config import settings
    from models import KnowledgePoint, QuestionKnowledgePoint, QuestionUnit, TextbookUnit

    async def link():
        engine = create_async_engine(settings.database_url, echo=False)
        Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with Session() as db:
            units = (await db.execute(
                select(TextbookUnit).where(TextbookUnit.version_id == VERSION)
            )).scalars().all()
            unit_map = {u.unit_number: u.id for u in units}
            kps = (await db.execute(
                select(KnowledgePoint).where(KnowledgePoint.subject == "数学")
            )).scalars().all()
            kp_ids = {k.name: k.id for k in kps}
            n = 0
            for qid, unit, kp in created:
                db.add(QuestionUnit(question_id=qid, unit_id=unit_map[unit], relevance="primary"))
                if kp in kp_ids:
                    db.add(QuestionKnowledgePoint(question_id=qid, knowledge_point_id=kp_ids[kp]))
                    n += 1
                else:
                    print(f"  ! 知识点未找到: {kp}")
            await db.commit()
            print(f"  关联完成：单元 {len(created)} 条，知识点 {n} 条")
        await engine.dispose()

    asyncio.run(link())
    print("✅ 补充完成")


if __name__ == "__main__":
    main()
