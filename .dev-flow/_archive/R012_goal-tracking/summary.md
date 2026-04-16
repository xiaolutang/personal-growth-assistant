# R012: 目标追踪闭环

> 归档日期: 2026-04-17
> 分支: feat/R012-goal-tracking (已合并到 main)
> 状态: completed

## 概述

目标追踪完整闭环：目标 CRUD + 三种衡量方式（手动计数/检查清单/Tag自动追踪）+ 进度计算 + 首页/回顾页集成。

## 完成任务

| ID | 名称 | 类型 | commit |
|----|------|------|--------|
| B45 | Goals CRUD API | 后端 | f335e5d |
| B46 | Goal 条目关联 + 进度计算 | 后端 | 09716d6 |
| B47 | Goal 自动追踪触发 | 后端 | 224bcfd |
| F34 | Goals 页面 + 详情 | 前端 | 2cad997 |
| F35 | 首页目标进度卡片 | 前端 | 7db4066 |
| F36 | 回顾页目标完成概览 | 前端 | 7db4066 |

## 关键决策

- 目标数据存储在 SQLite（与 entry_links 同级），不写 Markdown
- progress_percentage 由 GoalService 实时计算，不持久化
- tag_auto 类型使用 entry_tags 归一化表查询，支持时间范围过滤
- progress_delta 仅在 weekly/monthly 周期且 tag_auto 类型（含 start_date + end_date）时计算
- 状态不自动回退：进度下降时 status 保持 completed，用户可手动改回 active

## 测试

- 后端: 717+ tests pass (44 goals-specific)
- 前端: 231 tests pass
- 5 轮 Codex Plugin 审计收敛
