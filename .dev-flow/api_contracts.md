# API 契约

## 契约索引

### R033 新增/变更契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-AUTH01 | POST | /auth/logout (行为变更) | B90, F121 | done |
| CONTRACT-KNOWLEDGE01 | GET | /knowledge-map, /knowledge/stats (降级行为) | B92 | planned |

### R033 契约详情

#### CONTRACT-AUTH01: POST /auth/logout (行为变更)

现有端点，从空操作变更为将 token jti 加入黑名单。

请求：与现有相同（HTTPBearer credentials）

响应变更：
- 成功（200）：`{"message": "logged out"}`（不变），token jti 已加入黑名单
- 无 token（403）：无 credentials 时（不变）
- 无效 token（401）：token 解码失败时（不变）
- 过期 token（200）：过期 token 调 logout 仍成功（幂等），不报错

Token payload 变更：
- 新增 `jti` 字段（UUID4 字符串），用于唯一标识 token
- 现有 `sub`、`exp`、`type` 字段不变

生命周期约束：
- TokenBlacklist 在 app lifespan startup 启动清理任务、shutdown 取消
- 清理间隔 10 分钟，仅清理过期记录
- 黑名单为内存 Set，不引入 Redis

#### CONTRACT-KNOWLEDGE01: GET /knowledge-map, /knowledge/stats (降级行为)

现有端点，B92 修改降级时的返回行为。

| 端点 | Neo4j 不可用时 | Neo4j+SQLite 都不可用时 |
|------|--------------|----------------------|
| GET /knowledge-map | 200 + 空 KnowledgeMapResponse（空节点/关系列表） | 200 + 空 KnowledgeMapResponse |
| GET /knowledge/stats | 200 + 空 ConceptStatsResponse（零值字段） | 200 + 空 ConceptStatsResponse |
| GET /knowledge-graph/{concept} | 503 (ValueError，保留现有行为) | 503 |

不变：正常路径（Neo4j 可用）行为完全不变。

### R032 新增/变更契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-SEARCH01 | POST | /search (新增过滤参数) | B89, F119 | planned |

### R032 契约详情

#### CONTRACT-SEARCH01: POST /search (新增过滤参数)

现有端点，`SearchRequest` 模型新增可选过滤参数，`query` 改为可选。

| 新增参数 | 类型 | 必填 | 说明 |
|---------|------|------|------|
| query | string \| null | 否 | 搜索查询（改为可选，默认空字符串）。空时跳过向量/全文搜索，走列表+过滤 |
| start_time | string \| null | 否 | ISO 格式起始时间，如 `2026-04-20T00:00:00` |
| end_time | string \| null | 否 | ISO 格式结束时间，如 `2026-04-24T23:59:59` |
| tags | string[] \| null | 否 | 标签数组，结果需至少匹配其中一个标签 |

过滤规则：
- query 非空时：走混合搜索（向量+全文）+ 后过滤
- query 为空时：走 getEntries 列表 + 后过滤（跳过向量/全文搜索）
- 时间过滤：entry 的 `created_at` 在 `[start_time, end_time]` 闭区间内
- start_time 缺失时下界不限，end_time 缺失时上界不限
- start_time > end_time 时返回空结果
- 标签过滤：entry 的 `tags` 与请求 `tags` 有交集（至少匹配一个）
- tags 为空数组 `[]` 等价于不筛选
- 所有参数为可选，不传时行为与现有完全一致

响应格式不变（`SearchResponse`）。

### R030 新增/变更契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-MORNING-CACHE01 | GET | /review/morning-digest (cached_at 字段) | B85, F117 | done |

### R030 契约详情

#### CONTRACT-MORNING-CACHE01: GET /review/morning-digest (cached_at 字段)

现有端点，响应模型 `MorningDigestResponse` 新增可选字段。

| 变更字段 | 类型 | 说明 |
|---------|------|------|
| cached_at | string \| null | 缓存命中时为 ISO 格式时间戳，未命中时为 null |

新增字段为可选字段，不影响现有前端消费。

### R027 新增/变更契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-EXPORT01 | GET | /entries/{id}/export | B83, F114 | planned |
| CONTRACT-EXPORT02 | GET | /review/growth-report | B83, F115 | planned |
| CONTRACT-FEEDBACK-SYNC01 | POST | /feedback/sync | B84, F116 | planned |

### R027 契约详情

#### CONTRACT-EXPORT01: GET /entries/{entry_id}/export

单条目 Markdown 文件下载。

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| entry_id | path | string | 是 | 条目 ID（字符串，与现有 /entries/{entry_id} 一致）|

响应：
- 200: `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="{title}.md"`
- Body: 条目的 Markdown 源文件内容（从 MarkdownStorage 读取）
- 404: 条目不存在或不属于当前用户

#### CONTRACT-EXPORT02: GET /review/growth-report

成长报告 Markdown 文件下载。

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| - | - | - | - | 无参数，自动生成当前用户报告 |

响应：
- 200: `Content-Type: text/markdown; charset=utf-8`
- `Content-Disposition: attachment; filename="growth_report_{date}.md"`
- Body: 格式化 Markdown 文档，包含：
  - 总条目数、各分类统计
  - 学习连续天数
  - 近 4 周趋势数据
  - 知识图谱概览（概念数、关联数）
- 503: review_service 未初始化

报告模板结构（4 个固定 section）：

实现方式：在 review_service.py 新增 public 方法 `generate_growth_report_data(user_id)` 返回 dict，路由层格式化为 Markdown。

```markdown
# 📊 成长报告

> 生成时间：{date}
> 报告周期：全部数据

## 概览
| 指标 | 数值 |
|------|------|
| 总条目数 | {total} |
| 任务 | {task_count} |
| 笔记 | {note_count} |
| 灵感 | {inbox_count} |
| 项目 | {project_count} |
| 决策 | {decision_count} |
| 复盘 | {reflection_count} |
| 待解问题 | {question_count} |

数据来源：storage.sqlite.count_entries(type=category, user_id=user_id) 逐类调用
（7 种 category: task, note, inbox, project, decision, reflection, question）

## 学习趋势

{近 4 周每周条目创建数}

数据来源：review_service.get_trend_data(user_id=user_id, days=28)
取 daily_data 按周聚合

## 学习连续天数

{streak_days} 天

数据来源：review_service._calculate_learning_streak(user_id)
（private 方法，在 generate_growth_report_data 内部调用）

## 知识图谱概览

| 指标 | 数值 |
|------|------|
| 概念数 | {concept_count} |
| 关联数 | {relation_count} |
| 掌握度分布 | 初学 X / 入门 X / 熟悉 X / 精通 X |

数据来源：knowledge_service._stats_from_sqlite(user_id)
（private 方法，通过 deps.get_knowledge_service() 获取 service 实例后调用）
Neo4j 不可用时 _stats_from_sqlite 返回空结构，报告显示「暂无数据」
```

#### CONTRACT-FEEDBACK-SYNC01: POST /feedback/sync

同步反馈状态（从 log-service 拉取最新 issue 状态）。

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| - | - | - | - | 无参数，同步当前用户所有已上报反馈 |

响应：
```json
{
  "synced_count": 3,
  "updated_count": 1,
  "items": [FeedbackItem, ...],
  "total": 5
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| synced_count | int | 尝试同步的反馈数 |
| updated_count | int | 状态有变化的反馈数 |
| items | FeedbackItem[] | 同步后的完整反馈列表 |
| total | int | 用户总反馈数 |

状态映射：
- log-service `pending` → 本地 `reported`（已上报但未开始处理）
- log-service `in_progress` → 本地 `in_progress`
- log-service `resolved` → 本地 `resolved`
- log-service 返回未知 status → 保持原状态不更新

降级规则：
- log-service 不可用：synced_count=0，所有本地状态和 updated_at 不变，不抛错
- 单条远程 404：该条 status 和 updated_at 均不变（即使当前是 in_progress/resolved），其他条继续
- 单条超时：该条 status 和 updated_at 均不变，其他继续
- 远程返回未知 status 值：保持原状态不更新，updated_at 不变
- 批量部分成功：updated_count 只计入状态实际发生变更的条数

状态变更判定：
- 仅当远程 status ≠ 本地当前 status 时才计为「变更」
- 变更时同步更新 status 和 updated_at
- 未变更时不更新 updated_at（非首次同步场景）
- 首次同步（updated_at 为 null）且有远程匹配时：无论状态是否变更，都写入 updated_at

FeedbackItem 变更：
- `status` 枚举扩展：pending → reported → in_progress → resolved
- 新增 `updated_at: str | None` 字段，语义为「本地最近同步时间」
  - 初始值为 None（新反馈未同步过）
  - 首次同步且有远程匹配时写入当前时间
  - 仅当远程状态发生实际变更时才更新（幂等）
  - 不使用远程 issue 的 updated_at

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
