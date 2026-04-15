# 对齐清单

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
