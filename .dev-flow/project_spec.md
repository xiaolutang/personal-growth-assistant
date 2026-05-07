# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.50.0
> 状态：进行中（R050）
> 活跃分支：feat/R050-flutter-daily-usable

## 当前范围

R050 Flutter 移动端日常可用：补齐注册、快速捕获、首页晨报、目标详情、到期通知 5 个核心能力，达到日常可用。

### 核心问题

Flutter 移动端已有 10 个功能完整的页面，但缺少日常使用的关键闭环：
1. 新用户无法自行注册（只有登录页）
2. 没有「随时随地记一笔」的快速入口（需先进入对应页面）
3. 首页缺少 AI 晨报摘要（Web 端已有 morning-digest）
4. 目标只有展开/收起，无法深度管理
5. 任务到期无提醒

### 架构现状

- 后端 API 已全部就绪：entries/goals/review/notifications 共 40+ 端点
- 唯一缺口：forgot-password API（本轮简化处理，只做前端提示）
- Flutter 端：Riverpod + Dio + go_router 架构成熟，15 个 Provider

### Phase 1: 注册闭环（1 task）

1. **F01 注册页 + 忘记密码提示**：注册表单 + 登录页增加注册/忘记密码入口

### Phase 2: 捕获 + 首页（2 tasks）

2. **F02 全局 FAB 快速捕获**：所有主页面 FAB → 底部弹窗 → 存 inbox
3. **F03 首页升级**：晨报卡片（GET /review/morning-digest）+ 快捷录入栏

### Phase 3: 目标 + 通知（2 tasks）

4. **F04 目标详情独立页**：里程碑 CRUD + 关联条目 + 进度可视化
5. **F05 到期通知 + 设置**：本地通知 + 设置页（退出登录 + 通知开关）

### Phase 4: 质量收口（1 task）

6. **S06 全量验证**：flutter test + analyze + 主动线冒烟

## 技术约束

- 纯 Flutter 前端工作，后端 API 全部已有无需改动
- 新增依赖：flutter_local_notifications（F05）
- 遵循现有 MVVM 模式：View → Notifier(Riverpod) → Service(ApiClient)
- 遵循 architecture.md 前端不变量：pages → widgets → lib 依赖方向

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 6 |
| P0 | 3（F01, F02, F03）|
| P1 | 3（F04, F05, S06）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
