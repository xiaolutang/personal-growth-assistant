# S001 R035 需求讨论与范围确认

> 日期：2026-04-25
> 参与者：用户 + Claude

## 背景

R034 技术债收敛已完成并归档。Simplify 收敛审查发现 5 项预存问题，用户选择修复其中 3 项高/中优先级问题。

## 需求确认

### 用户选择范围

- A1（high）：export_growth_report 趋势数据字段名不匹配
- A2（high）：review_service 3 处全表扫描（选取前 2 处高优先级）
- A3（medium）：_calculate_mastery_from_stats 跨服务循环依赖

### 未选入范围（降级为 residual risks）

- A4（medium）：deps.py 访问私有属性
- A5（low）：其他页面 graph/ 子目录拆分模式不一致

## 调查结论

### A1: export_growth_report trend_data 字段名

- review_service.py:1515 检查 `trend_data.daily_data`
- TrendResponse 模型字段是 `periods`
- hasattr 永远 False → 趋势始终"暂无数据"
- fix_level L1，1 行改动

### A2: review_service 全表扫描

1. `_get_heatmap_from_sqlite`：list_entries(limit=1000) → 可直接用 get_tag_stats_for_knowledge_map()
2. `_compute_30d_tag_stats`：list_entries(limit=5000) → 需新增 get_tag_stats_in_range()
3. `get_growth_curve`：list_entries(limit=10000) → 本次不修（复杂度高，收益中）

### A3: 跨服务循环依赖

- knowledge_service 运行时导入 review_service 调用静态方法
- ReviewService 版本支持 4 参数，KnowledgeService 委托版本只有 3 参数
- 提取到 app/utils/mastery.py 独立模块

## 任务拆解

| Phase | ID | 名称 | 优先级 |
|-------|-----|------|--------|
| P1 | B96 | 修复 trend_data 字段名 | P0 |
| P1 | B97 | 提取掌握度计算到共享模块 | P1 |
| P2 | B98 | heatmap 改用 SQL 聚合 | P1 |
| P2 | B99 | tag_stats 改用 SQL 聚合 | P2 |
| P3 | S32 | 质量收口 | P2 |

## 决策

- workflow: B/codex_plugin/skill_orchestrated
- branch: fix/R035-preexisting-fixes
- B99 依赖 B98（共享 sqlite.py 文件，避免写冲突）
