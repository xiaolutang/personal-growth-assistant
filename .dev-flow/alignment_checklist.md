# 对齐清单

## R052: 聊天用户隔离 + Today 页 AI 对话入口

### 契约对齐

- [ ] S01: 不修改 API 契约，纯前端登出流程修复
- [ ] F02: 复用 POST /parse SSE 对话端点（chatProvider.sendMessage），不新增 API
- [ ] F02: 快捷录入创建条目复用 POST /entries（createEntry），不新增接口

### 依赖对齐

- [ ] S01: 无依赖（P0 bug 修复，独立可交付）
- [ ] F02 depends_on S01 ✓（Today 页复用 chatProvider，需先保证隔离正确）
- [ ] S03 depends_on S01 + F02 ✓（质量收口需全部功能就绪）

### 架构对齐

- [ ] S01: chatProvider 清理使用 Riverpod invalidate，符合 Flutter MVVM 分层
- [ ] S01: session_id 存储在 SecureStorage，登出时通过 AuthService._clearAuthData() 清除
- [ ] F02: Today 页输入栏复用 chatProvider.sendMessage()，不引入新的对话通道
- [ ] F02: 不修改 QuickCaptureFAB（保持独立灵感捕获功能）
- [ ] F02: Today 页对话展示遵循 Flutter MVVM — Widget → Notifier → ApiClient
- [ ] 所有任务不违反 architecture.md 不变量：user_id 隔离、JWT 认证、MVVM 分层

### 执行顺序

- [ ] Phase 1: S01（用户隔离修复）
- [ ] Phase 2: F02（Today 页 AI 对话入口）
- [ ] Phase 3: S03（质量收口）
