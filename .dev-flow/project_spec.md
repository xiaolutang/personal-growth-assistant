# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.53.0
> 状态：进行中（R053）
> 活跃分支：feat/R053-today-command-bar

## 当前范围

R053 Today 页智能命令栏：将 Today 页底部输入栏从 AI 聊天入口改为智能命令栏（Command Bar），实现「输入 → AI 意图识别 → 内联结果」的原子操作模式。

### 核心设计决策

真实使用验收（R052）发现 Today 页输入栏交互混乱：
- 输入后无即时反馈（对话内容藏在日知 tab）
- 与日知页共享 chatProvider 导致消息出现在两个页面
- FAB 和输入栏功能重叠但行为不同

**解决方案：三个入口职责清晰分离**

| 入口 | 职责 | 交互模式 |
|------|------|---------|
| Today 命令栏 | 快速执行（创建任务/记录/提问） | 输入→内联结果，无对话历史 |
| 日知 | 深度 AI 对话 | 全屏聊天 |
| FAB | 快速记录灵感 | 最短路径，1 步完成 |

### Phase 1: CommandBar Provider（1 task）

1. **F01 CommandBar Provider**：独立 Provider，每次命令无状态，POST /chat + page_type='command'

### Phase 2: UI + 后端优化（2 tasks）

2. **F02 Today 页命令栏 UI**：替换聊天区域，内联结果展示
3. **B01 后端 command 模式提示词**：Agent 更直接、不追问

### Phase 3: 质量收口（1 task）

4. **S03 全量验证**

## 技术约束

- F01 新建独立 Provider，不修改 chatProvider
- F02 移除 Today 页对 chatProvider 的全部依赖
- B01 仅修改 Agent 提示词，不涉及 API 变更
- POST /chat 接口不变，仅新增 page_type='command' 使用场景
- FAB（QuickCaptureFAB）保持不变

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 4 |
| P0 | 2（F01, F02）|
| P2 | 1（B01）|
| P3 | 1（S03）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
