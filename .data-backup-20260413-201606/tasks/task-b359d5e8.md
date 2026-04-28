---
id: task-b359d5e8
type: task
title: 聊天→创建任务 API 调用优化
status: complete
priority: medium
created_at: '2026-04-13T16:07:11'
updated_at: '2026-04-13T16:07:11'
tags:
- 个人助手
- API
parent_id: project-ba042be5
---

✅ 2026-03-20
  - 问题：create 意图 2 次请求（/chat + /entries），update/delete 意图 3 次请求
  - 解决：后端 `/chat` 接口一站式处理所有意图
    - create：解析后直接创建，返回 `created` 事件
    - update：搜索后单个直接更新，多个返回 `confirm` 事件
    - delete：搜索后返回 `confirm` 事件（必须确认）
    - read：搜索后返回 `results` 事件
  - 文件：
    - `backend/app/routers/parse.py` - 重构 `_stream_chat_with_intent`
    - `frontend/src/hooks/useStreamParse.ts` - 新增事件处理
    - `frontend/src/components/FloatingChat.tsx` - 简化逻辑

---

## Week 2: MCP + FastAPI + LLM 集成

---

### Day 1：FastAPI 入门 + CS146S Week 2 开篇 ✅

- [x] 安装 FastAPI 和 Uvicorn
- [x] 创建第一个 FastAPI 应用
  - [x] Hello World 接口
  - [x] 路由参数和查询参数
  - [x] 请求体（Pydantic 模型）
- [x] 阅读 CS146S Week 2 README
- [x] 运行自动文档（Swagger UI）

**产出**：`planToAiDevelper/fastapi_demo.py` ✅

---

### Day 2：FastAPI 进阶 + 结构化输出 ✅

- [x] FastAPI 进阶：依赖注入、响应模型、错误处理（学习笔记已完成）
- [x] CS146S Week 2 - TODO 1: LLM 结构化输出（等效实现：`personal-growth-assistant` 的 `TaskParser`）
- [x] CS146S Week 2 - TODO 2: 单元测试（10 个测试用例通过）
- [x] CS146S Week 2 - TODO 3: 代码重构（tests/ 目录规范化）
- [x] CS146S Week 2 - TODO 4: 新端点 + 前端（/parse、/health + React 前端）
- [x] CS146S Week 2 - TODO 5: 生成 README（已更新项目结构）
- [x] `/parse` 端点改造（请求/响应模型 + 错误处理）

**产出**：
- `notes/fastapi-learning-notes.md` - FastAPI 学习笔记
- `personal-growth-assistant/` - 完整项目（后端 + 前端）

---

### Day 3：流式响应（SSE）✅

- [x] 理解流式响应 vs 普通响应
- [x] 理解 SSE 协议原理（HTML5 规范、`\n\n` 分隔符）
- [x] 理解 SSE vs WebSocket 的区别和选型
- [x] 后端：LLMCaller 增加 `stream()` 方法
- [x] 后端：TaskParser 增加 `stream_parse()` 方法
- [x] 后端：`/parse` 端点改造为 SSE，删除 `/chat/stream`
- [x] 前端：新增 `useStreamParse` Hook 和 `ChatBox` 组件
- [x] 前端：流式显示 JSON 解析过程

**产出**：`personal-growth-assistant/` SSE 流式响应功能 ✅

---

### Day 3.5：LangGraph Memory 迁移 ✅

- [x] 理解 LangChain v0.3+ Memory 方案变更（官方推荐 LangGraph Checkpointer）
- [x] 新建 `backend/app/graphs/` 目录
- [x] 创建 `TaskParserGraph` 类（使用 StateGraph + InMemorySaver）
- [x] 修改 `main.py` 使用新的图结构
- [x] 删除旧的 `conversation_store.py`
- [x] 更新 `pyproject.toml` 添加 langgraph 依赖
- [x] 测试多轮对话记忆功能（成功）

**产出**：`personal-growth-assistant/` LangGraph Memory 集成 ✅

---

### Day 4：MCP 协议学习 ✅

- [x] MCP 协议概念理解
  - [x] 阅读 MCP 官方文档
  - [x] 理解 MCP 架构：Host、Client、Server
  - [x] 理解核心能力：Resources、Tools、Prompts
  - [x] 安装 MCP SDK，运行官方示例
  - [x] 理解 MCP 传输方式（stdio、streamable HTTP、SSE）
  - [x] 理解 MCP 协议（JSON-RPC 2.0）
  - [x] 理解 MCP vs Function Calling vs Skill
  - [x] 理解 MCP 断开重连机制
  - [x] 创建 simple_server 实践项目

**产出**：
- `mcp_servers/simple_server/` ✅
- `notes/mcp-learning-notes.md` ✅

---

### Day 4.5：意图识别 + LangGraph 深入（延后）

- [ ] 意图识别
  - [ ] 设计意图分类体系
  - [ ] 实现意图识别服务
- [ ] LangGraph 深入学习
  - [ ] 理解 LangGraph 核心概念（StateGraph, Node, Edge）
  - [ ] 理解 Checkpointer 持久化
  - [ ] 实践：复杂工作流设计

---

### Day 5：CS146S Week 3 - MCP Server 作业

- [ ] 完成 CS146S Week 3 作业
- [ ] 理解 STDIO 传输方式
- [ ] 用 Claude Desktop 测试 MCP Server

**产出**：`modern-software-dev-assignments/week3/` 作业完成

---

### Day 6：实战 - 写一个实用的 MCP Server

- [ ] 选择场景：文件搜索 / 代码片段管理
- [ ] 实现 MCP Server（定义 Tools、实现逻辑）
- [ ] 在 Claude Desktop 中配置并测试

**产出**：`planToAiDevelper/mcp_servers/`

---

### Day 7：本周总结

- [ ] 复盘本周学习内容
- [ ] 更新 `notes.md` 学习笔记
- [ ] Git 提交本周代码

---

## Week 1: Prompt 工程 ✅ 已完成

---

## 2026-03-12（周三）

### 已完成

- [x] Day 3：SSE 流式响应学习
  - [x] 教练模式考核：SSE vs WebSocket、`\n\n` 格式、消息处理
  - [x] 后端：`/parse` 端点改造为 SSE 流式输出
  - [x] 前端：`useStreamParse` Hook + `ChatBox` 组件
  - [x] 测试通过，代码已提交推送
- [x] 确认：CS146S Week 2 内容已在 Day 2 完成，SSE 是额外学习内容
- [x] 对话历史管理（SQLite + 滑动窗口）
  - [x] 新建 `ConversationStore` 模块
  - [x] 修改 `TaskParser` 集成历史消息
  - [x] 修改 API 支持 `session_id`
  - [x] 前端支持 `sessionId` 参数
  - [x] 测试通过：多轮对话历史正确保存

---

## 2026-03-06（周四）

### 已完成

- [x] Day 5：RAG 基础实现
  - [x] 完成 `planToAiDevelper/personal_rag.py`
  - [x] 修复 embedding 模型名称（text-embedding-v3）
  - [x] 测试通过：3个问题全部回答正确
- [x] Week 1 全部完成！

---

## 2026-03-05（周三）

### 已完成

- [x] Day 3：CoT、Few-shot 深入
- [x] Day 4：Self-Consistency 多次采样 + 多数投票
  - [x] 理解核心原理
  - [x] 完成 `planToAiDevelper/self_consistency.py`
  - [x] 测试通过：5次采样全部正确
- [x] Day 4：Reflexion 自我反思
  - [x] 理解核心原理：生成 → 反思 → 改进
  - [x] 完成 `planToAiDevelper/reflexion.py`
  - [x] 区分 Reflexion vs ReAct
- [x] Git 提交学习内容（本地已提交，待 push）

### 已完成（之前）

- [x] Day 2：Tool Calling ✅
  - [x] 理解 Tool Calling 原理
  - [x] 完成 `planToAiDevelper/tool_calling.py`
  - [x] 测试通过：天气查询、数学计算、搜索、普通对话

- [x] 提示词工程学习
  - [x] 学习核心知识（结构化提示词、CoT、Few-shot、XML标签）
  - [x] 生成提示词模版 → `planToAiDevelper/prompt-template.md`
  - [x] Bug分析器 → `planToAiDevelper/bug_analyzer.py`
  - [x] 代码转换器 → `planToAiDevelper/codeAdapter.py`
- [x] 完成离职交接文档
  - [x] PolicyDialog 隐私协议更新提示弹窗逻辑梳理
  - [x] BabyProfileDialog 宝贝档案弹窗逻辑梳理
- [x] Day 1：Prompt 基础与结构化设计（API 调通）

---

## 2026-03-03（周一）

### 今日重点

- [ ] Day 2：Prompt优化与Chain-of-Thought

### 进行中

- [ ] 任务1：代码注释生成器
- [ ] 任务2：Bug 分析器（CoT 实战）
- [ ] 任务3：Python → Kotlin 转换器

### 已完成

（待填写）

---

## 2026-03-02（周日）

### 今日重点

- [ ] Day 2：优化 Prompt，让输出更专业

### 已完成

- [x] 解决跟进伴读的 bug
  - [x] 1.0等待切换到伴读，播放动画时会先看到0等待页面
  - [x] 学习完成后在横版上布局宽度不对
  - [x] 上下滑动时主题穿透
- [x] 梳理账号 SDK 交接内容
  - [x] 账号 SDK：登录、账号管理、账号切换、jwt相关、人机验证
  - [x] 隐私协议弹窗：首页更新提示、启动弹窗
  - [x] 上课页-宝贝档案

---

## 2026-03-01（周六）

### 今日重点

- [ ] Day 2：优化 Prompt，让输出更专业
  - [ ] 设计结构化 Prompt 模板
  - [ ] 测试 3 段不同代码
  - [ ] 输出稳定、格式一致

### 已完成

- [x] 搭建个人成长管理系统
- [x] 整理 projects.md（转型计划）
- [x] 删除 plan.md
- [x] 3天任务 Day 1：调通 API

### 备注

今天完成了两件重要的事：
1. 搭建个人成长管理系统（记录机制）
2. 完成 Day 1：API 调通

明天继续 Day 2：优化 Prompt。
