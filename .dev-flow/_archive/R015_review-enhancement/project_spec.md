# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.12.0

## 目标

- R015 回顾增强 — 升级回顾页数据质量和可视化，让用户更清晰地看见成长轨迹

## 前置依赖（R001-R014 已完成）

- 条目 CRUD、分类管理、搜索（R001-R004）
- 知识图谱 + 图谱可视化（R005-R008）
- 认证隔离 + 用户数据隔离（R002, R009）
- 条目关联 + 知识上下文 + AI晨报（R011）
- 目标追踪闭环（R012）
- 月报 AI 总结 + 决策/复盘/疑问条目类型（R013）
- 页面级上下文 AI + 快捷建议 Chips（R014）
- 回顾页基础功能：日报/周报/月报、趋势折线图、成长曲线、知识热力图、活动热力图

## 现有基础设施

### 已完成（回顾页）

- `GET /review/trend` 趋势数据 API（TrendPeriod: total/completed/completion_rate/notes_count）
- `GET /review/knowledge-heatmap` 知识热力图 API（从 SQLite tags 提取概念）
- `GET /review/growth-curve` 成长曲线 API（按周统计概念数量）
- `GET /review/morning-digest` 晨报 API（AI 建议、待办、过期、连续天数）
- `GET /review/activity-heatmap` 活动热力图 API
- Review.tsx 四标签页：日报/周报/月报/趋势
- recharts 图表库已安装（LineChart + AreaChart）
- Neo4j `get_all_concepts_with_stats()` 已有但 review 未使用

### 需增强

1. 趋势数据仅单维度（completion_rate），TrendPeriod 有 notes_count 但未在前端渲染
2. 知识热力图用 SQLite tags，数据质量不如 Neo4j 概念数据
3. 晨报 API 已实现但未在 Review 页展示
4. 掌握度计算仅基于 entry_count，未利用概念关系数据

## 范围

### 包含

- B52: 后端趋势数据多维扩展 + 周环比对比
- B53: 后端知识热力图 Neo4j 数据源升级
- F40: 前端趋势图多维展示
- F41: 前端知识热力图升级
- F42: 前端晨报集成到回顾日报页

### 不包含

- 知识图谱可视化（@xyflow/react 图谱，留给后续周期）
- 灵感转化率统计（需跟踪 category 变更历史，超出本轮范围）
- Flutter 移动端（第三阶段 Phase 12，需独立周期）
- AI 主动推送完善（第三阶段 Phase 13，需数据积累）

## 用户路径

1. 回顾页 → 趋势标签 → 看到多线图（完成率 + 任务/笔记/灵感数量趋势）→ 直观了解成长节奏
2. 回顾页 → 趋势标签 → 知识热力图显示按类别分组的概念 → 点击查看掌握度详情
3. 回顾页 → 日报标签 → 顶部看到晨报卡片（AI 建议 + 待办 + 过期 + 连续天数）
4. 回顾页 → 周报 → 看到环比对比（↑12% vs 上周）

## 技术约束

- 趋势 API 扩展保持向后兼容（新增字段默认 0）
- 知识热力图 Neo4j 降级到 SQLite tags 必须无缝（try/except）
- recharts 已安装，不引入新图表库
- 晨报卡片样式复用现有 AI 总结卡片的展开/收起模式
- 所有数据操作带 user_id 隔离
