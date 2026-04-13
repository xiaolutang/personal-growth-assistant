# R004 产品演进计划 — 第一阶段 & 第二阶段

> 基于 `docs/product-design-analysis.md` 三阶段收敛策略的可执行任务计划。
> 前置完成：R001（v1 核心）、R002（认证隔离）、R003（内容恢复）。

---

## 依赖关系总览

```
Phase 1A（可并行）
  T01 [后端] 回顾趋势数据 API
  T02 [前端] 首页改版「今天」
  T03 [后端] 灵感转化 API
  T05 [全栈] 反馈闭环

Phase 1B（依赖 1A）
  T04 [前端] 灵感转化 UI          ← T03
  T06 [前端] 回顾页趋势对比       ← T01

Phase 2A
  T07 [全栈] Onboarding           ← T02

Phase 2B（可并行）
  T08 [前端] 探索页基础           ← T04
  T09 [前端] 搜索主入口           ← T08
  T10 [后端] Export 导出 API
  T11 [前端] Export 导出 UI       ← T10

Phase 2C
  T12 [后端] 条目关联 API
  T13 [前端] 条目详情页关联面板   ← T12
```

## 时间线参考

| 阶段 | 任务 | 并行度 |
|------|------|--------|
| Week 1 | T01 + T02 + T03 + T05 | 4 并行 |
| Week 2 | T04 + T06 | 1A 完成后 |
| Week 3 | T07 + T08 + T10 | 2A/2B 启动 |
| Week 4 | T09 + T11 + T12 + T13 | 收尾 |

最短关键路径：T03 → T04 → T08 → T09（约 5 天）

---

## Phase 1A — 补闭环

### T01 [后端] 回顾趋势数据 API

- **工作量**: 1 天 | **depends_on**: 无

为回顾页新增跨期对比数据接口。`ReviewService` 已有单期统计，需新增多期数组。

**涉及文件**：
- `backend/app/routers/review.py` — 新增 `GET /review/trend` 端点
- `backend/app/services/review_service.py` — 新增 `get_trend_data()` 方法

**实现要点**：
1. `GET /review/trend?period=daily&days=7` 返回每日统计数组
2. `GET /review/trend?period=weekly&weeks=8` 返回每周统计数组
3. 返回结构：`{ periods: [{ date, total, completed, completion_rate, notes_count }] }`
4. 复用已有 `list_entries` + 统计逻辑

**验收标准**：
- [ ] 返回正确的历史统计数据
- [ ] 空数据返回空数组
- [ ] 带用户认证隔离

---

### T02 [前端] 首页改版「今天」

- **工作量**: 2 天 | **depends_on**: 无

将首页从统计报表改为行动中心。当前 `Home.tsx` 展示统计卡片+列表，需重写为以「今日任务」为核心的行动页。

**涉及文件**：
- `frontend/src/pages/Home.tsx` — 重写首页布局
- `frontend/src/config/constants.ts` — 可能新增常量

**实现要点**：
1. 精简顶部为今日进度（完成率 + 进度条）
2. 今日任务区可操作：点击直接切换状态（doing ↔ complete）
3. 最近灵感区增加未处理计数角标
4. 新增快速操作区：记灵感、建任务、写笔记（触发 FloatingChat 或跳转）
5. 空数据时显示引导文案
6. 路由路径 `/` 保持不变，Sidebar 标签改为「今天」

**验收标准**：
- [ ] 今日任务可直接操作
- [ ] 灵感有未处理提示
- [ ] 空数据有引导
- [ ] 移动端可适配

---

### T03 [后端] 灵感转化 API

- **工作量**: 1 天 | **depends_on**: 无

支持 inbox 条目转为 task 或 note。当前 `update_entry` **完全不处理 category 字段变更**（entry_service.py:130-175 无 category 分支），需新增。

**当前存储规则**（markdown.py:15-19）：
- `Category.INBOX` 映射目录 `""`（数据根目录），文件落地为 `data/inbox-xxx.md`
- `Category.TASK` 映射目录 `"tasks"`，文件落地为 `data/tasks/task-xxx.md`
- `Category.NOTE` 映射目录 `"notes"`，文件落地为 `data/notes/note-xxx.md`

**涉及文件**：
- `backend/app/api/schemas.py` — `EntryUpdate` 新增 `category` 可选字段（如当前无）
- `backend/app/services/entry_service.py` — `update_entry` 新增 category 变更分支
- `backend/app/infrastructure/storage/markdown.py` — 新增 `move_entry()` 方法

**实现要点**：
1. `EntryUpdate` schema 新增 `category: Optional[str]` 字段
2. `update_entry` 检测 category 变更时：
   - 读取旧文件内容，按新 category 的 `_get_file_path()` 算出新路径
   - 实际路径变化：`data/inbox-xxx.md` → `data/tasks/inbox-xxx.md`（目录变，文件名不变）
   - 更新 entry.category、entry.file_path、front matter 中的 `type` 字段
   - 旧文件 `os.rename()` 到新路径（原子操作）
   - SQLite `upsert_entry` 更新索引
3. entry_id 前缀不变（`inbox-xxx` 保持为永久标识，不重命名为 `task-xxx`）

**验收标准**：
- [ ] `PUT /entries/{entry_id} { "category": "task" }` 成功
- [ ] 文件从 `data/inbox-xxx.md` 移到 `data/tasks/inbox-xxx.md`
- [ ] ID 前缀不变（仍为 `inbox-xxx`）
- [ ] front matter 的 `type` 字段同步更新
- [ ] SQLite 索引同步更新
- [ ] 新 category 列表可见

---

### T05 [全栈] 反馈闭环

- **工作量**: 2 天 | **depends_on**: 无（可与 1A 并行）

用户可查看自己提交的反馈列表和状态。当前 `POST /feedback`（feedback.py:35）是纯代理 log-service，用户端无本地记录。

**涉及文件（后端）**：
- `backend/app/routers/feedback.py` — 改造提交逻辑 + 新增 `GET /feedback`、`GET /feedback/:id`
- `backend/app/infrastructure/storage/sqlite.py` — 新增 feedback 表及 CRUD 方法

**涉及文件（前端）**：
- `frontend/src/components/FeedbackButton.tsx` — 改造为双 Tab（提交 + 我的反馈）

**实现要点**：

双写一致性策略（当前方案：**本地优先 + 远端 best-effort**）：
1. 提交时先写本地 SQLite（status=`pending`），返回成功
2. 异步调 log-service：成功 → 更新本地 status=`reported`、记录 `log_service_issue_id`；失败 → 保持 status=`pending`，可后续重试
3. `GET /feedback` 从本地 SQLite 按 user_id 过滤读取，status 字段反映上报状态
4. feedback 表结构：`(id, user_id, title, description, severity, log_service_issue_id, status, created_at)`
   - status 枚举：`pending`（待上报）、`reported`（已上报）

**验收标准**：
- [ ] 提交后在「我的反馈」立即可见（status=pending）
- [ ] log-service 上报成功后 status 更新为 reported
- [ ] 反馈列表按用户隔离
- [ ] 显示状态（pending/reported）和时间

---

## Phase 1B — 1A 收尾

### T04 [前端] 灵感转化 UI

- **工作量**: 1 天 | **depends_on**: T03

灵感列表项添加「转为任务/笔记」操作。

**涉及文件**：
- `frontend/src/pages/Inbox.tsx` — 灵感项增加操作菜单
- `frontend/src/pages/Home.tsx` — 最近灵感卡片增加转化入口

**实现要点**：
1. 灵感列表项右侧「...」菜单：转为任务、转为笔记、删除
2. 调用 `updateEntry(id, { category: 'task' })` 或 `{ category: 'note' })`
3. 成功后 toast 提示，列表自动刷新（条目因 category 变化从灵感列表消失）

**验收标准**：
- [ ] 操作菜单可用
- [ ] 转化后条目在目标列表可见
- [ ] 有 loading 和成功/失败提示

---

### T06 [前端] 回顾页趋势对比

- **工作量**: 1 天 | **depends_on**: T01

回顾页新增趋势折线图，展示完成率变化。

**涉及文件**：
- `frontend/src/pages/Review.tsx` — 新增趋势卡片
- `frontend/src/services/api.ts` — 新增 `getReviewTrend()` 调用

**实现要点**：
1. 安装 recharts（轻量图表库）
2. 新增趋势卡片：默认最近 7 天日完成率折线图，可切换为周维度
3. 图表下方显示简单摘要（如「本周比上周提升 12%」）

**验收标准**：
- [ ] 显示趋势折线图
- [ ] 可切换日/周
- [ ] 空数据有引导
- [ ] 符合设计规范

---

## Phase 2A — Onboarding

### T07 [全栈] Onboarding 机制

- **工作量**: 2 天 | **depends_on**: T02

新用户首次登录后通过对话引导完成第一次记录。

**当前后端约束**：
- 用户数据持久化在 `UserStorage`（user_storage.py），users 表在 `_init_db()` 创建（line 45-68）
- `_row_to_user()`（line 70-84）负责 DB 行 → User 对象映射
- `GET /auth/me`（auth.py:120-133）手动构造 `UserResponse`，不含额外字段
- `POST /auth/login`（auth.py:51-109）同样手动构造 `UserResponse`
- 已有用户表无 `onboarding_completed` 列，需 ALTER TABLE 迁移

**涉及文件（后端）**：
- `backend/app/infrastructure/storage/user_storage.py` — 表迁移 + `_row_to_user` + `update_onboarding()` 方法
- `backend/app/models/user.py` — `User` 新增 `onboarding_completed` 字段、`UserResponse` 新增字段
- `backend/app/routers/auth.py` — `GET /auth/me` 和 `POST /auth/login` 返回 onboarding 状态
- `backend/app/api/schemas.py` — 如需独立 schema 则新增

**涉及文件（前端）**：
- `frontend/src/components/OnboardingFlow.tsx` — 新建 Onboarding 组件
- `frontend/src/App.tsx` — 条件渲染

**实现要点**：
- 后端：
  1. `user_storage._init_db()` 加迁移逻辑：检查 `onboarding_completed` 列是否存在（`PRAGMA table_info(users)`），不存在时执行 `ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0`
  2. `_row_to_user()` 映射新字段
  3. 新增 `mark_onboarding_completed(user_id)` 方法
  4. `UserResponse` 新增 `onboarding_completed: bool = False`
  5. `GET /auth/me` 和 login 响应携带该字段
- 前端：登录后检查字段，未完成则显示引导 → 欢迎语 → 引导记录第一条 → 调 API 标记完成
- 可跳过，完成后不再显示

**验收标准**：
- [ ] 新用户自动触发
- [ ] 可跳过/可完成
- [ ] 已有用户不受影响（默认 FALSE = 未完成，首次登录会触发 → 完成后不再触发）
- [ ] `GET /auth/me` 正确返回 onboarding_completed

---

## Phase 2B — 统一探索

### T08 [前端] 探索页基础

- **工作量**: 2 天 | **depends_on**: T04

灵感/笔记/项目三页合并为统一探索页。信息架构调整的核心任务。

**涉及文件**：
- `frontend/src/pages/Explore.tsx` — 新建探索页
- `frontend/src/App.tsx` — 路由调整
- `frontend/src/components/layout/Sidebar.tsx` — 导航 6→5 项

**实现要点**：
1. 新建 Explore.tsx：搜索栏 + 类型 Tab（全部/灵感/笔记/项目）+ 混合列表
2. Sidebar 更新：今天/探索/任务/回顾（图谱第三阶段加）
3. 旧路由 `/inbox` `/notes` `/projects` 重定向到 `/explore?type=xxx`

**验收标准**：
- [ ] 探索页展示所有类型
- [ ] Tab 筛选可用
- [ ] 搜索可用
- [ ] 旧路由重定向
- [ ] 侧边栏 5 项

---

### T09 [前端] 搜索主入口

- **工作量**: 1 天 | **depends_on**: T08

强化探索页搜索体验，成为全局搜索主入口。

**涉及文件**：
- `frontend/src/pages/Explore.tsx` — 搜索体验增强

**实现要点**：
1. 搜索框聚焦时展开全宽面板
2. 搜索建议：最近搜索历史 + 热门标签
3. 实时搜索（debounce 300ms），结果高亮关键词
4. 快捷键 `Cmd+K` 全局聚焦

**验收标准**：
- [ ] 实时搜索可用
- [ ] 搜索历史
- [ ] 关键词高亮
- [ ] Cmd+K 可用

---

### T10 [后端] Export 导出 API

- **工作量**: 1 天 | **depends_on**: 无（可与 2B 并行）

数据导出 API，支持 Markdown 和 JSON 格式。

**路由冲突风险**：当前 `entries.py` 中 `GET /{entry_id}`（line 47）为动态路由，若在其后注册 `GET /export`，`export` 会被当作 `entry_id` 捕获，导致接口不可达。

**涉及文件**：
- `backend/app/routers/entries.py` — 新增导出端点（**必须注册在 `/{entry_id}` 之前**）

**实现要点**：
1. 导出端点 `GET /entries/export` **必须在路由注册顺序上排在 `/{entry_id}` 之前**（FastAPI 按注册顺序匹配）
2. `format=markdown` — zip 打包（每条目一个 .md）
3. `format=json` — JSON 数组
4. 支持类型过滤和日期范围
5. `StreamingResponse` 处理大数据量

**验收标准**：
- [ ] `GET /entries/export?format=markdown` 返回 zip，不被 `/{entry_id}` 吞掉
- [ ] 导出 zip/json 可下载
- [ ] 类型/日期过滤可用
- [ ] 用户隔离

---

### T11 [前端] Export 导出 UI

- **工作量**: 0.5 天 | **depends_on**: T10

导出功能的前端入口。

**涉及文件**：
- `frontend/src/components/ExportDialog.tsx` — 新建导出对话框
- `frontend/src/components/layout/Sidebar.tsx` — 底部增加导出按钮

**验收标准**：
- [ ] 选择格式后可下载
- [ ] 有 loading 提示

---

## Phase 2C — 关联与收尾

### T12 [后端] 条目关联 API

- **工作量**: 1.5 天 | **depends_on**: 无

为详情页提供关联推荐（同标签、同项目、向量相似）。

**涉及文件**：
- `backend/app/routers/entries.py` — 新增 `GET /entries/{entry_id}/related`
- `backend/app/services/entry_service.py` — 关联逻辑

**实现要点**：
- 同 parent_id 兄弟条目 → 标签重叠条目 → 向量相似条目
- 返回最多 5 条，含 `relevance_reason`

**验收标准**：
- [ ] 返回相关条目
- [ ] 相关性合理
- [ ] 用户隔离

---

### T13 [前端] 条目详情页关联面板

- **工作量**: 1 天 | **depends_on**: T12

详情页底部新增「相关条目」卡片。

**涉及文件**：
- `frontend/src/pages/EntryDetail.tsx` — 新增关联面板

**实现要点**：
- 一并修复项目详情页无内容问题：`/entries/{entry_id}` 当 entry.category=project 时展示项目描述、子任务进度和关联内容

**验收标准**：
- [ ] 显示相关条目
- [ ] 可点击跳转
- [ ] 空数据有引导
- [ ] 项目详情页内容完整

---

## 已知缺陷一并处理

- **项目详情页无内容**：在 T13 中一并修复，确保 `/entries/{entry_id}` 当 category=project 时展示项目描述、子任务进度和关联内容

## 验证策略

每个任务完成后：
1. `uv run pytest backend/tests/` — 后端测试通过
2. `npm run build --prefix frontend/` — 前端构建通过
3. 浏览器手动验证对应功能
4. 每阶段完成后做端到端冒烟测试
