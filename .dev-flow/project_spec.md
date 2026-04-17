# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.11.0

## 目标

- R014 页面级上下文 AI — 让聊天 AI 感知用户当前所在页面，提供更精准的交互

## 前置依赖（R001-R013 已完成）

- 条目 CRUD、分类管理、搜索（R001-R004）
- 知识图谱 + 图谱可视化（R005-R008）
- 认证隔离 + 用户数据隔离（R002, R009）
- 条目关联 + 知识上下文 + AI晨报（R011）
- 目标追踪闭环（R012）
- 月报 AI 总结 + 决策/复盘/疑问条目类型（R013）
- 聊天意图识别 + SSE 流式对话（R009）
- 探索页、导出、回顾页（R004-R006）

## 现有基础设施

### 已完成

- `PageContext` 模型（backend `parse.py`）：`page_type` / `entry_id` / `extra` 三字段
- `ChatRequest.page_context`：请求级透传
- `chat_service._build_page_context_hint()`：生成基础上下文文本（"用户当前在「X页」"）
- `FloatingChat.tsx` 路由感知：根据 pathname 设置 `pageContext`
- `chatStore.ts` `pageContext` 状态管理
- `useStreamParse.ts` 透传 `page_context` 到 API
- `PageAIAssistant.tsx` 页面数据感知组件（独立于 FloatingChat）

### 需增强

1. `_build_page_context_hint()` 只生成"用户当前在「X页」"，不含业务数据
2. `task_parser_graph.py` 系统提示词固定，不随页面变化
3. `FloatingChat` 不注入页面业务数据到 `pageContext.extra`
4. 无页面级快捷建议 chips

## 范围

### 包含

- B50: 后端页面上下文数据注入（条目详情、今日统计等）
- B51: 后端 LLM 页面感知系统提示词（动态调整解析规则）
- F39: 前端快捷建议 Chips + 探索页上下文注入

### 不包含

- PageAIAssistant 组件改造（独立入口，不在本轮范围）
- 条目详情页内嵌 AI 助手面板
- AI 自动分析当前页面并主动推送建议
- 跨页面对话记忆持久化（已有 session 机制）

## 用户路径

1. 首页 → 打开聊天 → 看到"今日有哪些任务?"建议 → 点击 → AI 返回今日任务列表
2. 条目详情页 → 打开聊天 → 看到"帮我补充内容"建议 → 点击 → AI 理解为更新当前条目
3. 探索页 → 打开聊天 → AI 知道当前在看什么类型的条目 → 建议相关搜索
4. 回顾页 → 打开聊天 → 看到"本周完成率?"建议 → AI 返回统计数据

## 技术约束

- `_build_page_context_hint()` 改为实例方法，利用已有 `entry_service`
- `task_parser_graph.py` 的 `stream_parse()` 新增可选参数，不破坏现有接口
- `PageSuggestions.tsx` 为新组件，集成到 `FloatingChat.tsx`
- 所有改动不涉及新的 API 端点
- 前端遵循现有 Zustand store + api.ts 模式
