# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.54.0
> 状态：进行中（R054）
> 活跃分支：feat/R054-fab-hybrid-upgrade

## 当前范围

R054 FAB 混合模式升级：将全局 FAB 从单一灵感记录升级为混合模式（灵感/任务/AI 智能创建），同时移除 Inbox 页底部输入栏消除功能冗余。

### 核心设计决策

决策记录：`.dev-flow/decisions/2026-05-10--fab-upgrade-and-input-consolidation.md`

**方案 C（混合模式）**：FAB 展开后提供 3 个选项：

| 选项 | 行为 | 实现方式 |
|------|------|---------|
| 记灵感 | 直接创建 inbox 条目 | 复用 createInboxEntry |
| 建任务 | 弹出任务创建 Sheet | 参考 QuickActions.CreateTaskSheet |
| AI 智能创建 | AI 意图识别 + 内联结果 | 复用 commandBarProvider（R053） |

### 输入入口整合

| 入口 | 决策 | 理由 |
|------|------|------|
| FAB | 升级为混合模式 | 全局快速入口 |
| Today 命令栏 | 保留 | 今日视角差异化 |
| Chat 对话 | 保留 | 深度对话场景不同 |
| Inbox 页输入栏 | 移除 | 与 FAB 灵感功能重复 |

### Phase 1: FAB 组件升级（1 task）

1. **F01 HybridFAB 混合模式升级**：展开式 FAB，3 个选项（灵感/任务/AI）

### Phase 2: 清理（1 task）

2. **F02 移除 Inbox 页底部输入栏**

### Phase 3: 质量收口（1 task）

3. **S03 全量验证**

## 技术约束

- 纯 Flutter 前端变更，不涉及后端
- 复用 commandBarProvider（R053 已交付）驱动 AI 入口
- 参考已有 QuickActions 组件的展开动画模式
- 保持 DraggableFAB 可拖动吸附功能
- 无 network/auth/first_use 风险

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 3 |
| P0 | 1（F01）|
| P1 | 1（F02）|
| P2 | 1（S03）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
