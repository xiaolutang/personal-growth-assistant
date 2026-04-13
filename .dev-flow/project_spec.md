# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.4.0

## 目标

- 实施 R004 产品演进 Phase 1A「补闭环」
- 新增回顾趋势数据 API，支持跨期对比
- 新增灵感转化能力（inbox→task/note）
- 补齐反馈闭环（本地存储 + 远端双写 + 状态追踪）
- 首页从统计报表改版为行动中心「今天」

## 范围

### 包含
- GET /review/trend 跨期趋势数据接口
- ReviewService user_id 修复（数据隔离 Bug）
- EntryUpdate 新增 category 字段 + 文件迁移
- Feedback 本地表 + 双写 + 列表查询
- 首页 UI 改版 + Sidebar 标签更新
- FeedbackButton 双 Tab 改造

### 不包含
- Phase 1B：灵感转化前端 UI（Inbox 页「转为任务/笔记」操作入口，r004-implementation-plan T04）、回顾页趋势折线图 UI（T06）— Phase 1A 仅交付后端 API 能力，前端 UI 消费在 Phase 1B 实现
- Phase 2A/2B/2C（探索页、Onboarding、Export、关联等）
- 图谱独立页、AI 内嵌、移动端 App
- MCP Server 用户隔离扩展

## 用户路径

1. 用户打开首页，看到今日进度和可直接操作的任务列表
2. 用户在灵感列表中选择一个灵感，转化为任务或笔记
3. 用户提交反馈后，可在「我的反馈」Tab 查看状态
4. 用户在回顾页查看趋势数据，了解完成率变化

## 技术约束

- 后端：Python 3.11+ / FastAPI / SQLite / Markdown 存储
- 前端：React 18 / Tailwind CSS / Vite / Zustand
- 数据隔离：所有操作必须按 user_id 隔离
- 文件迁移：os.rename 原子操作，entry_id 前缀不变
- 双写策略：本地优先 + 远端 best-effort

## 交付边界

- 后端：新增 3 个 API 端点（review/trend、feedback CRUD、entries category 转化）+ 修复 review 数据隔离
- 前端：首页改版 + 反馈组件升级（双 Tab）
- 不含前端 UI：灵感转化操作入口（Phase 1B T04）和回顾趋势折线图（Phase 1B T06）
- 测试：每个任务包含单元测试/集成测试
