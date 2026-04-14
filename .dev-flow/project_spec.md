# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.5.0

## 目标

- 实施 R004 产品演进 Phase 2：统一探索 + Export 导出 + 条目关联 + Onboarding
- 完善信息架构（Sidebar 6→5 项）、新增数据导出能力、条目关联推荐、新用户引导

## 前置依赖（Phase 1A/1B 已完成）

- B14: GET /review/trend 趋势数据 API
- B15: PUT /entries/{id} category 转化 API + 文件迁移
- B16: 反馈闭环后端 + 双写
- F05: 首页改版「今天」
- F06: FeedbackButton 双 Tab
- F07: 灵感转化 UI
- F08: 回顾页趋势折线图

## 范围

### 包含
- B18: Export 导出 API — zip/json 双格式
- B19: 条目关联 API — GET /entries/:id/related
- F09: Onboarding 对话引导 — 新用户首次登录引导
- F10: 探索页基础 — 灵感/笔记/项目统一浏览 + Sidebar 改造
- F11: 搜索增强 — 实时搜索 + Cmd+K 全局聚焦
- F12: Export 导出 UI — 导出对话框 + Sidebar 入口
- F13: 条目详情页关联面板 — 相关条目推荐

### 不包含
- Phase 3（图谱独立页、AI 内嵌、移动端 App）
- MCP Server 用户隔离扩展
- 知识图谱可视化

## 用户路径

1. 新用户首次登录 → 看到 Onboarding 引导 → 可跳过或完成首次记录
2. 用户在探索页浏览所有条目 → 类型 Tab 筛选 → 搜索栏搜索 → Cmd+K 快捷聚焦
3. 用户点击 Sidebar 导出按钮 → 选择格式和过滤 → 下载文件
4. 用户在条目详情页底部看到「相关条目」推荐 → 点击跳转

## 技术约束

- 后端：Python 3.11+ / FastAPI / SQLite / Markdown 存储
- 前端：React 18 / Tailwind CSS / Vite / Zustand
- 数据隔离：所有操作必须按 user_id 隔离
- 大数据量导出使用 StreamingResponse 流式响应
- 关联推荐：同项目 → 标签重叠 → 向量相似，最多 5 条

## 交付边界

- 后端：2 个新端点（/entries/export, /entries/{id}/related）+ 1 个字段扩展（onboarding_completed）
- 前端：5 个页面/组件改造（Explore.tsx, OnboardingFlow.tsx, ExportDialog.tsx, EntryDetail.tsx, Sidebar.tsx）
- 路由调整：Sidebar 6→5 项，旧路由重定向到 /explore
