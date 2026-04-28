# S001: R044 统一智能体重构 — 规划

> 时间：2026-04-28
> 类型：规划
> 决策来源：`decisions/2026-04-28--agent-refactoring.md`

## 需求摘要

将两套并行对话系统（ChatService + AIChatService）合并为 LangGraph ReAct Agent 统一智能体。

核心改动：
1. **后端**：新建 AgentService + ReAct Agent + 7 Tools，替代 ChatService/AIChatService/IntentService/TaskParserGraph
2. **前端**：新建 AgentChat 组件族 + agentStore
3. **路由**：POST /chat 统一入口，删除 /parse + /ai/chat
4. **SSE**：扩展事件类型（thinking/tool_call/tool_result）
5. **评估**：Golden Dataset 117 条 + LLM-as-Judge 9 维 + 转录审查
6. **可观测性**：Langfuse 自部署
7. **监控反馈**：指标告警 + 用户反馈闭环

## 架构校验

- 分层不变量 ✅：routers → AgentService → Agent → Tools → Services → Infrastructure
- MCP 不受影响 ✅
- 三层存储 ✅：Tools 通过 Service 访问
- user_id 隔离 ✅
- service 不依赖 router ✅

需更新 architecture.md：
- 后端结构：graphs/ → agent/
- 技术栈：LangSmith → Langfuse
- 新增 ReAct Agent / Tools / SSE 事件模式

## 规划结论

14 个任务，7 个 Phase，P0: 7 / P1: 5 / P2: 2

## Workflow

- mode: B
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin

## Plan Review 记录

### Round 1 (2026-04-28)
- status: conditional_pass
- required_changes: 4 项
  1. S-1/F-1: ask_user 中断机制未定义
  2. S-2: 会话管理端点迁移归属不明确
  3. J-1: /chat 请求体兼容策略缺失
  4. T-1/T-2/T-3: 核心 P0 任务失败分支测试不足
- 修复：全部 4 项已补充到 feature_list.json + api_contracts.md

### Round 2 (2026-04-28)
- status: pass
- required_changes: [] (无阻塞项)
- low severity findings: 7 项（不阻塞）
  - 2 journey: 反馈提交失败 UI、Agent 长时间无响应 UI
  - 1 seam: SSE 异常恢复序列规范
  - 2 test: 前端组件测试、评估体系 test_tasks
  - 1 architecture: 前端旧引用清理显式化
  - 1 feasibility: S47 依赖链完整性
