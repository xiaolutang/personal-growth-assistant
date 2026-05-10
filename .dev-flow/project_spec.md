# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.55.0
> 状态：进行中（R055）
> 活跃分支：feat/R055-interaction-basics

## 当前范围

R055 交互基础补齐：统一骨架屏加载、页面转场动画、搜索防抖、列表滑动操作。纯 Flutter 前端变更，不涉及后端。

### 核心目标

| # | 改进项 | 范围 | 优先级 |
|---|--------|------|--------|
| 1 | 骨架屏统一 | 9 个页面全屏 loading 替换为 SkeletonLoading | P0 |
| 2 | 页面转场动画 | 详情页 slide + 设置页 fade | P1 |
| 3 | 搜索防抖 | Notes 页搜索 300ms 防抖 | P0 |
| 4 | 列表滑动操作 | Tasks/Inbox Dismissible 滑动操作 | P0 |

### Phase 1: 基础组件（2 tasks）

1. **F01 通用骨架屏组件**：从 _DigestSkeleton 提取泛化，支持 list-card/text-line 预设
2. **F02 搜索防抖工具**：Debouncer utility，300ms 默认延迟

### Phase 2: 页面集成（4 tasks）

3. **F03 列表页骨架屏统一**：9 个页面全屏 loading 替换（依赖 F01）
4. **F04 Notes 搜索防抖**：接入 Debouncer（依赖 F02）
5. **F05 列表滑动操作**：Tasks/Inbox Dismissible + SnackBar 撤销
6. **F06 页面转场动画**：详情页 slide + 设置页 fade

### Phase 3: 质量收口（1 task）

7. **S07 R055 质量收口**：测试补充 + analyze 通过

## 技术约束

- 纯 Flutter 前端变更，不涉及后端
- 骨架屏不引入第三方 shimmer 包，纯 AnimationController 实现
- 转场动画使用 GoRouter pageBuilder，不引入额外路由包
- 滑动操作使用 Flutter 内置 Dismissible widget
- 遵循 MVVM：View → ViewModel(Riverpod) → Model
- 禁止 Widget 直接调用 ApiClient

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 7 |
| P0 | 4（F01/F02/F03/F04/F05）|
| P1 | 1（F06）|
| P2 | 1（S07）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
