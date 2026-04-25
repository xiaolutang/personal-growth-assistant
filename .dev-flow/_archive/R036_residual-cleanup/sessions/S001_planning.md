# S001 R036 需求讨论与范围确认

> 日期：2026-04-25
> 参与者：用户 + Claude

## 背景

R034 技术债收敛和 R035 预存问题修复均已完成并归档。经全面扫描，项目中仍有 8 项已记录但未解决的残留风险和技术债务。

## 需求确认

用户选择「全部残留项」纳入 R036。

### 范围

| # | 优先级 | 编号 | 来源 | 问题 |
|---|--------|------|------|------|
| 1 | medium | A4 | R035 | deps.py 访问私有属性（11 处） |
| 2 | medium | TD10 | R001 | 503 降级只在 Tasks 页生效，其他 7 页缺失 |
| 3 | medium | A2-partial | R035 | get_growth_curve 仍为 limit=10000 全量查询 |
| 4 | low | A5 | R035 | 7 个页面未按 graph/ 子目录拆分模式统一 |
| 5 | low | H10 | R017 | 移动端拖拽排序缺失 |
| 6 | info | F-017 | R034 | review_service.py 仍有 1845 行 |
| 7 | planned | — | R032 | 搜索增强/批量操作单元测试未补齐（~33 场景） |
| 8 | planned | — | R027 | 导出/反馈追踪单元测试未补齐（~22 场景） |

### 调查结论

**A4 deps.py 私有属性访问（11 处）：**
- Neo4jClient._driver（6 处 sync_service + 1 处 knowledge_service）→ 需加 is_connected
- QdrantClient._client（3 处 sync_service）→ 需加 is_connected
- ReviewService._goal_service/_knowledge_service（2 处 deps.py）→ 需加 getter
- entries.py 调用 _get_markdown_storage()/_get_file_path() → 需改为公共方法
- notification_service.py 调用 _sqlite._get_conn() → 需改为公共方法

**TD10 503 降级：**
- 仅 Tasks.tsx 完整实现（store 标记 + 组件渲染 + 重试）
- Home/Review/Explore/EntryDetail/GraphPage/GoalsPage/GoalDetail 缺失
- 最佳方案：提取 useServiceUnavailable 共享 hook

**A2-partial get_growth_curve：**
- list_entries(limit=10000) 全量加载后 Python 内存过滤
- 可用单条 SQL 按 ISO 周 + tag 分组聚合替代
- sqlite.py 已有 get_tag_stats_for_knowledge_map 的 SQL 模式可复用

**A5 页面拆分：**
- EntryDetail.tsx 1201 行（25+ useState, 3 组件）→ 优先级最高
- Home.tsx 730 行（4 组件, 15 useState）
- Explore.tsx 729 行（130 行工具函数 + 主组件）
- Review.tsx 525 行、Tasks.tsx 381 行
- GoalsPage.tsx 338 行、GoalDetail.tsx 330 行（ProgressRing 重复定义需去重）

**H10 移动端拖拽：**
- Flutter mobile/ 目录已确认存在
- 需要为任务列表添加长按拖拽排序

**F-017 review_service：**
- 当前 1845 行，B95 已拆出模型到 models/review.py
- 可进一步按方法组拆分（导出、图谱统计等）

## 任务拆解

| Phase | ID | 名称 | 优先级 |
|-------|-----|------|--------|
| P1 | B100 | 消除私有属性访问 | P1 |
| P1 | B101 | get_growth_curve SQL 聚合 | P1 |
| P2 | B102 | review_service 进一步拆分 | P2 |
| P3 | F128 | 503 降级共享 hook + 7 页接入 | P1 |
| P4 | F129 | EntryDetail.tsx 拆分 | P1 |
| P4 | F130 | Home.tsx + Explore.tsx 拆分 | P2 |
| P4 | F131 | Review + Tasks + Goals 拆分去重 | P3 |
| P5 | M100 | 移动端拖拽排序 | P3 |
| P6 | S33 | R032 + R027 测试覆盖补齐 | P2 |
| P6 | S34 | 质量收口 | P2 |

## 决策

- workflow: B/codex_plugin/skill_orchestrated
- branch: chore/R036-residual-cleanup
- B102 依赖 B101（共享 review_service.py）
- S33 依赖所有结构性改动完成后再补测试
