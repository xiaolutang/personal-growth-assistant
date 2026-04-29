# 对齐清单

## R045: 评估 HTML 报告

### 契约对齐

- [ ] 无 API 契约（纯测试工具链，不涉及生产代码）

### 依赖对齐

- [ ] B193 无外部依赖（纯 Python string.Template）
- [ ] B194 depends_on B193 ✓（模板依赖数据模型）
- [ ] B195 depends_on B194 ✓（集成依赖模板）
- [ ] 不依赖 Jinja2（改用 Python string.Template）
- [ ] 不依赖 /health 端点获取元数据（改用 os.environ + git CLI）

### 架构对齐

- [ ] 所有改动在 backend/tests/eval/ 目录下，不影响生产代码
- [ ] data/eval_reports/ 为输出目录，默认路径为项目根目录 data/eval_reports/（通过 Path(__file__) 向上 4 级解析），不纳入版本控制
- [ ] history.json 为追加式存储，不覆盖已有数据；损坏时备份为 .bak 后重建
- [ ] 环境元数据来源：LLM_MODEL 从 os.environ 读取，git commit 从 `git rev-parse --short HEAD` 获取，失败时降级为 "unknown"
- [ ] 统一 per-case schema：正向 {input, expected_tools, actual_tools, agent_reply, passed, category, elapsed_seconds}；负面 {input, should_not_call, actual_tools, agent_reply, violated, violated_tools, category, elapsed_seconds}
- [ ] B193 负责 escape_for_html() 和 escape_for_js() 转义/序列化辅助函数，B194 模板只使用转义后的数据
- [ ] agent_reply 来源：SSE content 事件 payload key 为 'content'（agent_service.py sse_event 发送 {"content": text}，parse_sse_stream 用 data.get("content", "")），二者一致
- [ ] 报告产物：single 模式正向完整 + 负面空态；negative 模式负面完整 + 正向空态；all 模式全板块
- [ ] B195 重构契约：run_single_turn 返回 (EvaluationReport, per_case_records)，run_negative 返回 (NegativeReport, per_case_records)
- [ ] --report-dir 同时影响 HTML 报告和 history.json 的输出位置
- [ ] 不违反 architecture.md 分层不变量

### 执行顺序

- [ ] Phase 1: B193 → B194 → B195（严格顺序）

## R043: 架构收敛

### 契约对齐

- [ ] F177: CONTRACT-MILESTONE-CRUD — 里程碑 CRUD 统一使用 openapi-fetch client（GET/POST/PUT/DELETE /goals/{goal_id}/milestones，注意路径参数为 goal_id）
- [ ] F177: CONTRACT-PROGRESS-HISTORY — fetchProgressHistory 统一 openapi-fetch（GET /goals/{goal_id}/progress-history）
- [ ] F177: CONTRACT-RECOMMENDATIONS — fetchRecommendations 统一 openapi-fetch（GET /knowledge/recommendations，已有端点）
- [ ] F177: 验证后端 OpenAPI schema 覆盖里程碑 CRUD + progress-history + knowledge/recommendations 端点

### 依赖对齐

- [ ] B177 无外部依赖（基础设施拆分）
- [ ] B178 depends_on B177 ✓（MCP 重构依赖 sqlite 拆分后结构）
- [ ] B179 depends_on B177 ✓（entry_service 依赖 sqlite 拆分）
- [ ] B180 无外部依赖（模型提取，独立）
- [ ] B181 depends_on B177 ✓（goal_service 依赖 sqlite 拆分）
- [ ] B182 depends_on B184 ✓（review_service 三报告提取依赖 sqlite 重复合并完成）
- [ ] B183 depends_on B177 ✓（entry_service batch 依赖 sqlite 拆分）
- [ ] B184 depends_on B177 ✓（sqlite 重复合并依赖拆分先完成）
- [ ] F177 无外部依赖（前端 API 层统一）
- [ ] S44 depends_on B177+B178+B179+B180+B181+B182+B183+B184+F177 ✓

### 架构对齐

- [ ] B177: SQLiteStorage 入口类不变，采用组合模式暴露子模块方法
- [ ] B177: 所有消费者通过同一个 SQLiteStorage 访问，接口不变
- [ ] B178: MCP server 启动时初始化 deps.storage（确保 MCP 进程内 get_*_service 不返回 503）
- [ ] B178: MCP knowledge_stats handler 通过 deps 获取 KnowledgeService（不再裸 new）
- [ ] B179: entry_service/chat_service/morning_digest 禁止 from app.routers import deps/intent，通过构造注入
- [ ] B179: ChatService 通过构造注入替代所有 router 层导入（含 intent module）
- [ ] B179: MorningDigest 通过构造注入 RecommendationService
- [ ] B179: parse.py 组合点正确注入 ChatService 依赖
- [ ] B180: knowledge_service 模型提取后通过 from app.models.knowledge import 引用
- [ ] B181-B184: services → infrastructure 单向调用不变
- [ ] F177: openapi-fetch 统一后错误处理与现有 API 风格一致
- [ ] 不违反 architecture.md 分层不变量（R043 新增）

### 执行顺序

- [ ] Phase 1: B177（基础设施拆分）
- [ ] Phase 2: B178 + B179 + B180（架构正确性，B178/B179/B180 可并行）
- [ ] Phase 3: B183 → B184 → B181 → B182（严格串行，文件冲突约束）
- [ ] Phase 4: F177（前端一致性）
- [ ] Phase 5: S44（质量收口）

### MCP-HTTP 收敛验证路径

- [ ] MCP 创建条目 → HTTP GET 读取 → 数据一致
- [ ] MCP 批量创建 → HTTP GET 列表查询 → 数据一致
- [ ] MCP 更新条目 → HTTP 报告/目标查询 → tag_auto/双链同步一致
- [ ] HTTP 创建条目 → MCP list_entries/get_entry → 数据一致（反向 parity）

## R042: Flutter 条目详情交互升级

### 契约对齐

- [ ] F172: CONTRACT-ENTRY-UPDATE — 消费已有 PUT /entries/{id}
- [ ] F172: CONTRACT-ENTRY-BACKLINKS — 消费已有 GET /entries/{id}/backlinks
- [ ] F172: CONTRACT-ENTRY-LINKS — 消费已有 GET /entries/{id}/links（direction 参数 in/out/both）
- [ ] F172: CONTRACT-ENTRY-LINK-CREATE — 消费已有 POST /entries/{id}/links（body: target_id + relation_type）
- [ ] F172: CONTRACT-ENTRY-LINK-DELETE — 消费已有 DELETE /entries/{id}/links/{link_id}
- [ ] F172: CONTRACT-ENTRY-KNOWLEDGE — 消费已有 GET /entries/{id}/knowledge-context
- [ ] F172: CONTRACT-ENTRY-AI-SUMMARY — 消费已有 POST /entries/{id}/ai-summary
- [ ] F173: CONTRACT-ENTRY-SEARCH — 消费已有 GET /entries/search/query（关联搜索用）

### 依赖对齐

- [ ] F172 无外部依赖（纯 Flutter API 层扩展）
- [ ] F173 depends_on F172 ✓（需 api_client 新方法先就绪）
- [ ] F174 depends_on F173 ✓（需 provider 编辑状态管理先就绪）
- [ ] F175 depends_on F173 ✓ + F174 ✓（需 provider + 编辑 UI 先就绪）
- [ ] F176 depends_on F175 ✓（严格顺序，在同一 entry_detail_page.dart 上增量开发）
- [ ] S43 depends_on F174 ✓ + F175 ✓ + F176 ✓

### 架构对齐

- [ ] F173: entryDetailProvider 改为 family provider（接受 entryId），按 entryId 隔离状态
- [ ] F173: 嵌套详情导航（详情A→关联详情B→返回详情A）状态不串页
- [ ] F173: createLink 方法接收 target_id + relation_type，处理 400 自关联/409 重复关联
- [ ] F173: searchEntriesForLink 搜索状态由 Provider 管理，Widget 不直接调用 ApiClient.searchEntries
- [ ] F173: updateEntry 保存后因 PUT 返回 SuccessResponse，需额外 GET 刷新 entry + invalidate EntryListProvider
- [ ] F174: 保存成功后 invalidate EntryListProvider，确保返回列表时数据一致
- [ ] F175: mastery 字符串等级映射（beginner/intermediate/advanced/null）→ 前端 UI 标签
- [ ] F175: AI 摘要空内容（summary=null）时禁用按钮 + 提示；缓存（cached=true）直接展示
- [ ] F176: 自关联（400）/ 重复关联（409）错误提示文案
- [ ] F176: 关联条目点击跳转使用 family provider，状态隔离
- [ ] 所有页面使用 ConsumerStatefulWidget + Riverpod 模式
- [ ] 所有 List 类型状态通过 copyWith 替换，不直接修改
- [ ] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫、MVVM 分层（Widget→Provider→ApiClient）

### 执行顺序

- [ ] Phase 1: F172 → F173（API 层 + Provider 层）
- [ ] Phase 2: F174 → F175 → F176（UI 增量链式开发）
- [ ] Phase 3: S43（质量收口）

## R041: Flutter 页面补齐 + 工程健康

### 契约对齐

- [x] F163: CONTRACT-INBOX — 消费已有 GET/POST /entries (type=inbox)
- [x] F164: CONTRACT-NOTES — 消费已有 GET /entries (type=note)
- [x] F167: CONTRACT-REVIEW — 消费已有 GET /review/summary + /review/insights
- [x] F168: CONTRACT-GOALS — 消费已有 GET /goals + /goals/{id}/milestones
- [x] F171: CONTRACT-ROUTES — GoRouter 新增 /notes, /inbox, /review, /goals 路由

### 依赖对齐

- [x] B117 无外部依赖（后端 priority 筛选/排序）
- [x] F163 depends_on B117 ✓（后端 API 先就绪）
- [x] F164 无外部依赖（纯 Flutter 页面）
- [x] F167 depends_on F163 ✓（Inbox API 层先就绪）
- [x] F168 depends_on F167 ✓（Review API 层先就绪）
- [x] F170 depends_on F168 ✓（Goals API 层先就绪）
- [x] F171 depends_on F163 ✓ + F164 ✓ + F167 ✓ + F170 ✓（路由注册最后）
- [x] S42 depends_on 全部任务 ✓

### 架构对齐

- [x] 所有 Flutter Provider 使用 Riverpod Notifier 模式
- [x] 所有页面使用 ConsumerStatefulWidget
- [x] 底部导航 5 Tab + 更多菜单
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫、MVVM 分层

### 执行顺序

- [x] Phase 1: B117（后端）
- [x] Phase 2: F163 → F164（API 层 + 页面）
- [x] Phase 3: F167 → F168 → F170（页面链式）
- [x] Phase 4: F171（路由注册）
- [x] Phase 5: S42（质量收口）

## R039: Flutter Explore + 工程维护

### 契约对齐

- [ ] F151: CONTRACT-ENTRIES-LIST — 消费已有 GET /entries，传递 type/status/tags/start_date/end_date query params
- [ ] F151: CONTRACT-ENTRIES-SEARCH — 消费已有 GET /entries/search/query，传递 q/limit params
- [ ] F151: CONTRACT-ENTRIES-DELETE — 消费已有 DELETE /entries/{id}
- [ ] F151: CONTRACT-ENTRIES-UPDATE — 消费已有 PUT /entries/{id}，body 含 category 字段
- [ ] F152: Tab→type 参数映射明确（灵感→type=inbox, 任务→type=task, 笔记→type=note, 项目→type=project），后端参数名为 type 非 category

### 依赖对齐

- [ ] S38 无外部依赖
- [ ] F151 无外部依赖（纯 Flutter API 层扩展）
- [ ] F152 depends_on S38 ✓（需 architecture.md 4-tab 约束先更新）+ F151 ✓（需 explore_provider）
- [ ] F153 depends_on F152 ✓（在 ExplorePage 基础上添加搜索）
- [ ] F154 depends_on F151 ✓（需批量编排方法）+ F152 ✓（需 ExplorePage）+ F153 ✓（严格顺序）
- [ ] S39 depends_on S38 ✓ + F153 ✓ + F154 ✓

### 架构对齐

- [ ] S38: 更新 architecture.md 底栏约束从 3 Tab 到 4 Tab
- [ ] S38: 更新 architecture.md 允许搜索历史使用内存 List（MVP 不引入本地持久化）
- [ ] F151: explore_provider 使用 Riverpod Notifier 模式，参照 entry_provider.dart
- [ ] F151: ExplorePage 作为 View 层，不含业务逻辑
- [ ] F151: 搜索历史使用内存 List<String>，不引入 SharedPreferences
- [ ] F153: 搜索逻辑和历史管理在 explore_provider，ExplorePage 仅渲染 UI
- [ ] F154: 批量操作编排在 explore_provider，部分失败状态管理在 Provider
- [ ] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫、MVVM 分层

### 执行顺序

- [ ] Phase 1: S38（分支清理 + arch 更新）
- [ ] Phase 2: F151（API 层 + Provider）
- [ ] Phase 3: F152 → F153 → F154（严格顺序）
- [ ] Phase 4: S39

## R038: 工程健康收口 + 小功能补齐

### 契约对齐

- [ ] B110: CONTRACT-TEMPLATE01 (GET /entries/templates) — 模板为预定义常量，不存数据库；支持 ?category 过滤
- [ ] F148: CONTRACT-TEMPLATE01 — 前端消费模板列表 + template_id 传递
- [ ] B111: CONTRACT-ANALYTICS01 (POST /analytics/event) — best-effort 写入；422 校验
- [ ] F149: CONTRACT-ANALYTICS01 — useAnalytics hook 消费埋点端点；离线时丢弃

### 依赖对齐

- [ ] B108 无外部依赖
- [ ] B109 无外部依赖
- [ ] S36 depends_on B108 ✓（先更新 architecture.md 再清理文档）
- [ ] B110 无外部依赖
- [ ] F148 depends_on B110 ✓（前端依赖后端模板端点）
- [ ] B111 无外部依赖
- [ ] F149 depends_on B111 ✓（前端依赖后端埋点端点）
- [ ] S37 depends_on 全部任务 ✓

### 架构对齐

- [ ] B108: 压缩 architecture.md 但不改变不变量和禁止模式
- [ ] B109: 不改变功能行为，只修 git 跟踪
- [ ] S36: 归档历史契约不删除数据，只移动位置；R038 契约保持 planned
- [ ] B110: 不改变现有 create flow（不传 template_id 行为不变）
- [ ] B110: template_id 优先于 CATEGORY_TEMPLATES；无效时不生效，使用 request.content
- [ ] B111: 新增路由不与现有路由冲突
- [ ] B111: 写入失败不影响业务（try/except 静默）
- [ ] B111: routers/__init__.py 导出 analytics_router
- [ ] F148: 创建链路通过 taskStore.ts → api.ts，不通过 ContentSection.tsx
- [ ] F149: 6 个事件源文件与实际组件一致
- [ ] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫

### 执行顺序

- [ ] Phase 1: B108 + B109（可并行）→ S36
- [ ] Phase 2: B110 → F148
- [ ] Phase 3: B111 → F149
- [ ] Phase 4: S37
