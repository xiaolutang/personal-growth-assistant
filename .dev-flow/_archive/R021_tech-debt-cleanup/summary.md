# R021 技术债清理

> 归档时间：2026-04-21
> 状态：已完成，已合并到 main

## 概要

代码质量 + 性能优化 + 架构整理 + 测试质量，11 项技术债整改。

## 任务完成情况

| Phase | 任务 | 状态 |
|-------|------|------|
| 1 快速清理 | S07 死代码清理 | completed |
| 1 快速清理 | B78 SQLite 索引补齐 + 查询形态复合索引 | completed |
| 2 性能优化 | F66 路由懒加载 + ErrorBoundary | completed |
| 2 性能优化 | F67 E2E waitForTimeout 硬等待清理 | completed |
| 3 代码质量 | F68 Review.tsx API 调用风格统一 | completed |
| 3 代码质量 | F69 Review.tsx 组件拆分 | completed |
| 3 代码质量 | F70 useMorningDigest 共享 Hook | completed |
| 3 代码质量 | F71 Explore.tsx 搜索类型安全 + 去重 | completed |
| 4 重构 | B79 KnowledgeService 查询优化 + entry_tags 反向索引 | completed |
| 4 重构 | F72 api.ts openapi-fetch 统一 + linkGoalEntry OpenAPI 契约打通 | completed |
| 5 收口 | S08 质量收口 | completed |

## 关键提交

- `2aa0caf` S07 死代码清理
- `d82e5c5` B78 SQLite 索引
- `72eab7e` F66 路由懒加载
- `f7816e9` F67 E2E 硬等待清理
- `0369291`–`29ac33f` F68–F71 代码质量
- `5b66df4` B79 KnowledgeService 优化
- `f2273e1` F72 api.ts openapi-fetch 统一
- `561635a` F72 linkGoalEntry 类型修复
- `a08b958` B78/B79/F66 codex review 修复

## 验证结果

- 857 后端测试通过
- 326 前端测试通过
- 生产构建通过
- Codex plugin code review：F72 conditional_pass、F66/B78/B79 修复后通过

## 产物

- feature_list.snapshot.json — 完整任务快照
