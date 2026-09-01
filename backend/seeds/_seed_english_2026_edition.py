"""Seed 题库：沪教版四年级英语 200 题（2025-2026 学年新教材）
  - 覆盖 4A 上册 M1-M4 + 4B 下册 M5-M8（新版沪教版）
  - 题型：单选题 + 判断题
  - 每题含 knowledge_point（Module 标签）、difficulty、content、options、correct_answer、explanation
"""
import asyncio
import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Question, QuestionBank

# ── 题库配置 ──
BANK_TITLE = "沪教版四年级英语（2025-2026 新版）"
BANK_DESC = (
    "覆盖 4A 上册 M1-M4 + 4B 下册 M5-M8，共 8 个 Module，"
    "对应新版沪教版《义务教育教科书·英语》四年级分册。"
    "题型：单选题 + 判断题。"
)

# ── 题型辅助 ──
def sc(content, knowledge_point, difficulty, options, correct_answer, explanation):
    """单选题"""
    return dict(
        knowledge_point=knowledge_point,
        question_type="single_choice",
        difficulty=difficulty,
        content=content,
        options=options,
        correct_answer=correct_answer,
        explanation=explanation,
    )

def tf(content, knowledge_point, difficulty, correct, explanation):
    """判断题；correct=True → A(正确), False → B(错误)"""
    return dict(
        knowledge_point=knowledge_point,
        question_type="true_false",
        difficulty=difficulty,
        content=content,
        options=["正确", "错误"],
        correct_answer="A" if correct else "B",
        explanation=explanation,
    )

# ═══════════════════════════════════════════════════════════════
# 4A 上册
# ═══════════════════════════════════════════════════════════════

# ━━━ 4A M1: Getting to know you ━━━
M1 = "4A M1"
QUESTIONS_M1 = [
    # 单选 easy ×5
    sc("— What's your name?  — ______", M1, "easy",
       ["A. I'm Lily", "B. My name is Lily", "C. This is Lily", "D. She is Lily"], "B",
       "回答 What's your name? 用 My name is... 或 I'm...，选项 B 最完整。"),
    sc("Nice to meet you!  — ______", M1, "easy",
       ["A. Thank you", "B. Nice to meet you too", "C. I'm fine", "D. See you"], "B",
       "Nice to meet you 的回应是 Nice to meet you too。"),
    sc("— How are you?  — ______", M1, "easy",
       ["A. I'm 10 years old", "B. I'm fine, thanks", "C. I'm a student", "D. I'm tall"], "B",
       "How are you? 问健康状况，用 I'm fine, thanks。"),
    sc("I can ______ basketball very well.", M1, "easy",
       ["A. play", "B. plays", "C. playing", "D. played"], "A",
       "can 是情态动词，后接动词原形 play。"),
    sc("— Are you happy?  — Yes, I ______.", M1, "easy",
       ["A. am", "B. is", "C. are", "D. do"], "A",
       "I am happy 的简略回答是 Yes, I am。"),
    # 单选 normal ×8
    sc("— Can you swim?  — No, I ______.", M1, "normal",
       ["A. can", "B. can't", "C. do", "D. don't"], "B",
       "Can you...? 否定回答 No, I can't。"),
    sc("My father ______ a new car.", M1, "normal",
       ["A. have", "B. has", "C. is have", "D. having"], "B",
       "一般现在时，主语是第三人称单数，have → has。"),
    sc("She ______ playing the piano at the party now.", M1, "normal",
       ["A. is", "B. are", "C. am", "D. do"], "A",
       "now 表示现在进行时，结构 be + doing；she 用 is。"),
    sc("We ______ going to visit the zoo tomorrow.", M1, "normal",
       ["A. is", "B. am", "C. are", "D. be"], "C",
       "主语 We 是复数，be going to 用 are。"),
    sc("— How old are you?  — I'm ______.", M1, "normal",
       ["A. nine", "B. nine years", "C. nine years old", "D. nine old"], "C",
       "回答年龄用 I'm nine years old。"),
    sc("— What can you do?  — I can ______ pictures.", M1, "normal",
       ["A. draw", "B. draws", "C. drawing", "D. drew"], "A",
       "can 后接动词原形 draw。"),
    sc("He ______ short black hair and big eyes.", M1, "normal",
       ["A. have", "B. has", "C. is", "D. are"], "B",
       "第三人称单数 has。"),
    sc("Let's ______ together.", M1, "normal",
       ["A. go", "B. goes", "C. going", "D. went"], "A",
       "Let's 后接动词原形 go。"),
    # 单选 hard ×5
    sc("— What does your mother do?  — She is a ______.", M1, "hard",
       ["A. student", "B. teacher", "C. child", "D. sister"], "B",
       "What does...do? 问职业；选项中只有 teacher 是职业。"),
    sc("I'm good at ______. I want to be a singer.", M1, "hard",
       ["A. sing", "B. singing", "C. sings", "D. sang"], "B",
       "be good at 后接动名词 singing。"),
    sc("— How do you feel?  — I feel ______ because I won the game.", M1, "hard",
       ["A. sad", "B. tired", "C. happy", "D. hungry"], "C",
       "won the game 应感觉 happy。"),
    sc("The girl ______ can swim is my sister.", M1, "hard",
       ["A. which", "B. who", "C. where", "D. what"], "B",
       "定语从句修饰人，关系代词用 who。"),
    sc("They ______ visit Beijing next week.", M1, "hard",
       ["A. are going to", "B. is going to", "C. am going to", "D. going to"], "A",
       "主语 They 用 are going to。"),
    # 判断 ×7
    tf("I am Lily.  →  My name is Lily.", M1, "easy", True, "两种方式都可以自我介绍，等价。"),
    tf("Can you swim? →  Yes, I can. 是正确的肯定回答。", M1, "easy", True, ""),
    tf("Can you swim? →  Yes, I do.  是正确的肯定回答。", M1, "easy", False, "Can 开头用 can 回答，不用 do。"),
    tf("My father have a new bike.  这句话是对的。", M1, "easy", False, "第三人称单数应用 has。"),
    tf("Nice to meet you.  →  Nice to meet you, too. 是正确的回应。", M1, "easy", True, ""),
    tf("Let's go home.  这里的 go 用原形。", M1, "normal", True, "Let's + 动词原形。"),
    tf("He is tall and have short hair.  这句话是对的。", M1, "normal", False, "并列结构应一致：is tall and has short hair。"),
]

# ━━━ 4A M2: Me, my family and friends ━━━
M2 = "4A M2"
QUESTIONS_M2 = [
    sc("My mother is a ______. She teaches English.", M2, "easy",
       ["A. doctor", "B. teacher", "C. driver", "D. farmer"], "B",
       "teaches English 说明是 teacher。"),
    sc("Do you have ______ cousins?", M2, "easy",
       ["A. a", "B. an", "C. any", "D. the"], "C",
       "疑问句中修饰可数名词 cousins 用 any。"),
    sc("— How many people are there in your family? — ______", M2, "easy",
       ["A. Four", "B. There are four", "C. There is four", "D. I have four"], "B",
       "问句用 How many...? 回答用 There are..."),
    sc("My father ______ in a big company.", M2, "easy",
       ["A. work", "B. works", "C. working", "D. is work"], "B",
       "第三人称单数用 works。"),
    sc("That girl is ______ sister.", M2, "easy",
       ["A. me", "B. my", "C. mine", "D. I"], "B",
       "后面有名词 sister，用形容词性物主代词 my。"),
    sc("This is ______ book. That one is ______.", M2, "normal",
       ["A. my / me", "B. mine / my", "C. my / mine", "D. mine / mine"], "C",
       "第一空后有名词用 my；第二空后无名词用名词性物主代词 mine。"),
    sc("— Whose ruler is this? — It's ______.", M2, "normal",
       ["A. she", "B. her", "C. hers", "D. herself"], "C",
       "问 Whose，用名词性物主代词 hers。"),
    sc("My cousin is ______ years old.", M2, "normal",
       ["A. three", "B. third", "C. the three", "D. thirds"], "A",
       "表示年龄直接用基数词 three。"),
    sc("— What's your father's job? — He is a ______.", M2, "normal",
       ["A. pupil", "B. worker", "C. baby", "D. grandpa"], "B",
       "问工作，选项中只有 worker 是职业。"),
    sc("She ______ her mother very much.", M2, "normal",
       ["A. like", "B. likes", "C. is like", "D. liking"], "B",
       "第三人称单数 likes。"),
    sc("My parents ______ at home on Sundays.", M2, "normal",
       ["A. is", "B. am", "C. are", "D. be"], "C",
       "主语 My parents 复数，用 are。"),
    sc("He has ______ big eyes and ______ small nose.", M2, "normal",
       ["A. / ; a", "B. a ; /", "C. a ; a", "D. / ; /"], "A",
       "eyes 复数前不加冠词；nose 单数可数前加 a。"),
    sc("We ______ like English. We think it is fun.", M2, "hard",
       ["A. all", "B. both", "C. each", "D. every"], "A",
       "We 三人以上用 all；both 只用于两人。"),
    sc("The girl ______ red is my friend. She ______ long hair.", M2, "hard",
       ["A. in ; has", "B. in ; have", "C. wear ; has", "D. wear ; have"], "A",
       "in + 颜色表示穿着；第三人称单数 has。"),
    tf("I have a brother. →  I have one brother. 两个句子意思相同。", M2, "easy", True, "a brother = one brother。"),
    tf("My mother teach English.  这句话是对的。", M2, "easy", False, "第三人称单数用 teaches。"),
    tf("This is my book. → That book is mine. 意思相同。", M2, "easy", True, "my book = mine。"),
    tf("Do you have some cousins?  疑问句用 some 是错误的。", M2, "normal", True, "疑问句/否定句用 any；some 用于肯定句。"),
    tf("My father works in a hospital.  →  He is a doctor. 一定正确。", M2, "normal", False, "hospital 里也可能是 nurse 或其他职业。"),
    tf("Whose ruler is this?  →  It's her. 是正确的回答。", M2, "normal", False, "应回答 It's hers（名词性物主代词）。"),
    tf("This is her book. →  That book is her. 这句话是对的。", M2, "hard", False, "应是 That book is hers。"),
    tf("He like ice cream very much.  这句话是对的。", M2, "hard", False, "第三人称单数 likes。"),
    sc("My uncle is a doctor. He works in a hospital.", M2, "normal",
       ["A. teacher", "B. doctor", "C. driver", "D. farmer"], "B",
       "works in a hospital 说明是 doctor。"),
    sc("Do you have any pets? Yes, I have a cat.", M2, "normal",
       ["A. have", "B. has", "C. am", "D. is"], "A",
       "I 第一人称用 have。"),
    tf("My brother have a dog.  这句话是对的。", M2, "easy", False, "第三人称单数用 has。"),
]

# ━━━ 4A M3: Places and activities ━━━
M3 = "4A M3"
QUESTIONS_M3 = [
    sc("We are ______ the classroom now.", M3, "easy",
       ["A. on", "B. in", "C. at", "D. under"], "B",
       "在教室里用介词 in。"),
    sc("The cat is ______ the desk.", M3, "easy",
       ["A. on", "B. in", "C. under", "D. to"], "C",
       "根据语境，under 表示在桌子下面。"),
    sc("I usually ______ my homework at 7.", M3, "easy",
       ["A. do", "B. does", "C. doing", "D. did"], "A",
       "I 第一人称用 do；usually 提示一般现在时。"),
    sc("She ______ a book in the library now.", M3, "easy",
       ["A. is reading", "B. reads", "C. read", "D. are reading"], "A",
       "now 表示现在进行时，she 用 is reading。"),
    sc("The shop is ______ the hospital.", M3, "easy",
       ["A. next", "B. next at", "C. next to", "D. next on"], "C",
       "next to 是固定搭配，意为「紧邻」。"),
    sc("There ______ a book on the desk.", M3, "normal",
       ["A. is", "B. are", "C. am", "D. be"], "A",
       "there be 句型，a book 单数用 is。"),
    sc("Look! The boys ______ football on the playground.", M3, "normal",
       ["A. play", "B. plays", "C. are playing", "D. is playing"], "C",
       "Look! 提示现在进行时；boys 复数用 are playing。"),
    sc("Where ______ you ______ now?", M3, "normal",
       ["A. are ; doing", "B. do ; do", "C. is ; doing", "D. are ; do"], "A",
       "now 提示现在进行时，you → are doing。"),
    sc("The library is ______ the second floor.", M3, "normal",
       ["A. on", "B. in", "C. at", "D. under"], "A",
       "在某楼层用介词 on。"),
    sc("— What's the time?  — It's ______ o'clock.", M3, "normal",
       ["A. half past three", "B. half to three", "C. three half", "D. three to half"], "A",
       "half past three = 3:30，正确表达。"),
    sc("There are ______ students in the playground.", M3, "normal",
       ["A. fourty", "B. forty", "C. fourty-two", "D. fourties"], "B",
       "40 的正确拼写是 forty（没有 u）。"),
    sc("______ the door, please.", M3, "normal",
       ["A. Open", "B. Opens", "C. Opening", "D. Opened"], "A",
       "祈使句用动词原形 Open。"),
    sc("I can see a ______ on the tree. It is green and sweet.", M3, "hard",
       ["A. flower", "B. apple", "C. leaf", "D. bird"], "C",
       "树上绿色的是 leaf（树叶）。"),
    sc("— How do you go to school? — I go to school ______.", M3, "hard",
       ["A. by foot", "B. on foot", "C. in foot", "D. with foot"], "B",
       "固定搭配 on foot。"),
    sc("They ______ a new park in the city now.", M3, "hard",
       ["A. build", "B. are building", "C. builds", "D. building"], "B",
       "now 提示现在进行时，用 are building。"),
    tf("There is a pen on the desk.  这句话是对的。", M3, "easy", True, "a pen 单数用 is。"),
    tf("The girl is in the library.  →  She is reading now. 一定正确。", M3, "easy", False, "在图书馆不一定在读书，可能是借书、找书等。"),
    tf("Next to 表示「紧邻」，是介词短语。", M3, "easy", True, ""),
    tf("There are some book on the desk.  这句话语法是对的。", M3, "normal", False, "some book 应为 some books（复数）。"),
    tf("Look! The bird fly away.  这句话是对的。", M3, "normal", False, "Look! 提示现在进行时：is flying。"),
    tf("The shop is next the park.  这句话是对的。", M3, "normal", False, "next 后应加 to。"),
    tf("Open the window, please.  这是祈使句。", M3, "hard", True, "动词原形开头，正确。"),
    sc("The children are playing games in the playground.", M3, "normal",
       ["A. play", "B. playing", "C. plays", "D. played"], "B",
       "are + playing 构成现在进行时。"),
    sc("Are there some chairs in the room?", M3, "normal",
       ["A. Is ; a", "B. Are ; some", "C. Is ; some", "D. Are ; a"], "B",
       "chairs 复数用 Are；疑问句用 some。"),
    tf("The cat is on the tree.  猫在树上，用 in the tree。", M3, "easy", False, "外来的东西在树上用 in the tree。"),
]

# ━━━ 4A M4: The world around ━━━
M4 = "4A M4"
QUESTIONS_M4 = [
    sc("A triangle has ______ sides.", M4, "easy",
       ["A. two", "B. three", "C. four", "D. five"], "B",
       "三角形有三条边。"),
    sc("A square has ______ right angles.", M4, "easy",
       ["A. two", "B. three", "C. four", "D. five"], "C",
       "正方形有 4 个直角。"),
    sc("It's ______ today. Take an umbrella.", M4, "easy",
       ["A. sunny", "B. rainy", "C. hot", "D. windy"], "B",
       "take an umbrella 暗示下雨。"),
    sc("The cat is ______ the box.", M4, "easy",
       ["A. in", "B. on", "C. at", "D. near"], "A",
       "in the box = 在盒子里。"),
    sc("The ______ is on the left of the park.", M4, "easy",
       ["A. hospital", "B. sun", "C. moon", "D. cloud"], "A",
       "A. hospital 是地点，可以位于公园旁边。"),
    sc("It's ______ in summer in Shanghai.", M4, "normal",
       ["A. cold", "B. hot", "C. snowy", "D. cool"], "B",
       "上海夏天热。"),
    sc("A circle has ______ corners.", M4, "normal",
       ["A. no", "B. one", "C. two", "D. four"], "A",
       "圆形没有角。"),
    sc("The ball is ______ the box and the chair.", M4, "normal",
       ["A. in", "B. on", "C. between", "D. behind"], "C",
       "between...and... 表示在两者之间。"),
    sc("My home is ______ the school. I walk to school.", M4, "normal",
       ["A. far from", "B. next to", "C. behind", "D. under"], "B",
       "走路上学说明住得近，next to 最合理。"),
    sc("It's ______ today. The sun is shining.", M4, "normal",
       ["A. rainy", "B. cloudy", "C. sunny", "D. snowy"], "C",
       "sun is shining → sunny。"),
    sc("A rectangle has ______ pairs of equal sides.", M4, "normal",
       ["A. one", "B. two", "C. three", "D. four"], "B",
       "长方形有两组对边分别相等。"),
    sc("Winter is ______ than autumn.", M4, "normal",
       ["A. cold", "B. colder", "C. coldest", "D. more cold"], "B",
       "than 提示用比较级 colder。"),
    sc("The sun ______ in the east.", M4, "hard",
       ["A. rise", "B. rises", "C. is rising", "D. rose"], "B",
       "客观真理用一般现在时，主语 the sun 单数，rise 加 s。"),
    sc("______ there a river near your home?", M4, "hard",
       ["A. Is", "B. Are", "C. Do", "D. Does"], "A",
       "there be 疑问句，a river 单数，用 Is。"),
    tf("A square has 3 sides.  这句话是对的。", M4, "easy", False, "正方形有 4 条边。"),
    tf("It's sunny. We need an umbrella.  这句话是对的。", M4, "easy", False, "晴天不需要伞。"),
    tf("A circle has no corners.  这句话是对的。", M4, "easy", True, "圆形没有角。"),
    tf("The sun rises in the west.  这句话是对的。", M4, "normal", False, "太阳从东方升起。"),
    tf("There is a apple on the table.  这句话是对的。", M4, "normal", False, "apple 元音开头，用 an。"),
    tf("Winter is colder than summer.  这句话是对的。", M4, "normal", True, "冬天比夏天冷。"),
    tf("It is 30°C. It is cold.  这句话是对的。", M4, "hard", False, "30°C 应该是 hot。"),
    tf("A rectangle has 4 pairs of equal sides.  这句话是对的。", M4, "hard", False, "长方形只有 2 组对边相等。"),
    sc("A circle is round.", M4, "easy",
       ["A. a line", "B. round", "C. a square", "D. a triangle"], "B",
       "圆形是圆形的 round。"),
    sc("The elephant is very big. It has a long nose.", M4, "easy",
       ["A. cat", "B. elephant", "C. rabbit", "D. monkey"], "B",
       "long nose 描述的是 elephant。"),
    tf("A triangle has 4 sides.  这句话是对的。", M4, "easy", False, "三角形有 3 条边。"),
]

# ═══════════════════════════════════════════════════════════════
# 4B 下册
# ═══════════════════════════════════════════════════════════════

# ━━━ 4B M5: Sports & hobbies ━━━
M5 = "4B M5"
QUESTIONS_M5 = [
    sc("Can you ______ fast?", M5, "easy",
       ["A. run", "B. runs", "C. running", "D. ran"], "A",
       "can 后接动词原形 run。"),
    sc("He ______ play basketball, but he can play football.", M5, "easy",
       ["A. can", "B. can't", "C. is", "D. do"], "B",
       "转折 but 提示前面是否定：can't。"),
    sc("I ______ go swimming every weekend.", M5, "easy",
       ["A. usually", "B. can", "C. am", "D. is"], "A",
       "usually 是频率副词，修饰一般现在时。"),
    sc("She ______ draw well.", M5, "easy",
       ["A. can", "B. cans", "C. can to", "D. caning"], "A",
       "can 后接动词原形 draw。"),
    sc("— Can you play the piano?  — ______", M5, "easy",
       ["A. Yes, I do.", "B. Yes, I can.", "C. No, I don't.", "D. Yes, I am."], "B",
       "Can 开头一般疑问句用 can 回答。"),
    sc("They ______ play football after school.", M5, "normal",
       ["A. can't", "B. aren't", "C. doesn't", "D. can"], "D",
       "表示能力用 can。"),
    sc("— Can you run fast? — No, I ______. I can run slowly.", M5, "normal",
       ["A. can", "B. can't", "C. do", "D. don't"], "B",
       "No 提示否定回答，用 can't。"),
    sc("I often ______ the piano on Sundays.", M5, "normal",
       ["A. play", "B. plays", "C. playing", "D. played"], "A",
       "often + 一般现在时，I 用 play。"),
    sc("He can ______ very well. He is a good singer.", M5, "normal",
       ["A. sing", "B. sings", "C. singing", "D. sang"], "A",
       "can + 动词原形 sing。"),
    sc("— What can you do? — I can ______ pictures.", M5, "normal",
       ["A. draw", "B. draws", "C. drawing", "D. drew"], "A",
       "can + draw。"),
    sc("She ______ plays the pipa. She plays it every day.", M5, "normal",
       ["A. never", "B. usually", "C. sometimes", "D. often"], "B",
       "every day 提示 usually/frequently。"),
    sc("He is ______ at basketball. He plays very well.", M5, "normal",
       ["A. good", "B. well", "C. nice", "D. fine"], "A",
       "固定搭配 be good at。"),
    sc("I go to the park ______ a week.", M5, "hard",
       ["A. one time", "B. once", "C. one", "D. first"], "B",
       "once a week = 一周一次。"),
    sc("— Can you sing and dance? — Yes, I can ______.", M5, "hard",
       ["A. sing", "B. dance", "C. sing and dance", "D. but"], "C",
       "and 提示两者都可以，回答也保留 and。"),
    tf("Can you swim? → Yes, I can't.  这句话是对的。", M5, "easy", False, "Yes 应与 can 搭配，Yes, I can。"),
    tf("He can plays football.  这句话是对的。", M5, "easy", False, "can 后接动词原形 play。"),
    tf("I usually play basketball.  这句话是对的。", M5, "easy", True, "usually + 一般现在时正确。"),
    tf("He is good at draw.  这句话是对的。", M5, "normal", False, "be good at + doing：drawing。"),
    tf("Can you sing? → No, I can't.  这是正确的否定回答。", M5, "normal", True, ""),
    tf("She can sings well.  这句话是对的。", M5, "normal", False, "can + 原形 sing。"),
    tf("He usually plays football every day.  这句话是对的。", M5, "hard", True, "usually + every day 都提示一般现在时，第三人称单数用 plays。"),
    tf("I can swim and I can draw. →  I can swim and draw.  两句意思相同。", M5, "hard", True, "can 共用，省去第二个 I can，意思不变。"),
    sc("I can run very fast, but I cannot swim.", M5, "easy",
       ["A. run", "B. runs", "C. running", "D. ran"], "A",
       "can + 原形 run；but 表示转折，不会游泳。"),
    sc("He usually plays the violin every evening.", M5, "normal",
       ["A. never", "B. sometimes", "C. usually", "D. often"], "C",
       "every evening 提示高频率 usually。"),
    tf("He can play the piano.  play the + 乐器要加 the。", M5, "normal", True, "play the piano 正确。"),
]

# ━━━ 4B M6: Food & festivals ━━━
M6 = "4B M6"
QUESTIONS_M6 = [
    sc("I'd like ______ juice, please.", M6, "easy",
       ["A. a", "B. an", "C. a glass of", "D. many"], "C",
       "juice 不可数，用 a glass of 表示一杯。"),
    sc("— Can I have ______ sweets? — Sure. Here you are.", M6, "easy",
       ["A. a", "B. an", "C. some", "D. much"], "C",
       "sweets 可数复数，请求时用 some。"),
    sc("How ______ apples do you have?", M6, "easy",
       ["A. much", "B. many", "C. any", "D. some"], "B",
       "apples 可数复数，用 How many。"),
    sc("There ______ some milk in the fridge.", M6, "easy",
       ["A. is", "B. are", "C. am", "D. be"], "A",
       "milk 不可数，用 is。"),
    sc("The Mid-Autumn Festival is in ______.", M6, "easy",
       ["A. spring", "B. summer", "C. autumn", "D. winter"], "C",
       "中秋节在秋天（农历八月十五）。"),
    sc("Would you like ______ coffee?", M6, "normal",
       ["A. any", "B. some", "C. a", "D. an"], "B",
       "Would you like...? 提出建议/邀请，期望肯定回答用 some。"),
    sc("There are ______ students in Class 1.", M6, "normal",
       ["A. fourty", "B. forty", "C. fourty-one", "D. forties"], "B",
       "40 的正确拼写是 forty（无 u）。"),
    sc("How ______ water do you drink every day?", M6, "normal",
       ["A. much", "B. many", "C. long", "D. often"], "A",
       "water 不可数，用 How much。"),
    sc("— What would you like? — ______, please.", M6, "normal",
       ["A. I'd like a pie", "B. I like pie", "C. I have a pie", "D. I want pie"], "A",
       "What would you like? 回答 I'd like...。"),
    sc("The Dragon Boat Festival is in ______.", M6, "normal",
       ["A. January", "B. March", "C. May or June", "D. September"], "C",
       "端午节在农历五月初五，对应公历 5 或 6 月。"),
    sc("I have ______ rice and ______ eggs for breakfast.", M6, "normal",
       ["A. many ; many", "B. much ; many", "C. many ; much", "D. much ; much"], "B",
       "rice 不可数用 much；eggs 可数复数用 many。"),
    sc("The Spring Festival is the ______ festival in China.", M6, "normal",
       ["A. big", "B. bigger", "C. biggest", "D. most big"], "C",
       "范围 in China 提示最高级 biggest。"),
    sc("— How many oranges? — ______.", M6, "hard",
       ["A. An orange", "B. Two orange", "C. Two oranges", "D. Many orange"], "C",
       "How many 后接可数名词复数 oranges。"),
    sc("She ______ some fish and rice for dinner.", M6, "hard",
       ["A. have", "B. has", "C. is have", "D. having"], "B",
       "第三人称单数 has；have some... 表示「吃了…」。"),
    tf("I'd like some juice.  →  I want some juice. 两句话意思相同。", M6, "easy", True, "would like = want，都表示「想要」。"),
    tf("How much apples do you have?  这句话是对的。", M6, "easy", False, "apples 可数复数，应 How many。"),
    tf("There is some water.  some 用于肯定句。", M6, "easy", True, ""),
    tf("Can I have some sweets?  这是正确的请求句式。", M6, "easy", True, "请求时用 some，不用 any。"),
    tf("How much milk?  →  milk 是不可数名词，正确。", M6, "normal", True, ""),
    tf("There are some bread on the table.  这句话是对的。", M6, "normal", False, "bread 不可数，用 There is。"),
    tf("I have many water.  这句话是对的。", M6, "hard", False, "water 不可数，用 much。"),
    tf("The Spring Festival is in spring.  这句话是对的。", M6, "hard", True, "春节（农历正月初一）在春天。"),
    sc("Would you like some bread?", M6, "easy",
       ["A. any", "B. some", "C. a", "D. an"], "B",
       "Would you like... 期望肯定回答用 some。"),
    sc("The boy is a little hungry. He eats two hamburgers.", M6, "normal",
       ["A. a little", "B. a little of", "C. a few", "D. many"], "A",
       "hungry 形容词，用 a little 修饰。"),
    tf("I have many water.  这句话是对的。", M6, "hard", False, "water 不可数，用 much。"),
]

# ━━━ 4B M7: There is / There are & Around us ━━━
M7 = "4B M7"
QUESTIONS_M7 = [
    sc("There ______ a cat under the tree.", M7, "easy",
       ["A. is", "B. are", "C. am", "D. be"], "A",
       "a cat 单数用 is。"),
    sc("There ______ three books on the desk.", M7, "easy",
       ["A. is", "B. are", "C. am", "D. was"], "B",
       "three books 复数用 are。"),
    sc("Is there ______ water in the cup?", M7, "easy",
       ["A. a", "B. an", "C. any", "D. some"], "C",
       "疑问句 + 不可数名词 water 用 any。"),
    sc("The bird is ______ the tree.", M7, "easy",
       ["A. on", "B. in", "C. at", "D. under"], "B",
       "外来的东西（鸟）在树上用 in the tree。"),
    sc("The book is ______ the schoolbag.", M7, "easy",
       ["A. in", "B. on", "C. at", "D. under"], "A",
       "in the schoolbag = 在书包里面。"),
    sc("There ______ two boys in the photo.", M7, "normal",
       ["A. is", "B. are", "C. am", "D. be"], "B",
       "two boys 复数用 are。"),
    sc("There ______ some children in the park.", M7, "normal",
       ["A. is", "B. are", "C. am", "D. was"], "B",
       "children 复数用 are。"),
    sc("Is there ______ milk in the fridge?", M7, "normal",
       ["A. a", "B. an", "C. any", "D. some"], "C",
       "疑问句 + 不可数 milk 用 any。"),
    sc("______ any flowers in the garden?", M7, "normal",
       ["A. Is there", "B. Are there", "C. There is", "D. There are"], "B",
       "flowers 复数用 Are there。"),
    sc("The pencil is ______ the pencil box.", M7, "normal",
       ["A. in", "B. on", "C. at", "D. near"], "A",
       "铅笔在铅笔盒内部，用 in。"),
    sc("The clock is ______ the wall.", M7, "normal",
       ["A. in", "B. on", "C. at", "D. under"], "B",
       "钟挂在墙表面用 on the wall。"),
    sc("There ______ a table, two chairs and a lamp in the room.", M7, "normal",
       ["A. is", "B. are", "C. am", "D. be"], "A",
       "there be 就近原则：a table 单数用 is。"),
    sc("______ there ______ juice in the glass?", M7, "hard",
       ["A. Is ; any", "B. Are ; any", "C. Is ; some", "D. Are ; some"], "A",
       "juice 不可数用 Is；疑问句用 any。"),
    sc("There are three ______ and five ______ on the farm.", M7, "hard",
       ["A. sheeps ; sheeps", "B. sheep ; sheeps", "C. sheep ; sheep", "D. sheeps ; sheep"], "C",
       "sheep 单复数同形。"),
    tf("There is a book on the desk.  这句话是对的。", M7, "easy", True, "a book 单数用 is。"),
    tf("There is some apples on the table.  这句话是对的。", M7, "easy", False, "apples 复数用 There are。"),
    tf("The bird is on the tree.  这句话是对的。", M7, "easy", False, "外来的鸟用 in the tree；on 用于树上长出来的果实/叶子。"),
    tf("Is there any milk?  any 用于疑问句，正确。", M7, "normal", True, ""),
    tf("There are a book and two pens on the desk.  这句话是对的。", M7, "normal", False, "就近原则，a book 单数用 There is。"),
    tf("The picture is in the wall.  这句话是对的。", M7, "normal", False, "画挂在墙表面，用 on the wall；in the wall 指嵌在墙内（如窗户）。"),
    tf("There are some sheeps in the picture.  这句话是对的。", M7, "hard", False, "sheep 单复数同形，仍是 sheep。"),
    tf("There are many students and a teacher. →  There is a teacher and many students.  两句话意思相同。", M7, "hard", True, "there be 就近原则只影响动词形式，意思不变。"),
    sc("There is a picture and two maps on the wall.", M7, "normal",
       ["A. is", "B. are", "C. am", "D. be"], "A",
       "there be 就近原则，a picture 单数用 is。"),
    sc("The toy is in the box. I cannot see it.", M7, "easy",
       ["A. in", "B. on", "C. at", "D. near"], "A",
       "看不见说明在盒子里面 in。"),
    tf("There are some childs in the park.  这句话是对的。", M7, "normal", False, "child 复数是 children，不是 childs。"),
]

# ━━━ 4B M8: Future plans (be going to) ━━━
M8 = "4B M8"
QUESTIONS_M8 = [
    sc("We ______ visit Hainan next month.", M8, "easy",
       ["A. are going to", "B. is going to", "C. am going to", "D. going to"], "A",
       "We 复数用 are going to。"),
    sc("He ______ ride a horse on the farm.", M8, "easy",
       ["A. is going to", "B. are going to", "C. am going to", "D. going to"], "A",
       "He 单数用 is going to。"),
    sc("I ______ to the park this Sunday.", M8, "easy",
       ["A. go", "B. goes", "C. am going", "D. went"], "C",
       "this Sunday 将来计划，用 be going to 或 will；选项只有 am going。"),
    sc("They ______ fly a kite tomorrow.", M8, "easy",
       ["A. are going to", "B. is going to", "C. am going to", "D. going"], "A",
       "They 复数用 are going to。"),
    sc("She is going to ______ a film tonight.", M8, "easy",
       ["A. watch", "B. watches", "C. watching", "D. watched"], "A",
       "be going to + 动词原形 watch。"),
    sc("He usually ______ to school by bike.", M8, "normal",
       ["A. go", "B. goes", "C. going", "D. is going"], "B",
       "usually 提示一般现在时，He 用 goes。"),
    sc("We ______ visit our grandparents next week.", M8, "normal",
       ["A. are", "B. are going to", "C. is going to", "D. am going to"], "B",
       "表示将来计划，用 are going to。"),
    sc("— What are you going to do tomorrow? — I ______.", M8, "normal",
       ["A. go swimming", "B. going swimming", "C. am going swimming", "D. went swimming"], "C",
       "问句用 be going to，答句也用 am going。"),
    sc("She is going to ______ a birthday card for her friend.", M8, "normal",
       ["A. make", "B. makes", "C. making", "D. made"], "A",
       "be going to + make。"),
    sc("I ______ go to the cinema with my parents this evening.", M8, "normal",
       ["A. will", "B. am going to", "C. A or B", "D. going"], "C",
       "will 和 be going to 都可以表示将来计划。"),
    sc("They ______ going to visit the museum.", M8, "normal",
       ["A. is", "B. am", "C. are", "D. was"], "C",
       "They 复数用 are。"),
    sc("Look at the black clouds! It ______ rain.", M8, "normal",
       ["A. is", "B. will", "C. does", "D. is going to"], "D",
       "Look at the black clouds 提示根据迹象预测，用 is going to。"),
    sc("The train ______ at 9:00 tomorrow morning.", M8, "hard",
       ["A. leaves", "B. will leave", "C. is leaving", "D. A or B"], "D",
       "按时刻表发生的动作用一般现在时或 will。"),
    sc("I think it ______ be sunny tomorrow.", M8, "hard",
       ["A. will", "B. am going to", "C. is going to", "D. are going to"], "A",
       "表示个人预测/看法，用 will；主语 it，be going to 用 is going to 也对，但选项里只有 A 完整。"),
    tf("I am going to visit my grandma.  这句话是对的。", M8, "easy", True, "be going to + 动词原形，结构正确。"),
    tf("He is going to play football tomorrow.  这句话是对的。", M8, "easy", True, ""),
    tf("We going to visit the zoo.  这句话是对的。", M8, "easy", False, "缺少 be 动词，应为 We are going to。"),
    tf("She will goes to school.  这句话是对的。", M8, "normal", False, "will + 动词原形 go，不是 goes。"),
    tf("Look at the black clouds! It will rain.  这句话是对的。", M8, "normal", True, "看迹象预测用 will 或 is going to，这里用 will 可以。"),
    tf("He is going to swims tomorrow.  这句话是对的。", M8, "hard", False, "be going to + 原形 swim，不是 swims。"),
    tf("I will to go to the park.  这句话是对的。", M8, "hard", False, "will + 动词原形 go，不加 to。"),
    tf("They are going to visit Beijing next month.  这句话是对的。", M8, "hard", True, "are going to + 动词原形，正确。"),
    sc("Will it rain tomorrow?", M8, "normal",
       ["A. Will", "B. Is", "C. Does", "D. Do"], "A",
       "will 表示将来，Will it rain...?"),
    sc("They are going to have a picnic this Sunday.", M8, "easy",
       ["A. have", "B. has", "C. having", "D. had"], "A",
       "be going to + 动词原形 have。"),
    tf("He is going to visit his grandma tomorrow.  这句话是对的。", M8, "easy", True, "be going to + 动词原形，结构正确。"),
]

# ═══════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════
QUESTIONS = (
    QUESTIONS_M1
    + QUESTIONS_M2
    + QUESTIONS_M3
    + QUESTIONS_M4
    + QUESTIONS_M5
    + QUESTIONS_M6
    + QUESTIONS_M7
    + QUESTIONS_M8
)

# ── 题库防重复检查 ──
# 如果已有同 grade+subject 的沪教版四年级英语题库，先删掉旧记录以便重新 seed
async def seed():
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        future=True,
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        from models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 清理同名旧题库（允许重新 seed）
        existing = (await db.execute(
            select(QuestionBank).where(
                QuestionBank.grade == "四年级",
                QuestionBank.subject == "英语",
                QuestionBank.title == BANK_TITLE,
            )
        )).scalars().first()
        if existing:
            print(f"删除旧题库：{existing.title} (id={existing.id})，重新 seed")
            await db.delete(existing)
            await db.commit()

        # 创建题库
        bank = QuestionBank(
            grade="四年级",
            subject="英语",
            title=BANK_TITLE,
            description=BANK_DESC,
            is_active=True,
        )
        db.add(bank)
        await db.commit()
        await db.refresh(bank)
        print(f"创建题库：{bank.title} (id={bank.id})")

        # 批量插入
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

        # 知识点分布
        kp_result = await db.execute(
            select(Question.knowledge_point, func.count(Question.id))
            .where(Question.bank_id == bank.id)
            .group_by(Question.knowledge_point)
            .order_by(func.count(Question.id).desc())
        )
        print("\n知识点分布：")
        for kp, cnt in kp_result.all():
            print(f"  {kp}: {cnt} 题")

        # 题型分布
        qt_result = await db.execute(
            select(Question.question_type, func.count(Question.id))
            .where(Question.bank_id == bank.id)
            .group_by(Question.question_type)
        )
        print("\n题型分布：")
        for qt, cnt in qt_result.all():
            print(f"  {qt}: {cnt} 题")

        # 难度分布
        diff_result = await db.execute(
            select(Question.difficulty, func.count(Question.id))
            .where(Question.bank_id == bank.id)
            .group_by(Question.difficulty)
            .order_by(func.count(Question.id).desc())
        )
        print("\n难度分布：")
        for d, cnt in diff_result.all():
            print(f"  {d}: {cnt} 题")


if __name__ == "__main__":
    asyncio.run(seed())
