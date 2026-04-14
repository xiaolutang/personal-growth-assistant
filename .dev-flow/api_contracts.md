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
