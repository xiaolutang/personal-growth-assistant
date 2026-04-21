# S001: R017 审计加固规划

> 日期：2026-04-18
> 状态：规划中

## 背景

R016 完成后，对全项目 5 个功能区域发起全面代码审计，共发现 96 个问题（9 Critical, 22 High, 39 Medium, 26 Low）。

## 本轮需求

修复审计发现的关键问题，按优先级分 5 个 Phase：

1. **安全加固** (B56/B57/B58) — P0，注入防护 + 认证 + 隔离
2. **数据正确性** (B59/B60) — P0，分类变更 + 存储一致性
3. **前端修复** (F56) — P1，SSE 泄漏 + useEffect cleanup
4. **后端架构** (B61/B62) — P1-P2，async 重构 + 性能优化
5. **测试修复** (B63) — P2，失效测试对齐

## 运行模式

- workflow.mode: B
- workflow.runtime: skill_orchestrated
- review/audit/risk_provider: codex_plugin

## 关键决策

1. 不修复 Medium/Low 纯风格问题，聚焦安全+正确性
2. _run_async 重构为 B61 单独任务（影响面大）
3. N+1 优化依赖 async 重构完成（B62 depends on B61）
4. 测试修复放在最后（B63 depends on B57+B61）
