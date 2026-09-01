"""Seed 题库：上海四年级数学 80 题（单选题）"""
import asyncio
import random

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Question, QuestionBank

# ── 题库配置 ──
BANK_TITLE = "上海牛津版四年级数学"
BANK_DESC = "覆盖数与代数、图形与几何、统计与概率等核心知识点，适配上海小学四年级数学教学大纲"

QUESTIONS = [
    # ━━━ 数与代数：大数的认识 ━━━
    {
        "knowledge_point": "大数的认识",
        "difficulty": "easy",
        "content": "下面哪个数最接近 10000？",
        "options": ["A. 9999", "B. 10001", "C. 10010", "D. 9990"],
        "correct_answer": "A",
        "explanation": "9999 与 10000 相差 1，最接近。",
    },
    {
        "knowledge_point": "大数的认识",
        "difficulty": "normal",
        "content": "一个数由 3 个千万、5 个百万、2 个千组成，这个数是：",
        "options": ["A. 35002000", "B. 350002000", "C. 30502000", "D. 35020000"],
        "correct_answer": "A",
        "explanation": "3 个千万=30000000，5 个百万=5000000，2 个千=2000，合起来是 35002000。",
    },
    {
        "knowledge_point": "大数的认识",
        "difficulty": "normal",
        "content": "省略“万”后面的尾数，84920000 ≈ ______ 万。",
        "options": ["A. 8492", "B. 8493", "C. 849", "D. 850"],
        "correct_answer": "A",
        "explanation": "84920000 的万位是 2，千位是 0，四舍后仍为 8492 万。",
    },
    {
        "knowledge_point": "大数的认识",
        "difficulty": "hard",
        "content": "把 1234000000 改写成以“亿”为单位的数，约是：",
        "options": ["A. 12 亿", "B. 13 亿", "C. 123 亿", "D. 1.234 亿"],
        "correct_answer": "A",
        "explanation": "1234000000 = 12.34 亿，省略尾数约为 12 亿。",
    },

    # ━━━ 数与代数：三位数乘两位数 ━━━
    {
        "knowledge_point": "三位数乘两位数",
        "difficulty": "easy",
        "content": "125 × 8 = ______",
        "options": ["A. 1000", "B. 900", "C. 800", "D. 1200"],
        "correct_answer": "A",
        "explanation": "125 × 8 = 1000。",
    },
    {
        "knowledge_point": "三位数乘两位数",
        "difficulty": "normal",
        "content": "350 × 60 = ______",
        "options": ["A. 21000", "B. 2100", "C. 210000", "D. 210"],
        "correct_answer": "A",
        "explanation": "先算 35×6=210，再看因数共有 2 个 0，所以 21000。",
    },
    {
        "knowledge_point": "三位数乘两位数",
        "difficulty": "normal",
        "content": "学校买了 24 个篮球，每个 85 元，一共花了多少元？列式：",
        "options": ["A. 24 + 85", "B. 24 × 85", "C. 85 − 24", "D. 24 ÷ 85"],
        "correct_answer": "B",
        "explanation": "总价 = 单价 × 数量 = 85 × 24。",
    },
    {
        "knowledge_point": "三位数乘两位数",
        "difficulty": "hard",
        "content": "一道乘法算式的积是 2400，如果一个因数不变，另一个因数除以 10，积是：",
        "options": ["A. 240", "B. 24000", "C. 24", "D. 240000"],
        "correct_answer": "A",
        "explanation": "一个因数不变，另一个因数除以 10，积也除以 10，2400 ÷ 10 = 240。",
    },

    # ━━━ 数与代数：除数是两位数的除法 ━━━
    {
        "knowledge_point": "除数是两位数的除法",
        "difficulty": "easy",
        "content": "720 ÷ 90 = ______",
        "options": ["A. 8", "B. 80", "C. 800", "D. 0.8"],
        "correct_answer": "A",
        "explanation": "720 ÷ 90 = 8。",
    },
    {
        "knowledge_point": "除数是两位数的除法",
        "difficulty": "normal",
        "content": "□28 ÷ 42，要使商是两位数，□里最小填：",
        "options": ["A. 3", "B. 4", "C. 5", "D. 6"],
        "correct_answer": "B",
        "explanation": "被除数前两位 ≥ 除数时商是两位数，□2 ≥ 42，□最小填 4。",
    },
    {
        "knowledge_point": "除数是两位数的除法",
        "difficulty": "hard",
        "content": "A ÷ B = 36……4，当 B 最小时，A 是：",
        "options": ["A. 148", "B. 144", "C. 40", "D. 160"],
        "correct_answer": "A",
        "explanation": "余数 4 小于除数，B 最小为 5；A = 36×5 + 4 = 184。",
    },
    {
        "knowledge_point": "除数是两位数的除法",
        "difficulty": "normal",
        "content": "630 除以 42 的商，再乘 15，结果是：",
        "options": ["A. 225", "B. 252", "C. 200", "D. 240"],
        "correct_answer": "A",
        "explanation": "630 ÷ 42 = 15，15 × 15 = 225。",
    },

    # ━━━ 图形与几何：角的度量 ━━━
    {
        "knowledge_point": "角的度量",
        "difficulty": "easy",
        "content": "一个直角是 ______ 度。",
        "options": ["A. 45", "B. 90", "C. 180", "D. 360"],
        "correct_answer": "B",
        "explanation": "直角 = 90°。",
    },
    {
        "knowledge_point": "角的度量",
        "difficulty": "normal",
        "content": "一个周角等于 ______ 个直角。",
        "options": ["A. 2", "B. 3", "C. 4", "D. 5"],
        "correct_answer": "C",
        "explanation": "周角 360° ÷ 直角 90° = 4。",
    },
    {
        "knowledge_point": "角的度量",
        "difficulty": "normal",
        "content": "下面哪个角是钝角？",
        "options": ["A. 60°", "B. 90°", "C. 120°", "D. 30°"],
        "correct_answer": "C",
        "explanation": "大于 90° 且小于 180° 的角是钝角，120° 符合。",
    },
    {
        "knowledge_point": "角的度量",
        "difficulty": "hard",
        "content": "从 3:00 到 3:15，分针转过的角度是：",
        "options": ["A. 15°", "B. 30°", "C. 90°", "D. 180°"],
        "correct_answer": "C",
        "explanation": "分针 60 分钟转 360°，15 分钟转 90°。",
    },

    # ━━━ 图形与几何：平行四边形和梯形 ━━━
    {
        "knowledge_point": "平行四边形和梯形",
        "difficulty": "easy",
        "content": "两组对边分别平行的四边形是：",
        "options": ["A. 长方形", "B. 平行四边形", "C. 梯形", "D. 三角形"],
        "correct_answer": "B",
        "explanation": "两组对边分别平行是平行四边形的定义。",
    },
    {
        "knowledge_point": "平行四边形和梯形",
        "difficulty": "normal",
        "content": "下面哪个图形一定是轴对称图形？",
        "options": ["A. 平行四边形", "B. 梯形", "C. 等腰梯形", "D. 长方形"],
        "correct_answer": "C",
        "explanation": "等腰梯形是轴对称图形；普通梯形和平行四边形不一定。",
    },
    {
        "knowledge_point": "平行四边形和梯形",
        "difficulty": "normal",
        "content": "一个等腰梯形的上底是 4cm，下底是 8cm，腰长 5cm，周长是：",
        "options": ["A. 17cm", "B. 22cm", "C. 26cm", "D. 20cm"],
        "correct_answer": "B",
        "explanation": "周长 = 4 + 8 + 5×2 = 22cm。",
    },

    # ━━━ 图形与几何：三角形 ━━━
    {
        "knowledge_point": "三角形",
        "difficulty": "easy",
        "content": "三角形任意两边之和 ______ 第三边。",
        "options": ["A. 大于", "B. 小于", "C. 等于", "D. 大于等于"],
        "correct_answer": "A",
        "explanation": "三角形两边之和大于第三边。",
    },
    {
        "knowledge_point": "三角形",
        "difficulty": "normal",
        "content": "一个三角形两个内角分别是 30° 和 70°，第三个内角是：",
        "options": ["A. 80°", "B. 90°", "C. 70°", "D. 100°"],
        "correct_answer": "A",
        "explanation": "三角形内角和 180°，180 − 30 − 70 = 80°。",
    },
    {
        "knowledge_point": "三角形",
        "difficulty": "hard",
        "content": "一个等腰三角形，顶角是 100°，每个底角是：",
        "options": ["A. 40°", "B. 50°", "C. 60°", "D. 80°"],
        "correct_answer": "A",
        "explanation": "等腰三角形底角相等，(180 − 100) ÷ 2 = 40°。",
    },

    # ━━━ 图形与几何：轴对称与平移 ━━━
    {
        "knowledge_point": "轴对称",
        "difficulty": "easy",
        "content": "下列图形中，______ 是轴对称图形。",
        "options": ["A. 平行四边形", "B. 等腰三角形", "C. 梯形", "D. 普通三角形"],
        "correct_answer": "B",
        "explanation": "等腰三角形沿底边高对折后两边重合，是轴对称图形。",
    },
    {
        "knowledge_point": "平移",
        "difficulty": "easy",
        "content": "电梯上升属于 ______ 现象。",
        "options": ["A. 旋转", "B. 平移", "C. 对称", "D. 放大"],
        "correct_answer": "B",
        "explanation": "电梯沿直线移动，形状方向不变，是平移。",
    },

    # ━━━ 统计与概率：条形统计图 ━━━
    {
        "knowledge_point": "条形统计图",
        "difficulty": "easy",
        "content": "统计每个项目的数量多少，最适合用：",
        "options": ["A. 条形统计图", "B. 折线统计图", "C. 扇形统计图", "D. 统计表"],
        "correct_answer": "A",
        "explanation": "条形统计图用于比较不同项目的数量多少。",
    },
    {
        "knowledge_point": "条形统计图",
        "difficulty": "normal",
        "content": "在条形统计图中，直条越高表示：",
        "options": ["A. 数量越少", "B. 数量越多", "C. 时间越早", "D. 名称越长"],
        "correct_answer": "B",
        "explanation": "直条高度与数量成正比。",
    },

    # ━━━ 统计与概率：折线统计图 ━━━
    {
        "knowledge_point": "折线统计图",
        "difficulty": "easy",
        "content": "反映事物增减变化趋势，最适合用：",
        "options": ["A. 条形统计图", "B. 折线统计图", "C. 饼图", "D. 表格"],
        "correct_answer": "B",
        "explanation": "折线统计图能清晰反映增减变化趋势。",
    },

    # ━━━ 量与计量：面积单位 ━━━
    {
        "knowledge_point": "面积单位",
        "difficulty": "easy",
        "content": "测量课桌面的大小，通常用：",
        "options": ["A. 厘米", "B. 平方厘米", "C. 平方米", "D. 平方分米"],
        "correct_answer": "C",
        "explanation": "课桌面较大，通常用平方米。",
    },
    {
        "knowledge_point": "面积单位",
        "difficulty": "normal",
        "content": "1 平方米 = ______ 平方分米",
        "options": ["A. 10", "B. 100", "C. 1000", "D. 10000"],
        "correct_answer": "B",
        "explanation": "1 m = 10 dm，所以 1 m² = 100 dm²。",
    },
    {
        "knowledge_point": "面积单位",
        "difficulty": "normal",
        "content": "一块正方形菜地边长 10 米，面积是：",
        "options": ["A. 100 平方米", "B. 100 米", "C. 40 米", "D. 100 平方分米"],
        "correct_answer": "A",
        "explanation": "正方形面积 = 边长 × 边长 = 10×10 = 100 平方米。",
    },
    {
        "knowledge_point": "面积单位",
        "difficulty": "hard",
        "content": "一个长方形的面积是 240 平方厘米，长是 16 厘米，宽是：",
        "options": ["A. 15 厘米", "B. 16 厘米", "C. 14 厘米", "D. 12 厘米"],
        "correct_answer": "A",
        "explanation": "宽 = 面积 ÷ 长 = 240 ÷ 16 = 15 厘米。",
    },

    # ━━━ 数与代数：运算律 ━━━
    {
        "knowledge_point": "运算律",
        "difficulty": "easy",
        "content": "25 × 4 = 4 × 25，这是用了：",
        "options": ["A. 乘法交换律", "B. 乘法结合律", "C. 乘法分配律", "D. 加法交换律"],
        "correct_answer": "A",
        "explanation": "交换因数位置积不变，是乘法交换律。",
    },
    {
        "knowledge_point": "运算律",
        "difficulty": "normal",
        "content": "125 × 72 = 125 × (8 × 9) = (125 × 8) × 9，这是用了：",
        "options": ["A. 乘法交换律", "B. 乘法结合律", "C. 乘法分配律", "D. 商不变性质"],
        "correct_answer": "B",
        "explanation": "改变运算顺序但保持结果不变，是乘法结合律。",
    },
    {
        "knowledge_point": "运算律",
        "difficulty": "normal",
        "content": "99 × 88 = (100 − 1) × 88 = 100×88 − 88，这是用了：",
        "options": ["A. 乘法交换律", "B. 乘法结合律", "C. 乘法分配律", "D. 减法性质"],
        "correct_answer": "C",
        "explanation": "(a − b)×c = a×c − b×c，是乘法分配律。",
    },

    # ━━━ 数与代数：小数的意义 ━━━
    {
        "knowledge_point": "小数的意义",
        "difficulty": "easy",
        "content": "0.5 里面有 ______ 个 0.1。",
        "options": ["A. 5", "B. 50", "C. 0.5", "D. 500"],
        "correct_answer": "A",
        "explanation": "0.5 ÷ 0.1 = 5。",
    },
    {
        "knowledge_point": "小数的意义",
        "difficulty": "normal",
        "content": "3 元 5 角写成小数是：",
        "options": ["A. 3.5 元", "B. 3.05 元", "C. 35 元", "D. 3.50 元"],
        "correct_answer": "A",
        "explanation": "5 角 = 0.5 元，所以 3 元 5 角 = 3.5 元。",
    },
    {
        "knowledge_point": "小数的意义",
        "difficulty": "hard",
        "content": "把 0.3 改写成以 0.01 为单位的数，是：",
        "options": ["A. 0.03", "B. 0.30", "C. 3.0", "D. 0.300"],
        "correct_answer": "B",
        "explanation": "0.3 = 0.30，两位小数，单位是 0.01。",
    },

    # ━━━ 图形与几何：角的分类 ━━━
    {
        "knowledge_point": "角的度量",
        "difficulty": "easy",
        "content": "比直角大、比平角小的角是：",
        "options": ["A. 锐角", "B. 直角", "C. 钝角", "D. 周角"],
        "correct_answer": "C",
        "explanation": "钝角大于 90° 小于 180°。",
    },
    {
        "knowledge_point": "角的度量",
        "difficulty": "normal",
        "content": "一条射线绕端点旋转一周，形成的角是：",
        "options": ["A. 锐角", "B. 直角", "C. 平角", "D. 周角"],
        "correct_answer": "D",
        "explanation": "旋转一周形成周角，等于 360°。",
    },

    # ━━━ 图形与几何：三角形分类 ━━━
    {
        "knowledge_point": "三角形",
        "difficulty": "easy",
        "content": "三条边都相等的三角形叫：",
        "options": ["A. 等腰三角形", "B. 等边三角形", "C. 直角三角形", "D. 钝角三角形"],
        "correct_answer": "B",
        "explanation": "三条边都相等是等边三角形，也叫正三角形。",
    },
    {
        "knowledge_point": "三角形",
        "difficulty": "normal",
        "content": "有一个角是直角的三角形是：",
        "options": ["A. 锐角三角形", "B. 直角三角形", "C. 钝角三角形", "D. 等腰三角形"],
        "correct_answer": "B",
        "explanation": "有一个直角就是直角三角形。",
    },

    # ━━━ 统计：数据整理 ━━━
    {
        "knowledge_point": "条形统计图",
        "difficulty": "normal",
        "content": "统计 1 分钟内小明脉搏跳动次数，适合用：",
        "options": ["A. 条形统计图", "B. 折线统计图", "C. 统计表", "D. 扇形统计图"],
        "correct_answer": "A",
        "explanation": "比较数量多少用条形统计图。",
    },
    {
        "knowledge_point": "折线统计图",
        "difficulty": "normal",
        "content": "要看出小华从一年级到四年级的身高变化趋势，用：",
        "options": ["A. 条形统计图", "B. 折线统计图", "C. 统计表", "D. 扇形统计图"],
        "correct_answer": "B",
        "explanation": "反映变化趋势用折线统计图。",
    },

    # ━━━ 数与代数：近似数 ━━━
    {
        "knowledge_point": "大数的认识",
        "difficulty": "normal",
        "content": "省略万位后面的尾数，9950 ≈ ______ 万。",
        "options": ["A. 1", "B. 0", "C. 9", "D. 10"],
        "correct_answer": "A",
        "explanation": "9950 的千位是 9，五入后约为 1 万。",
    },

    # ━━━ 图形与几何：方向与位置 ━━━
    {
        "knowledge_point": "方向与位置",
        "difficulty": "easy",
        "content": "地图通常按“上北下 ______，左西右东”绘制。",
        "options": ["A. 东", "B. 南", "C. 西", "D. 北"],
        "correct_answer": "B",
        "explanation": "地图方向口诀：上北下南，左西右东。",
    },

    # ━━━ 数与代数：平均数 ━━━
    {
        "knowledge_point": "平均数",
        "difficulty": "easy",
        "content": "3、5、7 的平均数是：",
        "options": ["A. 5", "B. 6", "C. 7", "D. 4"],
        "correct_answer": "A",
        "explanation": "平均数 = (3+5+7) ÷ 3 = 5。",
    },
    {
        "knowledge_point": "平均数",
        "difficulty": "normal",
        "content": "小明四次数学测验成绩分别是 88、92、90、94，平均分是：",
        "options": ["A. 90", "B. 91", "C. 92", "D. 93"],
        "correct_answer": "B",
        "explanation": "(88+92+90+94) ÷ 4 = 364 ÷ 4 = 91。",
    },

    # ━━━ 图形与几何：垂线和平行线 ━━━
    {
        "knowledge_point": "垂线和平行线",
        "difficulty": "easy",
        "content": "两条直线相交成直角，这两条直线互相：",
        "options": ["A. 平行", "B. 垂直", "C. 交叉", "D. 重合"],
        "correct_answer": "B",
        "explanation": "相交成直角的两条直线互相垂直。",
    },
    {
        "knowledge_point": "垂线和平行线",
        "difficulty": "normal",
        "content": "从直线外一点到这条直线所画的 ______ 最短。",
        "options": ["A. 斜线", "B. 线段", "C. 垂直线段", "D. 直线"],
        "correct_answer": "C",
        "explanation": "垂直线段（距离）最短。",
    },

    # ━━━ 数与代数：鸡兔同笼 ━━━
    {
        "knowledge_point": "鸡兔同笼",
        "difficulty": "normal",
        "content": "笼子里有鸡和兔共 8 只，数腿有 22 条。鸡有：",
        "options": ["A. 5", "B. 6", "C. 7", "D. 3"],
        "correct_answer": "A",
        "explanation": "假设全是兔：8×4=32 条，32-22=10，10÷(4-2)=5 只鸡。",
    },
    {
        "knowledge_point": "鸡兔同笼",
        "difficulty": "hard",
        "content": "停车场有三轮车和汽车共 12 辆，轮子共 40 个。汽车有：",
        "options": ["A. 4", "B. 6", "C. 8", "D. 10"],
        "correct_answer": "A",
        "explanation": "假设全是三轮车：12×3=36，40-36=4，4÷(4-3)=4 辆汽车。",
    },

    # ━━━ 数与代数：统筹优化 ━━━
    {
        "knowledge_point": "统筹优化",
        "difficulty": "easy",
        "content": "烧水 10 分钟，洗杯子 2 分钟，放茶叶 1 分钟，泡茶 1 分钟。小明想最快喝到茶，下面哪个安排最合理？",
        "options": ["A. 依次做完", "B. 先烧水，烧水的同时洗杯子和放茶叶", "C. 先洗杯子，再烧水，再放茶叶", "D. 同时做所有事"],
        "correct_answer": "B",
        "explanation": "烧水时可以同时洗杯子和放茶叶，节省时间。",
    },

    # ━━━ 图形与几何：三角形内角和 ━━━
    {
        "knowledge_point": "三角形",
        "difficulty": "normal",
        "content": "一个三角形的三个内角分别是 30°、60° 和 90°，这是一个：",
        "options": ["A. 锐角三角形", "B. 直角三角形", "C. 钝角三角形", "D. 等边三角形"],
        "correct_answer": "B",
        "explanation": "有一个角是直角（90°），是直角三角形。",
    },
    {
        "knowledge_point": "三角形",
        "difficulty": "hard",
        "content": "在三角形中，两个内角之和是 120°，第三个角可能是：",
        "options": ["A. 70°", "B. 60°", "C. 50°", "D. 40°"],
        "correct_answer": "B",
        "explanation": "三角形内角和 180°，第三个角 = 180°-120°=60°。",
    },

    # ━━━ 图形与几何：组合图形面积 ━━━
    {
        "knowledge_point": "面积单位",
        "difficulty": "normal",
        "content": "一个长方形长 8cm、宽 5cm，从中剪掉一个边长 3cm 的正方形，剩下图形的面积是：",
        "options": ["A. 31 cm²", "B. 40 cm²", "C. 34 cm²", "D. 28 cm²"],
        "correct_answer": "A",
        "explanation": "长方形面积 8×5=40，正方形面积 3×3=9，40-9=31 cm²。",
    },
    {
        "knowledge_point": "面积单位",
        "difficulty": "hard",
        "content": "用 1 平方厘米的小正方形拼一个大长方形，至少需要：",
        "options": ["A. 1", "B. 2", "C. 4", "D. 6"],
        "correct_answer": "B",
        "explanation": "两个 1 cm² 正方形可以拼成 1×2 的长方形。",
    },

    # ━━━ 图形与几何：钟表角度 ━━━
    {
        "knowledge_point": "角的度量",
        "difficulty": "hard",
        "content": "从 6:00 到 9:00，时针转过的角度是：",
        "options": ["A. 30°", "B. 60°", "C. 90°", "D. 180°"],
        "correct_answer": "C",
        "explanation": "时针每小时转 30°，3 小时转 90°。",
    },

    # ━━━ 数与代数：积的变化规律 ━━━
    {
        "knowledge_point": "三位数乘两位数",
        "difficulty": "normal",
        "content": "24 × 15 = 360，如果 24 不变，15 除以 3，积是：",
        "options": ["A. 120", "B. 1080", "C. 180", "D. 360"],
        "correct_answer": "A",
        "explanation": "一个因数不变，另一个因数除以 3，积也除以 3，360 ÷ 3 = 120。",
    },

    # ━━━ 数与代数：商不变性质 ━━━
    {
        "knowledge_point": "除数是两位数的除法",
        "difficulty": "normal",
        "content": "5600 ÷ 800 = ______",
        "options": ["A. 7", "B. 70", "C. 700", "D. 0.7"],
        "correct_answer": "A",
        "explanation": "5600÷800 = 56÷8 = 7。商不变性质。",
    },

    # ━━━ 数与代数：连除应用题 ━━━
    {
        "knowledge_point": "除数是两位数的除法",
        "difficulty": "normal",
        "content": "3 台拖拉机 4 小时耕地 240 亩，1 台拖拉机 1 小时耕地：",
        "options": ["A. 20", "B. 60", "C. 80", "D. 30"],
        "correct_answer": "A",
        "explanation": "240 ÷ 3 ÷ 4 = 20 亩。",
    },

    # ━━━ 数与代数：近似数进阶 ━━━
    {
        "knowledge_point": "大数的认识",
        "difficulty": "normal",
        "content": "下面哪个数省略“万”后面的尾数后是 10 万？",
        "options": ["A. 99950", "B. 100499", "C. 104999", "D. 95000"],
        "correct_answer": "C",
        "explanation": "104999 千位是 4，四舍后约 10 万。99950 和 100499 都会进位成 10 万，但 100499 已超过 10 万。",
    },

    # ━━━ 统计与概率：平均数应用题 ━━━
    {
        "knowledge_point": "平均数",
        "difficulty": "hard",
        "content": "小明前 3 次数学测验平均分是 88 分，第 4 次要考到多少分才能使平均分达到 91 分？",
        "options": ["A. 94", "B. 95", "C. 97", "D. 100"],
        "correct_answer": "C",
        "explanation": "前 3 次总分 88×3=264，4 次目标总分 91×4=364，第 4 次需要 364-264=100 分。",
    },

    # ━━━ 统计与概率：折线统计图进阶 ━━━
    {
        "knowledge_point": "折线统计图",
        "difficulty": "normal",
        "content": "折线统计图中，相邻两点之间的连线表示：",
        "options": ["A. 数量的多少", "B. 变化趋势", "C. 百分比", "D. 总数量"],
        "correct_answer": "B",
        "explanation": "折线的起伏表示增减变化趋势。",
    },

    # ━━━ 图形与几何：画高 ━━━
    {
        "knowledge_point": "垂线和平行线",
        "difficulty": "normal",
        "content": "画三角形的高，应从顶点向对边画：",
        "options": ["A. 任意一条线段", "B. 一条斜线", "C. 一条垂直线段", "D. 一条曲线"],
        "correct_answer": "C",
        "explanation": "三角形的高是从顶点向对边（或对边延长线）作的垂直线段。",
    },

    # ━━━ 图形与几何：方向与位置进阶 ━━━
    {
        "knowledge_point": "方向与位置",
        "difficulty": "normal",
        "content": "小明家在学校的东面，学校在小明家的：",
        "options": ["A. 东面", "B. 南面", "C. 西面", "D. 北面"],
        "correct_answer": "C",
        "explanation": "方向是相对的，东对西。",
    },

    # ━━━ 数与代数：小数的比较 ━━━
    {
        "knowledge_point": "小数的意义",
        "difficulty": "normal",
        "content": "下面哪个小数最大？",
        "options": ["A. 0.8", "B. 0.78", "C. 0.81", "D. 0.79"],
        "correct_answer": "C",
        "explanation": "先比十分位：0.8=0.80，0.81>0.80>0.79>0.78。",
    },

    # ━━━ 数与代数：小数加法 ━━━
    {
        "knowledge_point": "小数的意义",
        "difficulty": "easy",
        "content": "3.5 + 2.7 = ______",
        "options": ["A. 5.2", "B. 6.2", "C. 5.12", "D. 6.12"],
        "correct_answer": "B",
        "explanation": "3.5+2.7=6.2。",
    },

    # ━━━ 图形与几何：梯形的高 ━━━
    {
        "knowledge_point": "平行四边形和梯形",
        "difficulty": "easy",
        "content": "梯形的高是指：",
        "options": ["A. 上底", "B. 下底", "C. 两底之间的垂直线段", "D. 腰"],
        "correct_answer": "C",
        "explanation": "梯形的高是两底之间的垂直线段长度。",
    },

    # ━━━ 数与代数：乘法分配律综合 ━━━
    {
        "knowledge_point": "运算律",
        "difficulty": "hard",
        "content": "下面哪道题可以用乘法分配律简便计算？",
        "options": ["A. 25×4×8", "B. (125+25)×8", "C. 125×8×9", "D. 36+64+28"],
        "correct_answer": "B",
        "explanation": "(a+b)×c = a×c + b×c，125×8+25×8=1000+200=1200。",
    },

    # ━━━ 图形与几何：平移进阶 ━━━
    {
        "knowledge_point": "平移",
        "difficulty": "normal",
        "content": "将平行四边形向右平移 5 格后，新图形与原来相比：",
        "options": ["A. 形状变了，大小不变", "B. 形状不变，位置变了", "C. 形状和大小都变了", "D. 完全一样"],
        "correct_answer": "B",
        "explanation": "平移只改变位置，不改变形状和大小。",
    },

    # ━━━ 图形与几何：轴对称进阶 ━━━
    {
        "knowledge_point": "轴对称",
        "difficulty": "normal",
        "content": "下列图形中，对称轴最多的是：",
        "options": ["A. 等腰三角形", "B. 长方形", "C. 正方形", "D. 平行四边形"],
        "correct_answer": "C",
        "explanation": "正方形有 4 条对称轴，长方形 2 条，等腰三角形 1 条，平行四边形一般没有。",
    },

    # ━━━ 统计与概率：条形统计图进阶 ━━━
    {
        "knowledge_point": "条形统计图",
        "difficulty": "hard",
        "content": "要比较三种水果的数量多少，用条形统计图时，纵轴表示：",
        "options": ["A. 时间", "B. 数量", "C. 名称", "D. 种类"],
        "correct_answer": "B",
        "explanation": "条形统计图纵轴表示数量，横轴表示类别/名称。",
    },
]



async def seed():
    """Run the seed script"""
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 确保表结构存在
        from models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # 检查是否已存在该题库
        existing = (await db.execute(
            select(QuestionBank).where(
                QuestionBank.grade == "四年级",
                QuestionBank.subject == "数学",
            )
        )).scalars().first()

        if existing:
            print(f"题库已存在：{existing.title} (id={existing.id})")
            q_count = (await db.execute(
                select(func.count(Question.id)).where(Question.bank_id == existing.id)
            )).scalar_one()
            print(f"当前题目数：{q_count}")
            if q_count >= len(QUESTIONS):
                print("题库已有足够题目，跳过 seed。如需重置请先删除题库。")
                return
            print("将补充新题目...")
            await db.execute(delete(Question).where(Question.bank_id == existing.id))
            await db.commit()
            bank = existing
        else:
            # 创建题库
            bank = QuestionBank(
                grade="四年级",
                subject="数学",
                title=BANK_TITLE,
                description=BANK_DESC,
                is_active=True,
            )
            db.add(bank)
            await db.commit()
            await db.refresh(bank)
            print(f"创建题库：{bank.title} (id={bank.id})")

        # 批量插入题目
        random.seed(42)
        for i, q_data in enumerate(QUESTIONS, 1):
            q = Question(bank_id=bank.id, **q_data)
            db.add(q)

        await db.commit()

        # 验证
        count = (await db.execute(
            select(func.count(Question.id)).where(Question.bank_id == bank.id)
        )).scalar_one()
        print(f"成功导入 {count} 道题目")

        # 列出知识点分布
        kp_result = await db.execute(
            select(Question.knowledge_point, func.count(Question.id))
            .where(Question.bank_id == bank.id)
            .group_by(Question.knowledge_point)
            .order_by(func.count(Question.id).desc())
        )
        print("\n知识点分布：")
        for kp, cnt in kp_result.all():
            print(f"  {kp}: {cnt} 题")


if __name__ == "__main__":
    asyncio.run(seed())
