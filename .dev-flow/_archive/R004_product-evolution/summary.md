# R004 产品演进 — Phase 1A

> 状态: 规划中
> 分支: `feat/R004-product-evolution-phase1a`
> 创建: 2026-04-14

## 目标

基于 `docs/r004-implementation-plan.md` 和 `docs/product-design-analysis.md`，实施 Phase 1A「补闭环」的 4 个核心功能：
1. 回顾趋势数据 API
2. 首页改版「今天」
3. 灵感转化 API
4. 反馈闭环

## 范围

### 包含
- GET /review/trend 跨期对比数据接口
- 首页从统计报表改为行动中心
- inbox 条目转为 task/note 的 category 变更 + 文件迁移
- 本地 feedback 表 + 双写 log-service + 用户反馈列表查询

### 不包含
- Phase 1B（T04 灵感转化 UI、T06 回顾趋势 UI）
- Phase 2A/2B/2C（探索页、Onboarding、Export、关联等）
- 图谱独立页、AI 内嵌、移动端

## 关键发现

1. **Review Service 数据隔离 Bug**：review_service.py 所有方法调用 `list_entries()` 未传 user_id，导致所有用户看到 `_default` 数据。B14 一并修复。
2. **前后端 EntryUpdate 缺 category**：后端 schema 和前端类型都需要新增 category 字段。

## 任务进度

| Phase | ID | 名称 | 状态 |
|-------|----|------|------|
| P1A | S05 | Phase 1A 契约与模型定义 | pending |
| P1A | B14 | 回顾趋势 API + review user_id 修复 | pending |
| P1A | B15 | 灵感转化 API | pending |
| P1A | B16 | 反馈闭环后端 | pending |
| P1A | F05 | 首页改版「今天」 | pending |
| P1A | F06 | FeedbackButton 双 Tab | pending |

## 依赖关系

```
S05 ──┬── B14 (趋势 API)
       ├── B15 (灵感转化)
       ├── B16 (反馈后端) ── F06 (反馈前端)
       └── F05 (首页改版)
```
