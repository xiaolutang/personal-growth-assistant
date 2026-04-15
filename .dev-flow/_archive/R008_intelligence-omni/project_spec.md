# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.6.0

## 目标

- R008 智能化 & 全端适配 — 知识图谱增强 + AI 助手内嵌 + MCP 增强 + 移动端适配

## 前置依赖（R001-R007 已完成）

- 知识图谱基础：Neo4j 客户端 + 概念提取 + 图谱 API + GraphPage
- AI 基础：LangGraph 任务解析 + 浮动聊天 + 意图检测
- MCP 基础：11 个工具 + JWT 认证 + 用户隔离
- 响应式基础：Sidebar 抽屉 + MobileNavBar + md: 断点

## 范围

### 包含
- B28: 知识图谱增强 API — 概念搜索 + 时间维度 + 掌握度统计
- B29: MCP 工具增强 — 批量操作 + 降级搜索 + 学习路径（不重复已有 get_knowledge_stats）
- B30: AI 条目摘要 API — 自动生成条目摘要 + 缓存
- B31: 页面级 AI 上下文后端 — ChatRequest 扩展 + prompt 注入
- F27: 知识图谱页增强 — 搜索 + 掌握度卡片 + 概念时间线
- F28: AI 条目摘要 UI — EntryDetail 摘要卡片
- F29: 移动端适配优化 — 导航统一 + 平板布局 + 浮窗协调
- F30: 页面级 AI 上下文前端 — chatStore + 浮动聊天注入

### 不包含
- AI 多轮对话记忆（LangGraph 多节点图扩展）
- MCP 流式响应 / 实时通知
- 知识图谱手动编辑
- 横屏模式适配

## 用户路径

1. 用户在图谱页搜索框输入关键词 → 节点过滤/高亮 → 点击查看概念详情和学习时间线
2. 用户在条目详情页看到 AI 摘要卡片 → 展开查看/收起
3. 用户在任意页面打开浮动聊天 → AI 自动感知当前页面上下文给出针对性回复
4. 用户在平板上使用 → Sidebar 自动收为图标模式 → 聊天面板不遮挡底部导航
5. Claude Code 通过 MCP 批量创建条目、搜索（无 Qdrant 时也能工作）

## 技术约束

- Neo4j 可选：所有图谱功能必须有 SQLite 降级
- LLM 依赖：摘要生成依赖 LLM_API_KEY 配置
- MCP 协议：stdio 传输，环境变量认证
- ReactFlow 性能：>50 节点自动截取
- Tailwind 断点：md=768px, lg=1024px, xl=1280px

## 交付边界

- 后端：3 个新端点（知识图谱搜索/时间线/掌握度）+ 1 个字段扩展（ai_summary）+ ChatRequest page_context 扩展 + 4 个 MCP 新工具/增强
- 前端：GraphPage 增强 + EntryDetail 摘要 + 浮动聊天页面上下文 + 布局优化
- 导航：navConfig.ts（新文件）统一 + Sidebar icon-only 模式
