# 对齐清单

## R050: Flutter 日常可用

### 契约对齐

- [x] F01: 复用 POST /auth/register（注册）+ POST /auth/login（登录）
- [x] F02: 复用 POST /entries（createEntry, category=inbox）
- [x] F03: 复用 GET /review/morning-digest + POST /entries（快捷录入）
- [x] F04: 复用 GET /goals/{id} + 里程碑 CRUD + 关联条目端点
- [x] F05: 复用 GET /entries?due=today + flutter_local_notifications

### 依赖对齐

- [x] F01 无外部依赖
- [x] F02 无外部依赖（全局 FAB 组件 + inbox provider）
- [x] F03 depends_on F02 ✓（快捷录入使用 createInboxEntry）
- [x] F04 无外部依赖（目标详情独立页）
- [x] F05 无外部依赖（通知服务 + 设置页）
- [x] S06 depends_on F01+F02+F03+F04+F05 ✓

### 架构对齐

- [x] Flutter MVVM 分层：Widget → Riverpod Notifier → ApiClient
- [x] QuickCaptureFAB 统一捕获组件，Shell 层和页面层共用
- [x] inbox 创建权威收敛：entry_provider.createInboxEntry → inbox_provider.createInboxItem
- [x] 通知导航接线：NotificationService.onNotificationTap → GoRouter.go(payload)
- [x] BottomNavShell._shouldShowFab 条件隐藏（/entries/*, /goals/:id, /）
- [x] 不违反 architecture.md 不变量：user_id 隔离、JWT 认证守卫、MVVM 分层

### 执行顺序

- [x] Phase 1: F01（注册）
- [x] Phase 2: F02 + F03（FAB + 首页升级，可并行）
- [x] Phase 3: F04 + F05（目标详情 + 通知，可并行）
- [x] Phase 4: S06（质量收口）

## R048: 创建体验升级

### 契约对齐

- [x] 无新增 API 契约：复用已有 POST /entries（createEntry），所有 7 种类型均支持
- [x] 无后端改动：纯前端需求，createEntry API 已满足全部字段需求

### 依赖对齐

- [x] S01 无外部依赖（通用组件）
- [x] F02 depends_on S01 ✓（任务页使用 CreateDialog）
- [x] F03 depends_on S01 ✓（首页使用 CreateDialog 的"更多类型"入口）
- [x] F04 depends_on S01 ✓（探索页使用 CreateDialog）
- [ ] F05 depends_on S01 + F03（智能提示增强 CreateDialog + QuickCaptureBar）

### 架构对齐

- [x] CreateDialog 位于 components/，符合 pages/ → components/ → lib/ 单向依赖
- [x] QuickCaptureBar 位于 pages/home/，仅被 Home.tsx 使用
- [x] 写操作通过 taskStore.createEntry（符合"写操作优先通过 store"规范）
- [x] 不引入新 API 端点，不硬编码后端枚举值（使用 categoryConfig）

### 执行顺序

- [x] Phase 1: S01（基础组件）
- [x] Phase 2: F02 + F03 + F04（可并行）— F03 done, F04 done
- [ ] Phase 3: F05（增强，可延后）

## R047: 任务/探索 Tab 边界重新划分

### 契约对齐

- [ ] S01: POST /entries/{id}/convert 契约已定义 (CONTRACT-CONVERT)
- [ ] B02: GET /entries?category_group 契约已定义 (CONTRACT-CATEGORY-GROUP)

### 依赖对齐

- [ ] S01 无外部依赖
- [ ] B02 无外部依赖
- [ ] F03-F12 链式依赖

### 架构对齐

- [ ] 变更在现有 routers/services/infrastructure 分层内
- [ ] 不涉及三层存储架构变更
- [ ] 不涉及认证/权限变更
