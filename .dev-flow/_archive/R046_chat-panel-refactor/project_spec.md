# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.46.0
> 状态：规划中（R046）
> 活跃分支：feat/R046-chat-panel-refactor

## 当前范围

R046 聊天面板重构 + 首次引导：将 FloatingChat 从底部常驻面板改为悬浮按钮模式，反馈入口集成到聊天面板内，新用户首次聊天时 Agent 自动自我介绍。

### Phase 1: 后端 — 首次引导链路（1 task）

1. **B196 is_new_user 传递链修复**：识别 `__greeting__` 消息，查询用户会话数，透传 is_new_user 到 ONBOARDING_PROMPT

### Phase 2: 前端 — 聊天面板重构（2 tasks）

2. **F188 FloatingChat 折叠模式**：悬浮按钮 + 点击展开面板，移除底部常驻面板
3. **F189 反馈集成到聊天面板**：移除 FeedbackButton 浮动按钮，表单接入聊天面板 header

### Phase 3: 前端 — 首次引导触发（1 task）

4. **F190 前端首次 greeting**：新用户首次展开聊天自动发 `__greeting__`，触发 Agent 自我介绍

## 用户路径

1. 完成前端 OnboardingFlow 弹窗引导 → 聊天按钮出现
2. 新用户点击聊天按钮 → 面板展开 → 自动收到 Agent 自我介绍 + 示例
3. 老用户点击聊天按钮 → 面板展开 → 继续上一次对话或开始新对话
4. 任何页面右下角只有一个悬浮入口，反馈通过聊天面板 header 访问

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 4 |
| P0 | 4（B196, F188, F189, F190）|

## 技术约束

- is_new_user 通过 router → AgentService → Agent → prompt 链路透传，不新增 API
- __greeting__ 为隐藏触发消息，不存入对话历史
- 聊天面板重构后不再影响主内容区布局（无 paddingBottom）
- 复用现有 ONBOARDING_PROMPT，不重写 prompt 内容
- workflow: A/codex_plugin/skill_orchestrated
