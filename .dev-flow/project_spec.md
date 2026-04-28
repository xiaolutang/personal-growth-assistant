# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.43.0
> 状态：规划中（R043）
> 活跃分支：chore/R043-architecture-convergence

## 当前范围

R043 架构优化与代码收敛：基于 simplify 4 视角并行审查的 75 项发现，对 7 个核心文件（7,294 行）做架构级收敛。

### Phase 1: 基础设施拆分（1 task）

1. **B177 sqlite.py 领域拆分**：2229 行 God Class 拆分为 5 个文件 + 连接上下文管理器 + 代码质量修复

### Phase 2: 架构正确性（3 tasks）

2. **B178 MCP handlers 改用 deps service 实例**：消除 MCP 路径与 HTTP API 路径的业务逻辑分叉
3. **B179 entry_service 消除 deps 反向依赖**：构造注入替代运行时反向 import
4. **B180 knowledge_service 模型提取**：15 个 Pydantic 模型移到 models/

### Phase 3: 代码收敛（4 tasks）

5. **B181 goal_service N+1 + 进度计算统一**：批量查询 + DRY 消除
6. **B182 review_service 三报告模板提取**：消除日报/周报/月报三份重复
7. **B183 entry_service batch 查询优化**：消除 list_entry_links 和 note_references 的 N+1
8. **B184 sqlite 重复模式合并**：通用动态更新 + 标签统计合并

### Phase 4: 前端一致性（1 task）

9. **F177 api.ts 里程碑 API 统一 openapi-fetch**

### Phase 5: 质量收口（1 task）

10. **S44 全量测试 + 构建 + Docker smoke**

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 10 |
| P0 | 4（B177, B178, B179, S44）|
| P1 | 5（B180, B181, B182, B183, B184）|
| P2 | 1（F177）|

## 技术约束

- 所有改动必须保持接口兼容，消费者无感
- sqlite.py 拆分采用组合模式，SQLiteStorage 入口类不变
- MCP handlers 重构后两条路径（HTTP API + MCP）共享同一套 service 逻辑
- workflow: B/codex_plugin/skill_orchestrated
