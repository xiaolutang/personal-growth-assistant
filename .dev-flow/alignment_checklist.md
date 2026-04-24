# 对齐清单

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

- [ ] B83: CONTRACT-EXPORT01 + CONTRACT-EXPORT02
- [ ] B84: CONTRACT-FEEDBACK-SYNC01

### 依赖对齐

- [ ] F114 depends_on B83 ✓
- [ ] F115 depends_on B83 ✓
- [ ] F116 depends_on B84 ✓
- [ ] S21 depends_on B83, B84, F114, F115, F116 ✓

### 架构对齐

- [ ] 不新建路由文件，在现有 entries.py / review.py / feedback.py 内新增端点
- [ ] 前端不新建页面，在现有组件内添加导出按钮和状态标签

## R026: 收敛修复

### 契约对齐

- [x] 不涉及新契约 ✓

### 依赖对齐

- [x] S20 depends_on S18, S19, B82, F112, F113 ✓

### 架构对齐

- [x] 不新建服务文件 ✓
- [x] 掌握度算法收敛 ✓
