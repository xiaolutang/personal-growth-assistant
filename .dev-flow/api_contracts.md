# API 契约

## 契约索引

### R047 新增/修改契约（任务/探索 Tab 边界重新划分）

| 契约 ID | 方法 | 端点 | 任务 | 说明 |
|---------|------|------|------|------|
| CONTRACT-CONVERT | POST | /entries/{id}/convert | S01 | 类型转换，body: { target_category, priority?, planned_date?, parent_id? }，合法转换: inbox→task/inbox→decision/inbox→note，返回更新后的条目 |
| CONTRACT-CATEGORY-GROUP | GET | /entries?category_group={group} | B02 | 按类型组查询，actionable=task+decision+project，knowledge=inbox+note+reflection+question，与 type 参数互斥 |
| CONTRACT-TYPE-HISTORY | — | — | S01 | Task 模型新增 type_history: List[{from_category, to_category, at}]，EntryResponse 包含此字段 |

### R047 修改的现有端点

| 契约 ID | 方法 | 端点 | 变更 | 任务 |
|---------|------|------|------|------|
| CONTRACT-ENTRY-LIST | GET | /entries | 新增 category_group 查询参数 | B02 |

### R047 前端类型同步

| 变更 | 任务 | 说明 |
|------|------|------|
| api.generated.ts 更新 | S01, B02 | npm run gen:types 重新生成，包含 convert API + category_group + type_history |
| task.ts 更新 | S01 | 前端 Task 类型新增 type_history 字段 |

### R044 新增/修改契约（统一智能体重构）

| 契约 ID | 方法 | 端点 | 任务 | 说明 |
|---------|------|------|------|------|
| CONTRACT-AGENT-CHAT | POST | /chat | B187 | 统一聊天入口，SSE 流式响应，新增 thinking/tool_call/tool_result 事件 |
| CONTRACT-AGENT-SESSIONS | GET/DELETE/PATCH | /sessions/* | B187 | 会话管理端点保留不变（GET/DELETE/PATCH） |
| CONTRACT-FEEDBACK | POST | /feedback | B192 | 扩展支持 Agent 反馈类型（message_id + type + reason） |
| CONTRACT-LANGFUSE | — | — | S45 | Langfuse 自部署内部服务，不暴露外部端点 |
| CONTRACT-TOOLS-INTERNAL | — | — | B185 | Agent Tools 内部接口，封装 service 调用，不暴露端点 |

### R044 删除的端点

| 方法 | 端点 | 替代 | 任务 |
|------|------|------|------|
| POST | /parse | POST /chat | B188 |
| POST | /ai/chat | POST /chat | B188 |
| GET | /ai/chat/history | GET /sessions/{id}/messages | B188 |

## CONTRACT-AGENT-CHAT: POST /chat

### 请求体

```json
{
  "text": "string (required) — 用户输入文本",
  "session_id": "string (required) — 会话 ID",
  "page_context": {
    "page_type": "home|tasks|notes|inbox|projects|explore|review|entry_detail",
    "entry_id": "string? (entry_detail 页面时必填)",
    "extra": "object?"
  }
}
```

> **迁移说明**：旧字段 `confirm`、`skip_intent`、`force_intent` 已移除（IntentService 相关），Agent 通过 ReAct 循环自主决策。请求含这些字段时忽略不报错。

### 响应：SSE 流

```
event: thinking
data: {"content": "让我看看..."}

event: tool_call
data: {"id": "call_xxx", "tool": "create_entry", "args": {"type": "note", "content": "...", "tags": ["Rust"]}}

event: tool_result
data: {"tool_call_id": "call_xxx", "tool": "create_entry", "result": {"id": "xxx", "type": "note"}, "success": true}

event: content
data: {"text": "已为你创建了笔记"}

event: created
data: {"id": "xxx", "type": "note", "content": "..."}

event: updated
data: {"id": "xxx", "changes": {"status": "completed"}}

event: error
data: {"message": "操作失败：..."}

event: done
data: {}
```

### SSE 事件顺序

典型工具调用流程：`thinking → tool_call → tool_result → [循环] → content → done`
纯对话流程：`thinking → content → done`
多步操作流程：`thinking → tool_call → tool_result → thinking → tool_call → tool_result → content → done`

### ask_user 追问流程

1. Agent 调用 ask_user tool → SSE: `tool_call(ask_user) → tool_result(ask_user) → content(追问文本) → done`
2. ReAct 图条件边检测到 ask_user，路由到 END 中断循环
3. 前端收到 done 后输入框自动聚焦，展示追问文本
4. 用户输入回复 → 同 session_id 再次 POST /chat
5. Checkpointer 自动恢复对话历史，Agent 继续推理

## CONTRACT-FEEDBACK: POST /feedback（扩展）

### 请求体

```json
{
  "message_id": "string (required) — Agent 回复的消息 ID",
  "type": "thumbs_up|thumbs_down|report (required)",
  "reason": "understanding_error|action_error|unhelpful|should_ask_didnt|shouldnt_ask_did|other (required for thumbs_down)",
  "detail": "string? — 用户补充说明"
}
```

### 响应

```json
{"ok": true}
```

### 副作用

- 👎 自动创建 Issue (medium severity)
- Langfuse 标记对应 trace
- bad case 定期补充到 Golden Dataset
