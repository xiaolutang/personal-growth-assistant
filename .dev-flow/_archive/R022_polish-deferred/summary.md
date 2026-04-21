# R022 体验打磨 + 遗留项

> 创建时间：2026-04-21
> 状态：规划中（Codex plan review 修订后）

## 概要

移动端响应式、错误状态、搜索统一、离线同步扩展、批量操作。4 个 Phase 共 15 项任务。

## 任务规划

| Phase | 任务 | 状态 |
|-------|------|------|
| 1 快速赢 | F73 FloatingChat 触摸拖拽支持 | pending |
| 1 快速赢 | F74 Home 统计卡片响应式 | pending |
| 1 快速赢 | F75 Explore Tab 栏横向滚动 | pending |
| 1 快速赢 | F76 TaskCard 触摸目标增大 | pending |
| 1 快速赢 | F77 Review 加载态 spinner + 错误状态 | pending |
| 1 快速赢 | F78 Explore 错误状态处理 | pending |
| 1 快速赢 | F79 TaskList 空状态增强 | pending |
| 1 快速赢 | F80 NotificationCenter 轮询 + 时间戳 | pending |
| 1 快速赢 | F81 搜索结果内容摘要 | pending |
| 2 搜索统一 | B80 统一搜索入口 + 迁移到 HybridSearchService | pending |
| 2 搜索统一 | F83 前端搜索统一 + Tab 过滤透传 | pending |
| 3 体验增强 | F84 离线更新/删除入口拦截 + 队列扩展 | pending |
| 3 体验增强 | F85 批量操作 — 多选框架 + 选择状态 | pending |
| 3 体验增强 | F86 批量操作 — 批量删除/转分类执行 | pending |
| 4 收口 | S09 质量收口 | pending |

## Codex Plan Review 修正记录

**审核时间**：2026-04-21 22:06
**审核结果**：fail → 修订后重新提交

### 修正项
1. **B80 重定义**：原为"实现混合搜索"，但 HybridSearchService 已存在。改为"将 POST /search 迁移到 HybridSearchService"
2. **删除 F82**：离线同步进度展示已由 OfflineIndicator.tsx 实现，无需重复
3. **F84 扩展**：添加 taskStore.ts 到涉及文件，补离线拦截入口
4. **F85 拆分**：拆为 F85（多选框架）+ F86（批量执行）
5. **B80 合并**：原 B81 降级逻辑 + F81 content_snippet 合并到 B80
6. **补充 test_tasks**：B80/F77/F78/F84/F86 补充测试场景

## Sessions

| Session | 主题 | 日期 |
|---------|------|------|
| S001 | R022 需求讨论与范围确认 | 2026-04-21 |
| S002 | Codex plan review 修订 | 2026-04-21 |
