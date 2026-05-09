# 对齐清单

## R053: Today 页智能命令栏

### 契约对齐

- [ ] B01: POST /chat page_type 新增 'command'，Agent 直接执行不追问
- [ ] B01: 新增 SSE `redirect` 事件类型（conversational intent → redirect to chat）
- [ ] F01: 使用 POST /chat SSE + page_type='command'，不共享 chatProvider
- [ ] F01: 每次命令生成新 session_id（无状态）
- [ ] F02: 不修改 QuickCaptureFAB（保持独立灵感捕获功能）
- [ ] F02: 不修改 chat_page.dart（日知页保持不变）

### 依赖对齐

- [ ] B01: 无依赖（后端 Agent 提示词 + redirect 事件）
- [ ] F01 depends_on B01 ✓（前端需后端 redirect 事件信号）
- [ ] F02 depends_on F01 ✓（UI 使用 commandBarProvider）
- [ ] S03 depends_on B01 + F01 + F02 ✓

### 架构对齐

- [ ] F01: commandBarProvider 独立于 chatProvider，不共享 SseService 实例
- [ ] F01: 使用 Dio 直接发起 SSE 请求（不经过 SseService 单例），避免与 chatProvider SSE 连接冲突
- [ ] F01: 遵循 MVVM — Widget → commandBarProvider(Notifier) → Dio SSE
- [ ] F02: 移除 Today 页对 chatProvider 的全部依赖（import、watch、listener）
- [ ] F02: 不违反 architecture.md 禁止模式：多 Provider 不监听同一 SSE 连接
- [ ] B01: Agent prompt 变更不影响现有 /chat 行为（非 command page_type 行为不变）
- [ ] 所有任务不违反 architecture.md 不变量：user_id 隔离、JWT 认证、MVVM 分层

### 命令结果类型对齐

| SSE 事件 | CommandResult 类型 | F02 UX |
|----------|-------------------|--------|
| created | task_created / note_created / entry_created | SnackBar toast + todayProvider 刷新 |
| updated | entry_updated | SnackBar toast + todayProvider 刷新 |
| content (无 tool_call) | answer | 内联卡片展示 |
| redirect | redirect_chat | "在日知中继续对话 →" 跳转链接 |
| tool_call(ask_user) | follow_up | 内联追问卡片，允许在同一命令内回复 |
| error | error | 输入框下方错误条 + 重试按钮 |

### 执行顺序

- [ ] Phase 1: B01（后端 command 模式 + redirect 事件）
- [ ] Phase 2: F01（CommandBar Provider + 独立 SSE）
- [ ] Phase 3: F02（Today 页命令栏 UI + 移除 chatProvider 依赖）
- [ ] Phase 4: S03（质量收口 + smoke）
