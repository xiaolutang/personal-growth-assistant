# R024 规划 Session 1

> 日期：2026-04-22
> 主题：Flutter 移动端 MVP 规划

## 需求输入

- 独立代码库，录入优先的移动端应用
- 补齐「随时记录」核心体验
- 录入优先：灵感快记、AI 对话（SSE 流式）
- 轻量浏览：今日任务、最近笔记、简单回顾
- 不做全功能 Web 端移植
- 参考产品设计文档第七节「移动端设计」和 Phase 12

## 运行模式

- workflow.mode = B
- workflow.runtime = skill_orchestrated
- review_provider = codex_plugin
- audit_provider = codex_plugin
- risk_provider = codex_plugin

## 架构校验

- 无架构冲突：Flutter 端是纯 API 消费层，后端不需要改动
- 新增 Flutter 移动端架构 section 到 architecture.md
- 新增设计约束：3 Tab 底栏、录入优先、不做全功能移植

## 任务拆解结果

12 个任务，6 个 Phase：

- Phase 1 Foundation: S11, F99, F100
- Phase 2 Infrastructure + Auth: S12, S13, F101
- Phase 3 Today: F102, F103
- Phase 4 Chat: F104, F105
- Phase 5 Tasks + Detail: F106, F107
- Phase 6 Quality: S14

## 技术选型确认

- Flutter (iOS + Android)
- Riverpod 状态管理
- Dio + 自定义 SSE 客户端
- go_router 路由
- flutter_secure_storage JWT 持久化
- flutter_markdown Markdown 渲染
