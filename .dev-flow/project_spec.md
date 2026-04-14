# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.4.0

## 目标

- 实施 R004 产品演进 Phase 1B：消费 Phase 1A 后端 API 的前端 UI
- 灵感转化 UI：Inbox 页「转为任务/笔记」操作入口
- 回顾页趋势折线图：日/周完成率可视化

## 前置依赖（Phase 1A 已完成）

- B14: GET /review/trend 趋势数据 API
- B15: PUT /entries/{id} category 转化 API + 文件迁移
- taskStore.updateEntry 已可用

## 范围

### 包含
- F07: Inbox 页灵感项「转为任务/笔记」下拉操作
- F08: 回顾页趋势折线图（recharts）

### 不包含
- Phase 2A/2B/2C（探索页、Onboarding、Export、关联等）
- 图谱独立页、AI 内嵌、移动端 App
- MCP Server 用户隔离扩展

## 用户路径

1. 用户在 Inbox 页看到灵感列表，点击「...」选择「转为任务」或「转为笔记」
2. 转化成功后 toast 提示，条目从灵感列表消失
3. 用户在回顾页看到趋势折线图，切换日/周维度
4. 空数据时显示引导文案

## 技术约束

- 后端：Python 3.11+ / FastAPI / SQLite / Markdown 存储（Phase 1A 已交付，Phase 1B 不涉及）
- 前端：React 18 / Tailwind CSS / Vite / Zustand / recharts（新增）
- 数据隔离：所有操作必须按 user_id 隔离
- 前端 API 调用复用 taskStore.updateEntry + api.ts getReviewTrend（新增）

## 交付边界

- 前端：2 个前端页面改造（Inbox.tsx、Review.tsx）+ 1 个 API 函数新增（getReviewTrend）
- 测试：每个任务含组件/交互测试 + 构建通过
