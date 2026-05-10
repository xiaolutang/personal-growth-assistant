# 对齐清单

## R055: 交互基础补齐

### 用户路径对齐

- [ ] F01/F03: 打开列表页 → 看到 shimmer 骨架 → 数据加载后切换到真实内容（9 个页面）
- [ ] F02/F04: 在 Notes 页搜索 → 连续输入 → 300ms 后触发搜索
- [ ] F05: 在 Tasks 页左滑 → 完成任务 → SnackBar 撤销
- [ ] F05: 在 Inbox 页左滑 → 删除条目 → SnackBar 撤销
- [x] F06: 点击条目 → 进入详情 → 右滑入 → 返回 → 右滑出（iOS CupertinoPage + Android CustomTransitionPage）

### 架构对齐

- [ ] F01-F06: 均在 View 层操作，不涉及 ViewModel/Model 变更
- [ ] F05: Dismissible 通过 Riverpod provider 操作数据，Widget 不直接调用 ApiClient
- [ ] F02: Debouncer 是纯工具类，不引入 Provider 依赖
- [x] F06: 使用 GoRouter pageBuilder 替代 builder，iOS 用 CupertinoPage 保留 swipe back，Android 用 CustomTransitionPage
- [ ] 所有任务不违反 architecture.md 禁止模式

### 依赖对齐

- [ ] F01: 无依赖 ✓
- [ ] F02: 无依赖 ✓
- [ ] F03 depends_on F01 ✓（需要 SkeletonLoading 组件）
- [ ] F04 depends_on F02 ✓（需要 Debouncer 工具）
- [ ] F05: 无依赖 ✓
- [ ] F06: 无依赖 ✓
- [ ] S07 depends_on F03 + F04 + F05 + F06 ✓

### 完成性检查

- [ ] 所有 P0 任务有 acceptance_criteria
- [ ] 依赖链完整无循环
- [ ] 按钮内 spinner（CircularProgressIndicator）不被 F03 误改
- [ ] 无 risk_tags 任务（骨架屏/防抖/滑动/转场均无网络/认证/首用风险）

### 执行顺序

- [ ] Phase 1: F01 + F02（基础组件，可并行）
- [ ] Phase 2: F03 + F04 + F05 + F06（页面集成，F03/F04 有依赖，F05/F06 可并行）
- [ ] Phase 3: S07（质量收口）
