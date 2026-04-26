# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.40.0
> 状态：规划中（R040）
> 活跃分支：feat/R040-web-enhancement

## 当前范围

R040 Web 功能增强 + 工程收口：补齐产品设计分析文档中标注的所有未实现 Web 功能，并清理工程残留项。

### Phase 1: 工程清理（3 tasks）

1. **S40 历史残留清理**：8 个 pending 任务 + 430 条日志服务重复 issue
2. **F155 下拉刷新手势**：PullToRefresh 通用组件 + 3 页面集成
3. **F156 同步重试 UI**：OfflineIndicator 手动同步按钮 + 队列状态

### Phase 2: 任务优先级视图（2 tasks）

4. **B112 后端 priority 筛选/排序 API**：entries 路由 + SQLite 排序
5. **F157 Tasks 页面优先级筛选 UI**：筛选面板 + 排序 + Badge 始终显示

### Phase 3: 目标进度可视化增强（2 tasks）

6. **B113 目标进度历史快照 API**：progress_snapshots 表 + 时间序列端点
7. **F158 目标进度可视化增强**：颜色语义 + 截止日期紧迫性 + 趋势折线图

### Phase 4: 项目里程碑（3 tasks）

8. **B114 里程碑数据模型 + API**：milestones 表 + CRUD + 自动进度计算
9. **F159 里程碑管理 UI**：GoalDetail 里程碑列表 + 创建/完成/删除
10. **F160 甘特图时间线视图**：横向时间轴 + 目标条形 + 里程碑菱形标记

### Phase 5: 知识图谱主动推荐（2 tasks）

11. **B115 知识推荐引擎 + Neo4j 图算法**：缺口检测 + 复习推荐 + 共现推荐 + 晨报集成
12. **F161 图谱推荐 UI + 晨报知识建议**：GraphPage 推荐 Tab + 首页知识建议卡片

### Phase 6: AI 多轮上下文增强（2 tasks）

13. **B116 PageChatPanel 后端持久化 + FloatingChat 上下文窗口截断**
14. **F162 前端持久化集成 + 截断 UI 指示器**

### Phase 7: 质量收口（1 task）

15. **S41 全量测试 + build + Docker smoke**

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 15 |
| P0 | 1（S41 质量收口）|
| P1 | 8 |
| P2 | 6 |

## 技术约束

- 下拉刷新不引入 react-query/SWR，保持现有 fetch+useState 模式
- 甘特图使用纯 CSS/SVG 实现，不引入重量级甘特图库
- 知识推荐 Neo4j 不可用时降级到 SQLite 标签推荐
- AI 上下文截断策略可配置（MAX_MESSAGES, MAX_TOKENS 常量）
- 里程碑进度自动计算，与现有三种度量类型兼容
- workflow: B/codex_plugin/skill_orchestrated
