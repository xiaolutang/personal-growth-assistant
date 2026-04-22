# Session S001: R025 规划

> 日期: 2026-04-22

## 需求输入

- Phase 8：增强现有 GraphPage，加「能力地图」视图 + AI 图谱助手对话
- Phase 10：增强 AI 总结深度，周报/月报从 2-3 句扩展为结构化洞察报告

## 基线分析

- GraphPage 833 行，已有领域/掌握度/项目 3 种视图、搜索、节点聚合、详情面板
- 后端 8 个知识图谱 API，含全局图谱、概念统计、搜索、时间线、掌握度分布
- Review 页 453 行，已有趋势图、热力图、成长曲线、AI 总结（2-3 句短总结）
- review_service 1444 行，`_generate_ai_summary` 只有 2-3 句，缺深度洞察

## 确认

- Workflow: B / codex_plugin / skill_orchestrated
- 架构无冲突

## Plan Review Round 1

- review_provider: codex_plugin
- review_status: fail
- reviewed_at: 2026-04-22T16:39:17+0800

### Findings (6 项)

1. **High**: F111 数据来源不明确 — 契约未定义详细总结字段
2. **High**: B80 ID 与 R022 已完成任务冲突
3. **Medium**: test_coverage.md / alignment_checklist.md 缺 R025 段落
4. **Medium**: F110/B81/F108/F109 测试设计缺口
5. **Low**: F111 文件路径错误（应为 components/review/AiSummaryCard.tsx）

### 修复动作

- B80 → B81，所有依赖引用同步更新
- F111 明确数据来源为 /review/insights，前端拼装 Markdown
- F111 文件路径修正为 components/review/AiSummaryCard.tsx
- F110 补充 test_tasks（SSE 失败/空上下文/视图切换）
- F108 补充 test_tasks（日报隐藏/API 失败）
- F109 补充 test_tasks（筛选传参/API 失败）
- B81 补充 test_tasks（用户隔离）
- test_coverage.md 补 R025 段落
- alignment_checklist.md 补 R025 段落
- api_contracts.md B80→B81 引用更新

### Plan Review Round 2

- review_provider: codex_plugin
- review_status: conditional_pass
- reviewed_at: 2026-04-22T16:55:00+0800

#### Findings (3 项)

1. F110 pageContext 命名与现有 PageContext schema 不一致（`knowledge-graph` vs 已有 `graph`）
2. F110 缺主链路 happy path 测试（图谱上下文提问 + SSE 流式回答）
3. S15/B81 缺非法参数边界测试

#### 修复动作

- F110 pageContext 从 `knowledge-graph` 改为 `graph`（匹配已有 schema）
- F110 补主链路测试：图谱上下文提问成功 + SSE 流式回答
- S15 补非法 period 参数 422 测试
- B81 补非法 mastery_level 参数 422 测试
