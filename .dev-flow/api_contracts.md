# API 契约

## 契约索引

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-KG01 | GET | /knowledge/search | B28 | planned |
| CONTRACT-KG02 | GET | /knowledge/concepts/{name}/timeline | B28 | planned |
| CONTRACT-KG03 | GET | /knowledge/mastery-distribution | B28 | planned |
| CONTRACT-AI01 | POST | /entries/{id}/ai-summary | B30 | planned |
| CONTRACT-AI02 | POST | /chat | B31, F30 | planned |
| CONTRACT-MCP01 | — | MCP stdio tools | B29 | planned |

---

## CONTRACT-KG01: GET /knowledge/search

搜索概念。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| q | query | string | 是 | 搜索关键词 |
| limit | query | int | 否 | 最大返回数，默认 20 |

### 响应 200（Neo4j 可用）

```json
{
  "items": [
    {
      "name": "React",
      "entry_count": 5,
      "mastery": "intermediate"
    }
  ]
}
```

### 响应 200（SQLite 降级）

```json
{
  "items": [
    {
      "name": "React",
      "entry_count": 5,
      "mastery": null
    }
  ]
}
```

### 降级行为

Neo4j 不可用时从 SQLite tags 表 LIKE 搜索。降级响应中 `mastery` 字段为 `null`（SQLite 无掌握度数据），前端需适配。

---

## CONTRACT-KG02: GET /knowledge/concepts/{name}/timeline

概念学习时间线。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| name | path | string | 是 | 概念名 |
| days | query | int | 否 | 最近 N 天，默认 90 |

### 响应 200

```json
{
  "concept": "React",
  "items": [
    {
      "date": "2026-04-10",
      "entries": [
        {"id": "entry-1", "title": "学习 Hooks", "type": "note"}
      ]
    }
  ]
}
```

---

## CONTRACT-KG03: GET /knowledge/mastery-distribution

掌握度分布统计。

### 响应 200

```json
{
  "new": 12,
  "beginner": 8,
  "intermediate": 5,
  "advanced": 2,
  "total": 27
}
```

---

## CONTRACT-AI01: POST /entries/{id}/ai-summary

生成/获取条目 AI 摘要。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | path | string | 是 | 条目 ID |

### 响应 200

```json
{
  "summary": "本条目记录了 React Hooks 的学习...",
  "generated_at": "2026-04-15T10:00:00",
  "cached": false
}
```

### 特殊行为

- 空内容条目返回 `{"summary": null, "generated_at": null, "cached": false}`
- 摘要已缓存时返回 `cached: true`，不重复调用 LLM
- 条目不存在返回 404
- 非本人条目返回 403

---

## CONTRACT-AI02: POST /chat（page_context 扩展）

在现有 ChatRequest 基础上新增可选页面上下文字段。

### 请求变更

现有字段不变（text, session_id, skip_intent, confirm），新增：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| page_context | body | PageContext | 否 | 页面上下文 |

PageContext 结构：

```json
{
  "page_type": "entry",
  "entry_id": "entry-abc123",
  "extra": {"title": "React Hooks 学习笔记"}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| page_type | string | 页面类型：home/explore/entry/review/graph |
| entry_id | string? | 当前条目 ID（仅 entry 页面） |
| extra | object? | 扩展信息（如条目标题、统计数据摘要） |

### 行为

- `page_context` 为 null/缺失时，行为与现有一致
- `page_context` 存在时，chat_service 在构建 LLM prompt 时追加上下文指令
- 前端 F30 负责在各页面注入对应上下文

---

## CONTRACT-MCP01: MCP 工具增强

B29 新增/增强的 MCP 工具，通过 stdio 传输，环境变量 JWT 认证。

### 新增工具

| 工具名 | 参数 | 说明 |
|--------|------|------|
| batch_create_entries | entries: JSON[], max 10 | 批量创建条目 |
| batch_update_status | ids: string[], status: string, max 10 | 批量更新状态 |
| get_learning_path | concept: string | 学习路径（复用 knowledge_service） |

### 批量超限行为

- `entries` 或 `ids` 数量 > 10 时，**拒绝执行并返回错误消息**（不截断、不部分成功）
- 错误格式：`{"error": "batch limit exceeded: got N, max 10"}`
- 空数组 `[]` 返回友好提示：`{"error": "no items provided"}`

### 认证失败行为

- 无 JWT token / token 过期 / token 无效 → 统一返回 `{"error": "unauthorized"}`
- 认证失败时不执行任何数据操作
- 认证失败对所有新工具和增强工具一致

### 增强工具

| 工具名 | 变更 | 说明 |
|--------|------|------|
| search_entries | 新增 SQLite fallback | Qdrant 不可用时降级到 LIKE 搜索 |

### 不变更

| 工具名 | 说明 |
|--------|------|
| get_knowledge_stats | 已存在，B29 不重复 |

---

## R010 新增契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-ENG01 | GET | /health | B34 | planned |

---

## CONTRACT-ENG01: GET /health（增强）

健康检查端点增强，返回服务状态和依赖连接检查。

### 响应 200（全部正常）

```json
{
  "status": "ok",
  "services": {
    "sqlite": "ok",
    "neo4j": "ok",
    "qdrant": "ok"
  }
}
```

### 响应 503（核心依赖不可达）

```json
{
  "status": "degraded",
  "services": {
    "sqlite": "error",
    "neo4j": "ok",
    "qdrant": "unavailable"
  }
}
```

### 降级行为

- SQLite 不可达 → 整体返回 503（核心依赖）
- Neo4j 不可达 → 标记 `"neo4j": "unavailable"`，不影响整体 200
- Qdrant 不可达 → 标记 `"qdrant": "unavailable"`，不影响整体 200
