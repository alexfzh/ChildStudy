"""Seed：沪教版（五四制）数学四年级上册（2026秋）教材 + 配套题库 + 知识点 + 大宝暑期预习进度

依据《2026秋小学数学-沪教版五四制-四年级上册》真实目录：
  U1 运算关系与运算律 P1-20 / U2 四面八方的学问 P21-24 / U3 整数的四则运算与应用题 P25-39
  U4 大数的认识与改写 P40-51 / U5 度量衡的故事 P52-58 / U6 分数的初步认识 P59-78
  U7 线与角 P79-103 / U8 数学广场 P104-107 / U9 复习 P108-112

流程：
  1) DB 直写：教材版本 + 9 个单元 + 16 个四上数学知识点（去重）+ 题库 41 题 + 题目↔知识点/单元关联
  2) HTTP 模拟：大宝按单元做 6 场练习（提交后自动生成 StudyProgress / KP掌握度 / 成就）
"""
import asyncio
import json
import urllib.request

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import (
    KnowledgePoint,
    Question,
    QuestionBank,
    QuestionKnowledgePoint,
    QuestionUnit,
    TextbookUnit,
    TextbookVersion,
)

BASE = "http://127.0.0.1:8000/api"
CHILD_ID = 1  # 大宝

VERSION_CODE = "SH-MATH-5-4-2026A"
BANK_TITLE = "沪教版（五四制）数学四年级上册·配套练习"

# ── 教材单元（真实目录） ──
UNITS = [
    dict(code="U1", unit_number=1, title_zh="运算关系与运算律", page_start=1, page_end=20,
         topic_words=["加法各部分关系", "减法各部分关系", "乘法各部分关系", "除法各部分关系",
                      "加法交换律", "加法结合律", "乘法交换律", "乘法结合律", "乘法分配律"],
         structure="加数+加数=和；被减数-减数=差；一个加数=和-另一个加数",
         big_task="运算律寻宝：用运算律完成简便计算闯关"),
    dict(code="U2", unit_number=2, title_zh="四面八方的学问", page_start=21, page_end=24,
         topic_words=["东南西北", "辨认方向", "路线图", "平面图"],
         structure="地图定向：上北、下南、左西、右东",
         big_task="画出从家到学校的路线图并描述行走方向"),
    dict(code="U3", unit_number=3, title_zh="整数的四则运算与应用题", page_start=25, page_end=39,
         topic_words=["四则混合运算", "运算顺序", "小括号", "中括号", "应用题数量关系"],
         structure="先乘除后加减；有括号先算小括号，再算中括号",
         big_task="我是小小会计师：解决生活中的四则运算问题"),
    dict(code="U4", unit_number=4, title_zh="大数的认识与改写", page_start=40, page_end=51,
         topic_words=["万级数的认识", "亿以内数的读写", "数位顺序表", "大数的改写", "四舍五入求近似数"],
         structure="个级、万级、亿级；用“万”或“亿”作单位改写大数",
         big_task="生活中的大数调查：收集并改写 5 个大数"),
    dict(code="U5", unit_number=5, title_zh="度量衡的故事", page_start=52, page_end=58,
         topic_words=["长度单位", "质量单位", "容量单位", "单位换算", "度量衡历史"],
         structure="1千米=1000米；1吨=1000千克；1升=1000毫升",
         big_task="制作一张常用计量单位换算小报"),
    dict(code="U6", unit_number=6, title_zh="分数的初步认识", page_start=59, page_end=78,
         topic_words=["几分之一", "几分之几", "分数各部分名称", "分数大小比较", "同分母分数加减法"],
         structure="平均分成几份，每份是它的几分之一；分母相同，分子大的分数大",
         big_task="分一分：用分数记录生活中的平均分"),
    dict(code="U7", unit_number=7, title_zh="线与角", page_start=79, page_end=103,
         topic_words=["线段", "直线", "射线", "角的认识", "角的度量", "角的分类", "画角"],
         structure="线段两个端点可度量；射线一个端点；直线无端点；直角=90°，平角=180°",
         big_task="用角拼出美丽图案：一副三角尺能拼出哪些角"),
    dict(code="U8", unit_number=8, title_zh="数学广场", page_start=104, page_end=107,
         topic_words=["等量代换", "逻辑推理"],
         structure="用相等的量互相替换，化未知为已知",
         big_task="等量代换猜一猜：1个西瓜等于几个橘子"),
    dict(code="U9", unit_number=9, title_zh="复习", page_start=108, page_end=112,
         topic_words=["运算律复习", "大数复习", "分数复习", "线与角复习"],
         structure="全册知识梳理与综合练习",
         big_task="整理一本学期错题集"),
]

# ── 新增知识点（subject=数学, grade_level=四年级；若已存在则复用） ──
NEW_KPS = [
    ("加减法各部分关系", "数与代数", "加数+加数=和；一个加数=和-另一个加数；被减数-减数=差"),
    ("乘除法各部分关系", "数与代数", "因数×因数=积；一个因数=积÷另一个因数；被除数=商×除数"),
    ("乘法分配律", "数与代数", "(a+b)×c=a×c+b×c，乘法对加法的分配律"),
    ("简便运算", "数与代数", "运用运算律、凑整等方法简化计算"),
    ("方向与位置", "图形与几何", "东南西北八个方向的认识与路线描述"),
    ("括号与运算顺序", "数与代数", "含小括号、中括号算式的运算顺序"),
    ("整数应用题", "数与代数", "用四则运算解决实际问题，理清数量关系"),
    ("亿以内数的读写", "数与代数", "万级、亿级数的组成与正确读写"),
    ("大数的改写", "数与代数", "把整万、整亿的数改写成用“万”“亿”作单位"),
    ("近似数与四舍五入", "数与代数", "用四舍五入法求大数的近似数"),
    ("计量单位与换算", "常见的量", "长度、质量、容量单位的认识与换算"),
    ("分数的初步认识", "数与代数", "几分之一、几分之几的含义与读写"),
    ("同分母分数加减法", "数与代数", "分母不变，分子相加减"),
    ("线段、直线与射线", "图形与几何", "线段、直线、射线的特征与区别"),
    ("角的分类与画角", "图形与几何", "锐角、直角、钝角、平角、周角及用量角器画角"),
    ("等量代换", "数与代数", "用相等的量进行替换求解的数学思想"),
]

# ── 题目（kp=知识点名, unit=单元号） ──
QUESTIONS = [
    # U1 运算关系与运算律（6）
    dict(kp="加减法各部分关系", unit=1, difficulty="easy",
         content="由算式 120+50=170，可以得出下面哪个算式是正确的？",
         options=["A. 170-50=120", "B. 170+50=220", "C. 120-50=70", "D. 170+120=290"],
         answer="A", explanation="一个加数=和-另一个加数，所以 170-50=120。"),
    dict(kp="加减法各部分关系", unit=1, difficulty="normal",
         content="一道减法算式中，被减数是 800，差是 450，减数是多少？",
         options=["A. 350", "B. 450", "C. 1250", "D. 1150"],
         answer="A", explanation="减数=被减数-差=800-450=350。"),
    dict(kp="乘除法各部分关系", unit=1, difficulty="normal",
         content="由算式 60÷15=4，下面哪个算式是正确的？",
         options=["A. 60÷4=15", "B. 60×4=15", "C. 15÷4=60", "D. 4÷15=60"],
         answer="A", explanation="被除数=商×除数，所以 60÷4=15。"),
    dict(kp="运算定律", unit=1, difficulty="easy",
         content="计算 25×7×4 时，先算 25×4，这里运用了（　）。",
         options=["A. 乘法交换律", "B. 乘法结合律", "C. 乘法分配律", "D. 加法交换律"],
         answer="A", explanation="交换了 7 和 4 的位置，运用乘法交换律使计算简便。"),
    dict(kp="运算定律", unit=1, difficulty="normal",
         content="56×101=56×100+56，这里运用了（　）。",
         options=["A. 乘法分配律", "B. 乘法交换律", "C. 乘法结合律", "D. 加法结合律"],
         answer="A", explanation="101=100+1，56×(100+1)=56×100+56×1，运用乘法分配律。"),
    dict(kp="简便运算", unit=1, difficulty="normal",
         content="用简便方法计算 385+199，结果是（　）。",
         options=["A. 584", "B. 585", "C. 574", "D. 594"],
         answer="A", explanation="199 接近 200，385+200-1=584。"),
    # U2 四面八方的学问（4）
    dict(kp="方向与位置", unit=2, difficulty="easy",
         content="清晨，乐乐面向太阳升起的方向，他的前面是（　）方。",
         options=["A. 东", "B. 西", "C. 南", "D. 北"],
         answer="A", explanation="太阳从东方升起，面向太阳即面向东方。"),
    dict(kp="方向与位置", unit=2, difficulty="normal",
         content="地图上通常按“上北、下南、左西、右东”定向。医院在学校的西北方向，那么学校在医院的（　）方向。",
         options=["A. 东南", "B. 西北", "C. 东北", "D. 西南"],
         answer="A", explanation="西北的相对方向是东南。"),
    dict(kp="方向与位置", unit=2, difficulty="normal",
         content="从学校出发，先向东走 200 米，再向北走 100 米到少年宫。少年宫在学校的（　）方向。",
         options=["A. 东北", "B. 西北", "C. 东南", "D. 西南"],
         answer="A", explanation="东和北之间是东北方向。"),
    dict(kp="方向与位置", unit=2, difficulty="hard",
         content="明明从家出发，先向西走到邮局，再向南走到学校。他放学沿原路返回时，应该（　）。",
         options=["A. 先向北走到邮局，再向东走到家", "B. 先向南走到邮局，再向西走到家",
                  "C. 先向东走到邮局，再向南走到家", "D. 先向北走到邮局，再向西走到家"],
         answer="A", explanation="原路返回时方向都要相反：向南变向北，向西变向东。"),
    # U3 整数的四则运算与应用题（6）
    dict(kp="四则混合运算", unit=3, difficulty="easy",
         content="算式 96÷8÷4×2 应该按照（　）顺序计算。",
         options=["A. 从左往右依次计算", "B. 先算 4×2", "C. 先算 8÷4", "D. 先算 96÷4"],
         answer="A", explanation="同级运算从左往右依次计算。"),
    dict(kp="四则混合运算", unit=3, difficulty="normal",
         content="算式 96÷(8÷4)×2 的第一步应计算（　）。",
         options=["A. 8÷4", "B. 96÷8", "C. 4×2", "D. 96÷4"],
         answer="A", explanation="有括号先算小括号里面的 8÷4。"),
    dict(kp="括号与运算顺序", unit=3, difficulty="normal",
         content="一个算式里既有小括号，又有中括号，要先算（　）。",
         options=["A. 小括号里面的", "B. 中括号里面的", "C. 括号外面的", "D. 随便先算哪个"],
         answer="A", explanation="先算小括号里的，再算中括号里的，最后算括号外面的。"),
    dict(kp="括号与运算顺序", unit=3, difficulty="hard",
         content="660÷[10×(8+14)] 的计算结果是（　）。",
         options=["A. 3", "B. 30", "C. 33", "D. 66"],
         answer="A", explanation="8+14=22，10×22=220，660÷220=3。"),
    dict(kp="整数应用题", unit=3, difficulty="normal",
         content="水果店运来苹果和梨共 120 箱，苹果比梨多 24 箱。运来苹果（　）箱。",
         options=["A. 72", "B. 48", "C. 96", "D. 60"],
         answer="A", explanation="和差问题：(120+24)÷2=72 箱。"),
    dict(kp="整数应用题", unit=3, difficulty="normal",
         content="商店有 48 箱苹果，苹果的箱数是梨的 3 倍。苹果比梨多（　）箱。",
         options=["A. 32", "B. 16", "C. 24", "D. 36"],
         answer="A", explanation="梨有 48÷3=16 箱，苹果比梨多 48-16=32 箱。"),
    # U4 大数的认识与改写（6）
    dict(kp="大数认识", unit=4, difficulty="easy",
         content="万级包含的数位是（　）。",
         options=["A. 万位、十万位、百万位、千万位", "B. 个位、十位、百位、千位",
                  "C. 亿位、十亿位、百亿位、千亿位", "D. 万位、十万位、百万位、亿位"],
         answer="A", explanation="万级从左到右（低到高）包含万位、十万位、百万位、千万位。"),
    dict(kp="大数认识", unit=4, difficulty="normal",
         content="一个数由 5 个百万、6 个万和 2 个千组成，这个数是（　）。",
         options=["A. 5062000", "B. 5620000", "C. 5060200", "D. 5602000"],
         answer="A", explanation="5000000+60000+2000=5062000。"),
    dict(kp="亿以内数的读写", unit=4, difficulty="normal",
         content="3080000 读作（　）。",
         options=["A. 三百零八万", "B. 三千零八十万", "C. 三百零八千", "D. 三千万零八万"],
         answer="A", explanation="万级是 308，读作三百零八万，个级全是 0 不读。"),
    dict(kp="大数的改写", unit=4, difficulty="easy",
         content="把 80000 改写成用“万”作单位的数是（　）。",
         options=["A. 8万", "B. 80万", "C. 8000万", "D. 0.8万"],
         answer="A", explanation="80000=8万，去掉个级的 4 个 0，添上“万”字。"),
    dict(kp="大数的改写", unit=4, difficulty="normal",
         content="把 2500000000 改写成用“亿”作单位的数是（　）。",
         options=["A. 25亿", "B. 250亿", "C. 2.5亿", "D. 2500亿"],
         answer="A", explanation="2500000000=25亿。"),
    dict(kp="近似数与四舍五入", unit=4, difficulty="normal",
         content="84975000 省略万位后面的尾数，约是（　）万。",
         options=["A. 8498", "B. 8497", "C. 8500", "D. 8490"],
         answer="A", explanation="千位上是 7，满 5 向前一位进 1：8497+1=8498 万。"),
    # U5 度量衡的故事（4）
    dict(kp="计量单位与换算", unit=5, difficulty="easy",
         content="1 千米 =（　）米。",
         options=["A. 1000", "B. 100", "C. 10000", "D. 10"],
         answer="A", explanation="千米与米之间的进率是 1000。"),
    dict(kp="计量单位与换算", unit=5, difficulty="normal",
         content="3 吨 50 千克 =（　）千克。",
         options=["A. 3050", "B. 350", "C. 3005", "D. 3500"],
         answer="A", explanation="3 吨=3000 千克，再加 50 千克是 3050 千克。"),
    dict(kp="计量单位与换算", unit=5, difficulty="normal",
         content="一瓶果汁 2 升，倒出 500 毫升后还剩（　）毫升。",
         options=["A. 1500", "B. 1000", "C. 2500", "D. 500"],
         answer="A", explanation="2 升=2000 毫升，2000-500=1500 毫升。"),
    dict(kp="计量单位与换算", unit=5, difficulty="hard",
         content="一头大象约重 4（　），括号里应填的单位是（　）。",
         options=["A. 吨", "B. 千克", "C. 克", "D. 米"],
         answer="A", explanation="大象体型庞大，用质量单位“吨”计量最合适。"),
    # U6 分数的初步认识（6）
    dict(kp="分数的初步认识", unit=6, difficulty="easy",
         content="把一个蛋糕平均分成 8 份，每份是它的（　）。",
         options=["A. 1/8", "B. 1/4", "C. 8/8", "D. 1/2"],
         answer="A", explanation="平均分成 8 份，每份就是这个蛋糕的八分之一。"),
    dict(kp="分数的初步认识", unit=6, difficulty="normal",
         content="3/8 里面有（　）个 1/8。",
         options=["A. 3", "B. 8", "C. 5", "D. 38"],
         answer="A", explanation="3/8 表示 3 个八分之一。"),
    dict(kp="分数的初步认识", unit=6, difficulty="normal",
         content="同样大的一个圆，涂色部分表示 2/5 和 4/5，比较大小：（　）。",
         options=["A. 2/5 < 4/5", "B. 2/5 > 4/5", "C. 2/5 = 4/5", "D. 无法比较"],
         answer="A", explanation="分母相同，分子大的分数大。"),
    dict(kp="分数的初步认识", unit=6, difficulty="normal",
         content="比较 1/2 和 1/5 的大小：（　）。",
         options=["A. 1/2 > 1/5", "B. 1/2 < 1/5", "C. 1/2 = 1/5", "D. 无法比较"],
         answer="A", explanation="分的份数越多，每一份反而越小，所以二分之一大于五分之一。"),
    dict(kp="同分母分数加减法", unit=6, difficulty="normal",
         content="2/9 + 5/9 =（　）。",
         options=["A. 7/9", "B. 7/18", "C. 3/9", "D. 1"],
         answer="A", explanation="同分母分数相加，分母不变，分子相加：2+5=7，得 7/9。"),
    dict(kp="同分母分数加减法", unit=6, difficulty="hard",
         content="1 - 3/7 =（　）。",
         options=["A. 4/7", "B. 3/7", "C. 4/6", "D. 1/7"],
         answer="A", explanation="1=7/7，7/7-3/7=4/7。"),
    # U7 线与角（6）
    dict(kp="线段、直线与射线", unit=7, difficulty="easy",
         content="下面哪种图形可以量出长度？（　）",
         options=["A. 线段", "B. 直线", "C. 射线", "D. 都可以"],
         answer="A", explanation="线段有两个端点、长度有限，可以度量；直线和射线无限长。"),
    dict(kp="线段、直线与射线", unit=7, difficulty="normal",
         content="射线有（　）个端点。",
         options=["A. 1", "B. 2", "C. 0", "D. 无数"],
         answer="A", explanation="射线只有一个端点，向一端无限延伸；直线没有端点。"),
    dict(kp="角的度量", unit=7, difficulty="easy",
         content="度量角的大小，要用（　）。",
         options=["A. 量角器", "B. 直尺", "C. 三角尺", "D. 圆规"],
         answer="A", explanation="测量角的工具是量角器，计量单位是“度”。"),
    dict(kp="角的度量", unit=7, difficulty="normal",
         content="角的大小与（　）有关。",
         options=["A. 两边叉开的大小", "B. 边的长短", "C. 边画得粗细", "D. 纸的大小"],
         answer="A", explanation="角的大小只与两边叉开的程度有关，与边的长短无关。"),
    dict(kp="角的分类与画角", unit=7, difficulty="easy",
         content="1 个平角 =（　）个直角。",
         options=["A. 2", "B. 1", "C. 3", "D. 4"],
         answer="A", explanation="平角 180°，直角 90°，180÷90=2。"),
    dict(kp="角的分类与画角", unit=7, difficulty="hard",
         content="用一副三角尺（30°、45°、60°、90°），能直接拼出下面哪个角度？（　）",
         options=["A. 75°", "B. 85°", "C. 100°", "D. 25°"],
         answer="A", explanation="30°+45°=75°，其他三个角都无法用三角尺上的角拼出。"),
    # U8 数学广场（2）
    dict(kp="等量代换", unit=8, difficulty="normal",
         content="已知 1 个西瓜 = 4 个苹果，1 个苹果 = 2 个橘子，那么 1 个西瓜 =（　）个橘子。",
         options=["A. 8", "B. 6", "C. 4", "D. 2"],
         answer="A", explanation="4 个苹果 × 每个 2 个橘子 = 8 个橘子。"),
    dict(kp="等量代换", unit=8, difficulty="hard",
         content="△+△=24，△+○=20，那么 ○=（　）。",
         options=["A. 8", "B. 12", "C. 6", "D. 10"],
         answer="A", explanation="△=24÷2=12，○=20-12=8。"),
    # U9 复习（1）
    dict(kp="简便运算", unit=9, difficulty="hard",
         content="计算 25×4×125×8，最简便的方法是（　）。",
         options=["A. (25×4)×(125×8)=100×1000=100000", "B. 从左往右依次计算",
                  "C. 先算 4×125，再算 25×8", "D. 先算 25×125，再算 4×8"],
         answer="A", explanation="运用乘法交换律和结合律，25×4=100、125×8=1000，凑整最简便。"),
]


async def seed_structure():
    engine = create_async_engine(settings.database_url, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        # 1. 教材版本（幂等：按 code 查）
        ver = (await db.execute(select(TextbookVersion).where(TextbookVersion.code == VERSION_CODE))).scalars().first()
        if ver:
            print(f"教材版本已存在：{ver.name} (id={ver.id})")
        else:
            ver = TextbookVersion(
                code=VERSION_CODE,
                name="沪教版（五四制）数学四年级上册（2026秋）",
                publisher="上海教育出版社",
                grade="四年级", subject="数学", term="A", is_active=True,
                description="2026秋季学期用书。目录依据真实教材：9 个单元，含运算律、大数、分数初步、线与角等。",
            )
            db.add(ver)
            await db.commit()
            await db.refresh(ver)
            print(f"创建教材版本：{ver.name} (id={ver.id})")

        # 2. 单元（幂等：按 version+code）
        unit_map = {}  # code -> id
        for u in UNITS:
            unit = (await db.execute(select(TextbookUnit).where(
                TextbookUnit.version_id == ver.id, TextbookUnit.code == u["code"]))).scalars().first()
            if unit:
                unit_map[u["code"]] = unit.id
                continue
            unit = TextbookUnit(version_id=ver.id, title_en=None, is_project=False,
                                sound=None, sound_examples=[], project_type=None, **u)
            db.add(unit)
            await db.flush()
            unit_map[u["code"]] = unit.id
        await db.commit()
        print(f"单元就绪：{len(unit_map)} 个 {unit_map}")

        # 3. 知识点（幂等：按 subject+name）
        kp_ids = {}  # name -> id
        existing = (await db.execute(select(KnowledgePoint).where(KnowledgePoint.subject == "数学"))).scalars().all()
        for kp in existing:
            kp_ids[kp.name] = kp.id
        created = 0
        for name, cat, desc in NEW_KPS:
            if name in kp_ids:
                continue
            kp = KnowledgePoint(subject="数学", name=name, category=cat,
                                description=desc, grade_level="四年级")
            db.add(kp)
            await db.flush()
            kp_ids[name] = kp.id
            created += 1
        await db.commit()
        print(f"知识点：新增 {created} 个，可复用共 {len([k for k,_,_ in NEW_KPS])} 个")

        # 4. 题库（幂等：按 title）
        bank = (await db.execute(select(QuestionBank).where(QuestionBank.title == BANK_TITLE))).scalars().first()
        if bank:
            print(f"题库已存在：{bank.title} (id={bank.id})")
            old = (await db.execute(select(Question).where(Question.bank_id == bank.id))).scalars().all()
            for q in old:
                await db.delete(q)
            await db.flush()
        else:
            bank = QuestionBank(
                grade="四年级", subject="数学", title=BANK_TITLE,
                description="依据《沪教版（五四制）数学四年级上册（2026秋）》编写，41 道单选题覆盖全部 9 个单元核心知识点。",
                is_active=True,
            )
            db.add(bank)
            await db.commit()
            await db.refresh(bank)
            print(f"创建题库：{bank.title} (id={bank.id})")

        # 5. 题目 + 关联
        n_q = 0
        for qd in QUESTIONS:
            q = Question(
                bank_id=bank.id,
                knowledge_point=qd["kp"],
                question_type="single_choice",
                difficulty=qd["difficulty"],
                content=qd["content"],
                options=qd["options"],
                correct_answer=qd["answer"],
                explanation=qd["explanation"],
            )
            db.add(q)
            await db.flush()
            n_q += 1
            # 题目↔知识点
            if qd["kp"] in kp_ids:
                db.add(QuestionKnowledgePoint(question_id=q.id, knowledge_point_id=kp_ids[qd["kp"]]))
            else:
                print(f"  ! 知识点缺失：{qd['kp']}")
            # 题目↔单元
            db.add(QuestionUnit(question_id=q.id, unit_id=unit_map[f"U{qd['unit']}"], relevance="primary"))
        await db.commit()
        print(f"导入题目 {n_q} 道，并完成知识点/单元关联")
    await engine.dispose()


def http(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def simulate_preview():
    """模拟大宝暑期预习：6 场练习，控制对错形成真实的进度梯度"""
    # 找到新题库
    banks = http("GET", "/question-banks")
    bank = next(b for b in banks if b["title"] == BANK_TITLE)
    bid = bank["id"]
    print(f"题库 id={bid}")

    # 每场练习：(知识点过滤, 题数, 答错的题索引集合)
    sessions = [
        (["加减法各部分关系", "乘除法各部分关系", "运算定律"], 5, set()),        # U1 全对 → 精熟
        (["方向与位置"], 4, {1}),                                              # U2 错1 → 进行中
        (["四则混合运算", "括号与运算顺序", "整数应用题"], 6, {3}),             # U3 错1 → 进行中
        (["大数认识", "亿以内数的读写", "大数的改写", "近似数与四舍五入"], 4, {0}),  # U4 错1 → 进行中
        (["计量单位与换算"], 2, {0}),                                          # U5 错1 → 进行中
        (["分数的初步认识", "同分母分数加减法"], 2, set()),                     # U6 全对 → 起步
    ]
    for i, (kps, count, wrong_idx) in enumerate(sessions, 1):
        ex = http("POST", "/question-banks/exercises/start",
                  {"child_id": CHILD_ID, "bank_id": bid, "count": count,
                   "knowledge_points": kps, "mode": "manual"})
        answers = []
        for idx, q in enumerate(ex["questions"]):
            if idx in wrong_idx:
                # 答一个错误选项
                wrong = next(l for l in "ABCDEF"
                             if any(o.startswith(l + ".") for o in q["options"]) and l != q["correct_answer"])
                answers.append({"question_id": q["id"], "selected": wrong})
            else:
                answers.append({"question_id": q["id"], "selected": q["correct_answer"]})
        sub = http("POST", f"/question-banks/exercises/{ex['id']}/submit", {"answers": answers})
        print(f"  练习{i}（{'+'.join(k[:6] for k in kps[:2])}… 共{len(answers)}题）："
              f"得分 {sub['score']}，对 {sub['correct_count']}/{sub['total_questions']}")
    print("暑期预习练习模拟完成")


async def main():
    await seed_structure()
    try:
        simulate_preview()
    except Exception as e:
        print(f"练习模拟失败（结构数据已写入）：{e}")


if __name__ == "__main__":
    asyncio.run(main())
