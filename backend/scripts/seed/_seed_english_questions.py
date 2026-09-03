"""Seed 题库：上海四年级英语 50 题（单选题）"""
import asyncio
import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Question, QuestionBank

# ── 题库配置 ──
BANK_TITLE = "上海牛津版四年级英语"
BANK_DESC = "覆盖词汇、语法、句型、阅读理解等核心知识点，适配上海小学四年级英语教学大纲"

QUESTIONS = [
    # ━━━ 语法：现在进行时 ━━━
    {
        "knowledge_point": "现在进行时",
        "difficulty": "normal",
        "content": "Look! The boys ______ football on the playground.",
        "options": ["A. play", "B. are playing", "C. is playing", "D. plays"],
        "correct_answer": "B",
        "explanation": "Look! 表示动作正在进行，用现在进行时 be + doing。boys 是复数，用 are playing。",
    },
    {
        "knowledge_point": "现在进行时",
        "difficulty": "normal",
        "content": "She ______ a book in the library now.",
        "options": ["A. read", "B. reads", "C. is reading", "D. are reading"],
        "correct_answer": "C",
        "explanation": "now 表示正在进行的动作，she 是第三人称单数，用 is reading。",
    },
    {
        "knowledge_point": "现在进行时",
        "difficulty": "easy",
        "content": "— What are you doing?  — I ______ my homework.",
        "options": ["A. do", "B. did", "C. am doing", "D. does"],
        "correct_answer": "C",
        "explanation": "问句用现在进行时，答句也用现在进行时：am doing。",
    },
    {
        "knowledge_point": "现在进行时",
        "difficulty": "hard",
        "content": "Be quiet! The baby ______ in the next room.",
        "options": ["A. sleeps", "B. is sleeping", "C. sleep", "D. sleeping"],
        "correct_answer": "B",
        "explanation": "Be quiet! 提示动作正在进行，用 is sleeping。",
    },

    # ━━━ 语法：情态动词 can ━━━
    {
        "knowledge_point": "情态动词 can",
        "difficulty": "normal",
        "content": "Tom ______ swim very well. He is a good swimmer.",
        "options": ["A. can", "B. can't", "C. is", "D. do"],
        "correct_answer": "A",
        "explanation": "表示能力用 can，后接动词原形 swim。",
    },
    {
        "knowledge_point": "情态动词 can",
        "difficulty": "easy",
        "content": "— Can you play the piano?  — Yes, I ______.",
        "options": ["A. can", "B. can't", "C. do", "D. am"],
        "correct_answer": "A",
        "explanation": "Can 开头的一般疑问句，肯定回答用 Yes, I can。",
    },
    {
        "knowledge_point": "情态动词 can",
        "difficulty": "normal",
        "content": "The dog ______ fly. It doesn't have wings.",
        "options": ["A. can", "B. can't", "C. is", "D. does"],
        "correct_answer": "B",
        "explanation": "狗不会飞，表示否定能力用 can't。",
    },
    {
        "knowledge_point": "情态动词 can",
        "difficulty": "hard",
        "content": "— ______ you speak English?  — Yes, a little.",
        "options": ["A. Can", "B. Do", "C. Are", "D. Is"],
        "correct_answer": "A",
        "explanation": "speak 是动词原形，问'能力'用 Can。Do 后接实义动词原形，但问'会说英语'这种能力常用 Can。",
    },

    # ━━━ 语法：一般现在时 ━━━
    {
        "knowledge_point": "一般现在时",
        "difficulty": "normal",
        "content": "My mother ______ to work by bus every day.",
        "options": ["A. go", "B. goes", "C. going", "D. went"],
        "correct_answer": "B",
        "explanation": "every day 表示习惯性动作，用一般现在时。my mother 是第三人称单数，go 变 goes。",
    },
    {
        "knowledge_point": "一般现在时",
        "difficulty": "easy",
        "content": "The sun ______ in the east.",
        "options": ["A. rise", "B. rises", "C. is rising", "D. rose"],
        "correct_answer": "B",
        "explanation": "客观真理用一般现在时，the sun 是第三人称单数，rise 加 -s。",
    },
    {
        "knowledge_point": "一般现在时",
        "difficulty": "normal",
        "content": "I usually ______ up at 7:00 in the morning.",
        "options": ["A. get", "B. gets", "C. getting", "D. got"],
        "correct_answer": "A",
        "explanation": "I 是第一人称，用动词原形 get。",
    },
    {
        "knowledge_point": "一般现在时",
        "difficulty": "hard",
        "content": "He ______ TV every evening, but last night he ______ a book.",
        "options": ["A. watches / reads", "B. watch / read", "C. watches / readed", "D. watches / read"],
        "correct_answer": "D",
        "explanation": "前句 every evening 用一般现在时 watches；后句 last night 用过去时 read（read 的过去式同形）。",
    },

    # ━━━ 语法：介词 ━━━
    {
        "knowledge_point": "介词 in/on/at",
        "difficulty": "easy",
        "content": "The cat is ______ the table.",
        "options": ["A. in", "B. on", "C. at", "D. under"],
        "correct_answer": "B",
        "explanation": "猫在桌子上面用 on（在表面上）。",
    },
    {
        "knowledge_point": "介词 in/on/at",
        "difficulty": "normal",
        "content": "We have a party ______ Saturday afternoon.",
        "options": ["A. in", "B. on", "C. at", "D. /"],
        "correct_answer": "B",
        "explanation": "具体某天的上午/下午/晚上用 on：on Saturday afternoon。",
    },
    {
        "knowledge_point": "介词 in/on/at",
        "difficulty": "normal",
        "content": "My birthday is ______ July.",
        "options": ["A. in", "B. on", "C. at", "D. for"],
        "correct_answer": "A",
        "explanation": "月份前用 in：in July。",
    },
    {
        "knowledge_point": "介词 under/near/behind",
        "difficulty": "easy",
        "content": "The ball is ______ the chair. Can you see it?",
        "options": ["A. on", "B. in", "C. under", "D. at"],
        "correct_answer": "C",
        "explanation": "球在椅子下面用 under。",
    },

    # ━━━ 词汇辨析 ━━━
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "normal",
        "content": "I'm ______ than my sister. I'm 1.6m tall.",
        "options": ["A. tall", "B. taller", "C. tallest", "D. more tall"],
        "correct_answer": "B",
        "explanation": "than 提示用比较级，tall 的比较级是 taller。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "Please be ______ when you cross the road.",
        "options": ["A. happy", "B. careful", "C. hungry", "D. thirsty"],
        "correct_answer": "B",
        "explanation": "过马路要「小心」，用 careful。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "normal",
        "content": "The book is ______ interesting ______ I can't put it down.",
        "options": ["A. so / that", "B. such / that", "C. too / to", "D. very / and"],
        "correct_answer": "A",
        "explanation": "so + 形容词 + that 从句：so + 形容词 + that 从句：如此有趣以至于放不下。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "normal",
        "content": "I have ______ homework to do today.",
        "options": ["A. too many", "B. too much", "C. many", "D. a lot"],
        "correct_answer": "B",
        "explanation": "homework 是不可数名词，用 too much 修饰。too many 修饰可数名词复数。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "The dog is running ______ a cat.",
        "options": ["A. after", "B. at", "C. in", "D. on"],
        "correct_answer": "A",
        "explanation": "run after 表示「追赶」。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "hard",
        "content": "He is the ______ boy in our class.",
        "options": ["A. tall", "B. taller", "C. tallest", "D. more tall"],
        "correct_answer": "C",
        "explanation": "in our class 表示范围，用最高级 tallest。",
    },

    # ━━━ 句型：特殊疑问句 ━━━
    {
        "knowledge_point": "特殊疑问句",
        "difficulty": "easy",
        "content": "— ______ is your art teacher?  — Mr Wang.",
        "options": ["A. What", "B. Who", "C. Where", "D. How"],
        "correct_answer": "B",
        "explanation": "问「谁」用 Who。",
    },
    {
        "knowledge_point": "特殊疑问句",
        "difficulty": "normal",
        "content": "— ______ do you go to school?  — By bike.",
        "options": ["A. What", "B. Where", "C. How", "D. When"],
        "correct_answer": "C",
        "explanation": "问交通方式用 How。by bike 回答的是方式。",
    },
    {
        "knowledge_point": "特殊疑问句",
        "difficulty": "normal",
        "content": "— ______ is the science museum?  — It's next to the park.",
        "options": ["A. What", "B. Who", "C. Where", "D. Why"],
        "correct_answer": "C",
        "explanation": "问地点用 Where。next to the park 回答的是位置。",
    },
    {
        "knowledge_point": "特殊疑问句",
        "difficulty": "hard",
        "content": "— ______ time is it?  — It's half past four.",
        "options": ["A. What", "B. How", "C. Which", "D. Where"],
        "correct_answer": "A",
        "explanation": "问时间用 What time...?",
    },

    # ━━━ 句型：祈使句 ━━━
    {
        "knowledge_point": "祈使句",
        "difficulty": "easy",
        "content": "______ quiet in the library, please.",
        "options": ["A. Be", "B. Do", "C. Don't", "D. Is"],
        "correct_answer": "A",
        "explanation": "祈使句以动词原形开头，quiet 是形容词，用 Be quiet。",
    },
    {
        "knowledge_point": "祈使句",
        "difficulty": "normal",
        "content": "______ run in the classroom! It's dangerous.",
        "options": ["A. Do", "B. Be", "C. Don't", "D. Doesn't"],
        "correct_answer": "C",
        "explanation": "否定祈使句用 Don't + 动词原形：Don't run。",
    },
    {
        "knowledge_point": "祈使句",
        "difficulty": "easy",
        "content": "Let ______ clean the blackboard together.",
        "options": ["A. we", "B. us", "C. our", "D. ours"],
        "correct_answer": "B",
        "explanation": "let 是动词，后面用宾格 us。Let us = Let's。",
    },

    # ━━━ 阅读理解 ━━━
    {
        "knowledge_point": "阅读理解",
        "difficulty": "normal",
        "content": "Tom likes animals. He has a dog and two cats. The dog is brown and white. It can play football. The cats are black. They like to sleep on the sofa. How many cats does Tom have?",
        "options": ["A. One", "B. Two", "C. Three", "D. Four"],
        "correct_answer": "B",
        "explanation": "文中明确说 He has a dog and two cats，所以有 2 只猫。",
    },
    {
        "knowledge_point": "阅读理解",
        "difficulty": "normal",
        "content": "It's Sunday morning. Amy is cleaning her room. Her brother is doing homework. Her father is cooking in the kitchen. What is Amy doing?",
        "options": ["A. Doing homework", "B. Cooking", "C. Cleaning her room", "D. Sleeping"],
        "correct_answer": "C",
        "explanation": "文中明确说 Amy is cleaning her room。",
    },
    {
        "knowledge_point": "阅读理解",
        "difficulty": "hard",
        "content": "Mike goes to the park on Sundays. He likes to fly kites there. Sometimes he feeds the ducks in the lake. He goes home at 5 p.m. What does Mike do in the park?",
        "options": ["A. He swims in the lake.", "B. He flies kites and feeds ducks.", "C. He plays football.", "D. He reads books."],
        "correct_answer": "B",
        "explanation": "文中提到 fly kites 和 feeds the ducks，B 选项完整概括。",
    },

    # ━━━ 完形填空 ━━━
    {
        "knowledge_point": "完形填空",
        "difficulty": "normal",
        "content": "It's a sunny day. The pupils are ______ a picnic in the park. They ______ sandwiches and juice. They are very happy.",
        "options": ["A. having / have", "B. have / have", "C. having / having", "D. have / having"],
        "correct_answer": "C",
        "explanation": "第一空 are + having 构成现在进行时；第二空 they + having 也是现在进行时（They are having...，省略了 are 但在选项中 having 最准确，因为前面 They are 已给出）。",
    },
    {
        "knowledge_point": "完形填空",
        "difficulty": "hard",
        "content": "Last winter, I ______ to Harbin with my family. We ______ ice and ______ a big snowman. It was fun!",
        "options": ["A. go / see / make", "B. went / saw / made", "C. go / see / made", "D. went / see / make"],
        "correct_answer": "B",
        "explanation": "Last winter 提示用一般过去时，三个动词都要用过去式：went / saw / made。",
    },

    # ━━━ 语法：there be 句型 ━━━
    {
        "knowledge_point": "There be 句型",
        "difficulty": "normal",
        "content": "______ a big tree in front of the house.",
        "options": ["A. There is", "B. There are", "C. It is", "D. It has"],
        "correct_answer": "A",
        "explanation": "a big tree 是单数，用 There is。",
    },
    {
        "knowledge_point": "There be 句型",
        "difficulty": "normal",
        "content": "______ any water in the bottle?",
        "options": ["A. Is there", "B. Are there", "C. Is it", "D. Has"],
        "correct_answer": "A",
        "explanation": "water 是不可数名词，用 Is there 提问。",
    },
    {
        "knowledge_point": "There be 句型",
        "difficulty": "hard",
        "content": "There ______ some birds in the tree, but now there ______ only one.",
        "options": ["A. were / is", "B. was / are", "C. are / were", "D. is / are"],
        "correct_answer": "A",
        "explanation": "第一句 some birds 是复数且表示过去，用 were；第二句 only one 是单数现在，用 is。",
    },

    # ━━━ 情景交际 ━━━
    {
        "knowledge_point": "情景交际",
        "difficulty": "easy",
        "content": "当你想问别人「你会做什么「时，应该说：",
        "options": ["A. What can you do?", "B. What do you do?", "C. What are you doing?", "D. What did you do?"],
        "correct_answer": "A",
        "explanation": "问「能力/会做什么「用 What can you do?",
    },
    {
        "knowledge_point": "情景交际",
        "difficulty": "easy",
        "content": "别人帮了你，你应该说：",
        "options": ["A. You're welcome.", "B. Thank you.", "C. I'm sorry.", "D. Excuse me."],
        "correct_answer": "B",
        "explanation": "别人帮忙后应说 Thank you。You're welcome 是回应感谢时说的。",
    },
    {
        "knowledge_point": "情景交际",
        "difficulty": "normal",
        "content": "你想告诉同学「我通常7点吃早餐「，应该说：",
        "options": ["A. I usually eat breakfast at 7.", "B. I usually eats breakfast at 7.", "C. I am eating breakfast at 7.", "D. I usually eating breakfast at 7."],
        "correct_answer": "A",
        "explanation": "usually + 一般现在时，I 后用动词原形 eat。",
    },
    {
        "knowledge_point": "情景交际",
        "difficulty": "hard",
        "content": "当你想礼貌地打断别人时，应该说：",
        "options": ["A. Shut up!", "B. Excuse me.", "C. Go away!", "D. Be quiet!"],
        "correct_answer": "B",
        "explanation": "礼貌地打断/引起注意用 Excuse me。",
    },

    # ━━━ 语法：形容词比较级 ━━━
    {
        "knowledge_point": "形容词比较级",
        "difficulty": "normal",
        "content": "This pen is ______ than that one. It writes better.",
        "options": ["A. cheap", "B. cheaper", "C. cheapest", "D. more cheap"],
        "correct_answer": "B",
        "explanation": "than 提示用比较级，cheap 的比较级是 cheaper。",
    },
    {
        "knowledge_point": "形容词比较级",
        "difficulty": "hard",
        "content": "Shanghai is ______ than Suzhou, but ______ than Beijing.",
        "options": ["A. bigger / smaller", "B. big / small", "C. bigger / small", "D. big / smaller"],
        "correct_answer": "A",
        "explanation": "第一空 than 用比较级 bigger；第二空 than 也用比较级 smaller。",
    },

    # ━━━ 语法：物主代词 ━━━
    {
        "knowledge_point": "物主代词",
        "difficulty": "easy",
        "content": "This is ______ book. The blue one is ______.",
        "options": ["A. my / mine", "B. mine / my", "C. my / my", "D. mine / mine"],
        "correct_answer": "A",
        "explanation": "第一空后有名词 book，用形容词性物主代词 my；第二空后无名词，用名词性物主代词 mine。",
    },
    {
        "knowledge_point": "物主代词",
        "difficulty": "normal",
        "content": "— Whose ruler is this?  — It's ______.",
        "options": ["A. she", "B. her", "C. hers", "D. herself"],
        "correct_answer": "C",
        "explanation": "问「谁的」用名词性物主代词 hers（= her ruler）。",
    },

    # ━━━ 词汇：动物/食物/颜色 ━━━
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "The ______ is jumping. It has a long tail.",
        "options": ["A. fish", "B. rabbit", "C. monkey", "D. elephant"],
        "correct_answer": "C",
        "explanation": "jumping + long tail 描述的是 monkey（猴子）。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "I'd like a glass of ______, please. I'm very thirsty.",
        "options": ["A. bread", "B. cake", "C. juice", "D. rice"],
        "correct_answer": "C",
        "explanation": "thirsty（渴）对应 juice（果汁）。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "normal",
        "content": "Apples are ______. Bananas are ______.",
        "options": ["A. red / yellow", "B. yellow / red", "C. green / blue", "D. red / green"],
        "correct_answer": "A",
        "explanation": "苹果通常是红色 red，香蕉成熟后是黄色 yellow。",
    },

    # ━━━ 语法：动词过去式 ━━━
    {
        "knowledge_point": "动词过去式",
        "difficulty": "normal",
        "content": "Yesterday I ______ a film with my friends.",
        "options": ["A. see", "B. saw", "C. seen", "D. seeing"],
        "correct_answer": "B",
        "explanation": "Yesterday 提示用一般过去时，see 的过去式是 saw。",
    },
    {
        "knowledge_point": "动词过去式",
        "difficulty": "normal",
        "content": "We ______ to the zoo last weekend.",
        "options": ["A. go", "B. goes", "C. went", "D. going"],
        "correct_answer": "C",
        "explanation": "last weekend 提示用过去时，go 的过去式是 went。",
    },
    {
        "knowledge_point": "动词过去式",
        "difficulty": "hard",
        "content": "She ______ her homework and then ______ TV yesterday.",
        "options": ["A. did / watch", "B. do / watched", "C. did / watched", "D. does / watched"],
        "correct_answer": "C",
        "explanation": "yesterday 提示都用过去时：did 和 watched。",
    },

    # ━━━ 词汇：月份/星期 ━━━
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "The first month of the year is ______.",
        "options": ["A. January", "B. February", "C. March", "D. December"],
        "correct_answer": "A",
        "explanation": "一年中的第一个月是 January（一月）。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "We have Maths, English and ______ on Fridays.",
        "options": ["A. Monday", "B. Music", "C. Science", "D. Chinese"],
        "correct_answer": "B",
        "explanation": "选项 B Music（音乐）是科目，其他三项要么是星期（Monday）要么已列出。",
    },

    # ━━━ 句型：Let's 和 be going to ━━━
    {
        "knowledge_point": "句型：Let's",
        "difficulty": "easy",
        "content": "______ go to the park together!",
        "options": ["A. Let's", "B. Let we", "C. Lets", "D. Let me"],
        "correct_answer": "A",
        "explanation": "Let's = Let us，表示建议「我们一起「。",
    },
    {
        "knowledge_point": "句型：be going to",
        "difficulty": "normal",
        "content": "It ______ rain tomorrow. Take your umbrella.",
        "options": ["A. is", "B. is going to", "C. will going to", "D. going to"],
        "correct_answer": "B",
        "explanation": "根据天气/迹象预测将来用 be going to。It is going to rain。",
    },
    {
        "knowledge_point": "句型：be going to",
        "difficulty": "normal",
        "content": "They ______ visit their grandparents this weekend.",
        "options": ["A. are going to", "B. is going to", "C. are going", "D. is going"],
        "correct_answer": "A",
        "explanation": "they 对应 are，用 are going to + 动词原形。",
    },

    # ━━━ 阅读理解补充 ━━━
    {
        "knowledge_point": "阅读理解",
        "difficulty": "hard",
        "content": "Ben is 10 years old. He likes science best. On Saturdays, he goes to the science club. He learns about robots and space. He wants to be a scientist in the future. What does Ben want to be?",
        "options": ["A. A teacher", "B. A scientist", "C. A doctor", "D. A driver"],
        "correct_answer": "B",
        "explanation": "文中明确说 He wants to be a scientist in the future。",
    },
    {
        "knowledge_point": "阅读理解",
        "difficulty": "hard",
        "content": "Lily has a new pen pal from Australia. Her name is Anna. Anna likes swimming and drawing. She can speak a little Chinese. Lily is going to teach her. What can Anna do?",
        "options": ["A. She can teach Chinese.", "B. She can swim and draw.", "C. She can play football.", "D. She can cook."],
        "correct_answer": "B",
        "explanation": "文中说 Anna likes swimming and drawing，所以她会游泳和画画。",
    },

    # ━━━ 完形填空补充 ━━━
    {
        "knowledge_point": "完形填空",
        "difficulty": "normal",
        "content": "— ______ the matter?  — I'm ______. I want some water.",
        "options": ["A. What's / hungry", "B. What's / thirsty", "C. What / thirsty", "D. What's / tired"],
        "correct_answer": "B",
        "explanation": "What's the matter? 是固定句型。want some water 说明是 thirsty（渴）。",
    },
    {
        "knowledge_point": "完形填空",
        "difficulty": "hard",
        "content": "— ______ you like some tea?  — Yes, ______.",
        "options": ["A. Would / please", "B. Do / please", "C. Are / please", "D. Would / I do"],
        "correct_answer": "A",
        "explanation": "Would you like...? 是礼貌询问的固定句型，肯定回答 Yes, please。",
    },

    # ━━━ 语法：第三人称单数 ━━━
    {
        "knowledge_point": "一般现在时",
        "difficulty": "normal",
        "content": "He ______ lunch at school every day.",
        "options": ["A. have", "B. has", "C. having", "D. haves"],
        "correct_answer": "B",
        "explanation": "he 是第三人称单数，have 的三单形式是 has。",
    },
    {
        "knowledge_point": "一般现在时",
        "difficulty": "normal",
        "content": "The train ______ at 8:30 every morning.",
        "options": ["A. leave", "B. leaves", "C. is leaving", "D. leaved"],
        "correct_answer": "B",
        "explanation": "the train 是第三人称单数，用 leaves。",
    },
    {
        "knowledge_point": "一般现在时",
        "difficulty": "easy",
        "content": "I ______ my room every Sunday.",
        "options": ["A. clean", "B. cleans", "C. cleaning", "D. cleaned"],
        "correct_answer": "A",
        "explanation": "I 是第一人称，用动词原形 clean。",
    },

    # ━━━ 词汇：方位介词 ━━━
    {
        "knowledge_point": "介词 in/on/at/under",
        "difficulty": "normal",
        "content": "The picture is ______ the wall.",
        "options": ["A. in", "B. on", "C. at", "D. under"],
        "correct_answer": "B",
        "explanation": "画在墙的表面用 on the wall。in the wall 表示嵌在墙里面（如窗户）。",
    },
    {
        "knowledge_point": "介词 in/on/at/under",
        "difficulty": "normal",
        "content": "I have a meeting ______ 9:00 ______ Monday morning.",
        "options": ["A. at / in", "B. on / at", "C. at / on", "D. in / on"],
        "correct_answer": "C",
        "explanation": "具体时刻前用 at：at 9:00；具体某天的上午用 on：on Monday morning。",
    },

    # ━━━ 情景交际补充 ━━━
    {
        "knowledge_point": "情景交际",
        "difficulty": "easy",
        "content": "上课时你想上厕所，你应该说：",
        "options": ["A. I want to go.", "B. Excuse me. Can I go to the toilet?", "C. Let me out!", "D. I'm hungry."],
        "correct_answer": "B",
        "explanation": "礼貌地说 Excuse me，然后询问 Can I go to the toilet?",
    },
    {
        "knowledge_point": "情景交际",
        "difficulty": "normal",
        "content": "你问朋友周末通常做什么，应该说：",
        "options": ["A. What do you do on weekends?", "B. What are you doing?", "C. Did you do?", "D. What will you do?"],
        "correct_answer": "A",
        "explanation": "usually / on weekends 提示一般现在时，用 What do you do...?",
    },

    # ━━━ 语法：疑问词选择 ━━━
    {
        "knowledge_point": "特殊疑问句",
        "difficulty": "normal",
        "content": "— ______ is your favourite subject?  — English.",
        "options": ["A. What", "B. Which", "C. Who", "D. Where"],
        "correct_answer": "A",
        "explanation": "问「什么」科目用 What。Which 用于在有限选择中选一个，What 用于开放式提问。",
    },
    {
        "knowledge_point": "特殊疑问句",
        "difficulty": "normal",
        "content": "— ______ students are there in your class?  — Forty.",
        "options": ["A. How many", "B. How much", "C. How old", "D. How long"],
        "correct_answer": "A",
        "explanation": "students 是可数名词复数，问数量用 How many。",
    },

    # ━━━ 词汇：高频词 ━━━
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "My father is a ______. He works in a hospital.",
        "options": ["A. teacher", "B. doctor", "C. driver", "D. farmer"],
        "correct_answer": "B",
        "explanation": "在医院工作的职业是 doctor（医生）。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "easy",
        "content": "It's cold outside. Please ______ your coat.",
        "options": ["A. take off", "B. put on", "C. turn on", "D. look at"],
        "correct_answer": "B",
        "explanation": "天冷要「穿上「外套，用 put on。take off 是脱掉。",
    },
    {
        "knowledge_point": "词汇辨析",
        "difficulty": "normal",
        "content": "Don't ______ late for school again!",
        "options": ["A. be", "B. do", "C. have", "D. go"],
        "correct_answer": "A",
        "explanation": "be late for 是固定搭配「迟到」。",
    },

    # ━━━ 阅读理解：生活场景 ━━━
    {
        "knowledge_point": "阅读理解",
        "difficulty": "normal",
        "content": "Sam gets up at 6:30. He has breakfast at 7:00. He goes to school at 7:30. School starts at 8:00. What time does school start?",
        "options": ["A. 6:30", "B. 7:00", "C. 7:30", "D. 8:00"],
        "correct_answer": "D",
        "explanation": "文中明确说 School starts at 8:00。",
    },
    {
        "knowledge_point": "阅读理解",
        "difficulty": "hard",
        "content": "There is a new park near my home. It's big and beautiful. There are many flowers and trees. We can play on the grass and ride bikes on the path. I like the park very much. What can we do in the park?",
        "options": ["A. We can watch films.", "B. We can play on the grass and ride bikes.", "C. We can swim in the lake.", "D. We can climb the mountains."],
        "correct_answer": "B",
        "explanation": "文中说 play on the grass 和 ride bikes on the path，B 选项正确。",
    },

    # ━━━ 语法：a/an 用法 ━━━
    {
        "knowledge_point": "冠词 a/an",
        "difficulty": "easy",
        "content": "I have ______ apple and ______ banana for my snack.",
        "options": ["A. a / a", "B. an / a", "C. a / an", "D. an / an"],
        "correct_answer": "B",
        "explanation": "apple 以元音音素开头用 an；banana 以辅音音素开头用 a。",
    },
    {
        "knowledge_point": "冠词 a/an",
        "difficulty": "normal",
        "content": "He is ______ honest boy. We all like him.",
        "options": ["A. a", "B. an", "C. the", "D. /"],
        "correct_answer": "B",
        "explanation": "honest 的 h 不发音，以元音音素开头，用 an。",
    },

    # ━━━ 完形填空：购物场景 ━━━
    {
        "knowledge_point": "完形填空",
        "difficulty": "normal",
        "content": "— Can I help you?  — Yes. I want ______ pair of shoes, please.",
        "options": ["A. a", "B. an", "C. the", "D. /"],
        "correct_answer": "A",
        "explanation": "a pair of 是固定搭配「一双/一副」。",
    },
    {
        "knowledge_point": "完形填空",
        "difficulty": "hard",
        "content": "It was Sunday. Tom ______ up late. He ______ breakfast and then ______ to the park with his dog. They ______ happy there.",
        "options": ["A. got / had / went / were", "B. get / has / go / are", "C. got / has / went / were", "D. get / have / go / are"],
        "correct_answer": "A",
        "explanation": "整段是过去时，所有动词都用过去式：got / had / went / were。",
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
                QuestionBank.subject == "英语",
            )
        )).scalars().first()

        if existing:
            print(f"题库已存在：{existing.title} (id={existing.id})")
            # 检查题目数
            q_count = (await db.execute(
                select(func.count(Question.id)).where(Question.bank_id == existing.id)
            )).scalar_one()
            print(f"当前题目数：{q_count}")
            if q_count > 0:
                print("题库已有题目，跳过 seed。如需重置请先删除题库。")
                return

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
