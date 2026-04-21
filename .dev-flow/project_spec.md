# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.17.0

## 目标

- R021 技术债清理 — 代码质量 + 性能优化 + 架构整理 + 测试质量，11 项技术债整改

## 前置依赖（R001-R020 已完成）

- 条目 CRUD + 7 种类型（R001-R004, R013）
- 知识图谱 + 向量搜索（R005-R008）
- 认证隔离（R002, R009）
- 目标追踪闭环（R012）
- 页面级上下文 AI + Cmd+K 搜索（R014, R016）
- 离线 PWA（R019）
- E2E 测试补齐 + CI PR 增强（R020，113 个 E2E 用例）

## 基线分析

当前技术债分布（代码扫描 2026-04-20）：

**代码质量**：
- 3 个页面死代码（Inbox/Projects/Notes.tsx，路由已重定向）231 行
- QuickCommandHints.tsx + getRelatedConcepts() 无消费者
- Review.tsx 1098 行需拆分，混用 authFetch/api.ts
- Explore.tsx 搜索映射 any 类型 ×2 处重复
- getMorningDigest Home/Review 重复调用

**性能**：
- 前端未做路由级 lazy loading，recharts/@xyflow/react 打入首屏 ~350KB gz
- KnowledgeService 5 处 list_entries(limit=10000) 全量扫描
- SQLite 缺 parent_id/planned_date 索引

**测试质量**：
- E2E 26 处 waitForTimeout 硬等待（分布在 5 个文件）

**架构**：
- api.ts 混用 openapi-fetch 和原始 fetch（30+ 函数）

## 范围

### 包含（11 个任务）

**Phase 1 快速清理**：S07 死代码清理 + B78 SQLite 索引
**Phase 2 性能**：F66 路由懒加载 + F67 E2E 硬等待清理
**Phase 3 代码质量**：F68 Review API 统一 + F69 Review 拆分 + F70 晨报共享 Hook + F71 Explore 类型安全
**Phase 4 重构**：B79 KnowledgeService 优化 + F72 api.ts 统一
**Phase 5 收口**：S08 质量验证

### 不包含

- 13 个页面组件单元测试（范围过大，留后续专项）
- 4 个 router 单测补齐（search/intent/parse/playground）
- 跨浏览器测试（Firefox/WebKit）
- 前端状态管理统一（useState → Zustand 迁移）
- taskStore 乐观更新优化
- Neo4j N+1 查询并行化

## 用户路径

本轮无新增用户路径。改动集中在现有路径的性能和质量提升。

## 技术约束

- 不改变任何 API 接口契约
- 不改变任何用户可见的功能行为
- 不引入新依赖（除非 lazy loading 需要 @loadable/component 等，但 React.lazy 已内置）
- workflow: B/codex_plugin/skill_orchestrated
