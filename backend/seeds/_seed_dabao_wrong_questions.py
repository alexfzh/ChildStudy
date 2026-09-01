"""
为大宝（child_id=1）生成错题本模拟数据：
- 15 道错题，覆盖 5 个科目（语文/数学/英语/科学/信息科技）
- 错因、知识点、难度、掌握度分布合理
- 5 道设置为"今日/已逾期待复习"（测试艾宾浩斯提醒）
- 3 道通过复习接口补真实复习历史（其中 1 道复习两次后标记已掌握）

用法：后端服务运行中，执行
    python seeds/_seed_dabao_wrong_questions.py
"""
import json
import urllib.request
from datetime import date, timedelta

BASE = "http://127.0.0.1:8000/api"
CHILD_ID = 1  # 大宝

TODAY = date.today()
D = lambda n: (TODAY + timedelta(days=n)).isoformat()  # noqa: E731


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def put(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ============ 错题数据 ============
# (科目, 题干, 我的答案, 正确答案, 错因, 知识点, 难度, 掌握度,
#  错误次数, 最后错误日期, 下次复习日期, 来源, 备注)
WRONG_QUESTIONS = [
    # --- 今日待复习（next_review_date <= today） ---
    ("语文",
     "阅读理解：《白鹅》选段，概括第 3 自然段的主要意思。",
     "写了白鹅的样子。",
     "白鹅吃饭一板一眼、讲究三眼一板，需要人伺候。",
     "concept", ["阅读理解-概括段意"], "normal", "learning",
     2, D(-6), D(0), "exam", "概括不够具体，只抓住表层信息。"),
    ("数学",
     "竖式计算：145 × 12",
     "1640",
     "1740",
     "calculation", ["三位数乘两位数", "进位加法"], "normal", "new",
     1, D(-3), D(0), "homework", "十位相乘时漏加进位。"),
    ("数学",
     "一辆汽车每小时行 65 千米，行驶 3 小时 15 分钟，一共行了多少千米？",
     "65 × 3 = 195 千米",
     "65 × 3.25 = 211.25 千米（把 15 分钟换算成 0.25 小时）",
     "careless", ["行程问题", "单位换算"], "hard", "learning",
     2, D(-10), D(-1), "exam", "漏看「15分钟」，时间单位没统一。"),
    ("英语",
     "写出 go 的过去式：yesterday I ____ to the park.",
     "goed",
     "went",
     "concept", ["一般过去时", "不规则动词"], "normal", "learning",
     2, D(-8), D(0), "exam", "规则变化用习惯了，不规则动词要单独记。"),
    ("科学",
     "判断：声音可以在真空中传播。（　）",
     "√",
     "×（声音传播需要介质，真空不能传声）",
     "concept", ["声音的传播"], "normal", "new",
     1, D(-4), D(0), "quiz", "和光可在真空中传播混淆了。"),

    # --- 未来复习计划 ---
    ("语文",
     "修改病句：通过这次活动，使我明白了团结的重要性。",
     "用词不当",
     "成分残缺：「通过……使……」连用导致句子缺主语",
     "unfamiliar", ["修改病句", "句子结构"], "normal", "new",
     1, D(-2), D(1), "homework", None),
    ("语文",
     "古诗默写：《题西林壁》——不知_____，只缘身在_____。",
     "不知山中貌，只缘身在此山中",
     "不知真面目，只缘身在最高层",
     "careless", ["古诗默写"], "easy", "new",
     1, D(-1), D(3), "exam", None),
    ("数学",
     "判断：平行四边形是特殊的梯形。（　）",
     "√",
     "×（梯形只有一组对边平行，平行四边形两组对边分别平行）",
     "concept", ["平行四边形", "梯形"], "normal", "learning",
     2, D(-5), D(2), "exam", "两组对边与一组对边的区别没吃透。"),
    ("数学",
     "简便计算：25 × 32 × 125",
     "25 × (30+2) × 125 = 100000",
     "25×4×8×125 = 100×1000 = 100000（拆 32=4×8 再用结合律）",
     "concept", ["运算律", "简便运算"], "hard", "new",
     1, D(-1), D(4), "homework", "结果碰巧对了，但拆分思路不对。"),
    ("英语",
     "There ____ many books on the desk.（have / has / are）",
     "have",
     "are",
     "concept", ["There be 句型"], "easy", "new",
     1, D(-2), D(5), "homework", "和 There is/are 的就近原则一起复习。"),
    ("英语",
     "拼写单词：美丽的 b______",
     "beatiful",
     "beautiful",
     "careless", ["单词拼写"], "easy", "new",
     1, D(-1), D(6), "quiz", None),
    ("科学",
     "实验设计：探究「橡皮筋的松紧与声音高低的关系」，写出实验步骤。",
     "拨动橡皮筋听声音高低。",
     "需控制粗细、长度相同，只改变松紧，逐一拨动并对比音高（控制变量法）。",
     "unfamiliar", ["声音的高低", "控制变量法"], "hard", "new",
     1, D(-3), D(7), "exam", "第一次接触控制变量法，题型陌生。"),
    ("信息科技",
     "文件「照片.jpg」的扩展名说明它属于哪类文件？",
     "文档文件",
     "图片文件",
     "concept", ["文件管理", "文件类型"], "easy", "new",
     1, D(-2), D(8), "homework", None),
    ("信息科技",
     "WPS 表格中求 B2:B6 的和，公式 =SUM(B2:B6) 和 =B2+B3+B4+B5+B6 结果一样吗？哪种更好？",
     "不一样",
     "结果一样；SUM 函数更简洁、增删行会自动更新范围，更推荐",
     "reasoning", ["表格公式", "SUM 函数"], "normal", "new",
     1, D(-1), D(9), "quiz", None),

    # --- 已掌握（归档示例） ---
    ("数学",
     "口算：0.5 + 0.25 = ?",
     "0.75",
     "0.75（此前写成 0.30，小数点对齐出错）",
     "calculation", ["小数加减法"], "easy", "mastered",
     2, D(-14), D(10), "homework", "连续两次复习全对，已掌握。"),
]

# 需要补复习历史的题（按题干前缀匹配）：(结果, 备注, 复习次数)
REVIEW_HISTORY = [
    ("口算：0.5 + 0.25", "correct", "第二次复习全对", 2),
    ("古诗默写：《题西林壁》", "correct", "这次默写全对", 1),
    ("简便计算：25 × 32 × 125", "partial", "方法讲对了，书写跳步", 1),
]


def main():
    created = []
    for (subject, qtext, user_ans, correct_ans, reason, kps, diff,
         mastery, wrong_count, last_wrong, next_review, source, note) in WRONG_QUESTIONS:
        payload = {
            "child_id": CHILD_ID,
            "source_type": source,
            "subject": subject,
            "question_text": qtext,
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "error_reason": reason,
            "knowledge_points": kps,
            "difficulty": diff,
            "mastery_level": mastery,
            "wrong_count": wrong_count,
            "last_wrong_date": last_wrong,
            "next_review_date": next_review,
            "status": "active",
            "note": note,
        }
        out = post("/wrong-questions", payload)
        created.append((out["id"], qtext, mastery))
    print(f"[OK] 错题：{len(created)} 道")

    # 补复习历史 + 掌握状态
    n_reviews = 0
    for qid, qtext, mastery in created:
        for prefix, result, note, times in REVIEW_HISTORY:
            if qtext.startswith(prefix):
                for _ in range(times):
                    post(f"/wrong-questions/{qid}/review", {"result": result, "note": note})
                    n_reviews += 1
                if prefix.startswith("口算"):
                    # 连续全对 → 标记已掌握
                    put(f"/wrong-questions/{qid}", {"mastery_level": "mastered", "status": "mastered"})
    print(f"[OK] 复习记录：{n_reviews} 条（含艾宾浩斯自动排期）")
    print("\n错题本模拟数据写入完成 ✅")


if __name__ == "__main__":
    main()
