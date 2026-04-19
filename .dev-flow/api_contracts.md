# API 契约

## 契约索引

### R013 新增/变更契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-REVIEW03 | GET | /review/monthly (ai_summary 补齐) | B48, F37 | planned |
| CONTRACT-ENTRY-TYPE01 | POST | /entries (category 扩展) | B49, F38 | planned |
| CONTRACT-ENTRY-TYPE02 | GET | /entries?type=decision\|reflection\|question | B49, F38 | planned |
| CONTRACT-ENTRY-TYPE03 | GET | /entries/{id} (新类型详情) | B49, F38 | planned |
| CONTRACT-ENTRY-TYPE04 | GET | /entries/search/query (新类型搜索) | B49, F38 | planned |

### R013 契约详情

#### CONTRACT-REVIEW03: GET /review/monthly (ai_summary 补齐)

现有端点，变更仅限 ai_summary 字段从 None 变为 LLM 生成的总结文本。

| 变更字段 | 类型 | 说明 |
|---------|------|------|
| ai_summary | string \| null | LLM 生成的月度总结，10 秒超时，失败时为空字符串，LLM 未配置时为 null |

#### CONTRACT-ENTRY-TYPE01: POST /entries (category 扩展)

现有端点，category 枚举新增三个值。

| 新增枚举值 | 目录 | 模板 | 意图关键词 |
|-----------|------|------|-----------|
| decision | decisions/ | 决策背景/选项/选择/理由 | 记决策、决策日志 |
| reflection | reflections/ | 回顾目标/实际结果/经验教训/下一步 | 写复盘、复盘笔记 |
| question | questions/ | 问题描述/相关背景/思考方向 | 记疑问、待解问题 |

请求/响应格式不变，仅 category 可选值扩展。

#### CONTRACT-ENTRY-TYPE02: GET /entries?type=decision|reflection|question

现有端点，type 过滤参数支持新值。返回格式不变。

#### CONTRACT-ENTRY-TYPE03: GET /entries/{id} (新类型详情)

现有端点，返回的 entry 对象 category 为新值。content 为对应模板的 Markdown 文本。

#### CONTRACT-ENTRY-TYPE04: GET /entries/search/query (新类型搜索)

现有端点，搜索结果包含新类型条目。

### 类型同步链路

```
backend/app/models/enums.py Category 枚举
  → backend/app/api/schemas/entry.py CreateEntryRequest.category
    → OpenAPI schema (npm run gen:types)
      → frontend/src/types/api.generated.ts Category 枚举
        → frontend/src/types/task.ts category type
          → frontend/src/config/constants.ts categoryConfig
```

---

### 历史契约

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
| CONTRACT-GOAL01 | POST | /goals | B45 | planned |
| CONTRACT-GOAL02 | GET | /goals | B45 | planned |
| CONTRACT-GOAL03 | GET | /goals/{id} | B45 | planned |
| CONTRACT-GOAL04 | PUT | /goals/{id} | B45 | planned |
| CONTRACT-GOAL05 | DELETE | /goals/{id} | B45 | planned |
| CONTRACT-GOAL06 | POST | /goals/{id}/entries | B46 | planned |
| CONTRACT-GOAL07 | DELETE | /goals/{id}/entries/{entry_id} | B46 | planned |
| CONTRACT-GOAL08 | GET | /goals/{id}/entries | B46 | planned |
| CONTRACT-GOAL09 | PATCH | /goals/{id}/checklist/{item_id} | B46 | planned |
| CONTRACT-GOAL10 | GET | /goals/progress-summary | B46, F36 | planned |

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

- Neo4j 不可达时从 SQLite tags 共现关系生成子图，mastery 字段基于条目数量计算
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

---

## R012 新增契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-GOAL01 | POST | /goals | B45 | planned |
| CONTRACT-GOAL02 | GET | /goals | B45 | planned |
| CONTRACT-GOAL03 | GET | /goals/{id} | B45 | planned |
| CONTRACT-GOAL04 | PUT | /goals/{id} | B45 | planned |
| CONTRACT-GOAL05 | DELETE | /goals/{id} | B45 | planned |
| CONTRACT-GOAL06 | POST | /goals/{id}/entries | B46 | planned |
| CONTRACT-GOAL07 | DELETE | /goals/{id}/entries/{entry_id} | B46 | planned |
| CONTRACT-GOAL08 | GET | /goals/{id}/entries | B46 | planned |
| CONTRACT-GOAL09 | PATCH | /goals/{id}/checklist/{item_id} | B46 | planned |
| CONTRACT-GOAL10 | GET | /goals/progress-summary | B46, F36 | planned |

---

## CONTRACT-GOAL01: POST /goals

创建目标。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| title | body | string | 是 | 目标标题 |
| description | body | string | 否 | 目标描述 |
| metric_type | body | string | 是 | 衡量方式：count / checklist / tag_auto |
| target_value | body | int | 是 | 目标值（≥1） |
| start_date | body | string | 否 | 开始日期 ISO 格式 |
| end_date | body | string | 否 | 截止日期 ISO 格式 |
| auto_tags | body | string[] | 条件 | metric_type=tag_auto 时必填，自动追踪的标签列表 |
| checklist_items | body | string[] | 条件 | metric_type=checklist 时必填，检查项标题列表 |

### 响应 201

```json
{
  "id": "goal-abc",
  "title": "学习 React",
  "description": "掌握 React 核心概念",
  "metric_type": "tag_auto",
  "target_value": 10,
  "current_value": 0,
  "progress_percentage": 0,
  "status": "active",
  "start_date": "2026-04-16",
  "end_date": "2026-06-30",
  "auto_tags": ["react", "hooks"],
  "checklist_items": null,
  "created_at": "2026-04-16T10:00:00",
  "updated_at": "2026-04-16T10:00:00"
}
```

### 错误响应

| 状态码 | 场景 |
|--------|------|
| 422 | metric_type 非法 / tag_auto 缺少 auto_tags / checklist 缺少 checklist_items / target_value < 1 |
| 401 | 未认证 |

---

## CONTRACT-GOAL02: GET /goals

列出目标。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| status | query | string | 否 | 过滤：active / completed / abandoned |
| limit | query | int | 否 | 最大返回数，默认 20 |

### 响应 200

```json
{
  "goals": [
    {
      "id": "goal-abc",
      "title": "学习 React",
      "metric_type": "tag_auto",
      "target_value": 10,
      "current_value": 3,
      "progress_percentage": 30,
      "status": "active",
      "end_date": "2026-06-30"
    }
  ]
}
```

---

## CONTRACT-GOAL03: GET /goals/{id}

获取目标详情（含完整进度信息）。

### 响应 200

```json
{
  "id": "goal-abc",
  "title": "学习 React",
  "description": "掌握 React 核心概念",
  "metric_type": "tag_auto",
  "target_value": 10,
  "current_value": 3,
  "progress_percentage": 30,
  "status": "active",
  "start_date": "2026-04-16",
  "end_date": "2026-06-30",
  "auto_tags": ["react", "hooks"],
  "checklist_items": null,
  "linked_entries_count": 0,
  "created_at": "2026-04-16T10:00:00",
  "updated_at": "2026-04-16T10:00:00"
}
```

### 进度计算规则

| metric_type | current_value 来源 | progress_percentage |
|-------------|-------------------|-------------------|
| count | 手动关联条目数（关联即计数，不依赖条目 complete 状态） | min(100, current_value / target_value * 100) |
| checklist | checklist_items 中 checked=true 的数量 | min(100, current_value / target_value * 100) |
| tag_auto | 条目 tags 与 auto_tags 有交集且在时间范围内的数量 | min(100, current_value / target_value * 100) |

### 自动完成

progress_percentage 达到 100% 时，status 自动更新为 completed。进度下降时不自动回退，用户可手动将 completed 改回 active。

---

## CONTRACT-GOAL04: PUT /goals/{id}

更新目标。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| title | body | string | 否 | 标题 |
| description | body | string | 否 | 描述 |
| target_value | body | int | 否 | 目标值 |
| status | body | string | 否 | 状态：active / completed / abandoned |
| start_date | body | string | 否 | 开始日期 |
| end_date | body | string | 否 | 截止日期 |

### 响应 200

同 CONTRACT-GOAL03。

### 约束

- metric_type 不可修改

---

## CONTRACT-GOAL05: DELETE /goals/{id}

删除目标。

### 约束

- 仅 status=abandoned 的目标可删除
- 删除时级联清理 goal_entries 中的关联记录

### 错误响应

| 状态码 | 场景 |
|--------|------|
| 400 | 目标状态非 abandoned |
| 404 | 目标不存在 |
| 401 | 未认证 |

---

## CONTRACT-GOAL06: POST /goals/{id}/entries

关联条目到目标（仅 count 类型）。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| entry_id | body | string | 是 | 条目 ID |

### 响应 201

```json
{
  "id": "ge-abc",
  "goal_id": "goal-abc",
  "entry_id": "entry-123",
  "created_at": "2026-04-16T10:00:00"
}
```

### 错误响应

| 状态码 | 场景 |
|--------|------|
| 400 | 目标 metric_type 非 count |
| 404 | 条目不存在 |
| 409 | 重复关联 |
| 401 | 未认证 |

---

## CONTRACT-GOAL07: DELETE /goals/{id}/entries/{entry_id}

取消条目关联。

### 响应 204

### 错误响应

| 状态码 | 场景 |
|--------|------|
| 404 | 关联不存在 |
| 401 | 未认证 |

---

## CONTRACT-GOAL08: GET /goals/{id}/entries

获取目标关联的条目列表。

### 响应 200

```json
{
  "entries": [
    {
      "id": "entry-123",
      "title": "React Hooks 学习",
      "status": "complete",
      "category": "note",
      "created_at": "2026-04-16T10:00:00"
    }
  ]
}
```

---

## CONTRACT-GOAL09: PATCH /goals/{id}/checklist/{item_id}

切换检查项状态（仅 checklist 类型）。

### 响应 200

```json
{
  "id": "item-1",
  "title": "学习 Hooks",
  "checked": true
}
```

### 错误响应

| 状态码 | 场景 |
|--------|------|
| 400 | 目标 metric_type 非 checklist |
| 404 | item_id 不存在 |

---

## CONTRACT-GOAL10: GET /goals/progress-summary

目标进度概览（用于回顾页）。

### 请求

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| period | query | string | 否 | 周期：weekly / monthly，默认 weekly |

### 响应 200

```json
{
  "active_count": 3,
  "completed_count": 1,
  "goals": [
    {
      "id": "goal-abc",
      "title": "学习 React",
      "progress_percentage": 30,
      "progress_delta": 10
    }
  ]
}
```

progress_delta = 本周期进度 - 上周期末进度（正数表示进步）。

---

## R019 新增/变更契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-SWCACHE01 | — | SW runtimeCaching URL pattern | S03 | planned |
| CONTRACT-OFFLINE01 | — | IndexedDB offlineQueue (前端) | F59 | planned |
| CONTRACT-OFFLINE02 | POST | /entries (离线队列回放) | F60 | planned |
| CONTRACT-OFFLINE03 | POST | /chat (离线拦截) | F61 | planned |
| CONTRACT-PWA01 | — | manifest lang | F62 | planned |

### CONTRACT-SWCACHE01: SW runtimeCaching URL pattern 修复

不涉及新端点，修复现有 vite-plugin-pwa 配置。

**变更内容**：

| 策略 | URL Pattern（修复前） | URL Pattern（修复后） | 说明 |
|------|---------------------|---------------------|------|
| NetworkFirst | `/^\/growth\/api\/.*/i` | `/https?:\/\/[^/]+\/growth\/api\/entries(\?.*)?$/i` | 条目列表 GET（含 query string） |
| StaleWhileRevalidate | 无 | `/https?:\/\/[^/]+\/growth\/api\/entries\/[^/]+$/i` | 条目详情 GET |
| NetworkOnly | 无 | `/https?:\/\/[^/]+\/growth\/api\/(search|chat).*/i` | 搜索/SSE 不缓存 |

### CONTRACT-OFFLINE01: IndexedDB offlineQueue

纯前端数据层，不涉及后端 API。

**IndexedDB 结构**：

- 数据库名：`growth-offline`
- Object Store：`mutations`
- 索引：`status`（用于按状态查询）、`user_id`（用于用户隔离）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键，自动生成（如 `offline-{timestamp}-{random}`） |
| user_id | string | 创建时的用户 ID（从 userStore 获取），用于多账号隔离 |
| client_entry_id | string | 本地乐观条目 ID（如 `local-{ts}`），同步成功后用于映射 taskStore.removeOfflineEntry(client_entry_id) |
| method | string | HTTP 方法：`POST` |
| url | string | 请求路径：`/entries` |
| body | object | 请求体：`{type: 'inbox', title: string, content?: string}`（使用 `type` 字段，与 api.ts EntryCreate 输入类型一致，回放时由 createEntry() 完成 type→category 映射）|
| timestamp | number | 创建时间戳 |
| status | string | `pending` / `synced` / `failed` |
| retry_count | number | 重试次数，默认 0 |

**用户隔离策略**：

- `add()` 写入时从 `userStore` 获取当前 `user.id` 存入 `user_id`
- `getAll()` / `count()` 按 `current_user_id` 过滤，仅返回当前用户的队列项
- `logout()` 时调用 `clear()` 清空当前用户的所有队列项（未同步数据丢弃，这是产品决策：登出意味着放弃未提交的离线操作）
- 多账号场景：A 用户离线保存 → A 登出（队列清空，未同步数据丢弃）→ B 登录 → B 操作独立

**API（前端模块）**：

| 方法 | 签名 | 说明 |
|------|------|------|
| add | `(query: OfflineMutation) => Promise<string>` | 添加队列项，返回 id |
| getAll | `() => Promise<OfflineMutation[]>` | 获取当前用户的队列项（按 user_id 过滤） |
| update | `(id: string, changes: Partial<OfflineMutation>) => Promise<void>` | 更新队列项字段（retry_count/status） |
| remove | `(id: string) => Promise<void>` | 删除指定队列项 |
| count | `() => Promise<number>` | 返回当前用户 pending 状态数量 |
| clear | `() => Promise<void>` | 清空当前用户的所有队列项 |

**IndexedDB 不可用时的统一 fallback**：

所有方法在 IndexedDB.open 失败时：
- `add()` → 返回空字符串 `''`（调用方判断为失败，走在线降级）
- `getAll()` → 返回空数组 `[]`
- `remove()` → 无操作（静默）
- `count()` → 返回 `0`
- `clear()` → 无操作（静默）

不返回 null，不抛错，调用方无需 null 检查。

### CONTRACT-OFFLINE02: POST /entries（离线同步回放）

复用已有端点 `POST /entries`，离线同步时调用。

**回放行为**：

- 从 offlineQueue 取 pending 项，按 timestamp 排序
- 逐条调用 `createEntry(body)`（api.ts），body 使用 `type` 字段（如 `{type: 'inbox', title: '...'}`），由 createEntry 内部完成 type→category 映射和 openapi-fetch 封装
- 成功（200/201）：从队列 remove，通知 taskStore.removeOfflineEntry(item.client_entry_id)
- 失败 5xx：retry_count + 1，retry_count > 3 标记 failed
- 失败 401：立即标记 failed（不重试），UI 显示「请重新登录」
- 全部完成后调用 taskStore.fetchEntries() 刷新服务端数据

**初始化同步**：

- offlineSync 导出 `initSync()` 方法
- App.tsx useEffect 中调用：检查 `navigator.onLine === true` 且 `queue.count() > 0` 时立即触发同步
- 覆盖「app 重启时已在线但有 pending 队列」场景
- 内部复用同步核心逻辑，受布尔锁保护

### CONTRACT-OFFLINE03: POST /chat（离线拦截）

**拦截逻辑**（在 useStreamParse 中）：

1. 检测 `navigator.onLine === false`
2. 跳过 `authFetch POST /chat` SSE 请求
3. 生成本地乐观 ID：`local-{ts}`
4. 构造简化 mutation：`{method: 'POST', url: '/entries', body: {type: 'inbox', title: userInput, content: userInput}, client_entry_id: 'local-{ts}'}`（body 使用 `type` 字段，与 createEntry 输入类型一致）
5. 调用 `offlineQueue.add(mutation)` → 检查返回值
6. **add() 返回空字符串（IndexedDB 不可用）**：
   - 返回失败 ParseResponse：`{intent: null, operation: null, error: 'offline_save_failed'}`（`error` 字段为新增的离线保存失败标识）
   - FloatingChat 根据 `error === 'offline_save_failed'` 分支：显示失败 toast「保存失败，请检查浏览器存储设置」+ 不追加消息到聊天历史 + 不清空输入框
   - 不生成乐观条目，不触发 onCreated 回调
7. **add() 成功（返回有效 id）**：
   - 生成本地乐观 Task：`{id: 'local-{ts}', title: userInput, _offlinePending: true, category: 'inbox', status: 'waitStart', tags: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString(), file_path: '', content: userInput}`
   - 调用 `taskStore.upsertOfflineEntry(localTask)`
   - 触发 onCreated 回调链（等价 SSE created 事件）
   - 返回乐观 ParseResponse：`{intent: {intent: 'create', ...}, operation: {created: {ids: ['local-{ts}'], count: 1}}}`
   - FloatingChat 正常追加消息到聊天历史 + 清空输入框

**状态管理策略**（taskStore）：

- `_offlineEntries: Task[]` 内部数组存储离线条目
- `fetchEntries()` 获取服务端数据后合并 `_offlineEntries`（按 id 去重，离线条目保留）
- `removeOfflineEntry(localId)` 同步成功后移除
- 防止 `onCreated → fetchEntries()` 整包覆盖丢失离线条目

**UI 展示落点（MVP）**：

- Home.tsx `recentInbox` 区域：`_offlinePending` 条目标题旁显示灰色「待同步」badge
- Explore.tsx inbox tab：MVP 阶段不显示离线条目（Explore 使用独立 getEntries() 不订阅 taskStore）
- 同步完成后 Explore 需要重新进入页面才通过 getEntries() 获取真实数据（不自动刷新）
- 注意：`/inbox` 已重定向到 `/explore?type=inbox`（App.tsx:92），Inbox.tsx 不是实际页面

**回调链路**：

离线分支仅在 add() 成功时触发与 SSE `created` 事件等价的 `onCreated` 回调：
- `fetchEntries()` 更新 taskStore 列表
- 会话标题更新（`updateTitleIfNeeded`）
- `lastOperation` 状态设置
- F62 `incrementUsageCount()` 递增

add() 失败时不触发任何回调，避免状态污染。

**登出清理**：

- `userStore.logout()` 中调用 `taskStore.clearOfflineEntries()` + `offlineQueue.clear()`
- 以 fire-and-forget 方式执行（不阻塞同步 logout 流程，不改为 async）

**前端类型变更**：

```typescript
// types/task.ts 新增可选字段
export interface Task {
  // ...existing fields
  _offlinePending?: boolean;  // 离线待同步标记
}
```

### CONTRACT-PWA01: manifest lang

**变更内容**：

| 字段 | 修复前 | 修复后 |
|------|--------|--------|
| manifest.lang | 无 | `'zh-CN'` |

不涉及新端点，仅修改 `vite.config.ts` manifest 配置。
