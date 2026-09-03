"""Seed 教材配套内容：
  Phase F — Reading Comp 题（60 道，按 Unit Story/Reading 文本出题）
  Phase G — Sound 拼读专项题（75 道，按 Unit Sound 焦点出题）

题库标题：沪教版四年级英语·配套练习（Reading + Sound）
所有题 knowledge_point 关联到对应教材 Unit。
"""
import asyncio

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Question, QuestionBank, QuestionUnit, TextbookUnit, TextbookVersion

# ── 题库配置 ──
BANK_TITLE = "沪教版四年级英语·配套练习（Reading + Sound）"
BANK_DESC = (
    "Phase F: Reading time / Story time 阅读理解题，60 道\n"
    "Phase G: Sound 自然拼读专项题，75 道\n"
    "教材：沪教版（5·4 学制）2025 秋四年级上册\n"
    "knowledge_point 已映射到对应 Unit（U1-U10）"
)


# ═══════════════════════════════════════════════════════════════
# 题型辅助
# ═══════════════════════════════════════════════════════════════
def sc(content, knowledge_point, difficulty, options, correct_answer, explanation):
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
# Reading Comp — U1 My school (A bamboo school)
# ═══════════════════════════════════════════════════════════════
M1 = "Reading Comp: U1 My school"
READING_U1 = [
    sc("Green School Bali 的教学楼是用什么做的？", M1, "easy",
       ["A. Wood", "B. Bamboo", "C. Stone", "D. Glass"], "B",
       "原文：All its school buildings are made of bamboo. 所有学校建筑都是竹子做的。"),
    sc("Green School Bali 的教学楼看起来像什么？", M1, "easy",
       ["A. Trees", "B. Big mushrooms", "C. Birds", "D. Mountains"], "B",
       "原文：Three tall teaching buildings look like big mushrooms. 三栋高大的教学楼像大蘑菇。"),
    sc("What is special about the bamboo school?", M1, "easy",
       ["A. It has no walls", "B. It has no roof", "C. It has no doors", "D. It has no students"], "A",
       "原文：these bamboo buildings have no walls at all. 这些竹楼完全没有墙。"),
    sc("How many floors does each teaching building have?", M1, "normal",
       ["A. Two", "B. Three", "C. Four", "D. Five"], "B",
       "原文：Each teaching building has three floors. 每栋教学楼有 3 层。"),
    sc("Which is NOT made of bamboo according to the text?", M1, "hard",
       ["A. Floors", "B. Desks", "C. Chairs", "D. Walls"], "D",
       "原文：Floors, desks and chairs are all made of bamboo. Even the school toilets are made of bamboo! 地板、课桌、椅子都是竹子做的，连厕所都是。墙不是。"),
    sc("What do the students learn in the bamboo school?", M1, "normal",
       ["A. In bamboo classrooms only", "B. In computer, music and art rooms too", "C. Outside", "D. At home"], "B",
       "原文：Students learn and play in bamboo classrooms, computer rooms, music rooms and art rooms."),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U2 My classmates (You can do it!)
# ═══════════════════════════════════════════════════════════════
M2 = "Reading Comp: U2 My classmates"
READING_U2 = [
    sc("Why does James feel bad at the beginning?", M2, "easy",
       ["A. He's tired", "B. The rope skipping looks too hard", "C. He's angry", "D. He's hungry"], "B",
       "原文：It looks so hard. James feels bad. 跳长绳看起来太难了，James 觉得糟。"),
    sc("Who shows James how to skip the long rope?", M2, "easy",
       ["A. Shenshen", "B. Xiaojiang", "C. Minmin", "D. Max"], "C",
       "原文：Minmin shows James how. Minmin 示范给 James 看。"),
    sc("What do Shenshen and Xiaojiang do to help James?", M2, "normal",
       ["A. They laugh at him", "B. They slow down the rope", "C. They take the rope away", "D. They give up"], "B",
       "原文：Shenshen and Xiaojiang slow down the rope. 他们把绳子摇慢一点。"),
    sc("Why does James duck when he sees the rope coming?", M2, "normal",
       ["A. To play", "B. He's still afraid", "C. He's bored", "D. To rest"], "B",
       "原文：James is still afraid. He sees the rope coming and he ducks. James 仍然害怕，看到绳子过来就蹲下躲开了。"),
    sc("How does James feel at the end?", M2, "easy",
       ["A. Sad", "B. Excited and happy", "C. Angry", "D. Tired"], "B",
       "原文：James is happy and excited. James 又高兴又兴奋。"),
    sc("What's the moral of the story?", M2, "hard",
       ["A. Don't try new things", "B. With friends' help, you can do hard things", "C. Skipping rope is scary", "D. Don't be afraid of ropes"], "B",
       "故事寓意：在朋友帮助下，你能做到困难的事情。You can do it!"),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U3 Animals and their homes (Polar bears)
# ═══════════════════════════════════════════════════════════════
M3 = "Reading Comp: U3 Animals and their homes"
READING_U3 = [
    sc("Where do polar bears live?", M3, "easy",
       ["A. Near the South Pole", "B. Near the North Pole", "C. In the desert", "D. In the forest"], "B",
       "原文：Polar bears live near the North Pole. 北极熊生活在北极附近。"),
    sc("Why do polar bears have thick fur?", M3, "easy",
       ["A. To keep warm", "B. To look white", "C. To swim", "D. To hide"], "A",
       "原文：they have thick fur to keep warm. 厚皮毛保暖。"),
    sc("Why do polar bears look white?", M3, "normal",
       ["A. They are painted white", "B. There's lots of ice and snow around them", "C. They eat snow", "D. They are born white"], "B",
       "原文：There's lots of ice and snow. And that's why they look white. 周围都是冰雪，所以看起来是白色的。"),
    sc("What do polar bears eat?", M3, "easy",
       ["A. Bamboo", "B. Seals and fish", "C. Apples", "D. Noodles"], "B",
       "原文：they catch seals and fish for food. 它们抓海豹和鱼吃。"),
    sc("Why is life difficult for polar bears now?", M3, "hard",
       ["A. They have no food", "B. Ice and snow are melting", "C. They are sick", "D. Hunters hunt them"], "B",
       "原文：Now the ice and snow are melting because the area is getting warmer. 因为气候变暖冰雪在融化。"),
    sc("What can polar bears do well?", M3, "normal",
       ["A. Fly", "B. Climb trees", "C. Swim in cold water", "D. Run very fast"], "C",
       "原文：Polar bears are great swimmers. They like swimming in the cold water."),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U4 Our birthday (A bowl of birthday noodles)
# ═══════════════════════════════════════════════════════════════
M4 = "Reading Comp: U4 Our birthday"
READING_U4 = [
    sc("How old is Minmin in the story?", M4, "easy",
       ["A. Nine", "B. Ten", "C. Eleven", "D. Twelve"], "B",
       "原文：Minmin turns ten today. Minmin 今天十十。"),
    sc("What is in Minmin's bowl of noodles?", M4, "easy",
       ["A. Meatballs, an egg, tomatoes and vegetables", "B. Only meat", "C. Only rice", "D. Fruit"], "A",
       "原文：In this bowl, there are meatballs, an egg, tomatoes and other vegetables."),
    sc("Why is it a tradition to have noodles on birthdays?", M4, "normal",
       ["A. Noodles are cheap", "B. Parents wish children good health and a happy long life", "C. Children love noodles", "D. It's easy to cook"], "B",
       "原文：It is the parents' wish for their child. They wish the child good health and a happy long life."),
    sc("What does Grandma say is in the noodles?", M4, "normal",
       ["A. Only soup", "B. Lots of love", "C. Money", "D. Toys"], "B",
       "原文：there was lots of love in the bowl. 碗里有满满的爱。"),
    sc("What did Grandma have at ten years old?", M4, "hard",
       ["A. Birthday noodles", "B. Cake", "C. Only soup noodles", "D. A big dinner"], "C",
       "原文：Only soup noodles. 奶奶小时候只有清汤面。"),
    sc("What does Minmin want to put in his parents' birthday noodles?", M4, "hard",
       ["A. Only meat", "B. Whatever he likes (open-ended)", "C. Nothing", "D. Cake"], "B",
       "故事引发思考：你想给爸妈的生日面里放什么？开放性题目。"),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U5 Visiting places (Visiting Venice)
# ═══════════════════════════════════════════════════════════════
M5 = "Reading Comp: U5 Visiting places"
READING_U5 = [
    sc("Where is Venice?", M5, "easy",
       ["A. France", "B. Italy", "C. Spain", "D. China"], "B",
       "原文：Venice is a famous city in Italy. 威尼斯是意大利的著名城市。"),
    sc("Where are the houses in Venice?", M5, "easy",
       ["A. On hills", "B. By the waterways", "C. In the forest", "D. On the beach"], "B",
       "原文：The houses are all by the waterways. 房屋都建在水路旁边。"),
    sc("What is the special boat in Venice called?", M5, "easy",
       ["A. Gondola", "B. Canoe", "C. Yacht", "D. Ship"], "A",
       "原文：This special type of boat is called 'gondola'. 这种特别的船叫 gondola（贡多拉）。"),
    sc("What can visitors find in Venice?", M5, "normal",
       ["A. Tall buildings", "B. Restaurants, cafes and shops by the waterways", "C. Only museums", "D. No bridges"], "B",
       "原文：There are many restaurants and cafes by the waterways. And there are many interesting shops too."),
    sc("What is Venice also famous for?", M5, "normal",
       ["A. Mountains", "B. Museums", "C. Skiing", "D. Deserts"], "B",
       "原文：Venice is also famous for its museums. 威尼斯还以博物馆闻名。"),
    sc("Why do visitors like Venice?", M5, "hard",
       ["A. Because of the colourful houses, bridges and boats", "B. Because it's cold", "C. Because of the food", "D. Because of the museums only"], "A",
       "游客喜欢威尼斯的原因是多彩的房屋、桥梁和船只等。"),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U6 It's autumn! (Autumn in Saihanba)
# ═══════════════════════════════════════════════════════════════
M6 = "Reading Comp: U6 It's autumn!"
READING_U6 = [
    sc("Where is Minmin's family?", M6, "easy",
       ["A. In Shanghai", "B. In Saihanba National Forest Park", "C. In Beijing", "D. At school"], "B",
       "原文：Minmin's family are in Saihanba National Forest Park."),
    sc("What does Minmin enjoy doing in Saihanba?", M6, "easy",
       ["A. Swimming", "B. Picking apples and watching birds", "C. Sleeping", "D. Reading"], "B",
       "原文：He enjoys picking apples and watching different birds."),
    sc("What was Saihanba like many years ago?", M6, "normal",
       ["A. A city", "B. Only one tree could be seen", "C. A lake", "D. A desert"], "B",
       "原文：not many years ago, you could see only one tree in Saihanba."),
    sc("Who is working hard to make Saihanba wonderful?", M6, "normal",
       ["A. Children", "B. Workers", "C. Animals", "D. Teachers"], "B",
       "原文：Look at those workers. They are working hard."),
    sc("How does Minmin feel about autumn in Saihanba?", M6, "easy",
       ["A. Sad", "B. Excited, thinks it's beautiful", "C. Angry", "D. Bored"], "B",
       "原文：Minmin is excited to see the large colourful forest and golden fields."),
    sc("What kind of poem might you write for autumn according to the project?", M6, "hard",
       ["A. About spring", "B. Beginning with 'It's autumn' and 4-5 lines", "C. About winter", "D. About school"], "B",
       "原文：To write a poem for autumn, you can begin with the heading: 'It's autumn'. Then write four or five lines."),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U7 My healthy breakfast (The best breakfast)
# ═══════════════════════════════════════════════════════════════
M7 = "Reading Comp: U7 My healthy breakfast"
READING_U7 = [
    sc("What do Mr Baozi and Ms Shaomai give people?", M7, "easy",
       ["A. Vitamins", "B. Energy", "C. Protein", "D. Money"], "B",
       "原文：We give people energy. 他们给人能量。"),
    sc("What does Ms Egg have a lot of?", M7, "easy",
       ["A. Energy", "B. Protein and vitamin D", "C. Fat", "D. Sugar"], "B",
       "原文：I have a lot of protein and vitamin D."),
    sc("Why does Ms Egg say she helps children?", M7, "normal",
       ["A. Because she's delicious", "B. She helps children grow", "C. She's cheap", "D. She's pretty"], "B",
       "原文：I help children grow. 鸡蛋帮助孩子成长。"),
    sc("What does Miss Soya Milk claim to have?", M7, "easy",
       ["A. Animal protein", "B. Vegetable protein", "C. Only vitamin D", "D. Fat"], "B",
       "原文：I have a lot of vegetable protein. People need it."),
    sc("How does James feel about sandwiches?", M7, "normal",
       ["A. Boring", "B. Favourite breakfast, healthy and easy to make", "C. Tasty but unhealthy", "D. Too sweet"], "B",
       "原文：That's my favourite breakfast. ... healthy and easy to make."),
    sc("What does Shenshen like for breakfast?", M7, "normal",
       ["A. Sandwich", "B. Baozi", "C. Soya milk", "D. Egg"], "B",
       "原文：Baozi is my favourite breakfast. 包子是申申最喜欢的早餐。"),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U8 Be honest (The empty pot)
# ═══════════════════════════════════════════════════════════════
M8 = "Reading Comp: U8 Be honest"
READING_U8 = [
    sc("What does the old king want to find?", M8, "easy",
       ["A. A new flower", "B. A new king", "C. A pot", "D. A child"], "B",
       "原文：An old king wants to find a new king."),
    sc("What does the king give each child?", M8, "easy",
       ["A. A pot", "B. A flower seed", "C. A flower", "D. Money"], "B",
       "原文：He gives each child a flower seed."),
    sc("What does the little boy do with the seed?", M8, "easy",
       ["A. He throws it away", "B. Plants it in his pot and waters it every day", "C. He eats it", "D. He gives it away"], "B",
       "原文：A little boy plants the seed in his pot and waters it every day."),
    sc("Why doesn't the boy's seed grow?", M8, "hard",
       ["A. He forgets to water", "B. The seed was probably fake / not real", "C. He doesn't have a pot", "D. There's no sun"], "B",
       "故事寓意：诚实是金，种子是煮过的（不发芽）。其他孩子用假种子长出假花。男孩坚持浇水。"),
    sc("What does the little boy's pot look like at the end?", M8, "easy",
       ["A. Full of flowers", "B. Empty", "C. Cracked", "D. Big"], "B",
       "原文：Only the boy's pot is empty. 只有男孩的花盆是空的。"),
    sc("Why does the king choose the boy as the new king?", M8, "hard",
       ["A. He's handsome", "B. He's the only one who is honest (others cheated with fake flowers)", "C. He's rich", "D. He's clever"], "B",
       "故事寓意：诚实的孩子才是真正的国王，因为他没有用假的（没种出花的种子）。"),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U9 What time is it? (What is time?)
# ═══════════════════════════════════════════════════════════════
M9 = "Reading Comp: U9 What time is it?"
READING_U9 = [
    sc("What does the text compare time to?", M9, "normal",
       ["A. Money", "B. A line or a circle", "C. A river", "D. A mountain"], "B",
       "原文：Is time a line or maybe a circle? 时间像一条线还是一个圆？"),
    sc("What words do people use to call time?", M9, "easy",
       ["A. Money, hours", "B. Minutes, hours, days, weeks", "C. Spring, summer", "D. Earth, moon"], "B",
       "原文：People call me 'minutes' 'hours' 'days' 'weeks' and more."),
    sc("Can you see time?", M9, "easy",
       ["A. Yes", "B. No, you can't see it but it's always with you", "C. Only at night", "D. Only in spring"], "B",
       "原文：You can't see me. But I'm with you all the time."),
    sc("Time is different on the earth and on the moon. According to the text, time can be ____.", M9, "normal",
       ["A. only night", "B. night for someone and day for others", "C. only spring", "D. only a line"], "B",
       "原文：I can be night for someone and day for others."),
    sc("What are 'then' and 'now' in the text?", M9, "hard",
       ["A. Two different times", "B. Both are time", "C. Two places", "D. Two people"], "B",
       "原文：'Then' and 'now' are both of me. 过去和现在都是时间。"),
    sc("What's the main message of the text?", M9, "hard",
       ["A. Time is invisible but always with you", "B. Time is money", "C. Time stops at midnight", "D. Time is a circle"], "A",
       "中心思想：时间看不见摸不着，但一直在我们身边。"),
]


# ═══════════════════════════════════════════════════════════════
# Reading Comp — U10 Weather (Special weather reporters)
# ═══════════════════════════════════════════════════════════════
M10 = "Reading Comp: U10 Weather"
READING_U10 = [
    sc("Who is on his way to his grandparents' house?", M10, "easy",
       ["A. Tortoise", "B. Little Lamb", "C. Dragonfly", "D. Spider"], "B",
       "原文：Little Lamb is on his way to his grandparents' house."),
    sc("What does Tortoise tell Little Lamb to bring?", M10, "easy",
       ["A. Food", "B. An umbrella", "C. A book", "D. A hat"], "B",
       "原文：you'd better take an umbrella with you."),
    sc("How does Tortoise know rain is coming?", M10, "normal",
       ["A. He sees clouds", "B. There are water drops on his back", "C. He hears thunder", "D. He feels cold"], "B",
       "原文：Look at the water drops on my back. It means the rain is coming soon."),
    sc("What do dragonflies do before rain?", M10, "normal",
       ["A. Fly high", "B. Fly low", "C. Sing", "D. Sleep"], "B",
       "原文：Dragonflies are flying low. 蜻蜓飞得低。"),
    sc("What do spiders do before rain?", M10, "normal",
       ["A. Build new webs", "B. Take back their webs", "C. Eat flies", "D. Sleep"], "B",
       "原文：spiders are taking back their webs. 蜘蛛收回网。"),
    sc("What happens at the end of the story?", M10, "easy",
       ["A. It stops raining", "B. Heavy rain starts to fall", "C. Little Lamb plays outside", "D. Tortoise goes home"], "B",
       "原文：Very soon, a heavy rain starts to fall."),
]


# ═══════════════════════════════════════════════════════════════
# Sound 拼读专项题
# ═══════════════════════════════════════════════════════════════

# U1 Sound = w (wall, water, window, Wednesday, we, work, with, well, winter...)
SOUND_W_KP = "Sound 拼读: U1 /w/"
SOUND_W = [
    # 找出含 /w/ 音的单词
    sc("Which word has the /w/ sound like in 'wall'?", SOUND_W_KP, "easy",
       ["A. ball", "B. wall", "C. tall", "D. hall"], "B",
       "wall /w/ 开头，ball/tall/hall /b/ 或 /h/。"),
    sc("Which word begins with the /w/ sound?", SOUND_W_KP, "easy",
       ["A. water", "B. teacher", "C. student", "D. library"], "A",
       "water /w/ 开头，其余单词以辅音或元音开头，无 /w/ 音。"),
    sc("Which word has the /w/ sound like 'Wednesday'?", SOUND_W_KP, "easy",
       ["A. Sunday", "B. Friday", "C. Wednesday", "D. Monday"], "C",
       "Wednesday 以 /w/ 开头（W 字母发 /w/ 音）。"),
    sc("Which word does NOT begin with /w/?", SOUND_W_KP, "easy",
       ["A. we", "B. with", "C. work", "D. school"], "D",
       "school 以 /s/ 开头，不是 /w/。"),
    sc("Which word rhymes with 'wall' (same ending /ɔːl/)?", SOUND_W_KP, "normal",
       ["A. well", "B. small", "C. ball", "D. tell"], "B",
       "small 与 wall 押韵（都含 /ɔːl/）。"),
    # 听音选词
    sc("Which word has TWO /w/ sounds?", SOUND_W_KP, "hard",
       ["A. window", "B. water", "C. winter", "D. welcome"], "A",
       "window 拼为 w-i-n-d-o-w，含两个 w，发 /w/ 音两次。"),
    sc("Pick the word that starts with /w/:", SOUND_W_KP, "easy",
       ["A. very", "B. work", "C. seven", "D. river"], "B",
       "work /w/ 开头。"),
    sc("Which sentence uses /w/ correctly?", SOUND_W_KP, "normal",
       ["A. We walk to school.", "B. He is tvelve years old.", "C. The book is on the ball.", "D. They live in a tell house."], "A",
       "A 句 we/walk/w 都以 /w/ 开头。"),
    sc("Which of these words begins with the sound /w/?", SOUND_W_KP, "easy",
       ["A. win", "B. bin", "C. tin", "D. pin"], "A",
       "win /w/，bin/tin/pin /b/ /t/ /p/。"),
    sc("Which word is NOT a 'w' word?", SOUND_W_KP, "easy",
       ["A. wallet", "B. week", "C. wash", "D. garden"], "D",
       "garden 以 /g/ 开头，不是 /w/。"),
    # 判断
    tf("The word 'welcome' starts with the /w/ sound.", SOUND_W_KP, "easy", True, "w 字母发 /w/ 音。"),
    tf("The word 'water' has only ONE /w/ sound.", SOUND_W_KP, "normal", True, "water 中 w 在开头发一次 /w/。"),
    tf("The word 'swim' starts with /w/.", SOUND_W_KP, "hard", False, "swim 中 w 不发音，'sw' 整体发 /sw/。"),
    tf("The letter 'w' in English always makes the /w/ sound.", SOUND_W_KP, "hard", False, "在 swim, write, who 中 w 不发音或发其他音。"),
    tf("Wednesday starts with the sound /w/.", SOUND_W_KP, "easy", True, "W 发 /w/ 音。"),
    tf("The word 'which' starts with /w/.", SOUND_W_KP, "hard", True, "which 中 wh 发 /w/（在 who/what/where 等词中）。"),
]


# U2 Sound = x (excited, exam, expensive, fox, box, six)
SOUND_X_KP = "Sound 拼读: U2 /x/"
SOUND_X = [
    sc("The 'x' in 'excited' sounds like:", SOUND_X_KP, "easy",
       ["A. /z/", "B. /ks/", "C. /gz/", "D. silent"], "C",
       "excited 中 x 发 /gz/（如 exercise, exam）。"),
    sc("Which word starts with /x/ (sounds like /gz/)?", SOUND_X_KP, "easy",
       ["A. box", "B. six", "C. excited", "D. fox"], "C",
       "excited 开头 x 发 /gz/。"),
    sc("In which word does 'x' sound like /ks/?", SOUND_X_KP, "easy",
       ["A. excited", "B. exam", "C. box", "D. exit"], "C",
       "box 末尾 x 发 /ks/。"),
    sc("Which sentence uses /x/ correctly (as in 'excited')?", SOUND_X_KP, "normal",
       ["A. I have six apples.", "B. He is excited about the game.", "C. The fox runs fast.", "D. There is a box."], "B",
       "B 句 excited 词头 x 发 /gz/。"),
    sc("Which word has 'x' at the END sounding /ks/?", SOUND_X_KP, "easy",
       ["A. excited", "B. exam", "C. exercise", "D. exit"], "B",
       "exam 末尾 x 发 /ks/。"),
    sc("Pick the word with /x/ at the beginning:", SOUND_X_KP, "easy",
       ["A. taxi", "B. box", "C. six", "D. fox"], "A",
       "taxi 中 x 词中发 /ks/，但开头发音最明显：x-ray / exit / excited 等。"),
    sc("Which word contains the /x/ sound?", SOUND_X_KP, "easy",
       ["A. apple", "B. orange", "C. exam", "D. banana"], "C",
       "exam 含 /gz/。"),
    sc("Which word does NOT have the /x/ sound?", SOUND_X_KP, "easy",
       ["A. box", "B. fox", "C. six", "D. cow"], "D",
       "cow 不含 /x/。"),
    sc("The plural 'boxes' has /x/ sound how many times?", SOUND_X_KP, "hard",
       ["A. Once", "B. Twice", "C. Three times", "D. None"], "B",
       "boxes 中 x 发 /ks/（结尾 x）+ s 发 /z/；x 本身发 /ks/。"),
    sc("Which of these is a word starting with /x/?", SOUND_X_KP, "easy",
       ["A. xylophone", "B. yellow", "C. xerox", "D. All"], "D",
       "xylophone（乐器）和 xerox（复印）都以 /z/ 开头。"),
    tf("The word 'excited' starts with /gz/.", SOUND_X_KP, "easy", True, "excited 词头 x 发 /gz/。"),
    tf("In 'box', the letter 'x' sounds like /ks/.", SOUND_X_KP, "easy", True, "词尾 x 总是发 /ks/。"),
    tf("In 'six', the letter 'x' sounds like /gz/.", SOUND_X_KP, "normal", False, "词尾 x 发 /ks/，不是 /gz/。"),
    tf("The word 'exercise' starts with the sound /gz/.", SOUND_X_KP, "hard", True, "exercise 词头 x 发 /gz/。"),
    tf("In 'exam', the letter 'x' makes two sounds.", SOUND_X_KP, "hard", False, "exam 词中 x 发 /gz/，只发一次（不像辅音 + s 那样分开发）。"),
]


# U6 Sound = y (year, yellow, yes, young, your)
SOUND_Y_KP = "Sound 拼读: U6 /j/"
SOUND_Y = [
    sc("At the beginning of a word, 'y' often sounds like:", SOUND_Y_KP, "easy",
       ["A. /j/ (like 'yes')", "B. /iː/ (like 'bee')", "C. /aɪ/ (like 'my')", "D. /ɔː/ (like 'four')"], "A",
       "词首 y 在辅音前常发 /j/（yes, year, you）。"),
    sc("Which word begins with /j/?", SOUND_Y_KP, "easy",
       ["A. yes", "B. my", "C. cry", "D. play"], "A",
       "yes 词首 y 发 /j/。"),
    sc("In which word does 'y' NOT sound like /j/?", SOUND_Y_KP, "easy",
       ["A. yellow", "B. yard", "C. young", "D. gym"], "D",
       "gym 中 y 发 /dʒ/（gym 整体发 /dʒɪm/）。"),
    sc("Which word begins with /j/?", SOUND_Y_KP, "easy",
       ["A. your", "B. year", "C. yolk", "D. All"], "D",
       "your / year / yolk 词首 y 都发 /j/。"),
    sc("In 'young students plant a young pine tree', how many /j/ sounds?", SOUND_Y_KP, "hard",
       ["A. One", "B. Two", "C. Three", "D. Four"], "B",
       "young 中 y 发 /j/；students 没有；plant 没有；young 第二个又发一次 = 2 个 /j/。"),
    sc("Which sentence starts with a /j/ sound word?", SOUND_Y_KP, "normal",
       ["A. You are a good friend.", "B. My cat is cute.", "C. They play in the yard.", "D. I eat a yellow apple."], "A",
       "A 句 You 词首 y 发 /j/。"),
    sc("In which word does 'y' sound like /j/?", SOUND_Y_KP, "easy",
       ["A. cry", "B. baby", "C. yellow", "D. happy"], "C",
       "yellow 词首 y 发 /j/；cry/baby/happy 词尾 y 发 /iː/ 或 /ɪ/。"),
    sc("Pick the word that begins with the /j/ sound:", SOUND_Y_KP, "easy",
       ["A. year", "B. cookie", "C. beach", "D. school"], "A",
       "year 词首 y 发 /j/。"),
    sc("Which of these words starts with /j/?", SOUND_Y_KP, "easy",
       ["A. yoga", "B. van", "C. wagon", "D. All"], "D",
       "yoga 词首 y 发 /j/。van/wagon 词首不是 /j/。"),
    sc("In 'How ...!' (the structure), 'y' is used in:", SOUND_Y_KP, "normal",
       ["A. yes", "B. you", "C. your", "D. All"], "D",
       "yes/you/your 词首 y 都发 /j/。"),
    tf("The word 'yes' begins with the /j/ sound.", SOUND_Y_KP, "easy", True, "y 发 /j/。"),
    tf("The word 'my' begins with the /j/ sound.", SOUND_Y_KP, "easy", False, "my 词首 m，不是 /j/。"),
    tf("The word 'year' begins with /j/.", SOUND_Y_KP, "easy", True, "year 词首 y 发 /j/。"),
    tf("In 'yellow', the 'y' makes the /j/ sound.", SOUND_Y_KP, "easy", True, "yellow 词首 y 发 /j/。"),
    tf("The word 'you' starts with /j/.", SOUND_Y_KP, "easy", True, "you 词首 y 发 /j/。"),
]


# U7 Sound = sh (shout, ship, sheep, shirt, she)
SOUND_SH_KP = "Sound 拼读: U7 /ʃ/"
SOUND_SH = [
    sc("The 'sh' digraph sounds like:", SOUND_SH_KP, "easy",
       ["A. /s/", "B. /ʃ/ (shhh)", "C. /tʃ/", "D. /k/"], "B",
       "sh 发 /ʃ/（如 ship 中 sh）。"),
    sc("Which word begins with /ʃ/?", SOUND_SH_KP, "easy",
       ["A. ship", "B. skip", "C. slip", "D. snip"], "A",
       "ship 词首 sh 发 /ʃ/；skip/slip/snip 词首单 s。"),
    sc("Which word begins with the 'sh' sound?", SOUND_SH_KP, "easy",
       ["A. shop", "B. stop", "C. chop", "D. drop"], "A",
       "shop 词首 sh 发 /ʃ/。"),
    sc("Which word has the /ʃ/ sound?", SOUND_SH_KP, "easy",
       ["A. fish", "B. fit", "C. hit", "D. sit"], "A",
       "fish 中 sh 发 /ʃ/。"),
    sc("Which word does NOT have the /ʃ/ sound?", SOUND_SH_KP, "easy",
       ["A. sheep", "B. shout", "C. shirt", "D. spider"], "D",
       "spider 含 sp，不含 sh。"),
    sc("Pick the word that begins with 'sh':", SOUND_SH_KP, "easy",
       ["A. chair", "B. share", "C. pear", "D. bear"], "B",
       "share 词首 sh 发 /ʃ/；chair 含 ch 发 /tʃ/。"),
    sc("Which sentence has TWO words starting with /ʃ/?", SOUND_SH_KP, "hard",
       ["A. She sells shells.", "B. The cat is small.", "C. He has a pen.", "D. I see a dog."], "A",
       "She sells shells: She (sh) + sells (s) + shells (sh)。shells 词首 sh + s 音节。"),
    sc("In which word does 'sh' make the /ʃ/ sound?", SOUND_SH_KP, "easy",
       ["A. English", "B. Spanish", "C. Chinese", "D. French"], "D",
       "French 中 sh 不在词首，但 English/Spanish/Chinese 词尾 sh 都发 /ʃ/。"),
    sc("Which word begins with /ʃ/?", SOUND_SH_KP, "easy",
       ["A. shoe", "B. zoo", "C. two", "D. who"], "A",
       "shoe 词首 sh 发 /ʃ/。"),
    sc("Which word has the 'sh' sound at the END?", SOUND_SH_KP, "easy",
       ["A. fish", "B. fix", "C. fit", "D. fig"], "A",
       "fish 词尾 sh 发 /ʃ/。"),
    tf("The word 'ship' starts with the /ʃ/ sound.", SOUND_SH_KP, "easy", True, "sh 发 /ʃ/。"),
    tf("The word 'shop' starts with /s/ + /h/ as two sounds.", SOUND_SH_KP, "hard", False, "sh 是一个 /ʃ/ 音，不是 /s/+/h/。"),
    tf("The word 'wash' has the /ʃ/ sound at the end.", SOUND_SH_KP, "easy", True, "wash 词尾 sh 发 /ʃ/。"),
    tf("The word 'shy' starts with /ʃ/.", SOUND_SH_KP, "easy", True, "shy 词首 sh 发 /ʃ/。"),
    tf("The word 'sheep' has TWO /ʃ/ sounds.", SOUND_SH_KP, "hard", False, "sheep 中只有一个 sh，发一次 /ʃ/。"),
]


# U9 Sound = qu (question, queen, quiet, quarter, quilt)
SOUND_QU_KP = "Sound 拼读: U9 /kw/"
SOUND_QU = [
    sc("The 'qu' digraph usually sounds like:", SOUND_QU_KP, "easy",
       ["A. /k/", "B. /kw/", "C. /w/", "D. /kjuː/"], "B",
       "qu 在词首发 /kw/（如 question, queen）。"),
    sc("Which word begins with /kw/?", SOUND_QU_KP, "easy",
       ["A. queen", "B. green", "C. seen", "D. clean"], "A",
       "queen 词首 qu 发 /kw/。"),
    sc("Which word begins with the /kw/ sound?", SOUND_QU_KP, "easy",
       ["A. quiet", "B. diet", "C. violet", "D. comet"], "A",
       "quiet 词首 qu 发 /kw/。"),
    sc("Which word does NOT start with /kw/?", SOUND_QU_KP, "easy",
       ["A. quarter", "B. question", "C. quality", "D. banana"], "D",
       "banana 不含 qu 词首。"),
    sc("In which word does 'qu' make the /kw/ sound?", SOUND_QU_KP, "easy",
       ["A. unique", "B. antique", "C. mosquito", "D. quote"], "D",
       "quote 词首 qu 发 /kw/；antique/unique/mosquito 中 qu 词中，发 /k/。"),
    sc("Which sentence starts with a /kw/ word?", SOUND_QU_KP, "normal",
       ["A. Quick, come here!", "B. The dog is fast.", "C. I see a bird.", "D. She is happy."], "A",
       "Quick 词首 qu 发 /kw/。"),
    sc("Which word has the /kw/ sound at the beginning?", SOUND_QU_KP, "easy",
       ["A. quench", "B. bench", "C. french", "D. wrench"], "A",
       "quench 词首 qu 发 /kw/。"),
    sc("Pick the word with /kw/ sound:", SOUND_QU_KP, "easy",
       ["A. quilt", "B. guilt", "C. built", "D. All"], "D",
       "quilt/guilt/built 词中 u 发 /ɪ/，qu/gu 发 /k/，但词首发 qu 的 quilt /kwɪlt/。"),
    sc("How many /kw/ sounds are in 'quiet question'?", SOUND_QU_KP, "hard",
       ["A. One", "B. Two", "C. Three", "D. None"], "B",
       "quiet 词首 qu /kw/ + question 词首 qu /kw/ = 2 个 /kw/。"),
    sc("Which word contains the /kw/ sound at the start?", SOUND_QU_KP, "easy",
       ["A. square", "B. sphere", "C. sphere", "D. square"], "A",
       "square 词首 sq 发 /skw/，含 /kw/ 因素。"),
    tf("The word 'queen' starts with /kw/.", SOUND_QU_KP, "easy", True, "qu 词首发 /kw/。"),
    tf("The word 'antique' starts with /kw/.", SOUND_QU_KP, "hard", False, "antique 中 qu 词中，发 /k/。"),
    tf("The word 'quick' starts with the /kw/ sound.", SOUND_QU_KP, "easy", True, "qu 词首发 /kw/。"),
    tf("The letter 'q' is always followed by 'u' in English words.", SOUND_QU_KP, "easy", True, "qu 组合在英语里基本必出现。"),
    tf("The word 'quilt' has TWO syllables and BOTH start with /kw/.", SOUND_QU_KP, "hard", False, "quilt 是单音节，qu 只发一次 /kw/。"),
]


# ═══════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════
READING_ALL = (
    READING_U1 + READING_U2 + READING_U3 + READING_U4 + READING_U5
    + READING_U6 + READING_U7 + READING_U8 + READING_U9 + READING_U10
)
SOUND_ALL = SOUND_W + SOUND_X + SOUND_Y + SOUND_SH + SOUND_QU

ALL_QUESTIONS = READING_ALL + SOUND_ALL


async def seed():
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        from models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # 找教材版本
        version = (await db.execute(
            select(TextbookVersion).where(TextbookVersion.code == "SH-5-4-2025A")
        )).scalars().first()
        if not version:
            print("[ERROR] 找不到教材版本 SH-5-4-2025A，请先跑 _seed_textbook_grade4a.py")
            return

        # 加载所有 Unit（按 code 索引）
        units = (await db.execute(
            select(TextbookUnit).where(TextbookUnit.version_id == version.id)
        )).scalars().all()
        code_to_unit = {u.code: u for u in units}
        print(f"加载 {len(units)} 个 Unit")

        # 题库：去重同名
        existing_bank = (await db.execute(
            select(QuestionBank).where(
                and_(QuestionBank.grade == "四年级", QuestionBank.subject == "英语",
                     QuestionBank.title == BANK_TITLE)
            )
        )).scalars().first()
        if existing_bank:
            print(f"删除旧题库：{existing_bank.title} (id={existing_bank.id})")
            await db.delete(existing_bank)
            await db.commit()

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

        # 插入所有题
        random_seed = 42
        # 按 knowledge_point 前缀分发到 Unit
        KP_TO_UNIT = {
            "Reading Comp: U1": "U1",
            "Reading Comp: U2": "U2",
            "Reading Comp: U3": "U3",
            "Reading Comp: U4": "U4",
            "Reading Comp: U5": "U5",
            "Reading Comp: U6": "U6",
            "Reading Comp: U7": "U7",
            "Reading Comp: U8": "U8",
            "Reading Comp: U9": "U9",
            "Reading Comp: U10": "U10",
            "Sound 拼读: U1": "U1",
            "Sound 拼读: U2": "U2",
            "Sound 拼读: U6": "U6",
            "Sound 拼读: U7": "U7",
            "Sound 拼读: U9": "U9",
        }

        n_q = 0
        n_links = 0
        for q_data in ALL_QUESTIONS:
            q = Question(bank_id=bank.id, **q_data)
            db.add(q)
            await db.flush()
            n_q += 1
            # 关联 Unit
            kp = q_data["knowledge_point"]
            for prefix, unit_code in KP_TO_UNIT.items():
                if kp.startswith(prefix):
                    unit = code_to_unit.get(unit_code)
                    if unit:
                        relevance = "primary"
                        db.add(QuestionUnit(
                            question_id=q.id, unit_id=unit.id, relevance=relevance
                        ))
                        n_links += 1
                    break

        await db.commit()
        print(f"成功导入 {n_q} 道题 + {n_links} 条 Unit 关联")

        # 验证分布
        rc = (await db.execute(
            select(Question.difficulty, func.count(Question.id))
            .where(Question.bank_id == bank.id)
            .group_by(Question.difficulty)
        )).all()
        print("\n难度分布：")
        for d, c in rc:
            print(f"  {d}: {c}")

        qt = (await db.execute(
            select(Question.question_type, func.count(Question.id))
            .where(Question.bank_id == bank.id)
            .group_by(Question.question_type)
        )).all()
        print("\n题型分布：")
        for t, c in qt:
            print(f"  {t}: {c}")


if __name__ == "__main__":
    asyncio.run(seed())
