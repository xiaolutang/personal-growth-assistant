# Session S005: 反馈功能规划审核修正

> 日期: 2026-04-12
> 触发: 根据规划审核结果修正 P10 反馈功能计划
> 模式: workflow B / codex_plugin review

## 输入问题

- severity 枚举前后端不一致
- FB02 缺少对 FB03 的依赖
- FloatingChat 与反馈按钮的避让规则未定义
- `log_service_sdk.report_issue()` 签名未前置确认
- 测试覆盖缺少 422 分支和前端组件测试

## 本轮修正

- 新增前置任务 `S004`，用于确认 `report_issue()` 签名、异常类型、返回结构和 severity 枚举
- 将 `FB02.depends_on` 调整为 `FB01 + FB03`
- 将 severity 统一为 `low | medium | high | critical`
- 在架构与任务验收中补充 `FeedbackButton` 与 `FloatingChat` 的 16px 避让约束
- 扩充测试覆盖：`FB01` 增加 title 422 和 severity 422；`FB02` 增加组件交互与浮层避让测试；`FB03` 增加 422 分支

## 结果

- `feature_list.json`、`api_contracts.md`、`test_coverage.md`、`alignment_checklist.md` 已同步
- `architecture.md`、`project_spec.md`、`feature_structure.md`、`feature_map.md` 已补充 P10 约束
- 当前状态：等待重新审核
