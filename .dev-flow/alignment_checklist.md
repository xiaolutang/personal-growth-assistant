# 对齐清单

## R020: E2E 测试补齐 + CI PR 增强

### 契约对齐

- [ ] S05: 扩展现有 e2e/tests/helpers/api.ts，新增 goals.ts + export.ts ✓
- [ ] B74: 依赖 CONTRACT-GOAL01/06/10（Goals CRUD + 关联 + 进度汇总）✓
- [ ] F63: 依赖 B74（Goals API E2E 通过后测 UI）✓
- [ ] B75: 搜索使用 GET /entries/search/query（SQLite FTS5），不依赖 Qdrant ✓
- [ ] B76: 依赖已有 GET /entries/export 端点 ✓
- [ ] S05 searchEntries helper 使用 GET /entries/search/query（与 B75 一致）✓

### 依赖对齐

- [ ] S05 无外部依赖 ✓
- [ ] B74 depends_on S05 ✓（需要 Goals API helper）
- [ ] F63 depends_on B74 ✓（需要 API 测试验证端点正确）
- [ ] B75 depends_on S05 ✓（需要 searchEntries helper）
- [ ] F64 depends_on B75 ✓（需要 API 测试验证端点正确）
- [ ] B76 depends_on S05 ✓（需要 Export API helper）
- [ ] F65 depends_on B76 ✓（需要 API 测试验证端点正确）
- [ ] S06 depends_on B74, B75, B76 ✓（需要 API E2E 测试就绪）
- [ ] B77 depends_on F63, F64, F65, S06 ✓（收口任务）

### 架构对齐

- [ ] API E2E 使用 Playwright APIRequestContext 直接测试后端 API；UI E2E 使用 Page + Browser ✓
- [ ] 假 LLM 配置（LLM_BASE_URL=http://localhost:19999）✓
- [ ] 独立 DATA_DIR 隔离，测试后回收 ✓
- [ ] 搜索 E2E 使用 FTS5 全文搜索端点，不依赖 Qdrant 向量搜索 ✓
- [ ] F63 重新激活 AC 为 completed → active（前端仅 completed 状态显示重新激活按钮）✓
- [ ] B76 包含新类型导出测试（decision/reflection/question），跨模块闭环 ✓
- [ ] CI E2E 只跑关键子集（auth + entries + goals-api + new-types-api），控制运行时间 ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] B74 risk_tags: network ✓
- [ ] F63 risk_tags: network ✓
- [ ] B75 risk_tags: network ✓
- [ ] F64 risk_tags: network ✓
- [ ] B76 risk_tags: network ✓
- [ ] F65 risk_tags: network ✓
- [ ] S06 risk_tags: config ✓
- [ ] B77 risk_tags: startup ✓
- [ ] S06 统一 Python 版本为 3.12 ✓

---

## R019: 离线增强 + PWA

### 契约对齐

- [ ] S03: CONTRACT-SWCACHE01 (SW URL pattern 修复) 已定义 → 含完整 URL 正则 + 三层策略 ✓
- [ ] F59: CONTRACT-OFFLINE01 (IndexedDB offlineQueue) 已定义 → 纯前端数据层，无后端 API ✓
- [ ] F60: 复用已有 POST /entries 端点回放队列，无新端点 ✓
- [ ] F61: CONTRACT-OFFLINE03 (POST /chat 离线拦截) 已定义 → 拦截 useStreamParse SSE 请求 ✓
- [ ] F62: CONTRACT-PWA01 (manifest lang) 已定义 → 仅修改 vite.config.ts ✓
- [ ] F61 不假设 createEntry 路径，正确描述 useStreamParse → POST /chat SSE 路径 ✓

### 依赖对齐

- [ ] S03 无外部依赖 ✓
- [ ] S04 无外部依赖 ✓
- [ ] F58 使用 SPA 内 React 路由实现（不替换 SW navigateFallback index.html），保持 deep-link 兼容 ✓
- [ ] F59 无外部依赖 ✓（纯 IndexedDB 模块）
- [ ] F60 depends_on F59 + F61 + S04 ✓（需要队列数据 + taskStore 离线方法 + 在线状态检测）
- [ ] F61 depends_on F59 + S04 ✓（需要队列 + 在线状态）
- [ ] F62 depends_on S03 ✓（需要 SW 正确配置）
- [ ] B73 depends_on 全部 ✓（收口任务）
- [ ] F59 和 S04 无互相依赖，可并行 ✓

### 架构对齐

- [ ] 离线队列使用 IndexedDB，不引入重量级依赖 ✓
- [ ] 离线创建仅支持 inbox 类型（最小验证），不覆盖编辑/搜索/图谱 ✓
- [ ] F59 纯数据层，不做 API 拦截（与 F61 职责清晰分离）✓
- [ ] F61 拦截点在 useStreamParse（首页 AI 对话），不在 api.ts createEntry ✓
- [ ] F61 FloatingChat 通过 ParseResponse.error === 'offline_save_failed' 分支控制不清空输入 + 不追加聊天历史 ✓
- [ ] 首页 AI 对话创建 inbox 路径：useStreamParse → POST /chat SSE（非 createEntry）✓
- [ ] Task 类型添加 _offlinePending 可选字段，不破坏已有类型 ✓
- [ ] taskStore 内部维护 _offlineEntries 数组，新增 upsertOfflineEntry / removeOfflineEntry ✓
- [ ] taskStore.fetchEntries() 合并离线条目，不被整包覆盖丢失 ✓
- [ ] /inbox 已重定向到 /explore?type=inbox（App.tsx:92），F61 落点在 Home.tsx + Explore.tsx ✓
- [ ] F62 增强已有 usePWAInstall + Header，不创建新 InstallPrompt 组件 ✓
- [ ] F62 incrementUsageCount 由 useChatActions.onCreated 调用（可靠的创建事件源）✓
- [ ] F62 使用 localStorage 追踪使用次数，不引入新状态管理 ✓
- [ ] SW 缓存不缓存搜索和流式请求（NetworkOnly）✓
- [ ] 前端遵循现有 api.ts + authFetch + store 模式 ✓
- [ ] S04 离线启动恢复：userStore 网络失败不 logout，ProtectedRoute 检查 token 存在即放行 ✓
- [ ] F60 initSync() 覆盖 app 重启时已在线 + pending 队列场景 ✓

### 数据模型对齐

- [ ] OfflineMutation 类型定义在 offlineQueue.ts 模块内 ✓
- [ ] OfflineMutation 包含 client_entry_id 字段，同步成功后映射 removeOfflineEntry ✓
- [ ] Task._offlinePending 为可选字段，后端不感知 ✓
- [ ] taskStore._offlineEntries 独立于 tasks，fetchEntries 合并后不被覆盖 ✓
- [ ] offlineQueue 按 user_id 隔离，getAll/count 按当前用户过滤 ✓
- [ ] userStore.logout() 清理 _offlineEntries + offlineQueue.clear() ✓
- [ ] F60 401 = 立即 failed（不重试），5xx = retry_count + 1（策略明确）✓
- [ ] F60 同步成功后通过 client_entry_id 映射 removeOfflineEntry + fetchEntries ✓
- [ ] F60 使用 createEntry（api.ts）回放，body 用 `type` 字段（与 EntryCreate 输入一致），createEntry 自动映射 type→category ✓
- [ ] F61 覆盖 FloatingChat.tsx（输入清空控制：add() 失败时保留输入）✓
- [ ] F62 usePWAInstall 通过 window 自定义事件 `pwa-usage-updated` + storage 事件实现跨 hook 实例状态同步 ✓
- [ ] 本期不做 Background Sync API，仅用 online 事件 + initSync() 实现同步 ✓
- [ ] IndexedDB 不可用时统一 fallback：add→''，getAll→[]，count→0，不返回 null ✓
- [ ] F61 add() 返回 '' 时：失败 toast + 保留输入 + 不生成乐观条目 + 不触发 onCreated ✓
- [ ] Explore.tsx MVP 阶段不显示离线条目（独立 getEntries），同步后需重新进入 Explore 才可见（不自动刷新）✓
- [ ] Home.tsx recentInbox 是离线「待同步」badge 的主要 UI 落点 ✓
- [ ] 登出即丢弃未同步数据（clear 清空当前用户队列），不承诺重新登录后恢复 ✓
- [ ] S04 区分网络失败（保留登录态）vs 401/无效 token（登出），认证不变量不被破坏 ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] S03 risk_tags: network, startup ✓
- [ ] S03 test_tasks 包含 DevTools 缓存命中验证 ✓
- [ ] F59 test_tasks 包含 IndexedDB 不可用 fallback ✓
- [ ] F60 test_tasks 包含防重入 + 401 token 过期 ✓
- [ ] F61 test_tasks 包含在线/离线路径对比 ✓
- [ ] F62 test_tasks 包含使用次数阈值 + 关闭 7 天逻辑 ✓
- [ ] 前端任务都要求 npm run build 通过 ✓

---

## R016: 小闭环收口

### 契约对齐

- [ ] F54: 无新 API 契约（前端路由+快捷键调整）✓
- [ ] F55: 复用已有 PUT /entries/:id（category 变更），无新端点 ✓
- [ ] F55: 复用已有 taskStore.updateEntry 调用模式 ✓

### 依赖对齐

- [ ] F54 无外部依赖 ✓
- [ ] F55 无外部依赖 ✓
- [ ] F54 和 F55 可并行 ✓

### 架构对齐

- [ ] Cmd+K 监听挂在 AppLayout 层，不在全局 window ✓
- [ ] input/textarea 输入态不抢占快捷键 ✓
- [ ] Explore.tsx 局部监听移除，不重复注册 ✓
- [ ] F55 按钮点击 stopPropagation 不触发 Link 导航 ✓
- [ ] 每条灵感独立 loading 状态，转化中禁用按钮 ✓
- [ ] 前端遵循现有 api.ts + taskStore 模式 ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] F54 test_tasks 包含输入态边界 + 监听清理 ✓
- [ ] F55 test_tasks 包含点击隔离 + 防双击 + 失败保留 ✓
- [ ] 前端任务都要求 npm run build 通过 ✓

---

## R014: 页面级上下文 AI

### 契约对齐

- [ ] B50: 复用已有 PageContext 模型（parse.py），无新端点 ✓
- [ ] B51: 复用已有 task_parser_graph.py stream_parse 接口，扩展参数 ✓
- [ ] F39: 复用已有 chatStore pageContext，新增 pageExtra 状态 ✓
- [ ] 不新增 API 端点，仅增强已有接口的上下文透传 ✓

### 依赖对齐

- [ ] B50 无外部依赖 ✓（使用已有 entry_service + chat_service）
- [ ] B51 depends_on B50 ✓（需要增强后的上下文数据）
- [ ] F39 depends_on B51 ✓（需要后端页面感知能力）
- [ ] B50 和 B51 不可并行（B51 消费 B50 的 context hint）✓

### 架构对齐

- [ ] 所有数据操作显式携带 user_id（architecture.md:47）✓
- [ ] _build_page_context_hint 改为实例方法，利用 self.entry_service ✓
- [ ] 数据源失败时优雅降级（try/except 包裹，不阻塞主流程）✓
- [ ] 不修改 deps.py 全局单例模式 ✓
- [ ] 前端 pageExtra 状态同步由页面组件主动写入，FloatingChat 不被动读取 ✓
- [ ] 不引入新的全局状态管理模式 ✓

### 类型同步对齐

- [ ] PageContext.extra 类型为 Optional[dict]，无需前端类型更新 ✓
- [ ] chatStore.pageExtra 为 Record<string, unknown>，无需 OpenAPI 同步 ✓
- [ ] 无新枚举值需要前后端同步 ✓

### 验收对齐

- [ ] 每个任务有 acceptance_criteria ✓
- [ ] 每个任务有 test_tasks ✓
- [ ] B50 risk_tags: auth ✓（涉及 user_id 数据访问）
- [ ] B50 test_tasks 包含跨用户隔离 + 数据源异常降级 + update 路径 entry_id 消费 ✓
- [ ] F39 test_tasks 包含 pageExtra 同步 + chip 隐藏/显示 ✓
- [ ] 前端任务都要求 npm run build 通过 ✓

---

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
