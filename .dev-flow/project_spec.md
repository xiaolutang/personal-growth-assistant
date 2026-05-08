# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.51.0
> 状态：进行中（R051）
> 活跃分支：chore/R051-code-quality-optimization

## 当前范围

R051 项目代码优化：跨三端（Backend + Frontend + Flutter）的代码质量收敛、性能优化和工程健壮性提升。

### 核心问题

经过 16 轮需求迭代（R036-R050），三端积累了可观的优化机会：

1. **Flutter P0 Bug**：goalsProvider 状态共享导致数据错乱、copyWith sentinel 缺失导致 error 被意外清除
2. **Backend 性能**：feedback sync N+1 串行 HTTP、弃用 asyncio API、HybridSearchService 未复用缓存
3. **Frontend 性能**：taskStore 全局 tasks 数组导致联动重渲染、列表项缺 React.memo
4. **三端代码重复**：Flutter 8 页面共享状态组件重复 ~500 行、Frontend MorningDigestCard 两套实现、Backend Neo4j 降级模式不统一
5. **死代码**：Frontend AgentChat (162 行) + KnowledgeGraph (262 行) + SearchResultCard + ActionIndicator 未使用

### Phase 1: Flutter P0 Bug 修复（2 tasks）

1. **S01 goalsProvider 状态隔离**：GoalDetailPage 改用独立 family provider
2. **S02 copyWith sentinel 修复**：ChatState + EntryListState 统一 sentinel 模式

### Phase 2: Backend 性能优化（2 tasks）

3. **B03 弃用 API + HybridSearchService 复用**：asyncio + deps 缓存实例
4. **B04 N+1 并发化 + 连接管理修复**：feedback sync gather + AnalyticsService _conn()

### Phase 3: Frontend 性能 + 死代码（2 tasks）

5. **F05 taskStore 优化 + React.memo**：selector + memo 包裹
6. **F06 死代码清理**：删除 AgentChat/KnowledgeGraph/SearchResultCard/ActionIndicator

### Phase 4: Flutter 代码质量（3 tasks）

7. **F07 共享组件提取 + EntryCard/TaskCard 去重**：EmptyState/ErrorState widget + statusIcon/tagRow
8. **F07b formatDate 统一**：DateFormatter 工具函数替换 5 处重复实现
9. **F08 ExplorePage TabBarView 优化 + sseService 清理**：tab 隔离 + 死代码

### Phase 5: Frontend + Backend 代码质量（2 tasks）

10. **F09 MorningDigestCard 合并 + BaseDialog 统一**
11. **B10 Neo4j 降级统一 + goal_service JSON 去重**

### Phase 6: 质量收口（1 task）

12. **S11 全量验证**：pytest + vitest + flutter test + build

## 技术约束

- 纯重构/优化工作，不新增功能
- 不修改 API 契约（不改接口签名和返回格式）
- 不引入新依赖
- 每个任务独立可验证、可回滚

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 12 |
| P0 | 2（S01, S02）|
| P1 | 7（B03, B04, F05, F06, F07, F07b, F09）|
| P2 | 2（F08, B10）|
| P3 | 1（S11）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
