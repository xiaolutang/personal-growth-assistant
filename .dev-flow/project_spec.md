# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.52.0
> 状态：进行中（R052）
> 活跃分支：fix/R052-chat-isolation-and-today-input

## 当前范围

R052 聊天用户隔离 + Today 页 AI 对话入口：修复切换用户后聊天记录残留 bug，将 Today 页底部输入栏从无条件创建 inbox 改为 AI 对话入口。

### 核心问题

真实使用发现两个关联问题：

1. **P0 Bug — 用户切换后聊天记录残留**：用户 A 对话后登出，用户 B 登录进入日知页，仍看到 A 的消息。根因：前端登出流程未清理 chat 相关状态（messages 内存 + session_id 存储）。后端隔离正确（thread_id 含 user_id），问题仅在前端。
2. **产品设计缺陷 — Today 页输入栏功能模糊**：底部输入栏和全局悬浮按钮（FAB）都无条件调用 createInboxEntry()，无意图分类。输入栏用"聊天"隐喻但只创建 inbox，用户输入"你好"也被记为灵感。后端 ReAct Agent 已具备对话 vs 工具调用能力，但该能力仅暴露在 ChatPage tab。

### Phase 1: 用户隔离修复（1 task）

1. **S01 聊天用户隔离修复**：登出时清除 session_id、invalidate chatProvider、清空 messages

### Phase 2: Today 页 AI 对话入口（1 task）

2. **F02 Today 页输入栏改为 AI 对话入口**：复用 chatProvider.sendMessage() + SSE，闲聊→AI 回复，灵感/任务→后端 Agent 判断后创建条目

### Phase 3: 质量收口（1 task）

3. **S03 全量验证**：pytest + vitest + flutter test + flutter analyze + build

## 技术约束

- S01 为纯 bug 修复，不涉及 API 契约变更
- F02 复用现有 chatProvider + SSE 基础设施，不新增后端 API
- F02 不修改 QuickCaptureFAB（FAB 保持纯灵感捕获功能不变）
- Today 页对话与日知页对话共享同一个 chatProvider 状态

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 3 |
| P0 | 1（S01）|
| P1 | 1（F02）|
| P3 | 1（S03）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
