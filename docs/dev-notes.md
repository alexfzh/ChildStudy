# ChildStudy 开发工作流

面向开发者（自己 + 后续贡献者）的速查手册。涵盖日常工作流、关键命令、已知问题、调试技巧。

## 目录

- [日常工作流](#日常工作流)
- [关键命令](#关键命令)
- [已知问题 / 踩坑速查](#已知问题--踩坑速查)
- [调试技巧](#调试技巧)
- [审计工具链](#审计工具链)
- [版本发布流程](#版本发布流程)

---

## 日常工作流

### 修改代码后必须跑

```bash
python scripts/check.py
```

四道 gate（任何一道非零退出 = 阻止 commit）：

| Gate | 命令 | 作用 |
|------|------|------|
| ruff | `ruff check .` | Python 静态检查（未用导入 / 裸 except / 不可达代码等） |
| audit:schema-router | `python backend/scripts/audit-schema-router.py` | 防 422 类 bug（schema/router 冲突） |
| pytest | `pytest --tb=line -q` | 后端 168 个测试 |
| audit:routes | `python frontend/scripts/audit-routes.py` | 前端路由 meta 完整性 |

总用时 ~17.5s（pytest 主导）。CI 也调同一个脚本。

### 改前端后必须跑

```bash
cd frontend
npm run build          # 12.34s 全量 build，确认编译通过
```

前端 dev server 默认 5173，proxy 转发 `/api` 到后端 8000。改前端不需重启后端。

### 改后端后必须重启

**`uvicorn --reload` 在本项目是关闭的**（`APP_DEBUG=false`），所以：

1. 改了 `.py` 文件 → **手动重启后端进程**才生效
2. 改了 `models.py` 新表 → 重启时 `init_db()` 自动 `create_all`
3. 改了 `models.py` 新字段 → 重启时 `init_db()` 走幂等 ALTER TABLE 迁移

确认后端进程：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  ForEach-Object { Get-Process -Id $_.OwningProcess }
```

### 提交流程（git 工作流）

1. `git status` 看修改面
2. `python scripts/check.py` 全过
3. `git add <精确文件>`（不要 `git add .`）
4. `git commit -F <UTF-8 文件>`（中文走 stdin bytes 在 Py3.14 失灵，见 [踩坑](#踩坑-1-windows--py-314--subprocess-stdin-bytes-失灵)）
5. 验证 commit：`git cat-file -p <oid>` 直读 git object

---

## 关键命令

### 启动 / 重启

```powershell
# 一键启动（开发）
.\start.bat

# 后端（手动）
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端（手动）
cd frontend
npm run dev
```

### 跑测试

```bash
# 全量
cd backend && pytest

# 单文件
pytest tests/test_auth.py

# 单个用例
pytest tests/test_auth.py::test_login_success

# 不跑测试只 lint
python scripts/check.py --skip-tests
```

### 数据库

```bash
# 备份
cp backend/data/childstudy.db backend/data/backup-$(date +%Y%m%d).db

# 看 schema
sqlite3 backend/data/childstudy.db ".schema"

# 升级历史
sqlite3 backend/data/childstudy.db "SELECT * FROM upgrade_log LIMIT 5"
```

### 部署相关

```bash
# 升版（手动）— 见 [版本发布流程](#版本发布流程)
# 看当前版本
cat VERSION
cat backend/routers/system.py | grep CURRENT_VERSION

# 生成 JWT secret
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## 已知问题 / 踩坑速查

### 踩坑 1: Windows + Py 3.14 + subprocess stdin bytes 失灵

**症状**：

```python
subprocess.run(['git','commit','-F','-'], input=msg.encode('utf-8'), ...)
# 报 TypeError: write() argument must be str, not bytes
```

**原因**：Py 3.14 + Windows 下 subprocess 默认 stdin text mode。

**解法**：写 UTF-8 文件 + `git commit -F <file>`，绕过 stdin。

```python
with open('/tmp/msg.txt', 'w', encoding='utf-8') as f:
    f.write(msg)
subprocess.run(['git','-C',repo,'commit','-F','/tmp/msg.txt'])
```

**验证姿势**：`git cat-file -p <oid>` 直读 git object，确认 UTF-8 字节完好。

详见 AGENTS.md "Git 编码 & 验证" 章节。

### 踩坑 2: Pydantic v2 Decimal JSON 序列化为 string

**症状**：财务/积分字段返回 `"1378.00"`（带引号字符串），前端 TS 类型是 `number`，runtime 必须 `Number() || 0` 兜底。ECharts 等图表库遇到非 number 直接崩。

**解法**：

```python
from typing import Annotated
from decimal import Decimal
from pydantic import PlainSerializer

AmountField = Annotated[
    Decimal,
    PlainSerializer(lambda x: float(x), return_type=float, when_used="json"),
]

class Money(BaseModel):
    amount: AmountField       # 之前是 Decimal
```

详见 MEMORY.md "Pydantic v2 + FastAPI: Decimal 字段 JSON 序列化踩坑"。

### 踩坑 3: 进程管理 — taskkill /T 杀整棵树

**症状**：`taskkill /F /PID <pid> /T` 杀一个 uvicorn worker，连带 master 进程自杀，dev 后端 8000 端口空了。

**解法**：

```powershell
# 先查父子关系
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Select-Object ProcessId, ParentProcessId, CommandLine | Format-Table

# 最小动作：单 PID 杀，不加 /T
taskkill /F /PID <single-pid>

# 观察其他进程是否还活着，再决定下一步
```

详见 MEMORY.md "进程管理红线 (2026-07-25)"。

### 踩坑 4: vite + React.lazy() HMR 缓存踩坑

**症状**：改了 lazy-loaded `.vue` 文件，浏览器硬刷新还是看到旧版。

**原因**：vite dev server 模块图缓存分裂（lazy module HMR 失效）。

**诊断**：

```bash
curl /src/pages/X.vue | base64 -d | grep "新加字符串"
```

无 query 找不到，加 `?t=99999` 找得到 → 确认是 HMR 缓存。

**修法**：`touch vite.config.js` 触发 vite 完全重启。

### 踩坑 5: SQLAlchemy async + ORM @property → MissingGreenlet

**症状**：Pydantic `from_attributes=True` 序列化 ORM 对象时抛 `MissingGreenlet`，API 返 500。

**根因**：@property 访问 lazy load 关系会触发隐式 IO，async 会话在序列化阶段已离开 async 上下文，greenlet spawn 失败。

**修法（任选其一，多个组合更稳）**：

```python
# 1. 列表查询端点
stmt = select(Exam).options(selectinload(Exam.child))

# 2. create/update 类端点显式赋值（不触发 lazy load）
obj.child = rel_obj

# 3. 单 get 端点：if obj.rel is None: obj.rel = await db.get(...)
```

### 踩坑 6: schema 与 router 设计意图冲突 = 422

**症状**：POST 422。

**根因**：`@router.post("/{child_id}")` + `XxxCreate` schema 中 child_id 必填 = 前端不传 body 必 422。

**修法**：schema 中 child_id: int → Optional[int] = None。

**防回归**：`python backend/scripts/audit-schema-router.py` 静态扫所有 POST 路由冲突。

详见 `.learnings/2026-09-02_schema-router-conflict-422.md`。

### 踩坑 7: 多 master uvicorn 抢同一端口

**症状**：dev 后端 8000 端口连不上，或循环报错但进程不死。

**检测**：

```powershell
wmic process where "CommandLine like '%uvicorn%'" get ProcessId,CommandLine
```

看到多个 master → 全部停掉再起一个干净的。

### 踩坑 8: FastAPI 临时脚本写到 backend/ 会触发 reload 崩

**症状**：在 `backend/` 下创建临时测试 `.py` → uvicorn worker reload 时新 worker 起不来 → master 进程崩溃 / 端口拒绝连接。

**修法**：临时脚本写到 `python -c "..."` inline 或 `/tmp/` 或 workspace 根（不在 backend/ 下，不被 watch）。

### 踩坑 9: edit 工具 partial-success 陷阱

**症状**：edit 工具传 5 个 edits，第 3 个失败但工具返回 "Successfully replaced 1 block(s)"，让人误以为全部成功。

**代价**：用户硬刷新浏览器报 `childStore.loadConfig is not a function`。

**修法**：
- 多 edit 改同一文件，每个文件单独一次 edit 调用（不要混文件）
- 重要改动后立刻 `read` 磁盘或 curl 编译产物 verify
- 跨多文件的实质性改动优先用 `write` 整文件覆盖

---

## 调试技巧

### 后端 500 / Pydantic 422 排查**：

```powershell
# 1. 看 stderr / 异常堆栈
Get-Content backend/backend_run.log -Tail 50

# 2. 看 health
curl http://127.0.0.1:8000/api/health

# 3. 看 OpenAPI（schema 实时）
curl http://127.0.0.1:8000/openapi.json | python -m json.tool | head -50
```

### 前端 HMR 失败 / 看不到改动**：

```powershell
# 1. curl 拿原始 JS，看是否是新版本
curl 'http://127.0.0.1:5173/src/views/X.vue' | Select-String "新加字符串"

# 2. 无 query 找不到，加 ?t=99999 找得到 → vite HMR 缓存分裂
# 修法: touch vite.config.js 触发 vite 完全重启

# 3. ERR_ABORTED 504 (Outdated Optimize Dep)
# 修法: Remove-Item -Recurse -Force node_modules/.vite; 重启 vite
```

### 后端 listener 验证（多 worker / 多 cmd wrapper 残留）**：

```powershell
# 多次重启后端会有多个 cmd /c wrapper 残留
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  ForEach-Object { Get-Process -Id $_.OwningProcess }
```

### 数据库锁死 / 慢查询**：

```python
# backend/.venv/Scripts/python.exe
import sqlite3
con = sqlite3.connect('backend/data/childstudy.db')
# 看活跃查询（SQLite 是文件锁，一般不会真锁死，但 N+1 会让 API 慢）
```

---

## 审计工具链

`scripts/check.py` 聚合的 4 道 gate：

| Gate | 写在哪 | 触发历史问题 |
|------|--------|-------------|
| ruff | Python 标准 | 不可达代码 / 裸 except / 未用导入 |
| audit:schema-router | 自研（v1.7.3） | 422 类 bug（schema/router 冲突） |
| pytest | 项目内 | 回归检测 |
| audit:routes | 自研（v1.7.2） | 路由 meta 不一致 / 拼写错误 |

**新增 audit 脚本时**：集成到 `scripts/check.py`，加注释说"防 X 类 bug"。

---

## 版本发布流程

按 AGENTS.md SemVer + 业务后缀：

| 变更类型 | 版本号 | 例子 |
|---------|--------|------|
| 新功能 | MAJOR.MINOR.0 | v1.8.0 (新功能模块) |
| Bug 修复 | MAJOR.MINOR.PATCH | v1.7.4 (下一个 hotfix) |
| 安全/体检加固 | MAJOR.MINOR.0-audit.N | v1.8.0-audit.1 |
| 设计重做 | MAJOR.0.0-design | v2.0.0-design |
| 性能优化 | MAJOR.MINOR.PATCH-perf | v1.7.4-perf |
| 紧急 hotfix | MAJOR.MINOR.PATCH-hotfix | v1.7.4-hotfix |
| 预发 | MAJOR.MINOR.0-rcN | v1.8.0-rc1 |

**升版必改 6 处**：

1. `VERSION`
2. `frontend/package.json` version
3. `backend/main.py` FastAPI version
4. `backend/routers/system.py` CURRENT_VERSION
5. `backend/routers/system.py` BUILD_TIME（YYYY-MM-DD）
6. `README.md` 版本 badge

**升版必加 1 条**：`_SEED_LOG` 新条目（首次启动会自动写入 `data/upgrade_log.json`）

**未变更**：

- 注释中引用旧版本号（"登录防爆破（v1.7.1）：..."）保留——事件归属上下文
- `requirements.txt` / `package.json` 依赖版本（独立 bump 节奏）

---

## 速查表（高频操作）

| 我想... | 命令 |
|--------|------|
| 全量自检 | `python scripts/check.py` |
| 跑后端测试 | `cd backend && pytest` |
| 跑单个测试文件 | `pytest tests/test_auth.py` |
| 看后端日志 | `Get-Content backend/backend_run.log -Tail 50` |
| 看前端日志 | `Get-Content frontend/dev.log -Tail 50` |
| 验证 listener | `Get-NetTCPConnection -LocalPort 8000 -State Listen` |
| 验证 schema 冲突 | `python backend/scripts/audit-schema-router.py` |
| 验证路由 meta | `python frontend/scripts/audit-routes.py` |
| 备份数据库 | `cp backend/data/childstudy.db backend/data/backup-$(date +%Y%m%d).db` |
| 看升级历史 | `Get-Content backend/data/upgrade_log.json` |
| commit 中文 | 写 UTF-8 文件 + `git commit -F <file>` |

---

## 贡献者

- alexfzh (founder) — 主力开发
- workbuddy — 辅助开发
- openclaw — AI 开发助理 / 文档维护

## 反馈

发现新坑？补到本文档对应章节 + 写一条 `.learnings/YYYY-MM-DD_<topic>.md` + 更新 `.learnings/INDEX.md`。