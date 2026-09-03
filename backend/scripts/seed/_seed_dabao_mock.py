"""
为大宝（child_id=1）生成模拟数据：
- 考试记录：5 个科目（语文/数学/英语/科学/信息科技）× 5 次考试
- 成长发育：8 个月度记录（身高/体重/BMI/视力）
- 作业追踪：近期 3 周作业记录
- 成长时间轴：荣誉/里程碑/日常事件
- 社交情感：隔周情绪记录
- 兴趣特长：暑期活动记录

用法：后端服务运行中，执行
    python scripts/seed/_seed_dabao_mock.py
数据通过 API 写入，与界面录入行为一致。
"""
import json
import urllib.request

BASE = "http://127.0.0.1:8000/api"
CHILD_ID = 1  # 大宝


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ============ 1. 考试数据（5 科目 × 5 次考试） ============
# (考试名称, 类型, 日期, 班级平均分基准)
EXAM_EVENTS = [
    ("三年级上学期期中考试", "exam", "2025-11-13", 83.5),
    ("三年级上学期期末考试", "exam", "2026-01-15", 84.2),
    ("三年级下学期第一次月考", "quiz", "2026-03-20", 82.8),
    ("三年级下学期期中考试", "exam", "2026-04-23", 84.6),
    ("三年级下学期期末考试", "exam", "2026-06-25", 85.3),
]

# 各科成绩走势（与 EXAM_EVENTS 一一对应）
SUBJECT_SCORES = {
    "语文":   {"scores": [85, 87, 84, 89, 91], "ranks": [12, 9, 11, 7, 5],
               "kps": [["阅读理解-概括段意", "生字词"], ["作文-写人", "修辞手法"],
                        ["阅读理解-概括段意"], ["阅读理解-体会情感", "作文-写事"],
                        ["作文-写景", "文言文启蒙", "阅读理解-体会情感"]]},
    "数学":   {"scores": [92, 88, 95, 93, 96], "ranks": [6, 10, 3, 5, 2],
               "kps": [["两位数乘法", "角的认识"], ["年月日", "小数初步"],
                        ["三位数乘两位数", "平行四边形"], ["运算律", "解决问题"],
                        ["平均数", "图形计数", "应用题综合"]]},
    "英语":   {"scores": [88, 91, 90, 94, 95], "ranks": [8, 5, 6, 3, 3],
               "kps": [["一般现在时", "单词拼写"], ["There be 句型"],
                        ["现在进行时"], ["一般过去时", "阅读理解"],
                        ["综合复习", "听力", "写作-My family"]]},
    "科学":   {"scores": [86, 90, 88, 92, 93], "ranks": [10, 6, 8, 4, 4],
               "kps": [["水的外形与状态"], ["空气的性质"],
                        ["声音的产生"], ["声音的传播", "光的反射"],
                        ["热胀冷缩", "实验设计"]]},
    "信息科技": {"scores": [95, 92, 97, 96, 98], "ranks": [3, 5, 2, 3, 1],
               "kps": [["键盘指法"], ["文件管理"],
                        ["文字编辑", "画图工具"], ["表格初步"],
                        ["幻灯片制作", "网络搜索技巧"]]},
}

COMMENTS = {
    "语文": ["阅读概括能力有进步，作文细节描写可再丰富。", None,
             None, "课堂发言积极，作文结构清晰。", "书写工整，阅读题得分率明显提升。"],
    "数学": ["计算准确率高，注意审题。", "应用题失分较多，需加强读题训练。",
             None, None, "本学期进步显著，思维灵活。"],
    "英语": [None, "听力满分，继续保持。", "单词拼写偶有小错。",
             "口语表达自然大方。", "综合能力班级前列。"],
    "科学": [None, None, "实验报告完成认真。", None, "对科学探究兴趣浓厚。"],
    "信息科技": ["操作熟练。", None, None, None, "打字速度全班第一，作品创意好。"],
}


def seed_exams():
    n = 0
    for i, (exam_name, exam_type, exam_date, class_avg) in enumerate(EXAM_EVENTS):
        for subject, cfg in SUBJECT_SCORES.items():
            score = cfg["scores"][i]
            payload = {
                "child_id": CHILD_ID,
                "subject": subject,
                "exam_name": exam_name,
                "exam_type": exam_type,
                "score": score,
                "full_score": 100.0,
                "target_score": 90,
                "class_rank": cfg["ranks"][i],
                "grade_rank": cfg["ranks"][i] * 2 + 3,
                "exam_date": exam_date,
                "knowledge_points": cfg["kps"][i],
                "teacher_comment": COMMENTS[subject][i],
                "class_average": round(class_avg + (0 if subject != "信息科技" else 3.5), 1),
            }
            post("/exams", payload)
            n += 1
    print(f"[OK] 考试记录：{n} 条（5 科目 × 5 次考试）")


# ============ 2. 成长发育（月度记录） ============
# (日期, 身高cm, 体重kg, 左眼视力, 右眼视力, 备注)
GROWTH = [
    ("2026-01-18", 134.2, 30.1, 4.8, 4.9, None),
    ("2026-02-15", 134.8, 30.5, 4.8, 4.9, None),
    ("2026-03-18", 135.3, 30.8, 4.9, 4.9, None),
    ("2026-04-20", 136.0, 31.2, 4.9, 4.9, None),
    ("2026-05-17", 136.5, 31.6, 4.9, 5.0, "视力有改善"),
    ("2026-06-21", 137.0, 32.0, 5.0, 5.0, "期末体检测视力 5.0"),
    ("2026-07-19", 137.4, 32.4, 5.0, 5.0, None),
    ("2026-08-22", 137.8, 32.8, 5.0, 5.0, "暑假游泳+篮球，长高明显"),
]


def seed_growth():
    for date, h, w, vl, vr, note in GROWTH:
        payload = {
            "child_id": CHILD_ID,
            "record_date": date,
            "height_cm": h,
            "weight_kg": w,
            "bmi": round(w / (h / 100) ** 2, 1),
            "vision_left": vl,
            "vision_right": vr,
            "note": note,
        }
        post(f"/growth/{CHILD_ID}", payload)
    print(f"[OK] 成长发育：{len(GROWTH)} 条月度记录")


# ============ 3. 作业追踪（近期 3 周） ============
HOMEWORKS = [
    # (科目, 标题, 日期, 用时min, 总题数, 对题数, 难度, 备注)
    ("数学", "《三位数乘两位数》竖式计算 20 题", "2026-08-10", 25, 20, 18, "normal", None),
    ("语文", "暑假阅读理解专练（二）", "2026-08-10", 30, 8, 6, "hard", "概括段意仍需练习"),
    ("英语", "Unit 1 单词抄写 + 跟读打卡", "2026-08-11", 20, None, None, "easy", "完成认真"),
    ("数学", "口算天天练 P12-13", "2026-08-11", 15, 60, 57, "easy", None),
    ("科学", "《声音是怎样产生的》预习笔记", "2026-08-12", 25, None, None, "normal", None),
    ("信息科技", "打字练习（金山打字通 20 分钟）", "2026-08-12", 20, None, None, "easy", None),
    ("语文", "四年级生字表（一）抄写", "2026-08-13", 20, None, None, "easy", None),
    ("英语", "课文朗读录音打卡", "2026-08-13", 15, None, None, "easy", None),
    ("数学", "《平行四边形与梯形》练习卷", "2026-08-16", 35, 24, 21, "normal", "图形题正确率高"),
    ("英语", "Unit 1 同步练习（语法部分）", "2026-08-16", 25, 30, 26, "normal", "一般过去时错 4 题"),
    ("语文", "小作文《我的暑假一天》", "2026-08-17", 40, None, None, "hard", "家长评：条理清晰"),
    ("数学", "口算天天练 P16", "2026-08-17", 12, 60, 58, "easy", None),
    ("科学", "完成科学小实验：观察声音振动", "2026-08-18", 30, None, None, "normal", "很感兴趣"),
    ("信息科技", "PPT《我的暑假》制作", "2026-08-19", 45, None, None, "normal", "自主完成，配了动画"),
    ("语文", "阅读理解专练（三）+ 订正", "2026-08-20", 30, 8, 7, "normal", None),
    ("英语", "英语绘本阅读《The Gruffalo》", "2026-08-21", 25, None, None, "normal", None),
    ("数学", "《平均数与条形统计图》练习", "2026-08-23", 30, 20, 17, "normal", None),
    ("语文", "四年级古诗背诵 + 默写", "2026-08-24", 20, 4, 4, "easy", "全部默写正确"),
    ("英语", "Unit 2 单词预习 + 自然拼读", "2026-08-25", 20, None, None, "easy", None),
    ("数学", "口算天天练 P20", "2026-08-26", 12, 60, 59, "easy", None),
]


def seed_homeworks():
    for subject, title, date, dur, total, correct, diff, note in HOMEWORKS:
        payload = {
            "child_id": CHILD_ID,
            "subject": subject,
            "title": title,
            "homework_date": date,
            "duration_minutes": dur,
            "completed": True,
            "difficulty": diff,
            "note": note,
        }
        if total is not None:
            payload["total_questions"] = total
            payload["correct_questions"] = correct
            payload["accuracy"] = round(correct / total * 100, 1)
        post("/homeworks", payload)
    print(f"[OK] 作业记录：{len(HOMEWORKS)} 条")


# ============ 4. 成长时间轴 ============
TIMELINE = [
    ("award", "获评「数学之星」", "三年级下学期期末被评为班级数学之星，数学期末 96 分班级第 2。", "2026-06-30",
     ["数学", "荣誉"], None),
    ("award", "校运动会跳绳比赛第二名", "三年级组 30 秒单摇跳绳 82 个，获得年级第二名。", "2026-04-28",
     ["运动", "跳绳"], None),
    ("milestone", "完成 Python 趣味编程入门课", "暑期完成 20 课时编程入门，能独立编写猜数字小游戏。", "2026-08-20",
     ["编程", "暑假"], None),
    ("milestone", "三年级顺利毕业", "全学年综合评价为「优秀」，进步明显的是数学和英语。", "2026-06-30",
     ["学期总结"], None),
    ("note", "开启四年级预习计划", "每天上午预习 2 门课 + 30 分钟课外阅读，状态不错。", "2026-08-25",
     ["四年级", "预习"], None),
]


def seed_timeline():
    for etype, title, desc, date, tags, _ in TIMELINE:
        payload = {
            "child_id": CHILD_ID,
            "event_type": etype,
            "title": title,
            "description": desc,
            "event_date": date,
            "tags": tags,
        }
        post("/timeline", payload)
    print(f"[OK] 成长时间轴：{len(TIMELINE)} 条事件")


# ============ 5. 社交情感（隔周记录） ============
SOCIAL = [
    ("2026-07-12", 4, ["开心", "放松"], "和小伙伴在小区打篮球", 4, "暑假开始，心情很好"),
    ("2026-07-26", 5, ["开心", "专注"], "夏令营认识新朋友", 4, "主动举手当小组长"),
    ("2026-08-09", 4, ["平静", "专注"], None, 4, "编程课攻克难题很有成就感"),
    ("2026-08-16", 3, ["烦躁"], None, 3, "预习遇到难的数学题有点急躁，后来自己解开了"),
    ("2026-08-23", 5, ["开心", "自信"], "和同学相约图书馆", 5, "主动给同学讲解题思路"),
    ("2026-08-28", 4, ["期待"], "报名学校编程社团", 4, "期待四年级新学期"),
]


def seed_social():
    for date, mood, tags, activity, conf, note in SOCIAL:
        payload = {
            "child_id": CHILD_ID,
            "record_date": date,
            "mood_score": mood,
            "emotion_tags": tags,
            "social_activity": activity,
            "confidence_level": conf,
            "note": note,
        }
        post(f"/social-emotional/{CHILD_ID}", payload)
    print(f"[OK] 社交情感：{len(SOCIAL)} 条记录")


# ============ 6. 兴趣特长（暑期活动） ============
INTERESTS = [
    # (日期, 类型, 名称, 时长min, 等级, 备注)
    ("2026-07-08", "运动", "篮球训练课", 90, "intermediate", None),
    ("2026-07-10", "编程", "Python 趣味编程（第 1-2 课）", 60, "beginner", "学会 print 和变量"),
    ("2026-07-15", "运动", "游泳课（蛙泳）", 60, "intermediate", None),
    ("2026-07-22", "阅读", "科普阅读《十万个为什么》", 30, "intermediate", None),
    ("2026-07-29", "编程", "Python 趣味编程（第 5-6 课）", 60, "beginner", "完成猜数字小游戏"),
    ("2026-08-05", "运动", "篮球训练课", 90, "intermediate", "三步上篮有进步"),
    ("2026-08-12", "编程", "Python 趣味编程（结课作品）", 90, "intermediate", "独立完成走迷宫游戏"),
    ("2026-08-19", "运动", "游泳课（自由泳）", 60, "intermediate", None),
    ("2026-08-26", "阅读", "《夏洛的网》整本阅读", 45, "intermediate", "写了读后感"),
]


def seed_interests():
    for date, atype, name, dur, level, note in INTERESTS:
        payload = {
            "child_id": CHILD_ID,
            "record_date": date,
            "activity_type": atype,
            "activity_name": name,
            "duration_minutes": dur,
            "skill_level": level,
            "note": note,
        }
        post(f"/interests/{CHILD_ID}", payload)
    print(f"[OK] 兴趣特长：{len(INTERESTS)} 条记录")


if __name__ == "__main__":
    seed_exams()
    seed_growth()
    seed_homeworks()
    seed_timeline()
    seed_social()
    seed_interests()
    print("\n全部模拟数据写入完成 ✅")
