# 对齐清单

## R013: 月报AI总结 + 思考/决策记录

### 契约对齐

- [ ] B48: CONTRACT-REVIEW03 (月报 ai_summary 补齐) 已定义 ✓
- [ ] B49: CONTRACT-ENTRY-TYPE01-04 (新类型 CRUD + 搜索) 已定义 ✓
- [ ] F37 依赖 CONTRACT-REVIEW03 ✓
- [ ] F38 依赖 CONTRACT-ENTRY-TYPE01-04 ✓

### 依赖对齐

- [ ] B48 无外部依赖 ✓（修改已有 review_service 方法）
- [ ] B49 无外部依赖 ✓（扩展现有枚举和存储层）
- [ ] F37 depends_on B48 ✓（需要后端返回 ai_summary）
- [ ] F38 depends_on B49 ✓（需要后端支持新类型）
- [ ] B48 和 B49 无互相依赖，可并行 ✓

### 类型同步对齐

- [ ] B49 包含 Category 枚举扩展 (backend/app/models/enums.py) ✓
- [ ] B49 包含 schema 更新 (backend/app/api/schemas/entry.py) ✓
- [ ] B49 验收条件包含 OpenAPI 类型同步 (npm run gen:types) ✓
- [ ] F38 包含前端类型定义更新 (types/task.ts, constants.ts) ✓
- [ ] F38 验收条件包含 npm run build 通过 ✓

### 架构对齐

- [ ] 新类型复用现有 entries 表，不新增数据表 ✓
- [ ] 新类型使用 Markdown 目录存储，遵循 Source of Truth 原则 ✓
- [ ] 意图识别扩展在 intent_service CATEGORY_KEYWORDS 中，不改架构 ✓
- [ ] 模板为固定 Markdown heading 结构，不新增结构化字段 ✓
- [ ] 所有 API 通过 Depends(get_current_user) 认证 ✓
- [ ] 所有数据按 user_id 隔离 ✓
- [ ] 前端遵循现有 api.ts + 类型定义模式 ✓

### 渲染契约对齐

- [ ] decision 类型详情页渲染：Markdown heading 解析 → 决策背景/选项/选择/理由结构 ✓
- [ ] reflection 类型详情页渲染：Markdown heading 解析 → 回顾目标/结果/教训/下一步 ✓
- [ ] question 类型详情页渲染：Markdown heading 解析 → 问题描述/背景/思考方向 ✓
- [ ] 渲染方式为 Markdown 内容展示，不做额外结构化解析 ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] B49 risk_tags: first_use ✓
- [ ] B49 test_tasks 包含首用 smoke + 类型同步验证 + 搜索 fallback ✓
- [ ] F37 test_tasks 包含错误态测试 ✓
- [ ] F38 test_tasks 包含首用 smoke + 空数据 tab + 构建校验 ✓
- [ ] 前端任务都要求 npm run build 通过 ✓

---

## R012: 目标追踪闭环

### 契约对齐

- [ ] B45: CONTRACT-GOAL01-05 (Goals CRUD) 已定义 → POST/GET/PUT/DELETE
- [ ] B46: CONTRACT-GOAL06-10 (Goal 条目关联 + 检查项 + 进度概览) 已定义 → POST/DELETE/GET + PATCH + progress-summary
- [ ] B47: 无新契约（集成到 entry_service 内部触发）
- [ ] F34 依赖 CONTRACT-GOAL01-09 ✓
- [ ] F35 依赖 CONTRACT-GOAL02 (GET /goals?status=active) ✓
- [ ] F36 依赖 CONTRACT-GOAL10 (GET /goals/progress-summary) ✓

### 依赖对齐

- [ ] B45 无外部依赖 ✓（新表 + 新路由）
- [ ] B46 depends_on B45 ✓（需要 goals 表和 CRUD）
- [ ] B47 depends_on B45 ✓（需要 goals 表查询 tag_auto 目标）
- [ ] F34 depends_on B45, B46 ✓（需要 CRUD + 条目关联）
- [ ] F35 depends_on B45 ✓（只需目标列表）
- [ ] F36 depends_on B45, B46, B47 ✓（需要进度概览 API + tag_auto 数据）

### 架构对齐

- [ ] 所有新 API 通过 Depends(get_current_user) 认证 ✓
- [ ] 所有数据按 user_id 隔离 ✓
- [ ] goals 属于 SQLite 元数据层（与 entry_links 同级），不写入 Markdown ✓
- [ ] B47 异步触发不阻塞条目操作 ✓
- [ ] 前端遵循现有 api.ts + 类型定义模式 ✓
- [ ] F34 Sidebar 导航从 5 项增为 6 项 ✓
- [ ] 进度计算为查询时计算，不依赖物化字段 ✓
- [ ] B45 删除语义统一：仅 status=abandoned 可删除 ✓
- [ ] B46 tag_auto 使用 entry_tags 归一化表查询，不走 LIKE ✓
- [ ] F36 仅在 weekly/monthly Tab 下显示，daily/trend 隐藏 ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] B45 risk_tags: auth ✓
- [ ] B45 test_tasks 包含 metric_type 校验 + 422 场景 ✓
- [ ] B46 test_tasks 包含三种类型的进度计算 + 401/403/progress-summary + 状态不回退 ✓
- [ ] B47 test_tasks 包含异步触发失败不影响主流程 + tag 更新前后集合重算 ✓
- [ ] F34 test_tasks 包含无目标引导 + checklist 创建 + count 关联/取消关联 + completed→active 重新激活 + API 失败降级 + 构建通过 ✓
- [ ] F35 test_tasks 包含 API 失败不阻塞首页 + 构建通过 ✓
- [ ] 前端任务都要求 npm run build 通过 ✓

---

## R011: 条目关联增强 + AI 晨报升级

### 契约对齐

- [ ] B42: CONTRACT-LINK01 (POST /entries/{id}/links) 已定义 → 含请求体/响应体/错误码
- [ ] B42: CONTRACT-LINK02 (GET /entries/{id}/links) 已定义 → 含 direction 参数
- [ ] B42: CONTRACT-LINK03 (DELETE /entries/{id}/links/{link_id}) 已定义 → 双向删除语义
- [ ] B43: CONTRACT-KG04 (GET /entries/{id}/knowledge-context) 已定义 → 含 nodes/edges/center_concepts
- [ ] B44: CONTRACT-REVIEW02 (GET /review/morning-digest 增强) 已定义 → 新增可选字段
- [ ] F31 依赖 CONTRACT-KG04 ✓
- [ ] F32 依赖 CONTRACT-LINK01/02/03 ✓，同时使用 GET /entries/search/query（已有）
- [ ] F33 依赖 CONTRACT-REVIEW02 ✓

### 依赖对齐

- [ ] B42 无外部依赖 ✓（新表 + 新端点）
- [ ] B43 无外部依赖 ✓（复用 knowledge_service + Neo4j/SQLite 降级）
- [ ] B44 无外部依赖 ✓（增强现有 morning-digest）
- [ ] F31 depends_on B43 ✓（需要 knowledge-context API）
- [ ] F32 depends_on B42, F31 ✓（需要 links API + 避免同文件冲突）
- [ ] F33 depends_on B44 ✓（需要增强后的 morning-digest 响应）

### 架构对齐

- [ ] 所有新 API 通过 Depends(get_current_user) 认证 ✓
- [ ] 所有数据按 user_id 隔离 ✓
- [ ] B42 entry_links 属于 SQLite 元数据层（与 users 表同级），不写入 Markdown ✓
- [ ] B42 导出时由 export API 单独查询 entry_links 序列化 ✓
- [ ] B43 Neo4j 不可达时降级为 SQLite 标签共现 ✓
- [ ] B44 MorningDigestResponse 新增字段 Optional + 默认值 ✓（向后兼容）
- [ ] F31 GraphPage 支持 ?focus= 参数 ✓（deep-link 落点）
- [ ] 前端遵循现有 api.ts + 类型定义模式 ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] B42 risk_tags: auth ✓
- [ ] B42 test_tasks 包含级联删除 + 事务回滚 + 422 非法枚举 ✓
- [ ] B44 test_tasks 包含向后兼容 + LLM 异常 + 悬挂 entry_id ✓
- [ ] F31 test_tasks 包含 API 失败降级 + 移动端溢出 ✓
- [ ] F32 test_tasks 包含 API 失败 toast ✓
- [ ] F33 test_tasks 包含字段缺失降级 ✓
- [ ] 前端任务都要求 npm run build 通过 ✓

---

## R010: 工程化提升

### 契约对齐

- [ ] B34: CONTRACT-ENG01 (GET /health 增强) 已定义 → 状态值域明确 (ok/error/unavailable)
- [ ] B35: 无新契约（使用现有 auth + entries API）
- [ ] B36-B39: 使用现有 auth/entries/chat/review API
- [ ] B40-B41: 无 API 契约

### 依赖对齐

- [ ] B34 无外部依赖 ✓（增强现有 /health 端点）
- [ ] B35 depends_on B34 ✓（E2E 健康检查依赖 /health 增强后可用）
- [ ] B36 depends_on B35 ✓（认证 E2E 依赖基础设施）
- [ ] B37 depends_on B35 ✓（CRUD E2E 依赖基础设施）
- [ ] B38 depends_on B35 ✓（Chat E2E 依赖基础设施）
- [ ] B39 depends_on B35 ✓（回顾 E2E 依赖基础设施）
- [ ] B40 depends_on B36, B37 ✓（CI 跑认证+CRUD E2E）
- [ ] B41 depends_on B34 ✓（性能基线用 /health 响应时间）

### 架构对齐

- [ ] B34 增强现有端点，不新建 ✓
- [ ] B35 双服务器拓扑与 vite proxy 一致 ✓
- [ ] B35 使用假 LLM 配置（LLM_API_KEY=fake, LLM_BASE_URL=localhost:19999），避免真实外部调用 ✓
- [ ] B38 read/delete 路径不触发 stream_parse，不依赖真实 LLM ✓
- [ ] B39 覆盖全部 7 个 review API 端点（daily/weekly/monthly/trend/knowledge-heatmap/growth-curve/activity-heatmap）✓
- [ ] B40 保留现有 docker-build-test job ✓
- [ ] 所有 E2E 测试通过临时 DATA_DIR 做数据隔离和回收 ✓

### 验收对齐

- [ ] B34 acceptance_criteria 与 CONTRACT-ENG01 一致（非核心降级 → 200 + status: "degraded"）✓
- [ ] B36 清理策略为临时 DATA_DIR 回收，不依赖删除用户 API ✓
- [ ] B38 可选 smoke（需 LLM）标记为 skip ✓
- [ ] B40 depends_on 只包含实际 CI 范围（B36/B37），不被 B38/B39 阻塞 ✓

---

## R008: 智能化 & 全端适配

### 契约对齐

- [ ] B28: CONTRACT-KG01 (knowledge/search) 已定义 → 前端 F27 调用
- [ ] B28: CONTRACT-KG02 (concept timeline) 已定义 → 前端 F27 调用（含 days 参数）
- [ ] B28: CONTRACT-KG03 (mastery distribution) 已定义 → 前端 F27 调用
- [ ] B30: CONTRACT-AI01 (ai-summary) 已定义 → 前端 F28 调用
- [ ] B31: CONTRACT-AI02 (chat page_context) 已定义 → 前端 F30 调用
- [ ] B29: CONTRACT-MCP01 (MCP 工具增强) 已定义（含超限行为 + 认证失败行为）

### 依赖对齐

- [ ] F27 depends_on B28 ✓（知识图谱页需要搜索/时间线/掌握度 API）
- [ ] F28 depends_on B30 ✓（摘要 UI 需要摘要 API）
- [ ] F30 depends_on B31 ✓（前端 pageContext 注入需要后端 ChatRequest 扩展）
- [ ] F29 无依赖 ✓（纯前端布局优化）
- [ ] B28 无依赖 ✓（增强现有 knowledge router）
- [ ] B29 无依赖 ✓（增强现有 MCP tools，注意不重复 get_knowledge_stats）
- [ ] B30 无依赖 ✓（新增 ai_summary 字段 + LLM 调用）
- [ ] B31 无依赖 ✓（扩展 ChatRequest + chat_service prompt 注入）

### 架构对齐

- [ ] 所有新 API 通过 Depends(get_current_user) 认证 ✓
- [ ] 所有数据按 user_id 隔离 ✓
- [ ] Neo4j 功能有 SQLite 降级 ✓（CONTRACT-KG01 降级时 mastery=null）
- [ ] 新增 SQLite 字段在 _migrate_schema 中处理 ✓（ai_summary）
- [ ] MCP 工具遵循现有 handler 模式 ✓
- [ ] 前端遵循现有 api.ts + 类型定义模式 ✓
- [ ] B31 不改变现有 /chat 无 page_context 时的行为 ✓
- [ ] B31 schema 变更后需执行 npm run gen:types ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] B29 有 risk_tags: auth（MCP 认证场景）✓
- [ ] 前端任务都要求 npm run build 通过 ✓
- [ ] B30 test_tasks 包含迁移测试 ✓
- [ ] F27 test_tasks 包含异常状态测试 ✓
- [ ] B28 test_tasks 包含 days 参数测试 ✓
- [ ] F28 触发时机统一为「首次展开」✓
- [ ] F28 test_tasks 包含 loading/缓存/空内容/失败测试 ✓
- [ ] F29 包含 FeedbackButton + FloatingChat + MobileNavBar 三者共存测试 ✓
- [ ] B29 test_tasks 包含认证失败场景 ✓
- [ ] CONTRACT-MCP01 定义了批量超限行为（拒绝，不截断）✓
