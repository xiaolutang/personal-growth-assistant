# R015 回顾增强

- **分支**: feat/R015-review-enhancement
- **状态**: completed
- **时间**: 2026-04-17 ~ 2026-04-18

## 任务清单

| ID | 类型 | 名称 | 验证 | 状态 |
|----|------|------|------|------|
| B52 | 后端 | 趋势数据多维扩展 + 周环比对比 | L2 | completed |
| B53 | 后端 | 知识热力图 Neo4j 数据源升级 | L2 | completed |
| F40 | 前端 | 趋势图多维展示 | F2 | completed |
| F41 | 前端 | 知识热力图升级 | F2 | completed |
| F42 | 前端 | 晨报集成到回顾日报页 | F2 | completed |

## 依赖关系

```
B52 ──→ F40
B53 ──→ F41
F42（独立）
```

## 测试汇总

- 后端：810 passed（含 B52 13 + B53 32 新增）
- 前端：245 passed
- Build：全绿

## 关键改动

- TrendPeriod 新增 task_count/inbox_count，按分类统计趋势
- WeeklyReport/MonthlyReport 新增 vs_last_week/vs_last_month 环比对比
- 知识热力图 Neo4j 优先 + SQLite 降级，掌握度算法增强含 relationship_count
- 前端趋势图从单线升级为 4 线（完成率+任务+笔记+灵感），双 Y 轴 + 图例
- 前端热力图按 category 分组展示，掌握度配色统一
- 晨报卡片集成到日报标签页顶部
