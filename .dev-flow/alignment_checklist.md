# 对齐清单

## R029: Simplify 收敛检查

### 契约对齐

- [ ] S26a: 不涉及新契约，只做代码审查和报告输出
- [ ] S26b: 不涉及新契约，修改范围限定在 S26a files 列表及直接协作者

### 依赖对齐

- [ ] S26a 无外部依赖 ✓
- [ ] S26b depends_on S26a ✓
- [ ] R030 entry_conditions: S26b must_fix 全部关闭 + residual 不涉及主链路 + 全量测试通过

### 架构对齐

- [ ] 不新建服务文件，在现有 router/service/page 内修改
- [ ] 前端组件拆分在文件内完成，不新建文件
- [ ] 修改不违反 architecture.md 不变量: user_id 隔离、JWT 认证守卫、存储工厂模式
- [ ] 错误处理收敛到与全局 ErrorHandlerMiddleware 一致的脱敏原则
- [ ] JWT 守卫 / Authorization 注入回归已纳入验证（auth risk_tag）

## R027: 数据导出 + 反馈追踪

### 契约对齐

- [ ] B83: CONTRACT-EXPORT01 /entries/{id}/export + CONTRACT-EXPORT02 /review/growth-report
- [ ] B84: CONTRACT-FEEDBACK-SYNC01 /feedback/sync + status 枚举扩展 + updated_at 语义

### 依赖对齐

- [ ] B83 无外部依赖（复用 MarkdownStorage + ReviewService + KnowledgeService）
- [ ] B84 无外部依赖（httpx 调 log-service API）
- [ ] F114 depends_on B83 ✓（前置 npm run gen:types）
- [ ] F115 depends_on B83 ✓（前置 npm run gen:types）
- [ ] F116 depends_on B84 ✓（前置 npm run gen:types）
- [ ] S21 depends_on B83, B84, F114, F115, F116 ✓

### 类型同步对齐

- [ ] B83/B84 完成后执行 npm run gen:types 更新 api.generated.ts
- [ ] 前端任务 F114/F115/F116 开始前确认类型已同步

- [ ] B83 无外部依赖（复用现有 MarkdownStorage + ReviewService）
- [ ] B84 无外部依赖（httpx 调 log-service API）
- [ ] F114 depends_on B83 ✓
- [ ] F115 depends_on B83 ✓
- [ ] F116 depends_on B84 ✓
- [ ] S21 depends_on B83, B84, F114, F115, F116 ✓

### 执行顺序

- [ ] 推荐：B84 先做或与 B83 并行 → gen:types → F114/F115/F116 → S21

### 架构对齐

- [ ] 不新建路由文件，在现有 entries.py / review.py / feedback.py 内新增端点
- [ ] 前端不新建页面，在现有组件内添加导出按钮和状态标签
- [ ] log-service 状态同步用 httpx 直接调 API，不修改 SDK
- [ ] 导出复用现有 FileResponse / StreamingResponse 模式
- [ ] 反馈状态扩展不破坏现有 pending/reported 语义

## R026: 收敛修复

### 契约对齐

- [x] S18: 不涉及新契约，修改 review_service._calculate_mastery_from_stats 算法 ✓
- [x] S19: 不涉及新契约，修改 knowledge_service 内部实现（删除 2 个死方法）✓
- [x] B82: 不涉及新契约，修改 knowledge.py 路由错误处理 ✓

### 依赖对齐

- [x] S18 无外部依赖 ✓
- [x] S19 无外部依赖 ✓
- [x] B82 无外部依赖 ✓
- [x] F112 无外部依赖 ✓
- [x] F113 无外部依赖 ✓
- [x] S20 depends_on S18, S19, B82, F112, F113 ✓

### 架构对齐

- [x] 不新建服务文件，在现有 review_service/knowledge_service/knowledge.py 内修改 ✓
- [x] 前端组件拆分在文件内完成，不新建文件 ✓
- [x] review_service 掌握度算法收敛到 knowledge_service 同一套阈值式 ✓
- [x] 路由层错误处理收敛到与全局 ErrorHandlerMiddleware 一致的脱敏原则 ✓
