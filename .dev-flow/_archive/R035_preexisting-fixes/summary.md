# R035 预存问题修复

> 创建时间：2026-04-25
> 完成时间：2026-04-25
> 状态：completed
> 分支：fix/R035-preexisting-fixes

## 概要

修复 R034 Simplify 收敛审查发现的预存 bug 和性能问题。

## 任务清单

| ID | 模块 | 名称 | 状态 |
|----|------|------|------|
| B96 | review | 修复 export_growth_report 趋势数据字段名 | completed |
| B97 | mastery-utils | 提取 _calculate_mastery_from_stats 到共享模块 | completed |
| B98 | review-perf | _get_heatmap_from_sqlite 改用 SQL 聚合 | completed |
| B99 | review-perf | _compute_30d_tag_stats 改用 SQL 聚合 | completed |
| S32 | quality | 质量收口 | completed |

## 提交记录

| 提交 | 说明 |
|------|------|
| 0a8bb47 | B96 修复 export_growth_report 趋势数据字段名 |
| dadb2d1 | B97 提取掌握度算法到共享模块 |
| 9466331 | B98+B99 heatmap 和 tag_stats 改为 SQL 聚合 |
| fc74b7f | S32 R035 质量收口 |
| 4d1fe64 | S32 code-review 修复 |
| 7468349 | S32 聚合层状态一致修复 |
| 573acb8 | S32 审计回写 |
| aae1b3e | S32 Docker smoke 通过 + R035 全部完成 |

## Sessions

| Session | 主题 | 日期 |
|---------|------|------|
| S001 | R035 需求讨论与范围确认 | 2026-04-25 |
