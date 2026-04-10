# API 契约

## Contract Index

| ID | Method | Path | Description | Related Tasks |
|----|--------|------|-------------|---------------|
| CONTRACT-001 | POST | /api/logs/ingest | 批量写入日志 | B004 |
| CONTRACT-002 | GET | /api/logs | 查询日志列表 | B005 |
| CONTRACT-003 | GET | /api/logs/stats | 查询日志统计 | B005 |
| CONTRACT-004 | DELETE | /api/logs/cleanup | 清理过期日志 | B005 |
| CONTRACT-005 | GET | /health | 服务健康检查 | B001 |

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
