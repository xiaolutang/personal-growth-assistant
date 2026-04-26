# S001 R037 需求讨论与范围确认

> 日期：2026-04-26
> 参与者：用户 + Claude Code

## 需求输入

用户要求：基于 `docs/product-design-analysis.md` 规划文档，规划下一轮需求。

## 需求讨论

1. **三阶段路线图完成度评估**：产品三阶段演进路径（补闭环 → 统一探索 → 差异化）已基本全部落地。R001-R036 共 36 轮迭代覆盖了所有 Phase 0-13 的核心功能。

2. **遗留问题排查**：全面排查后确认：
   - R032+R027 测试缺口已在 R036 S33 中补齐（63 tests）
   - R022 体验打磨 15 项全部仍为 pending
   - H8 搜索混合搜索仍未迁移到 HybridSearchService
   - 代码层技术债 6 项
   - 归档中"后续处理"标记的功能增强若干

3. **范围确认**：用户选择全部四项方向：
   - R022 体验打磨全量（15 tasks）
   - 测试覆盖补齐（已在 R036 完成，不再需要）
   - 技术债 + 搜索迁移
   - 规划文档 P1 功能（任务截止日期、成长曲线、笔记双链）

4. **工作流模式**：B（Codex Plugin 自动审核），skill_orchestrated

## 架构校验

- 无与 architecture.md 冲突的变更
- 搜索迁移属于现有模块增强
- 任务截止日期需要扩展 entry 模型字段（planned_date 已有，需加 due_date）
- 笔记双链需要新增 [[note-id]] 解析逻辑，不改变存储层架构
- 成长曲线数据端点可复用现有 review_service 趋势数据

## 决策记录

- 搜索迁移沿用 R022 S001 决策：优先在现有 search.py 内实现，不新建 service
- 体验打磨任务沿用 R022 原始设计，ID 从 F132 起重新编号
- P1 功能按纵向切片组织：每个功能后端 → 前端闭环
- 批量操作扩展到 Explore 页（R022 原计划仅支持 Tasks 页）

## Codex Plugin 审核记录

### 第 1 轮审核：fail（5 findings）

1. 双链语法 B107/F147 不一致 → 修复：B107 统一两种语法
2. 缺少契约文档和对齐块 → 修复：补充 api_contracts.md + alignment_checklist.md
3. F144 未依赖 F142 → 修复：添加依赖和离线批量行为
4. F142 测试缺少失败分支 → 修复：增补 5xx/超时/快速切换测试
5. project_spec 计数错误 → 修复：Phase 2 从 7 改为 8

### 第 2 轮审核：fail（6 findings）

1. B105 due_date vs planned_date 语义分叉 → 修复：改为扩展 planned_date
2. F147 NoteEditor.tsx 不存在 → 修复：改为 ContentSection.tsx
3. B107 缺少回填路径 → 修复：添加 reindex_backlinks 延迟初始化
4. test_coverage.md 缺 R037 节 → 修复：添加完整测试设计
5. F141 范围错误（SearchResultCard vs TaskCard）→ 修复：改为 TaskCard
6. F142/F144 同条目冲突测试缺失 → 修复：补充 5 个冲突场景

### 第 3 轮审核：conditional_pass（3 findings）

1. B105/F145 时区边界未统一 → 修复：明确 UTC midnight 规则 + 边界测试
2. F147 补全数据源未指定 → 修复：明确复用 GET /entries + 降级策略
3. S35 验收条件太宽泛 → 修复：缩小到 7 个核心端点 + 具体警告策略

### 最终状态

审核结果：conditional_pass → 用户决定是否接受建议并进入执行
审核时间：2026-04-26T09:57:17+0800
审核轮次：3
