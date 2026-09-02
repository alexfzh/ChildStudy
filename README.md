# 🌱 学业成长系统

> 隐私优先的家庭学情追踪平台 · 数据完全本地存储 · AI 分析靠"导出→外部AI→粘回"

![version](https://img.shields.io/badge/version-1.7.1-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![privacy](https://img.shields.io/badge/privacy-100%25%20local-orange)

## ✨ 核心理念

**数据归家长，AI 归外部。** 所有学业数据存储在本机 SQLite，不上传任何服务器。需要 AI 分析时，一键导出上下文 → 粘贴给任意 AI → 把报告粘回系统。

## 🎯 功能特性

| 模块 | 能力 |
|------|------|
| 🔐 **多用户认证** | 家长 + 孩子账号，JWT 登录，数据按家庭/角色隔离 |
| 👶 **多孩子档案** | 独立档案 + 一键切换，最多支持 4 个孩子 |
| 📝 **考试管理** | 科目、得分、排名、知识点标签、错题自动关联 |
| 📚 **作业追踪** | 完成情况、正确率、用时、难度自评 |
| 📙 **错题本** | 错题录入 + 艾宾浩斯复习提醒 + 掌握度跟踪 |
| ✏️ **题库练习** | 自定义题 bank → 组卷 → 答题 → 评分 → 错题回流 |
| 📖 **教材学习进度** | 按教材版本/单元跟踪学习进度 + 成就积分 |
| 🎨 **Big Task 作品** | 单元项目作品提交 + 图片上传 + AI/家长评语 |
| 🏷️ **知识点标签库** | 按年级/科目/类别管理 KP，题与 KP 多对多关联 |
| 📊 **可视化看板** | 成绩趋势、能力雷达、科目对比、多孩子对比 |
| 🌱 **成长时间轴** | 里程碑、荣誉、日常记录按月归档 |
| 📏 **生长发育** | 身高/体重/BMI/视力 曲线跟踪 |
| 💭 **社交情感** | 情绪评分、社交活动、自信度记录 |
| 🎨 **兴趣特长** | 活动类型、技能等级、时长跟踪 |
| 🎁 **奖励商城** | 积分兑换 + 等级排名 + 成就墙 |
| 🤖 **AI 报告管理** | 导出上下文 → 外部 AI 分析 → 导入报告存档 |
| ⚙️ **系统设置** | 多孩子对比 + 配置管理 |
| ℹ️ **关于系统** | 版本信息 + 升级日志 + 技术栈 |

## 🏗️ 技术架构

```
┌──────────────────────────┐      HTTP/API      ┌──────────────────────────┐
│  Vue 3 + Vite            │  ────────────────► │  FastAPI (Python)        │
│  + Tailwind CSS          │   /api/*           │  + SQLAlchemy 2.0        │
│  + Element Plus          │                    │  + SQLite (aiosqlite)    │
│  + ECharts               │                    │  + Pydantic v2           │
│  + Pinia                 │                    │                          │
└──────────────────────────┘                    └──────────────────────────┘
                                                       │
                                         本地 AI 分析（可选）：
                                         导出 Markdown → DeepSeek/Kimi/ChatGPT
                                          → 粘贴报告 → 导入系统存档
```

## 🚀 快速开始

### 环境要求

- **Python** ≥ 3.10
- **Node.js** ≥ 18
- **npm** ≥ 9

### 一键启动（推荐，Windows）

双击 `start.bat`，脚本会自动：
1. 创建 Python 虚拟环境并安装后端依赖
2. 安装前端 npm 依赖
3. 启动后端（`127.0.0.1:8000`）与前端开发服务器（`127.0.0.1:5173`）

### 手动启动

#### 后端

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # 编辑配置（可选）

# 开发模式（热重载）
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 生产模式
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

后端运行在 `http://127.0.0.1:8000`，OpenAPI 文档在 `http://127.0.0.1:8000/docs`

#### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 `http://127.0.0.1:5173`，API 请求通过 Vite proxy 转发到后端。

### 生产部署

```bash
cd frontend
npm run build      # 生成 dist/

cd ../backend
python main.py     # 后端自动托管前端 dist/ 静态文件
```

访问 `http://127.0.0.1:8000` 即可。

## 📂 项目结构

```
ChildStudy/
├── backend/
│   ├── main.py                   # FastAPI 入口（含 SPA 静态托管 + lifespan）
│   ├── config.py                 # 配置（pydantic-settings，读 .env）
│   ├── database.py               # SQLAlchemy 异步引擎 + init_db
│   ├── models.py                 # 数据模型（32 张表，见下方 schema）
│   ├── schemas.py                # Pydantic 请求/响应模式
│   ├── requirements.txt          # Python 依赖
│   ├── .env.example              # 环境变量模板
│   ├── routers/                  # API 路由（23 个 router）
│   │   ├── auth.py               #   多用户认证（setup/登录/JWT/子账号）
│   │   ├── children.py           #   孩子档案 CRUD + 年级历史
│   │   ├── exams.py              #   考试记录
│   │   ├── homework.py           #   作业追踪
│   │   ├── timeline.py           #   成长时间轴
│   │   ├── dashboard.py          #   看板聚合 + 多孩子对比
│   │   ├── reports.py            #   AI 报告 CRUD + 导出上下文
│   │   ├── config.py             #   公开系统配置
│   │   ├── knowledge_points.py   #   知识点标签库
│   │   ├── wrong_questions.py    #   错题本 + 复习记录
│   │   ├── growth.py             #   生长发育
│   │   ├── social_emotional.py   #   社交情感
│   │   ├── interests.py          #   兴趣特长
│   │   ├── rewards.py            #   奖励商城 + 成就 + 积分
│   │   ├── question_banks.py     #   题库 + 练习 + 推荐
│   │   ├── textbook.py           #   教材版本/单元
│   │   ├── study_progress.py     #   教材学习进度
│   │   ├── project_works.py      #   Big Task 作品
│   │   ├── kp_unit.py            #   知识点-单元关联
│   │   ├── question_kp.py        #   题-知识点关联
│   │   ├── kp_progress.py        #   KP 细粒度掌握度
│   │   ├── import_export.py      #   导入/导出（CSV）
│   │   └── system.py             #   版本 + 升级日志
│   ├── utils/
│   │   ├── analysis.py           #   统计计算（趋势、雷达数据）
│   │   └── grade.py              #   年级历史工具
│   ├── data/                     # SQLite 数据库（自动创建，勿提交 git）
│   └── uploads/                  # 上传文件（作品图片等）
│
├── frontend/
│   ├── src/
│   │   ├── main.js               # 入口（Vue + Element Plus + Pinia + Router）
│   │   ├── App.vue               # 根组件
│   │   ├── api/index.js          # axios 封装（所有后端 API）
│   │   ├── stores/
│   │   │   ├── auth.js           # Pinia：登录态 + JWT + 角色
│   │   │   └── child.js          # Pinia：孩子状态 + 切换
│   │   ├── router/index.js       # 22 个路由
│   │   ├── components/
│   │   │   ├── Layout.vue        # 侧边栏布局（5 分组 + 系统）
│   │   │   ├── ChildSelector.vue # 孩子切换下拉框
│   │   │   ├── SubjectPicker.vue # 科目选择器
│   │   │   ├── AchIcon.vue       # 成就图标组件
│   │   │   └── charts/           # ECharts 封装
│   │   │       ├── BaseChart.vue
│   │   │       ├── RadarChart.vue
│   │   │       ├── SubjectBarChart.vue
│   │   │       └── TrendLineChart.vue
│   │   ├── views/                # 22 个页面
│   │   │   ├── Login.vue         #   登录
│   │   │   ├── Setup.vue         #   首次启动
│   │   │   ├── Dashboard.vue     #   家长看板
│   │   │   ├── Children.vue      #   孩子档案
│   │   │   ├── Exams.vue         #   考试管理
│   │   │   ├── ExamAnalysis.vue  #   考试分析
│   │   │   ├── Homework.vue      #   作业追踪
│   │   │   ├── StudyProgress.vue #   教材学习进度
│   │   │   ├── ProjectWorks.vue  #   Big Task 作品
│   │   │   ├── KnowledgePoints.vue # 知识点标签库
│   │   │   ├── WrongQuestions.vue # 错题本
│   │   │   ├── QuestionBank.vue  #   题库练习
│   │   │   ├── Exercise.vue      #   开始练习
│   │   │   ├── AIReports.vue     #   AI 报告管理
│   │   │   ├── Timeline.vue      #   成长时间轴
│   │   │   ├── Growth.vue        #   生长发育
│   │   │   ├── SocialEmotional.vue # 社交情感
│   │   │   ├── Interests.vue     #   兴趣特长
│   │   │   ├── Rewards.vue       #   奖励商城
│   │   │   ├── Achievements.vue  #   成就墙
│   │   │   ├── Settings.vue      #   系统设置
│   │   │   └── About.vue         #   关于系统
│   │   ├── constants/subjects.js #   科目常量
│   │   └── style.css             #   全局样式
│   ├── vite.config.js            #   Vite 配置（proxy → 后端）
│   ├── tailwind.config.js        #   Tailwind CSS
│   ├── postcss.config.js
│   └── package.json
│
├── start.bat                     # Windows 一键启动
├── start.sh                      # macOS/Linux 一键启动
├── README.md                     # 本文件
├── .gitignore
└── LICENSE
```

## 🗄️ 数据库 Schema（33 张表）

### 多用户认证
| 表名 | 说明 |
|------|------|
| `families` | 家庭（v1.6.0 起数据按家庭隔离） |
| `users` | 账号（parent/child 角色，归属家庭） |

### 核心业务
| 表名 | 说明 |
|------|------|
| `children` | 孩子档案（姓名、年级、学校、生日） |
| `exams` | 考试记录（科目、得分、排名、知识点） |
| `exam_questions` | 考试-题目关联（含每题得分） |
| `homeworks` | 作业记录（完成率、正确率、用时） |
| `wrong_questions` | 错题本（题文、错因、掌握度、复习计划） |
| `wrong_question_reviews` | 错题复习记录 |
| `timelines` | 成长时间轴事件 |
| `growth_records` | 生长发育（身高/体重/BMI/视力） |
| `social_emotional_records` | 社交情感（情绪/社交/自信度） |
| `interest_records` | 兴趣特长（活动类型/技能等级） |

### 激励系统
| 表名 | 说明 |
|------|------|
| `rewards` | 奖励物品（名称/成本/图标） |
| `child_rewards` | 孩子兑换记录 |
| `achievements` | 成就定义（代码/条件/图标） |
| `child_achievements` | 孩子获得成就记录 |
| `child_ranks` | 科目等级排名（星星数） |
| `points_log` | 积分流水 |

### 教材与知识点
| 表名 | 说明 |
|------|------|
| `textbook_versions` | 教材版本（出版社/年级/学期） |
| `textbook_units` | 教材单元（标题/结构/Big Task） |
| `study_progress` | 学习进度（完成率/正确率/掌握状态） |
| `unit_achievement_logs` | 单元成就积分记录 |
| `project_works` | Big Task 作品（提交/AI评分/评语） |
| `knowledge_points` | 知识点（科目/类别/年级） |
| `knowledge_point_units` | 知识点-单元关联 |
| `kp_study_progress` | KP 掌握度（child × KP × unit） |

### 题库与练习
| 表名 | 说明 |
|------|------|
| `question_banks` | 题库（年级/科目/标题） |
| `questions` | 题目（题干/选项/答案/解析） |
| `question_knowledge_points` | 题-KP 多对多关联 |
| `question_units` | 题-单元关联 |
| `exercises` | 练习记录（答题/评分） |

### 其他
| 表名 | 说明 |
|------|------|
| `ai_reports` | AI 学情报告（Markdown 存档） |
| `grade_history` | 年级变更历史 |

## 🔌 API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/setup-status` | GET | 首次启动检测 |
| `/api/auth/setup` | POST | 创建第一个家长账号 |
| `/api/auth/login` | POST | JWT 登录 |
| `/api/auth/logout` | POST | 登出（客户端清 token） |
| `/api/auth/me` | GET | 当前用户 + 可访问孩子列表 |
| `/api/auth/users` | GET | 本家庭账号列表 |
| `/api/auth/users` | POST | 家长创建子账号 |
| `/api/health` | GET | 健康检查 |
| `/api/config` | GET | 公开配置（max_children） |
| `/api/system/version` | GET | 系统版本信息 |
| `/api/system/upgrade-log` | GET | 升级历史 |
| `/api/children` | GET/POST | 孩子档案列表/创建 |
| `/api/children/{id}` | GET/PUT/DELETE | 单个档案 CRUD |
| `/api/children/{id}/grade-history` | GET/POST/DELETE | 年级历史 |
| `/api/exams` | GET/POST | 考试记录列表/创建 |
| `/api/exams/{id}` | PUT/DELETE | 更新/删除 |
| `/api/homeworks` | GET/POST | 作业记录 |
| `/api/timeline` | GET/POST | 时间轴事件 |
| `/api/growth/{child_id}` | GET/POST/PUT/DELETE | 生长发育 |
| `/api/social-emotional/{child_id}` | 同上 | 社交情感 |
| `/api/interests/{child_id}` | 同上 | 兴趣特长 |
| `/api/dashboard/{child_id}` | GET | 看板聚合数据 |
| `/api/dashboard/compare/all` | GET | 多孩子对比 |
| `/api/reports` | GET/POST | AI 报告列表/创建 |
| `/api/reports/{id}` | GET/PUT/DELETE | 单条报告 |
| `/api/reports/export/context` | GET | 导出学情上下文（Markdown） |
| `/api/knowledge-points` | GET/POST | 知识点 CRUD |
| `/api/knowledge-points/subjects` | GET | 科目列表 |
| `/api/knowledge-points/categories` | GET | 分类列表 |
| `/api/knowledge-points/grade-levels` | GET | 年级列表 |
| `/api/wrong-questions` | GET/POST | 错题列表/录入 |
| `/api/wrong-questions/{id}` | GET/PUT/DELETE | 单条错题 |
| `/api/wrong-questions/stats/{child_id}` | GET | 错题统计 |
| `/api/wrong-questions/today/{child_id}` | GET | 今日待复习 |
| `/api/wrong-questions/{id}/review` | POST | 复习记录 |
| `/api/rewards/ranks/{child_id}` | GET | 等级排名 |
| `/api/rewards/points/{child_id}` | GET | 积分余额 |
| `/api/rewards/shop/{child_id}` | GET | 奖励商店 |
| `/api/rewards/redeem/{child_id}/{reward_id}` | POST | 兑换奖励 |
| `/api/rewards/history/{child_id}` | GET | 兑换历史 |
| `/api/rewards/rewards` | GET/POST | 奖励物品 CRUD |
| `/api/rewards/achievements` | GET/POST | 成就定义 CRUD |
| `/api/rewards/achievements/{child_id}` | GET | 孩子成就 |
| `/api/rewards/points-log/{child_id}` | GET | 积分流水 |
| `/api/rewards/exam-reward/{exam_id}` | POST | 为考试补发积分/成就（幂等，同一考试只发一次） |
| `/api/rewards/backfill/{child_id}` | POST | 回填某孩子全部考试/成就奖励（重跑不重复发分） |
| `/api/question-banks` | GET/POST | 题库列表/创建 |
| `/api/question-banks/{id}` | GET/PUT/DELETE | 单个题库 |
| `/api/question-banks/{id}/questions` | GET/POST | 题目列表/创建 |
| `/api/question-banks/exercises` | GET | 练习记录 |
| `/api/question-banks/exercises/start` | POST | 开始练习 |
| `/api/question-banks/exercises/{id}/submit` | POST | 提交答案 |
| `/api/question-banks/exercises/{id}` | GET | 练习详情 |
| `/api/question-banks/recommend/{child_id}` | GET | 智能推荐 |
| `/api/textbook/versions` | GET | 教材版本列表 |
| `/api/textbook/versions/{id}` | GET | 单个版本 |
| `/api/textbook/versions/{id}/units` | GET | 单元列表 |
| `/api/textbook/units/{id}` | GET | 单个单元 |
| `/api/study-progress/child/{id}/version/{vid}` | GET | 学习进度汇总 |
| `/api/study-progress/child/{id}/unit/{uid}` | GET | 单元进度 |
| `/api/project-works` | GET/POST | 作品列表/提交 |
| `/api/project-works/{id}/upload` | POST | 上传图片 |
| `/api/project-works/{id}/review` | PUT | 评语 |
| `/api/project-works/{id}` | DELETE | 删除 |
| `/api/knowledge-point-units/unit/{unit_id}` | GET | 单元知识点 |
| `/api/kp-progress/child/{cid}/unit/{uid}` | GET | 单元 KP 掌握度 |
| `/api/kp-progress/child/{cid}/version/{vid}` | GET | 版本 KP 掌握度 |
| `/api/import-export/exams` | GET/POST | 考试导入/导出（CSV） |
| `/api/import-export/homeworks` | GET/POST | 作业导入/导出（CSV） |

完整交互式文档：启动后端后访问 `http://127.0.0.1:8000/docs`

## 🤖 AI 分析工作流

本系统**不内置 AI 引擎**，采用"导出 → 外部 AI → 粘回"模式：

```
┌──────────────┐    导出 Markdown      ┌──────────────┐    粘贴报告     ┌──────────────┐
│  学业成长系统  │  ──────────────────►  │  外部 AI      │  ────────────► │  学业成长系统  │
│  (本机 SQLite)│                      │ (DeepSeek等)  │               │ (报告存档)    │
└──────────────┘                      └──────────────┘               └──────────────┘
```

1. 进入「AI 报告管理」→ 点"导出当前数据为上下文" → 一键复制 Markdown
2. 粘贴给 DeepSeek / Kimi / ChatGPT / Gemini 等任意 AI
3. 复制 AI 输出的报告 → 回到「AI 报告管理」→ "导入新报告" → 保存

> 💡 **推荐 DeepSeek**：注册即送额度，中文教育场景表现优秀。https://platform.deepseek.com

## 🔒 隐私设计

- ✅ 所有数据存储在本机 SQLite（`backend/data/childstudy.db`）
- ✅ 上传文件仅保存在 `backend/uploads/`
- ✅ 不上传任何学业数据到云端
- ✅ AI 分析靠手动"导出→粘贴→导入"，无自动调用
- ✅ 前端为静态文件，可离线运行
- ✅ 不收集任何遥测/分析数据
- ✅ 认证使用本地 JWT，无第三方鉴权服务

## ⚙️ 环境变量（.env）

```env
# 应用（LAN 访问需改 0.0.0.0；只本地用可留 127.0.0.1）
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=false

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/childstudy.db

# 多孩子上限
MAX_CHILDREN=4

# 上传
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=10

# ====== 多用户认证（v1.6.0） ======
# 生成随机密钥：python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET=change-me-in-production-please-use-32-bytes-random
JWT_EXPIRE_SECONDS=86400

# CORS 白名单（逗号分隔）。LAN 访问追加对应地址，如 http://192.168.1.50:5173
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000
```

> `.env` 文件不会提交到 git，请自行保管。

## 🗺️ 路线图

- [x] ~~多用户家庭账号（父母/祖父母权限）~~ → v1.6.0 已上线
- [ ] 教材 Reading Comprehension 专项题自动生成
- [ ] 教材 Sound/Phonics 拼读专项题
- [ ] 错题推荐对接新知识点体系
- [ ] 学情周报/月报 PDF 导出
- [ ] 移动端 PWA 适配

## 🐛 常见问题

**Q: 端口被占用？**
A: 编辑 `backend/.env` 修改 `APP_PORT=8001`，并同步修改 `frontend/vite.config.js` 的 proxy 目标。

**Q: 数据备份？**
A: 直接复制 `backend/data/childstudy.db` 文件即可。建议定期备份。

**Q: 升级系统？**
A: 保留 `backend/data/` 目录（数据库），然后 `git pull` + 重启服务。

## 👥 贡献者

| 贡献者 | 角色 |
|--------|------|
| alexfzh | 项目维护者 · 产品与数据设计 |
| workbuddy | AI 开发助手 · 功能开发 / 复核 / 文档同步 |
| openclaw | AI 开发助手 · 代码实现与运维支持 |

## 📄 License

MIT
