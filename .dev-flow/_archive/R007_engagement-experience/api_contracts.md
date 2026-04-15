# API 契约

## Contract Index

| ID | Method | Path | Description | Related Tasks |
|----|--------|------|-------------|---------------|
| CONTRACT-001 | POST | /api/logs/ingest | 批量写入日志 | B004 |
| CONTRACT-002 | GET | /api/logs | 查询日志列表 | B005 |
| CONTRACT-003 | GET | /api/logs/stats | 查询日志统计 | B005 |
| CONTRACT-004 | DELETE | /api/logs/cleanup | 清理过期日志 | B005 |
| CONTRACT-005 | GET | /health | 服务健康检查 | B001 |
| CONTRACT-006 | POST | /feedback | 提交用户反馈（双写，需认证） | S05, B16 |
| CONTRACT-R01 | GET | /review/trend | 回顾趋势数据 | S05, B14 |
| CONTRACT-E01 | PUT | /entries/{entry_id} | 灵感转化（category 变更） | S05, B15 |
| CONTRACT-E02 | GET | /entries/export | 条目数据导出 | B18, F12 |
| CONTRACT-E03 | GET | /entries/{id}/related | 条目关联推荐 | B19, F13 |
| CONTRACT-O01 | GET | /auth/me | 获取当前用户（含 onboarding_completed） | F09 |
| CONTRACT-O02 | PUT | /auth/me | 更新 onboarding 状态 | F09 |
| CONTRACT-FB01 | GET | /feedback | 反馈列表查询 | S05, B16, F06 |
| CONTRACT-FB02 | GET | /feedback/{id} | 反馈详情查询 | S05, B16 |
| CONTRACT-MD01 | GET | /review/morning-digest | AI 晨报（每日主动建议） | B24, F20 |
| CONTRACT-AI01 | POST | /ai/chat | 页面级 AI 对话（SSE 流式） | F22 |
| CONTRACT-NT01 | GET | /notifications | 获取当前用户通知列表（按需生成） | B26, F25 |
| CONTRACT-NT02 | POST | /notifications/{id}/dismiss | 标记通知已读 | B26, F25 |
| CONTRACT-NT03 | GET | /notification-preferences | 获取提醒偏好 | B26, F25 |
| CONTRACT-NT04 | PUT | /notification-preferences | 更新提醒偏好 | B26, F25 |
| CONTRACT-HM01 | GET | /review/activity-heatmap | 年度每日活动热力图 | B27, F26 |
| CONTRACT-A01 | POST | /auth/register | 用户注册 | S01, B02 |
| CONTRACT-A02 | POST | /auth/login | 用户登录 | S01, B02 |
| CONTRACT-A03 | POST | /auth/logout | 用户登出 | S01, B02 |
| CONTRACT-A04 | GET | /auth/me | 获取当前用户 | S01, B02 |

---

## 条目导出

### 导出条目数据

| 字段 | 值 |
|------|----|
| ID | CONTRACT-E02 |
| Method | GET |
| Path | /entries/export |
| Auth | Bearer Token |
| Related Tasks | B18, F12 |

#### Request (Query Params)

```
format=markdown    # markdown 或 json，默认 markdown
type=inbox         # 可选，按 category 过滤（inbox/task/note/project）
start_date=2026-04-01  # 可选，ISO 日期，起始时间
end_date=2026-04-15    # 可选，ISO 日期，结束时间
```

#### Response 200 (format=markdown)

- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename="entries_export.zip"`
- zip 内按 category 子目录组织：`inbox/`, `tasks/`, `notes/`, `projects/`

#### Response 200 (format=json)

```json
[
  {
    "id": "inbox-abc123",
    "title": "灵感标题",
    "category": "inbox",
    "content": "# 灵感内容\n\nMarkdown 正文...",
    "tags": ["tag1", "tag2"],
    "status": "pending",
    "created_at": "2026-04-14T10:00:00",
    "updated_at": "2026-04-14T10:00:00"
  }
]
```

#### Notes

- 大数据量使用 StreamingResponse + zipfile 流式写入
- 所有查询带 user_id 隔离
- 空数据时 markdown 格式返回空 zip，json 格式返回空数组
- type 参数与 category 值对应：inbox/task/note/project

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
| 422 | format 参数不在 markdown/json 中 |

---

## 条目关联

### 获取关联条目

| 字段 | 值 |
|------|----|
| ID | CONTRACT-E03 |
| Method | GET |
| Path | /entries/{id}/related |
| Auth | Bearer Token |
| Related Tasks | B19, F13 |

#### Response 200

```json
[
  {
    "id": "task-def456",
    "title": "相关任务标题",
    "category": "task",
    "relevance_reason": "同项目",
    "status": "completed",
    "created_at": "2026-04-13T10:00:00"
  },
  {
    "id": "note-ghi789",
    "title": "相关笔记标题",
    "category": "note",
    "relevance_reason": "标签重叠：React, Hooks",
    "status": "pending",
    "created_at": "2026-04-12T10:00:00"
  }
]
```

#### Notes

- 关联优先级：同 parent_id 兄弟条目 → 标签重叠条目 → 向量相似条目
- 最多返回 5 条
- relevance_reason 描述关联原因
- 所有查询带 user_id 隔离
- 无关联时返回空数组

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
| 404 | 条目不存在 |

---

## Onboarding 状态

### 获取当前用户（含 onboarding_completed）

| 字段 | 值 |
|------|----|
| ID | CONTRACT-O01 |
| Method | GET |
| Path | /auth/me |
| Auth | Bearer Token |
| Related Tasks | F09 |

#### Response 200

```json
{
  "id": "usr_abc123",
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "is_active": true,
  "onboarding_completed": false,
  "created_at": "2026-04-13T10:00:00Z"
}
```

### 更新 onboarding 状态

| 字段 | 值 |
|------|----|
| ID | CONTRACT-O02 |
| Method | PUT |
| Path | /auth/me |
| Auth | Bearer Token |
| Related Tasks | F09 |

#### Request

```json
{
  "onboarding_completed": true
}
```

#### Response 200

```json
{
  "id": "usr_abc123",
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "is_active": true,
  "onboarding_completed": true,
  "created_at": "2026-04-13T10:00:00Z"
}
```

#### Notes

- 已有用户的 onboarding_completed 默认 FALSE
- 可通过迁移脚本将已有用户设为 TRUE

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |

---

## 回顾趋势

### 获取趋势数据

| 字段 | 值 |
|------|----|
| ID | CONTRACT-R01 |
| Method | GET |
| Path | /review/trend |
| Auth | Bearer Token |
| Related Tasks | S05, B14 |

#### Request (Query Params)

```
period=daily      # daily 或 weekly
days=7            # period=daily 时有效，默认 7
weeks=8           # period=weekly 时有效，默认 8
```

#### Response 200

```json
{
  "periods": [
    {
      "date": "2026-04-14",
      "total": 5,
      "completed": 3,
      "completion_rate": 60.0,
      "notes_count": 2
    }
  ]
}
```

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
| 422 | period 参数不在 daily/weekly 中 |

---

## 灵感转化

### 更新条目 category

| 字段 | 值 |
|------|----|
| ID | CONTRACT-E01 |
| Method | PUT |
| Path | /entries/{entry_id} |
| Auth | Bearer Token |
| Related Tasks | S05, B15 |

#### Request

```json
{
  "category": "task"
}
```

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
| 404 | 条目不存在 |

---

## 反馈提交

### 提交用户反馈

| 字段 | 值 |
|------|----|
| ID | CONTRACT-006 |
| Method | POST |
| Path | /feedback |
| Auth | Bearer Token |
| Related Tasks | S05, B16 |

#### Request

```json
{
  "title": "搜索功能响应慢",
  "description": "在任务列表中搜索时，页面卡顿约 3 秒",
  "severity": "medium"
}
```

#### Errors

| Code | Meaning |
|------|---------|
| 422 | title 为空、缺失，或 severity 不在 low/medium/high/critical |

---

## 反馈列表查询

### 获取当前用户反馈列表

| 字段 | 值 |
|------|----|
| ID | CONTRACT-FB01 |
| Method | GET |
| Path | /feedback |
| Auth | Bearer Token |
| Related Tasks | S05, B16, F06 |

#### Notes

- status 枚举: `pending`（待上报）、`reported`（已上报到 log-service）
- 按 created_at 倒序排列
- 只返回当前用户的反馈（user_id 隔离）

---

## 用户认证

### 用户注册

| 字段 | 值 |
|------|----|
| ID | CONTRACT-A01 |
| Method | POST |
| Path | /auth/register |
| Auth | None |
| Related Tasks | S01, B02 |

#### Request

```json
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "mysecretpassword"
}
```

#### Errors

| Code | Meaning |
|------|---------|
| 409 | username 或 email 已存在 |
| 422 | 参数校验失败 |

---

### 用户登录

| 字段 | 值 |
|------|----|
| ID | CONTRACT-A02 |
| Method | POST |
| Path | /auth/login |
| Auth | None |
| Related Tasks | S01, B02 |

#### Response 200

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "usr_abc123",
    "username": "zhangsan",
    "email": "zhangsan@example.com"
  }
}
```

---

### 用户登出

| 字段 | 值 |
|------|----|
| ID | CONTRACT-A03 |
| Method | POST |
| Path | /auth/logout |
| Auth | Bearer Token |
| Related Tasks | S01, B02 |

---

### 获取当前用户

| 字段 | 值 |
|------|----|
| ID | CONTRACT-A04 |
| Method | GET |
| Path | /auth/me |
| Auth | Bearer Token |
| Related Tasks | S01, B02 |

#### Response 200

```json
{
  "id": "usr_abc123",
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "is_active": true,
  "created_at": "2026-04-13T10:00:00Z"
}
```

---

## AI 晨报

### 获取每日晨报

| 字段 | 值 |
|------|----|
| ID | CONTRACT-MD01 |
| Method | GET |
| Path | /review/morning-digest |
| Auth | Bearer Token |
| Related Tasks | B24, F20 |

#### Response 200

```json
{
  "date": "2026-04-15",
  "ai_suggestion": "你有3个任务待完成，建议先做 R003代码审查...",
  "todos": [
    {"id": "task-abc", "title": "R003 代码审查", "priority": "high", "planned_date": "2026-04-13"}
  ],
  "overdue": [
    {"id": "task-def", "title": "Review 代码", "priority": "medium", "planned_date": "2026-04-10"}
  ],
  "stale_inbox": [
    {"id": "inbox-ghi", "title": "AI读书摘要", "created_at": "2026-04-12T10:00:00"}
  ],
  "weekly_summary": {
    "new_concepts": ["Rust", "React Hooks"],
    "entries_count": 12
  }
}
```

#### Notes

- LLM 不可用时 `ai_suggestion` 降级为模板文本
- 同一天内多次请求返回缓存结果（按 date 缓存）
- 所有查询带 user_id 隔离
- 空数据时各数组为空，ai_suggestion 为引导文案

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |

---

## 页面级 AI 对话

### 上下文感知对话（SSE 流式）

| 字段 | 值 |
|------|----|
| ID | CONTRACT-AI01 |
| Method | POST |
| Path | /ai/chat |
| Auth | Bearer Token |
| Related Tasks | F22 |

#### Request

```json
{
  "message": "帮我看看今天的任务",
  "context": {
    "page": "home",
    "page_data": {"todo_count": 3, "overdue_count": 1},
    "selected_items": [],
    "filters": {}
  },
  "conversation_id": "conv-abc123",
  "messages": [
    {"role": "user", "content": "今天有什么任务？"},
    {"role": "assistant", "content": "你有3个任务待完成..."}
  ]
}
```

#### Response 200 (SSE)

```
Content-Type: text/event-stream

data: {"token": "你"}
data: {"token": "今天"}
data: {"token": "有3个任务"}
```

#### Notes

- conversation_id 由前端生成，用于隔离不同对话面板的上下文
- messages 数组由前端携带最近 5 轮历史（role + content），不新增后端存储层
- page_data 由前端注入当前页面关键数据摘要
- LLM 不可用时返回 503

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
| 422 | message 为空 |
| 503 | LLM 服务不可用 |

---

## 通知/提醒

### 获取当前用户通知列表（按需生成）

| 字段 | 值 |
|------|----|
| ID | CONTRACT-NT01 |
| Method | GET |
| Path | /notifications |
| Auth | Bearer Token |
| Related Tasks | B26, F25 |

#### Response 200

```json
{
  "items": [
    {
      "id": "overdue:task-abc:2026-04-15",
      "type": "overdue_task",
      "title": "任务已拖延",
      "message": "\"R003 代码审查\" 已超过计划日期 2 天",
      "ref_id": "task-abc",
      "created_at": "2026-04-15T09:00:00",
      "dismissed": false
    },
    {
      "id": "stale_inbox:inbox-def:2026-04-15",
      "type": "stale_inbox",
      "title": "灵感未转化",
      "message": "\"AI读书摘要\" 已在收件箱 4 天，考虑转化为任务或笔记",
      "ref_id": "inbox-def",
      "created_at": "2026-04-15T09:00:00",
      "dismissed": false
    },
    {
      "id": "review_prompt:2026-04-13",
      "type": "review_prompt",
      "title": "回顾提醒",
      "message": "你已 2 天没有记录，回顾一下最近的学习进展吧",
      "ref_id": null,
      "created_at": "2026-04-15T09:00:00",
      "dismissed": false
    }
  ],
  "unread_count": 3
}
```

#### Notes

- 通知按需生成：每次 GET 时从当前数据实时计算，不依赖后台调度
- 通知 ID 格式：`{type}:{ref_id}:{date}`（当日日期），用于 dismiss 去重
- 已 dismiss 的通知记录到 SQLite `notifications` 表（id, user_id, notification_type, ref_id, dismissed_at, created_at），同一天内不再重复生成
- 通知类型规则：
  - `overdue_task`：planned_date < 今天 且 status != complete 的任务
  - `stale_inbox`：created_at 距今 > 3 天 且 category 仍为 inbox 的灵感
  - `review_prompt`：最近 2 天内无任何条目创建/更新时触发
- review_prompt 触发窗口：检测最近 2 天（含今天）是否有条目活动，无活动则生成
- review_prompt 生成频率：按天去重（同一天只生成一条，dismiss 后当日不再出现）
- dismiss 去重周期：当日有效，跨天后 dismiss 记录不影响新一天的通知生成
- 所有查询带 user_id 隔离

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |

---

### 标记通知已读

| 字段 | 值 |
|------|----|
| ID | CONTRACT-NT02 |
| Method | POST |
| Path | /notifications/{id}/dismiss |
| Auth | Bearer Token |
| Related Tasks | B26, F25 |

#### Path Params

- `id`: 通知 ID（如 `overdue:task-abc:2026-04-15`）

#### Response 200

```json
{
  "success": true
}
```

#### Notes

- dismiss 后写入 SQLite，当日不再重复展示该通知
- 跨天后 dismiss 记录不影响新一天的通知生成

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
| 404 | 通知不存在 |

---

### 获取/更新提醒偏好

| 字段 | 值 |
|------|----|
| ID | CONTRACT-NT03 / CONTRACT-NT04 |
| Method | GET / PUT |
| Path | /notification-preferences |
| Auth | Bearer Token |
| Related Tasks | B26, F25 |

#### Response 200 (GET) / Request (PUT)

```json
{
  "overdue_task_enabled": true,
  "stale_inbox_enabled": true,
  "review_prompt_enabled": true
}
```

#### Notes

- 偏好存储在 SQLite `notification_preferences` 表（user_id, overdue_task_enabled, stale_inbox_enabled, review_prompt_enabled）
- 某类型 enabled=false 时，GET /notifications 不生成该类型通知
- 默认全部 enabled=true

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |

---

## 活动热力图

### 获取年度每日活动数据

| 字段 | 值 |
|------|----|
| ID | CONTRACT-HM01 |
| Method | GET |
| Path | /review/activity-heatmap |
| Auth | Bearer Token |
| Related Tasks | B27, F26 |

#### Request (Query Params)

```
year=2026    # 年份，默认当前年
```

#### Response 200

```json
{
  "year": 2026,
  "items": [
    {"date": "2026-04-14", "count": 5},
    {"date": "2026-04-13", "count": 2},
    {"date": "2026-04-12", "count": 0}
  ]
}
```

#### Notes

- count 统计口径：当日 **created_at** 的条目数（与现有 list_entries 查询能力一致，不新增 updated_at 查询）
- 返回全年 365/366 天数据，无活动日期 count=0
- 所有查询带 user_id 隔离
- 复用现有 list_entries 的时间筛选能力

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
