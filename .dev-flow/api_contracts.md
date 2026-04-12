# API 契约

## Contract Index

| ID | Method | Path | Description | Related Tasks |
|----|--------|------|-------------|---------------|
| CONTRACT-001 | POST | /api/logs/ingest | 批量写入日志 | B004 |
| CONTRACT-002 | GET | /api/logs | 查询日志列表 | B005 |
| CONTRACT-003 | GET | /api/logs/stats | 查询日志统计 | B005 |
| CONTRACT-004 | DELETE | /api/logs/cleanup | 清理过期日志 | B005 |
| CONTRACT-005 | GET | /health | 服务健康检查 | B001 |
| CONTRACT-006 | POST | /feedback | 提交用户反馈 | S004, FB01, FB03 |
| CONTRACT-A01 | POST | /auth/register | 用户注册 | S01, B02 |
| CONTRACT-A02 | POST | /auth/login | 用户登录 | S01, B02 |
| CONTRACT-A03 | POST | /auth/logout | 用户登出 | S01, B02 |
| CONTRACT-A04 | GET | /auth/me | 获取当前用户 | S01, B02 |

---

## 日志写入

### 批量写入日志

| 字段 | 值 |
|------|----|
| ID | CONTRACT-001 |
| Method | POST |
| Path | /api/logs/ingest |
| Auth | None |
| Related Tasks | B004 |

#### Request

```json
{
  "service_name": "personal-growth-assistant",
  "logs": [
    {
      "level": "ERROR",
      "message": "数据库连接失败",
      "logger_name": "app.services.sync",
      "timestamp": "2026-03-28T10:30:00Z",
      "request_id": "abc-123",
      "method": "GET",
      "path": "/api/entries",
      "status_code": 500,
      "process_time_ms": 1200,
      "client_ip": "127.0.0.1",
      "exception_type": "ConnectionError",
      "exception_message": "Could not connect to database",
      "stack_trace": "Traceback...",
      "extra": {"key": "value"}
    }
  ]
}
```

#### Response 200

```json
{
  "ingested": 5
}
```

#### Errors

| Code | Meaning |
|------|---------|
| 400 | 请求体格式错误或 service_name 缺失 |
| 422 | 日志条目校验失败 |

---

## 日志查询

### 查询日志列表

| 字段 | 值 |
|------|----|
| ID | CONTRACT-002 |
| Method | GET |
| Path | /api/logs |
| Auth | None |
| Related Tasks | B005 |

#### Request (Query Params)

```
level=ERROR
service_name=personal-growth-assistant
request_id=abc-123
keyword=数据库
start_time=2026-03-28T00:00:00Z
end_time=2026-03-28T23:59:59Z
page=1
page_size=50
sort_by=timestamp
sort_order=desc
```

#### Response 200

```json
{
  "logs": [
    {
      "id": 1,
      "service_name": "personal-growth-assistant",
      "level": "ERROR",
      "message": "数据库连接失败",
      "logger_name": "app.services.sync",
      "timestamp": "2026-03-28T10:30:00Z",
      "request_id": "abc-123",
      "method": "GET",
      "path": "/api/entries",
      "status_code": 500,
      "process_time_ms": 1200,
      "client_ip": "127.0.0.1",
      "exception_type": "ConnectionError",
      "exception_message": "Could not connect to database",
      "stack_trace": "Traceback...",
      "extra": {"key": "value"}
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

#### Errors

| Code | Meaning |
|------|---------|
| 400 | 查询参数格式错误 |

---

### 查询日志统计

| 字段 | 值 |
|------|----|
| ID | CONTRACT-003 |
| Method | GET |
| Path | /api/logs/stats |
| Auth | None |
| Related Tasks | B005 |

#### Response 200

```json
{
  "total_count": 15000,
  "count_by_level": {
    "DEBUG": 5000,
    "INFO": 8000,
    "WARNING": 1500,
    "ERROR": 500
  },
  "count_by_service": {
    "personal-growth-assistant": 10000,
    "other-service": 5000
  },
  "oldest_log": "2026-02-28T00:00:00Z",
  "newest_log": "2026-03-28T10:30:00Z",
  "db_size_mb": 5.2
}
```

---

### 清理过期日志

| 字段 | 值 |
|------|----|
| ID | CONTRACT-004 |
| Method | DELETE |
| Path | /api/logs/cleanup |
| Auth | None |
| Related Tasks | B005 |

#### Request (Query Params)

```
retention_days=30
```

#### Response 200

```json
{
  "deleted_count": 500,
  "retention_days": 30
}
```

---

## 健康检查

### 服务健康检查

| 字段 | 值 |
|------|----|
| ID | CONTRACT-005 |
| Method | GET |
| Path | /health |
| Auth | None |
| Related Tasks | B001 |

#### Response 200

```json
{
  "status": "healthy"
}
```

---

## 反馈提交

### 提交用户反馈

| 字段 | 值 |
|------|----|
| ID | CONTRACT-006 |
| Method | POST |
| Path | /feedback |
| Auth | None |
| Related Tasks | S004, FB01, FB03 |

#### Request

```json
{
  "title": "搜索功能响应慢",
  "description": "在任务列表中搜索时，页面卡顿约 3 秒",
  "severity": "medium"
}
```

#### Request Constraints

- `severity` 枚举统一为 `low | medium | high | critical`
- 代理层调用前先完成 `log_service_sdk.report_issue()` 签名确认，确保入参与返回结构一致

#### Response 200

```json
{
  "success": true,
  "issue": {
    "id": 1,
    "title": "搜索功能响应慢",
    "status": "open",
    "created_at": "2026-04-12T10:00:00Z"
  }
}
```

#### Errors

| Code | Meaning |
|------|---------|
| 422 | title 为空、缺失，或 severity 不在 low/medium/high/critical |
| 503 | log-service 不可达 |

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

#### Request Constraints

- `username`: 必填，3-50 字符，仅允许字母数字下划线
- `email`: 必填，有效 email 格式
- `password`: 必填，最少 6 字符

#### Response 201

```json
{
  "id": "usr_abc123",
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "created_at": "2026-04-13T10:00:00Z"
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

#### Request

```json
{
  "username": "zhangsan",
  "password": "mysecretpassword"
}
```

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

#### Notes

- access_token 有效期 7 天（604800 秒），到期后需重新登录
- R002 不提供 refresh_token 机制，后续版本按需添加

#### Errors

| Code | Meaning |
|------|---------|
| 401 | 用户名或密码错误（不区分具体原因） |

---

### 用户登出

| 字段 | 值 |
|------|----|
| ID | CONTRACT-A03 |
| Method | POST |
| Path | /auth/logout |
| Auth | Bearer Token |
| Related Tasks | S01, B02 |

#### Response 200

```json
{
  "message": "logged out"
}
```

#### Notes

- R002 logout 为前端清除 localStorage token，后端仅返回确认响应，不维护 token 黑名单

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

#### Errors

| Code | Meaning |
|------|---------|
| 401 | Token 缺失、无效或过期 |
