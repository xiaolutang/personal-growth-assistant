# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.26.0

## 目标

- R026 收敛修复 — simplify 发现的 5 个残留问题修复

## 前置依赖（R001-R025 已完成）

- AI 深度洞察 API + 洞察卡片（R025 S15, F108）
- 能力地图 API + 视图 + AI 助手（R025 B81, F109, F110）
- AI 总结深度增强（R025 F111）
- 知识图谱完整 API（R005-R008）
- 回顾统计 + 趋势分析（R015）
- 全局错误处理中间件（R017）

## 范围

### 包含（6 个任务）

**Phase 1**（3 项）：S18 统一掌握度算法 + S19 消除 N+1 查询 + B82 错误脱敏
**Phase 2**（2 项）：F112 消除重复请求 + F113 GraphPage 状态拆分
**Phase 3**（1 项）：S20 构建验证

### 不包含

- 移动端改动
- 新功能开发
- 架构重构

## 修复来源

R025 simplify 阶段发现的 5 个收敛问题：

1. **[critical] 掌握度算法不一致**：review_service 使用加权评分式，knowledge_service 使用阈值式
2. **[critical] N+1 查询**：knowledge_service 4 个方法逐概念调用 get_entries_by_concept
3. **[major] 重复 API 请求**：InsightCard + AiSummaryCard 各自独立调用 getInsights
4. **[major] GraphPage 状态膨胀**：18 个 useState 跨 5 个功能域
5. **[major] 错误信息泄露**：knowledge.py 9 个路由直接返回 str(e)

## 技术约束

- 不新建服务文件，在现有文件内修改
- 前端组件拆分在文件内完成，不新建文件
- 验证走标准 Docker 发布流程（./deploy/deploy.sh）
- workflow: B/codex_plugin/skill_orchestrated
