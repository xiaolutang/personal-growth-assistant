# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.18.0

## 目标

- R022 体验打磨 + 遗留项 — 移动端响应式、错误状态、搜索统一、离线同步扩展、批量操作，共 15 项任务

## 前置依赖（R001-R021 已完成）

- 条目 CRUD + 7 种类型（R001-R004, R013）
- 知识图谱 + 向量搜索（R005-R008）
- 认证隔离（R002, R009）
- 目标追踪闭环（R012）
- 页面级上下文 AI + Cmd+K 搜索（R014, R016）
- 离线 PWA（R019）
- E2E 测试补齐 + CI PR 增强（R020，113 个 E2E 用例）
- 技术债清理（R021，api.ts 统一、路由懒加载、索引补齐等 11 项）
- 混合搜索服务已有（R008 hybrid_search.py，向量 0.7 + 全文 0.3 融合）

## 基线分析（Codex plan review 修正后）

**搜索现状**：
- `HybridSearchService`（hybrid_search.py）已实现向量+全文混合搜索，被 `GET /entries/search/query` 使用
- `POST /search`（search.py）仍为纯 Qdrant 向量搜索，不支持 filter_type，Qdrant 不可用时返回 503
- 前端同时调用两个搜索端点（api.ts searchEntries + searchEntriesByKeyword）
- SearchResult 仅有 id/title/score/type/tags/file_path，无内容摘要

**移动端响应式**：FloatingChat 无触摸事件、Home grid-cols-4 小屏挤压、Explore Tab 溢出、TaskCard 触摸目标偏小

**错误状态**：Review 加载态无 spinner、Review 无错误提示、Explore 失败静默吞错、TaskList 空状态无引导

**离线同步现状**：
- OfflineIndicator.tsx 已有同步进度 UI（"正在同步 1/3..."）✅ 无需重复实现
- useStreamParse 离线时入队 POST /entries ✅ 创建已覆盖
- taskStore.updateEntry/deleteTask 仍直接打在线 API ❌ 更新/删除未拦截
- offlineSync 仅回放 POST /entries ❌ PUT/DELETE 未扩展

**批量操作**：前端无多选和批量操作能力

## 范围

### 包含（15 个任务）

**Phase 1 快速赢**（9 项）：F73-F81 移动端响应式 + 错误状态 + 搜索摘要
**Phase 2 搜索统一**（2 项）：B80 统一搜索入口 + F83 前端统一+过滤透传
**Phase 3 体验增强**（3 项）：F84 离线同步扩展 + F85 多选框架 + F86 批量执行
**Phase 4 收口**（1 项）：S09 质量验证

### 不包含

- logout Token 黑名单（D1，需要 Redis/DB 支撑，留后续专项）
- 移动端下拉刷新手势（需要全局手势管理，复杂度高）
- 同步失败项重试 UI（需要独立管理页面，留后续）
- 通知偏好改用 Switch 组件（纯 UI 细节，低优先级）
- Flutter 移动端 MVP（独立代码库，需单独规划）
- F82 离线同步进度展示（已由 OfflineIndicator.tsx 实现，无需重复）

## 用户路径

本轮改进的现有路径：
- 移动端使用：拖拽面板、查看统计卡片、浏览 Tab、操作任务卡片
- 搜索：关键词搜索 → POST /search（统一后）→ 结果列表 → Tab 过滤
- 离线使用：创建/更新/删除条目 → 队列入队 → 上线后回放
- 批量管理：进入编辑模式 → 多选条目 → 批量删除或转分类

## 技术约束

- B80 迁移 POST /search 到 HybridSearchService，不新建搜索服务
- 搜索返回结构仅扩展（content_snippet、filter_type），不破坏现有契约
- 移动端响应式使用 Tailwind 断点（sm/md/lg）
- 触摸事件使用原生 DOM API（onTouchStart 等），不引入手势库
- 离线拦截在 taskStore 层实现，乐观更新 + 回滚
- 批量操作仅限 Tasks 页，操作通过逐个调用现有 API 执行
- workflow: B/codex_plugin/skill_orchestrated
