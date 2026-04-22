# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.25.0

## 目标

- R025 第三阶段收口 — Phase 8 图谱增强 + Phase 10 回顾 AI 总结增强

## 前置依赖（R001-R024 已完成）

- 知识图谱 Neo4j 完整 API（R005-R008）
- 回顾统计 + 趋势 + 热力图 + 成长曲线（R015）
- AI 对话 SSE 流式 + 页面感知角色（R014, R023）
- 目标追踪闭环（R012）
- Flutter 移动端 MVP（R024）

## 范围

### 包含（8 个任务）

**Phase 1**（1 项）：S15 AI 深度洞察 API
**Phase 2**（1 项）：F108 AI 深度洞察卡片
**Phase 3**（1 项）：B81 能力地图数据 API
**Phase 4**（1 项）：F109 能力地图视图
**Phase 5**（1 项）：F110 图谱 AI 助手
**Phase 6**（1 项）：F111 AI 总结深度增强
**Phase 7**（2 项）：S16 后端测试收口 + S17 构建验证

### 不包含

- 移动端图谱和回顾增强（V2）
- 数据导出增强（已完成 R004）
- 新用户引导优化（已完成 R004）

## 用户路径

**图谱增强路径**：
- 侧边栏 → 图谱页 → 切换「能力地图」Tab → 浏览按领域聚合的能力概览 → 点击领域展开概念 → AI 助手对话

**回顾增强路径**：
- 侧边栏 → 回顾页 → 切换周报/月报 → 查看 AI 洞察卡片（行为模式+成长建议+能力变化）→ 展开详细总结

## 技术约束

- 后端增强 review_service 和 knowledge_service，不新建服务
- 前端增强 GraphPage 和 Review 页面，复用 PageChatPanel
- workflow: B/codex_plugin/skill_orchestrated
