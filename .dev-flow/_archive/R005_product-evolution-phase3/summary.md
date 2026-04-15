# R005 — 产品演进 Phase 3：差异化能力

## 状态：completed
## 分支：feat/R005-product-evolution-phase3
## 完成时间：2026-04-15

## 范围

Phase 3 交付四大差异化能力：知识图谱独立页（可视化 + 统计 + 掌握度）、回顾增强（AI 总结 + 知识热力图）、AI 助手内嵌（页面级上下文感知）、MCP 终端接入（JWT 认证 + 用户隔离 + 新工具）。

## 任务清单

| ID | 类型 | 模块 | 名称 | 验证级别 |
|----|------|------|------|----------|
| B20 | 后端 | knowledge-graph | 图谱数据 API — 全局图谱 + 概念统计 + 掌握度 | L2 |
| B21 | 后端 | review | AI 总结 + 知识热力图 API | L2 |
| F14 | 前端 | knowledge-graph | 图谱独立页 — @xyflow/react 可视化 + Sidebar 更新 | F2 |
| F15 | 前端 | review | 回顾页增强 — AI 总结卡片 + 知识热力图 | F2 |
| B22 | 后端 | ai-assistant | 页面级上下文 AI API — 上下文感知对话 | L2 |
| F16 | 前端 | ai-assistant | 日知 AI 内嵌组件 — 浮动助手 + 页面上下文 | F2 |
| B23 | 后端 | mcp-terminal | MCP Server 认证增强 — JWT + 用户隔离 + 新工具 | L2 |

## Commit 日志

| Commit | 任务 ID | 摘要 |
|--------|---------|------|
| 04e7530 | B20 | 图谱数据 API — 全局图谱 + 概念统计 + 掌握度 |
| — | B21 | AI 总结 + 知识热力图 API |
| — | F14 | 图谱独立页 — @xyflow/react 可视化 + Sidebar 更新 |
| — | F15 | 回顾页增强 — AI 总结卡片 + 知识热力图 |
| — | B22 | 页面级上下文 AI API — 上下文感知对话 |
| — | F16 | 日知 AI 内嵌组件 — 浮动助手 + 页面上下文 |
| 6e20fed | B23 | MCP Server 认证增强 — JWT + 用户隔离 + 新工具 |

## 关键决策

- 图谱可视化使用已有 @xyflow/react 库，节点按掌握度着色（advanced=绿, intermediate=蓝, beginner=橙, new=灰）
- Sidebar 从 4 项扩展为 5 项：今天/探索/图谱/任务/回顾
- AI 总结调用 LLM 基于日报/周报数据生成自然语言总结，LLM 不可用时降级为空字符串
- AI 助手使用独立 /ai/chat 端点，基于页面上下文注入系统提示词，SSE 流式返回
- MCP Server 新增 JWT 认证，所有工具操作按 user_id 隔离，新增 get_review_summary 和 get_knowledge_stats 工具

## 测试覆盖

- 后端：596 tests passed（B20: 17 新增，B21: 27 review 测试，B22: 6 AI chat 测试，B23: 32 MCP 测试含 18 新增）
- 前端：npm run build 全部通过

## 产品设计对齐

对应 `docs/product-design-analysis.md` 第三阶段规划：

| 规划 Phase | 本周期交付 |
|-----------|-----------|
| Phase 8: 图谱独立页 | B20 + F14 完成 |
| Phase 9: 页面级上下文 AI | B22 + F16 完成 |
| Phase 10: 回顾增强 | B21 + F15 完成 |
| Phase 11: MCP 终端接入 | B23 完成 |

## 三阶段演进总览

至此，产品演进三个阶段全部完成：

| 阶段 | 需求周期 | 核心交付 |
|------|---------|---------|
| Phase 1: 补闭环 | R004 Phase 1A/1B | 首页改版、灵感转化、反馈闭环、趋势回顾 |
| Phase 2: 统一探索 | R004 Phase 2 | Onboarding、探索页、Export 导出、条目关联 |
| Phase 3: 差异化 | R005 Phase 3 | 图谱独立页、AI 总结、日知内嵌、MCP 增强 |

产品设计文档中的 Phase 0-13 已完成 Phase 0-11（Onboarding + 首页改版 + 灵感转化 + 反馈闭环 + 趋势对比 + 探索页 + Export + 条目关联 + 图谱独立页 + AI 内嵌 + 回顾增强 + MCP 终端接入）。

**尚未完成**：
- Phase 12: Flutter 移动端（录入优先 MVP）
- Phase 13: AI 晨报/主动推送
