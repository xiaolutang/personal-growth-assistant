# S06: R004 Phase 1A 规划会话

> 日期: 2026-04-14
> 状态: 进行中

## 输入

用户请求基于 `docs/product-design-analysis.md` 和 `docs/r004-implementation-plan.md` 制定 Phase 1A 的实施计划。

## 需求分析

Phase 1A 包含 4 个可并行的高阶任务（T01-T05），需拆解为可执行的原子任务。

### 代码审查发现

1. **review_service.py 数据隔离 Bug**：所有 list_entries() 调用未传 user_id，默认查 `_default` 用户数据
2. **EntryUpdate 前后端都缺 category 字段**
3. **SQLite 无 feedback 表**，需在 `_init_db()` 中创建
4. **FeedbackButton 不感知 auth context**，user_id 由后端 JWT 解析
5. **Sidebar 首页标签为「首页」**，需改为「今天」

### 架构校验

- review user_id bug 违反 architecture.md 不变量「所有数据操作必须携带 user_id」
- 新需求不违反现有禁止模式
- 无架构约束冲突

## 决策

- **执行模式**: B（Codex Plugin 自动审核）
- **分支**: `feat/R004-product-evolution-phase1a`
- **任务拆解**: 4 个高阶任务 → 6 个原子任务（S05 + B14/B15/B16 + F05/F06）
- **并行策略**: S05 先行，之后 B14/B15/B16/F05 四路并行，F06 等待 B16

## 输出

- feature_list.json（6 个新任务）
- api_contracts.md（3 个新契约）
- project_spec.md（R004 范围）
- test_coverage.md / alignment_checklist.md（新增任务行）
