# S001 R034 技术债收敛规划

> 日期：2026-04-25
> 参与者：用户 + Claude Code

## 需求输入

用户要求规划下一轮需求。经分析历史规划文档：
- R022 体验打磨 15 项任务已在 R023-R033 期间全部完成
- R029 Simplify 收敛审查的 9 项 residual risks 仍未处理
- 用户选择全部 9 项一起做

## 需求讨论

1. **R022 已完成确认**：逐一验证 14 个功能任务的代码，确认全部已实现
2. **R029 Residual Risks 验证**：
   - F-011: useMorningDigest `useState(false)` 仍为 boolean
   - F-013: api.ts 从 700 行增长到 1188 行
   - F-014: GraphPage.tsx 1016 行未变
   - F-015: 5 个 Review 组件都有双重导出
   - F-017: review_service.py 从 1800 行增长到 2091 行
3. **范围确认**：全部 9 项 residual risks + 1 项测试缺口(AC8)

## 架构校验

- 无与 architecture.md 冲突的变更
- 所有改动为现有模块内的代码质量提升，不引入新模式
- 大型重构(F-013/F-014/F-017)为文件拆分和类型迁移，不改业务逻辑

## Plan Review

- **审核时间**：2026-04-25T00:46:29+08:00
- **审核结果**：conditional_pass
- **审核发现**（5 项）：
  1. [high] F127 测试覆盖不足：缺少 focus 高亮/搜索防抖/聚合模式/详情面板等状态流
  2. [medium] B95 文件清单遗漏 review.py 路由层 import 切换
  3. [medium] B93 缺少成长报告导出链路回归验证
  4. [medium] B94 缺少部分匹配/大小写/去重/最多 5 条行为锁定测试
  5. [medium] alignment_checklist.md 和 test_coverage.md 未更新
- **修复动作**：全部 5 项已修复

## 决策记录

- B 模式：Codex Plugin 自动审核
- 按依赖分 4 个 Phase：快速修复 → 效率优化 → 大型重构 → 测试补齐 + 质量收口
- F125(GraphPage 拆分)必须在 F127(Tab 测试)之前完成
- api.ts 迁移采用渐进策略：逐个类型替换而非一次性重写
