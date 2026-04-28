# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.44.0
> 状态：规划中（R044）
> 活跃分支：feat/R044-unified-react-agent

## 当前范围

R044 统一智能体重构：将两套并行对话系统（ChatService + AIChatService）合并为 LangGraph ReAct Agent 统一智能体，具备多步推理、多轮对话、主动追问能力。

### Phase 1: 后端核心 — Agent 基础设施（3 tasks）

1. **B185 Agent Tools 定义与实现**：7 个 tools 的 Pydantic schema + 函数实现，封装现有 service
2. **B186 LangGraph ReAct Agent 图**：StateGraph + Agent/ToolNode 循环，system prompt 模板，循环上限 5 轮
3. **B187 AgentService + 统一 Router**：会话管理、SSE 事件编排（新增 thinking/tool_call/tool_result）

### Phase 2: 前端适配（2 tasks）

4. **F185 agentStore + SSE 解析**：统一 store 替换 chatStore，8 种 SSE 事件解析
5. **F186 AgentChat 组件族**：8 个组件（AgentChat/MessageList/AgentMessage/ToolCallCard/ThinkingIndicator/ChatInput/AgentPrompt/UserMessage）

### Phase 3: 清理旧代码（1 task）

6. **B188 删除旧服务和路由**：删除 ChatService/AIChatService/IntentService/TaskParserGraph + 旧路由

### Phase 4: 评估体系（3 tasks）

7. **B189 Golden Dataset 框架**：测试框架 + 87 条数据 + pass@k + 环境隔离
8. **B190 LLM-as-Judge + 多轮评估**：9 维评分 + 30 条多轮数据 + 模拟用户 + outcome grading
9. **B191 评估转录系统**：转录记录 + 审查工具 + 饱和度监控

### Phase 5: 可观测性（2 tasks）

10. **S45 Langfuse 自部署 + 接入**：Docker 部署 + CallbackHandler 接入
11. **S46 监控指标 + 告警**：指标采集 + 告警规则

### Phase 6: 用户反馈（2 tasks）

12. **F187 反馈 UI**：👍👎⚑ 按钮 + 反馈面板
13. **B192 反馈 API + 闭环**：反馈存储 + Issue 自动创建

### Phase 7: 质量收口（1 task）

14. **S47 全量测试 + E2E 验证**：单元测试 + 集成测试 + Golden Dataset 回归 + Docker smoke

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 14 |
| P0 | 7（B185, B186, B187, F185, F186, B188, S47）|
| P1 | 5（B189, B190, B191, S45, S46）|
| P2 | 2（F187, B192）|

## 技术约束

- 所有 tools 通过现有 service 层操作，不直接访问 storage
- 分层不变量：routers → AgentService → Agent → Tools → Services → Infrastructure
- Agent 循环上限 5 轮
- SSE 向后兼容（保留 content/created/updated/error/done 事件）
- 旧代码删除前需确认新系统完全替代
- workflow: B/codex_plugin/skill_orchestrated

## 决策来源

- `.dev-flow/decisions/2026-04-28--agent-refactoring.md`（完整 brainstorm 决策记录）
