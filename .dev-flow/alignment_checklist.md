# 对齐清单

## R037: 全面补齐与功能增强

### 契约对齐

- [ ] B105: CONTRACT-DUE01 (GET /entries?due=) — 基于已有 planned_date 字段，不新增 due_date
- [ ] B107: CONTRACT-BACKLINK01 (GET /entries/{id}/backlinks)
- [ ] F145 无需 gen:types（复用已有 planned_date 类型）
- [ ] F147 无需 gen:types（backlinks 为新增独立 API，前端手写类型即可）

### 依赖对齐

- [x] F132 无外部依赖（HybridSearchService 已集成）✓ (completed)
- [ ] F134-F141 无外部依赖（独立体验打磨）
- [ ] F142 无外部依赖（离线队列扩展）
- [ ] F143 无外部依赖（多选框架）
- [ ] F144 depends_on F143 ✓ + F142 ✓（批量操作复用离线队列）
- [ ] F145 depends_on B105 ✓（前端消费后端 due_date 契约）
- [ ] F147 depends_on B107 ✓（前端消费后端 backlinks 契约）
- [ ] S35 depends_on 所有 pending 任务 ✓

### 架构对齐

- [ ] B105: 扩展 SQLite 查询条件（planned_date 已有），不新增列或字段
- [ ] B107: 新增 note_references 表，不改变 Markdown 存储架构，含回填路径（reindex_backlinks）
- [ ] F142: 扩展现有 offlineSync 队列，不引入新状态管理
- [ ] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫

## R036: 残留问题全面收口

### 契约对齐

- [x] 不涉及新契约，所有改动为架构修复、性能优化、代码组织和测试补齐 ✓

### 依赖对齐

- [x] B100 无外部依赖 ✓ (completed)
- [x] B101 无外部依赖 ✓ (completed)
- [x] B102 depends_on B101 ✓（共享 review_service.py）
- [x] F128 无外部依赖 ✓ (completed)
- [x] F129 无外部依赖 ✓ (completed)
- [x] M100 无外部依赖 ✓ (completed)
- [x] S33 depends_on B100-B102, F128-F131 ✓（结构性改动完成后再补测试）
- [x] S34 depends_on S33, M100 ✓ (completed)

### 架构对齐

- [x] B100: 添加公共属性/方法，不改变行为 ✓ (completed)
- [x] B101: SQL 聚合替换内存过滤，结果等价 ✓ (completed)
- [x] B102: 拆分到子模块，路由层 import 同步更新 ✓ (completed)
- [x] F128: 共享 hook，不新建全局状态 ✓ (completed)
- [x] F129-F131: 组件拆分，不引入新依赖 ✓ (completed)
- [x] M100: Flutter 端独立功能 ✓ (completed)
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫 ✓ (completed)

### 执行顺序

- [x] Phase 1: B100, B101（可并行）✓
- [x] Phase 2: B102（depends B101）✓
- [x] Phase 3: F128 ✓
- [x] Phase 4: F129, F130, F131（可并行，不共享文件）✓
- [x] Phase 5: M100（独立）✓ (completed)
- [x] Phase 6: S33 → S34 ✓

## R035: 预存问题修复（R034 Simplify 发现）

### 契约对齐

- [x] 不涉及新契约，所有改动为内部缺陷修复和性能优化 ✓

### 依赖对齐

- [x] B96 无外部依赖 ✓
- [x] B97 depends_on B96 ✓（共享 review_service.py，串行避免写冲突）
- [x] B98 depends_on B97 ✓（_get_heatmap_from_sqlite 内部调用 _calculate_mastery_from_stats，B97 提取后需适配新调用路径）
- [x] B99 depends_on B98 ✓（共享 sqlite.py 文件，串行避免写冲突）
- [x] S32 depends_on B96-B99 ✓

### 架构对齐

- [x] B96: 字段名修正，不改变数据模型 ✓
- [x] B97: 新建 app/utils/mastery.py，ReviewService 和 KnowledgeService 各自导入，消除循环依赖 ✓
- [x] B97: 统一签名为 4 参数版本（含 relationship_count） ✓
- [x] B98: 复用已有 SQL 聚合方法，不新增 SQL 查询
- [x] B99: sqlite.py 新增 get_tag_stats_in_range 方法
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫 ✓

### 执行顺序

- [x] Phase 1: B96 → B97（串行，共享 review_service.py）✓
- [x] Phase 2: B98 → B99（串行，B98 depends_on B97，B99 depends_on B98）✓
- [x] Phase 3: S32 ✓

## R034: 技术债收敛 (R029 Residual Risks)

### 契约对齐

- [x] 不涉及新契约，所有改动为内部代码质量提升

### 依赖对齐

- [x] F122 无外部依赖 ✓
- [x] F123 无外部依赖 ✓
- [x] B93 无外部依赖 ✓
- [x] F124 无外部依赖 ✓
- [x] B94 无外部依赖 ✓
- [x] F125 无外部依赖 ✓
- [x] B95 无外部依赖 ✓（需同步更新 review.py 路由层 import）
- [x] F126 无外部依赖 ✓
- [x] F127 depends_on F125 ✓（GraphPage 拆分完成后再写测试）
- [x] S31 depends_on F122-F127 全部 ✓

### 架构对齐

- [x] 所有改动不改变用户可见行为 ✓
- [x] B93: ReviewService 构造函数注入 knowledge_service，不新增全局状态 ✓
- [x] B95: Pydantic 模型迁移到 models/review.py，路由层 import 同步更新 ✓
- [x] F125: GraphPage 拆分为独立文件，不引入新依赖 ✓
- [x] F126: api.ts 类型迁移到 api.generated.ts，保持类型兼容 ✓
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫 ✓

### 执行顺序

- [x] Phase 1: F122, F123, B93（可并行）
- [x] Phase 2: F124, B94（可并行）
- [x] Phase 3: F125, B95, F126（串行推荐，避免共享文件冲突）
- [x] Phase 4: F127（依赖 F125）→ S31

## R033: 安全增强收口（R017 deferred 项）

### 契约对齐

- [x] B90: CONTRACT-AUTH01 — /auth/logout 行为变更 + Token payload 新增 jti
- [x] F121: CONTRACT-AUTH01 — 前端 logout 改 async，本地清理前置+后端 best-effort ✓

### 依赖对齐

- [x] B90 无外部依赖
- [x] F121 depends_on B90 ✓（前端依赖后端黑名单就绪）
- [x] B91 无外部依赖 ✓
- [x] B92 无外部依赖 ✓
- [x] S30 depends_on B90, F121, B91, B92 ✓

### 架构对齐

- [x] Token 黑名单为内存 Set，不引入 Redis ✓
- [x] 黑名单清理任务生命周期挂在 app lifespan ✓
- [x] TokenData 模型新增 jti 字段 ✓
- [x] F121 logout 改 async，本地清理前置消除 auth 闪现窗口，Sidebar 改为 await 后再跳转 ✓
- [x] B91 sync_service 双重检查覆盖 sync_entry/sync_to_graph_and_vector/delete_entry ✓
- [x] B92 路由名对齐实际代码：/knowledge-map, /knowledge/stats, /knowledge-graph/{concept} ✓
- [x] B92 /knowledge-map 和 /knowledge/stats 返回 200+空数据，/knowledge-graph/{concept} 保留 503 ✓
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫 ✓

## R032: 搜索增强 + Explore 批量操作

### 契约对齐

- [x] B89: CONTRACT-SEARCH01 — SearchRequest 新增 start_time/end_time/tags，query 改为 Optional ✓
- [x] F119: CONTRACT-SEARCH01 — 前端 searchEntries 扩展参数 ✓
- [x] F120: 不涉及新契约，复用现有条目更新/删除 API ✓

### 依赖对齐

- [x] B89 无外部依赖 ✓
- [x] F119 depends_on B89 ✓（前端依赖后端过滤参数就绪）
- [x] F120 depends_on F119 ✓（两者都修改 Explore.tsx，串行避免写冲突）
- [x] S29 depends_on F119, F120 ✓

### 类型同步对齐

- [x] B89 完成后执行 npm run gen:types 更新 api.generated.ts（SearchRequest 新增字段） ✓
- [x] F119 开始前确认类型已同步 ✓

### 架构对齐

- [x] 不新建后端服务文件，在现有 search.py + hybrid_search.py 内修改 ✓
- [x] 不新建前端页面，在现有 Explore.tsx 内修改 ✓
- [x] 搜索过滤采用后过滤模式，不改变 Qdrant/SQLite 搜索接口 ✓
- [x] 批量操作通过现有 taskStore.deleteTask/updateEntry 执行，不新建 API ✓
- [x] TaskCard 可能需要新增 disableActions prop（选择模式下禁用单卡动作） ✓
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫 ✓

### 执行顺序

- [x] 推荐：B89 → npm run gen:types → F119 → F120 → S29（串行，避免 Explore.tsx 写冲突）✓

## R031: 对话式 Onboarding

### 契约对齐

- [x] B88: 不涉及新契约，context.is_new_user 通过现有 chat body 透传 ✓
- [x] F118: 不涉及新契约，复用现有 onboarding_completed 字段和 updateMe API ✓

### 依赖对齐

- [x] B88 无外部依赖 ✓
- [x] F118 depends_on B88 ✓（前端依赖后端 prompt 注入就绪）
- [x] S28 depends_on F118 ✓

### 架构对齐

- [x] 不新建服务文件，在现有 ai_chat_service.py _build_system_prompt 内注入 onboarding 段 ✓
- [x] 不新建前端组件，复用现有 PageChatPanel + greetingMessage prop ✓
- [x] 新用户首页隐藏 FloatingChat，确保单入口（PageChatPanel） ✓
- [x] onboarding 完成后通过 key 变化重挂载 PageChatPanel，恢复正常模式 ✓
- [x] updateMe 防重复：boolean flag 保证只调用一次 ✓
- [x] updateMe 失败不阻塞，静默记录，下次仍为 onboarding 模式 ✓
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫 ✓

## R030: AI 晨报增强

### 契约对齐

- [x] B85: CONTRACT-MORNING-CACHE01 — MorningDigestResponse 添加可选 cached_at 字段 ✓
- [x] B86: 不涉及新契约，只改 prompt 构造 ✓
- [x] B87: 不涉及新契约，只改内部实现（pattern_insights 最多 5 条，现有 schema 已支持 list） ✓

### 依赖对齐

- [x] B85 无外部依赖 ✓
- [x] B86 depends_on B85 ✓（缓存先就绪，个性化建议写入缓存）
- [x] B87 depends_on B86 ✓（串行，共享 review_service.py 避免冲突）
- [x] F117 depends_on B87 ✓（前端展示依赖后端全部完成）
- [x] S27 depends_on F117 ✓

### 类型同步对齐

- [x] B85 完成后执行 npm run gen:types 更新 api.generated.ts（新增 cached_at 字段） ✓
- [x] F117 开始前确认类型已同步 ✓

### 架构对齐

- [x] 不新建服务文件，在现有 review_service.py 内修改缓存逻辑 ✓
- [x] 不新建前端文件，在现有 Home.tsx + useMorningDigest.ts 内修改 ✓
- [x] 缓存使用模块级 dict，不引入 Redis 等外部依赖 ✓
- [x] LLM 改动保留现有降级机制（超时 + 模板兜底） ✓
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫 ✓

### 执行顺序

- [x] 推荐：B85 → B86 → B87 → npm run gen:types → F117 → S27（串行，避免 review_service.py 冲突） ✓

## R029: Simplify 收敛检查

### 契约对齐

- [x] S26a: 不涉及新契约，只做代码审查和报告输出
- [x] S26b: 不涉及新契约

### 依赖对齐

- [x] S26a 无外部依赖
- [x] S26b depends_on S26a
- [x] R030 entry_conditions 已满足

### 架构对齐

- [x] 不新建服务文件，在现有 router/service/page 内修改
- [x] 修改不违反 architecture.md 不变量

## R027: 数据导出 + 反馈追踪

### 契约对齐

- [x] B83: CONTRACT-EXPORT01 + CONTRACT-EXPORT02
- [x] B84: CONTRACT-FEEDBACK-SYNC01

### 依赖对齐

- [x] F114 depends_on B83 ✓
- [x] F115 depends_on B83 ✓
- [x] F116 depends_on B84 ✓
- [x] S21 depends_on B83, B84, F114, F115, F116 ✓

### 架构对齐

- [x] 不新建路由文件，在现有 entries.py / review.py / feedback.py 内新增端点
- [x] 前端不新建页面，在现有组件内添加导出按钮和状态标签

## R026: 收敛修复

### 契约对齐

- [x] 不涉及新契约 ✓

### 依赖对齐

- [x] S20 depends_on S18, S19, B82, F112, F113 ✓

### 架构对齐

- [x] 不新建服务文件 ✓
- [x] 掌握度算法收敛 ✓
