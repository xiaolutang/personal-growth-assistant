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
| CONTRACT-LINK01 | POST | /entries/{id}/links | B42, F32 | planned |
| CONTRACT-LINK02 | GET | /entries/{id}/links | B42, F32 | planned |
| CONTRACT-LINK03 | DELETE | /entries/{id}/links/{link_id} | B42, F32 | planned |
| CONTRACT-KG04 | GET | /entries/{id}/knowledge-context | B43, F31 | planned |
| CONTRACT-REVIEW02 | GET | /review/morning-digest | B44, F33 | planned |

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

### 响应字段定义

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 整体状态：`"ok"` 或 `"degraded"` |
| services | object | 各依赖服务状态 |
| services.sqlite | string | `"ok"` / `"error"` |
| services.neo4j | string | `"ok"` / `"unavailable"` |
| services.qdrant | string | `"ok"` / `"unavailable"` |

### 状态取值规则

- `"ok"` — 服务连接正常
- `"error"` — 核心依赖连接失败（仅 sqlite）
- `"unavailable"` — 非核心依赖连接失败（neo4j、qdrant）
- `status` 字段规则：所有服务 ok → `"ok"`；任意非核心 unavailable → `"degraded"`；sqlite error → `"degraded"`

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

### 响应 200（非核心依赖降级，整体仍 200）

```json
{
  "status": "degraded",
  "services": {
    "sqlite": "ok",
    "neo4j": "unavailable",
    "qdrant": "unavailable"
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
- 多个非核心同时不可达 → 仍返回 200，`status: "degraded"`

---

## R011 新增契约

---

## CONTRACT-LINK01: POST /entries/{id}/links

创建条目间手动关联。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | path | string | 是 | 源条目 ID |
| target_id | body | string | 是 | 目标条目 ID |
| relation_type | body | string | 是 | 关系类型枚举 |

relation_type 枚举：`related` | `depends_on` | `derived_from` | `references`

### 响应 201

```json
{
  "id": "link-abc",
  "source_id": "entry-1",
  "target_id": "entry-2",
  "relation_type": "related",
  "created_at": "2026-04-16T10:00:00",
  "target_entry": {
    "id": "entry-2",
    "title": "React Hooks 学习",
    "category": "note"
  }
}
```

### 错误响应

| 状态码 | 场景 |
|--------|------|
| 400 | 自关联（source_id = target_id） |
| 404 | 目标条目不存在 |
| 409 | 重复关联（同 pair + 同类型） |
| 422 | relation_type 非法值 |
| 401 | 未认证 |

### 行为

- 创建时自动生成反向关联（B→A），两行在同一事务中写入
- 唯一约束：UNIQUE(user_id, source_id, target_id, relation_type)

---

## CONTRACT-LINK02: GET /entries/{id}/links

获取条目的手动关联列表。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | path | string | 是 | 条目 ID |
| direction | query | string | 否 | 过滤方向：`out` / `in` / `both`（默认） |

### direction 语义

- `out`：返回以当前条目为 source_id 的关联，`target_entry` 为关联的对方条目
- `in`：返回以当前条目为 target_id 的关联，`target_entry` 仍为关联的对方条目（即 source 侧）
- `both`：返回所有关联，每条的方向由 `direction` 字段标记

### 响应 200

```json
{
  "links": [
    {
      "id": "link-abc",
      "target_id": "entry-2",
      "target_entry": {
        "id": "entry-2",
        "title": "React Hooks 学习",
        "category": "note"
      },
      "relation_type": "related",
      "direction": "out",
      "created_at": "2026-04-16T10:00:00"
    }
  ]
}
```

### id 与 DELETE link_id 的关系

GET 返回的 `id` 字段即为 DELETE 操作使用的 `link_id`。无论 direction 为何值，返回的 `id` 始终是该行记录的主键 ID。DELETE /entries/{id}/links/{link_id} 会删除该 ID 对应的记录，并自动按 (source_id, target_id, relation_type, user_id) 交换条件查找删除配对记录。

---

## CONTRACT-LINK03: DELETE /entries/{id}/links/{link_id}

删除手动关联（双向同时删除）。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | path | string | 是 | 条目 ID |
| link_id | path | string | 是 | 关联记录 ID（可直接使用 GET 返回的 id） |

### 响应 204

无响应体。服务端按传入 link_id 定位该行记录，再按 (source_id, target_id, relation_type, user_id) 的交换条件查找并删除配对记录，实现双向同时删除。

### 错误响应

| 状态码 | 场景 |
|--------|------|
| 404 | link_id 不存在或不属于该条目 |
| 401 | 未认证 |

---

## CONTRACT-KG04: GET /entries/{id}/knowledge-context

获取条目的知识图谱子图上下文。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| id | path | string | 是 | 条目 ID |

### 响应 200

```json
{
  "nodes": [
    {"id": "react", "name": "React", "category": "frontend", "mastery": "intermediate", "entry_count": 5},
    {"id": "hooks", "name": "Hooks", "category": "frontend", "mastery": "beginner", "entry_count": 2}
  ],
  "edges": [
    {"source": "react", "target": "hooks", "relationship": "RELATED_TO"}
  ],
  "center_concepts": ["react", "hooks"]
}
```

### 降级行为

- Neo4j 不可达时从 SQLite tags 共现关系生成子图，mastery 字段为 null
- 无 tags 时返回 `{"nodes": [], "edges": [], "center_concepts": []}`
- 子图深度 1 跳，节点上限 20

---

## CONTRACT-REVIEW02: GET /review/morning-digest（增强）

在现有 MorningDigestResponse 基础上新增可选字段。

### 新增响应字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| learning_streak | int | 0 | 连续记录天数 |
| daily_focus | DailyFocus? | null | 每日聚焦建议 |
| pattern_insights | string[] | [] | 行为模式洞察（最多 3 条） |

DailyFocus 结构：

```json
{
  "title": "完成 R003 代码审查",
  "description": "这个任务已拖延 2 天，建议优先处理",
  "target_entry_id": "task-abc"
}
```

### 降级行为

- learning_streak: 新用户或无数据返回 0
- daily_focus: LLM 不可用时基于 overdue 中最紧急任务生成模板文本
- pattern_insights: 数据不足时返回空数组
- 所有新字段 Optional + 默认值，旧客户端忽略不报错
