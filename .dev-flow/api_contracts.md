# API 契约

## 契约索引

### R038 新增/变更契约

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-TEMPLATE01 | GET | /entries/templates | B110, F148 | planned |
| CONTRACT-ANALYTICS01 | POST | /analytics/event | B111, F149 | planned |

### R038 契约详情

#### CONTRACT-TEMPLATE01: GET /entries/templates

新增端点，返回可用的条目模板列表。

请求：
- `GET /entries/templates`
- 需认证（Depends(get_current_user)）
- 可选 `category` 查询参数过滤特定类型的模板

响应（200）：
```json
{
  "templates": [
    {
      "id": "learning",
      "name": "学习笔记",
      "category": "note",
      "description": "记录学习内容和心得",
      "content": "## 核心概念\n\n## 关键要点\n\n## 个人思考\n\n## 后续行动"
    },
    {
      "id": "reading",
      "name": "读书笔记",
      "category": "note",
      "description": "记录读书摘要和感悟",
      "content": "## 书名与作者\n\n## 核心观点\n\n## 精彩摘录\n\n## 我的思考\n\n## 推荐理由"
    },
    {
      "id": "meeting",
      "name": "会议记录",
      "category": "note",
      "description": "记录会议内容和决议",
      "content": "## 会议主题\n\n## 参与者\n\n## 讨论要点\n\n## 决议事项\n\n## 后续行动"
    }
  ]
}
```

POST /entries 扩展：
- 新增可选字段 `template_id: string | null`
- 提供 template_id 时，使用模板 content 作为初始内容
- template_id 无效或不存在时忽略，使用 request.content
- template_id 与 category 不匹配时（如 template_id='learning' 但 category='task'）忽略模板
- request.content 非空时，template_id 不覆盖用户内容
- 提供 template_id 时跳过 CATEGORY_TEMPLATES 自动模板（template_id 优先）
- 不提供 template_id 时行为不变

#### CONTRACT-ANALYTICS01: POST /analytics/event

新增端点，接收前端埋点事件。

请求：
- `POST /analytics/event`
- 需认证（Depends(get_current_user)）

请求体：
```json
{
  "event_type": "entry_created",
  "metadata": { "category": "note", "template_id": "learning" }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| event_type | string | 是 | 事件类型枚举 |
| metadata | object \| null | 否 | 附加信息 |

event_type 枚举值：
- `entry_created` — 创建条目
- `entry_viewed` — 查看条目
- `chat_message_sent` — 发送 AI 对话
- `search_performed` — 执行搜索
- `page_viewed` — 页面切换
- `onboarding_completed` — 完成 Onboarding

响应（200）：
```json
{
  "ok": true
}
```

写入失败时仍返回 200（best-effort，不暴露内部错误）。

### R037 新增/变更契约（已完成）

| 契约 ID | 方法 | 端点 | 任务 | 状态 |
|---------|------|------|------|------|
| CONTRACT-DUE01 | GET | /entries?due=today\|overdue | B105 | done |
| CONTRACT-BACKLINK01 | GET | /entries/{id}/backlinks | B107 | done |
