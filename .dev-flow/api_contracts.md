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
