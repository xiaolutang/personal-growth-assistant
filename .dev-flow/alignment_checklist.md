# 对齐清单

## R052: 聊天用户隔离 + Today 页 AI 对话入口

### 契约对齐

- [ ] S01: 不修改 API 契约，纯前端登出/401 流程修复
- [ ] F02: 复用 POST /chat SSE 对话端点（CONTRACT-AGENT-CHAT），page_type='today'
- [ ] F02: chatProvider.sendMessage() 增加 page_context 参数透传
- [ ] F02: 后端 page_type 枚举新增 'today'（parse.py PageContext.description）

### 依赖对齐

- [ ] S01: 无依赖（P0 bug 修复，独立可交付）
- [ ] F02 depends_on S01 ✓（Today 页复用 chatProvider，需先保证隔离正确）
- [ ] S03 depends_on S01 + F02 ✓（质量收口需全部功能就绪）

### 架构对齐

- [ ] S01: 清理逻辑统一在 AuthNotifier 层（logout + _onApiUnauthorized 两条路径），不依赖页面层调用
- [ ] S01: auth_provider.dart 纳入任务文件列表，负责 invalidate chatProvider + 清除 session_id
- [ ] S01: chatProvider 增加 clearMessages() 方法供 AuthNotifier 调用
- [ ] F02: Today 页输入栏复用 chatProvider.sendMessage()（POST /chat），不引入新的对话通道
- [ ] F02: 不修改 QuickCaptureFAB（保持独立灵感捕获功能）
- [ ] F02: Today 页对话展示遵循 Flutter MVVM — Widget → Notifier → ApiClient
- [ ] F02: SSE created 事件触发 todayProvider 刷新，不走额外 API
- [ ] 所有任务不违反 architecture.md 不变量：user_id 隔离、JWT 认证、MVVM 分层

### 执行顺序

- [ ] Phase 1: S01（用户隔离修复 — AuthNotifier 层）
- [ ] Phase 2: F02（Today 页 AI 对话入口 — POST /chat + page_type='today'）
- [ ] Phase 3: S03（质量收口 + 需求级 smoke）
