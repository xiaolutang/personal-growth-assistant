---
date: 2026-04-29
type: requirement_clarification
status: decided
requirement_cycle: R047
architecture_impact: false
supersedes: null
---

# 任务 vs 探索 Tab 边界重新划分

## 背景

当前任务 Tab 只显示 category=task，探索 Tab 显示其余 6 种类型（inbox/note/project/decision/reflection/question）。探索页承载过重，同时处理"捕获"、"回顾"、"项目管理"三种节奏不同的场景。任务页功能偏窄，作为"执行中心"密度不足。

## 决策

- 选择：按「行动性」重新划分（方案 B）
- 理由：有 status 字段的类型（task/decision/project）天然需要推进，归入任务 Tab；无 status 的类型（inbox/note/reflection/question）是沉淀性的，归入探索 Tab
- 前提条件：用户在切换 tab 时心智模型是"做事"vs"回顾"
- 风险：project 类型既包含行动又包含文档，需明确归属

## 类型归属

| 类型 | 归属 | 理由 |
|------|------|------|
| task | 任务 Tab | 天然行动项 |
| decision | 任务 Tab | 需要行动（做决定）才能关闭 |
| project | 任务 Tab | 长期承诺，需推进，含子任务 |
| inbox | 探索 Tab | 原始素材，未加工 |
| note | 探索 Tab | 知识输出 |
| reflection | 探索 Tab | 回顾沉淀 |
| question | 探索 Tab | 探索性 |

## 关键设计决策

1. **project 搜索可见性**：探索页搜索可命中 project 的 title/content，点击后跳转任务 Tab。project 卡片只在任务页展示。
2. **类型转换历史**：条目新增 `type_history` 嵌套字段，记录类型变迁时间线。
3. **decision 终态**：待定，倾向保留在任务页（complete 状态），通过筛选自然隐藏。

## 探索 Tab 精简

类型 tab 从 6 种精简为 4 种 + 全部 = 5 个 tab：全部、灵感、笔记、复盘、疑问。

## 跨 Tab 转化

- inbox → task/decision 为核心路径（探索页点击"转为任务"）
- task → reflection 为辅助路径（完成任务后写复盘）
- decision → task(s)（决策后拆出行动项）

## 任务 Tab 新增能力

- 三种视图模式：列表 / 按项目分组 / 时间线
- 类型子 Tab：全部、任务、决策、项目
- decision 专属卡片 UI（YES/NO/延后按钮 + 拆任务）
- project 卡片带进度条
- 逾期提醒

## 后续动作

- 进入 xlfoundry-plan 拆解为可执行任务
