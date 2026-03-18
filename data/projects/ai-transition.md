# 项目清单

> 所有长期项目及其进度跟踪

---

## 进行中的项目

### 客户端 → AI 应用开发工程师转型

| 属性 | 内容 |
|------|------|
| 开始日期 | 2025-03-01 |
| 当前阶段 | 第一阶段（Week 2 - MCP + FastAPI）|
| 目标 | AI 应用开发工程师 |
| 预计周期 | 8周核心 + 持续优化 |

#### 阶段规划（整合 CS146S 完整内容）

| 阶段 | 周期 | AI 应用开发（主线） | AI 辅助开发（CS146S）| 状态 |
|------|------|-------------------|---------------------|------|
| 第一阶段 | 4周 | Prompt + RAG基础 + MCP | Week 1-4 | **进行中（Week 2）** |
| 第二阶段 | 2周 | 项目一（知识库助手）⭐RAG深度 | Week 5-6 并行 | 未开始 |
| 第三阶段 | 2周 | Agent + 项目二 | Week 7-8 并行 | 未开始 |
| 第四阶段 | 1周 | 简历 + 部署 + 总结 | 整合总结 | 未开始 |

> **双线并行**：主线做 AI 应用（RAG/Agent），辅线学 AI 辅助开发（Claude Code/安全/审查）

#### CS146S 课程完整整合

| CS146S 周次 | 内容 | 整合方式 | 你的计划周次 |
|------------|------|---------|-------------|
| Week 1 | Prompt Engineering | ✅ 核心基础 | Week 1 |
| Week 2 | LLM Integration | ✅ FastAPI + LLM | Week 2 |
| Week 3 | MCP Server | ✅ MCP 协议 | Week 2 |
| Week 4 | Claude Code | ✅ AI IDE 深度使用 | Week 3-4 |
| Week 5 | Warp | ⚠️ 了解即可 | Week 5-6 并行 |
| Week 6 | Semgrep | ✅ 安全扫描 | Week 5-6 并行 |
| Week 7 | Graphite | ✅ AI 代码审查 | Week 7-8 并行 |
| Week 8 | Bolt.new | ⚠️ 快速原型 | Week 7-8 并行 |

#### 第一阶段详细计划（第1-3周）- 打基础

**目标**：掌握 AI 应用开发的基础技能

**第1周：Prompt 工程（CS146S Week 1）** ✅ 已完成
- [x] Day 1：Prompt 基础与结构化设计（API 调通）
- [x] Day 2：Tool Calling ← `planToAiDevelper/tool_calling.py` ✅
- [x] Day 3：CoT、Few-shot 深入
- [x] Day 4：Self-Consistency 多次采样 + 多数投票 ← `planToAiDevelper/self_consistency.py`
- [x] Day 5：Reflexion 自我反思 + RAG Demo ← `planToAiDevelper/reflexion.py`, `planToAiDevelper/personal_rag.py`

**第2周：MCP + FastAPI + LLM 集成** 🔄 进行中

*主线（AI 应用开发）*：
- FastAPI 基础与实战
- MCP 协议入门与实践
- FastAPI + LLM 封装

*CS146S 整合*：
- Week 2: LLM Integration → 结构化输出、流式响应
- Week 3: MCP Server → 完成 MCP Server 作业

*学习资源*：
- CS146S Week 2-3 作业：`modern-software-dev-assignments/week2/`, `week3/`
- MCP 官方文档：https://modelcontextprotocol.io/
- FastAPI 官方教程：https://fastapi.tiangolo.com/zh/

---

**Day 1：FastAPI 入门 + CS146S Week 2 开篇**

*学习目标*：
- 理解 FastAPI 基本概念和优势
- 能创建简单的 API 服务
- 了解 CS146S Week 2 的整体结构

*任务清单*：
- [ ] 安装 FastAPI 和 Uvicorn：`pip install fastapi uvicorn`
- [ ] 创建第一个 FastAPI 应用
  - [ ] Hello World 接口
  - [ ] 路由参数和查询参数
  - [ ] 请求体（Pydantic 模型）
- [ ] 阅读 CS146S Week 2 README，了解本周目标
- [ ] 运行自动文档（Swagger UI）：`/docs`

*产出物*：
- `planToAiDevelper/fastapi_demo.py` - 基础 API 示例

*预计时间*：3-4 小时

---

**Day 2：FastAPI 进阶 + 结构化输出**

*学习目标*：
- 掌握 FastAPI 的依赖注入
- 理解 LLM 结构化输出的重要性
- 实现第一个 LLM + FastAPI 集成

*任务清单*：
- [ ] FastAPI 进阶特性
  - [ ] 依赖注入（Depends）
  - [ ] 响应模型（response_model）
  - [ ] 错误处理（HTTPException）
- [ ] CS146S Week 2 - 结构化输出
  - [ ] 使用 Pydantic 定义输出格式
  - [ ] 让 LLM 返回结构化 JSON
- [ ] 创建 `/chat` 接口，调用大模型

*产出物*：
- `planToAiDevelper/llm_api.py` - LLM API 服务

*预计时间*：3-4 小时

---

**Day 3：流式响应 + 对话历史管理（基础）**

*学习目标*：
- 理解流式响应（Streaming）的原理和优势
- 实现 SSE（Server-Sent Events）
- 理解对话历史管理的基本概念

*任务清单*：
- [ ] 理解流式响应 vs 普通响应
- [ ] 实现流式聊天接口
  - [ ] 使用 `StreamingResponse`
  - [ ] SSE 格式：`data: {content}\n\n`
- [ ] CS146S Week 2 - 流式输出练习
- [ ] 对话历史管理（内存版）
  - [ ] 理解 messages 数组结构
  - [ ] 实现简单的会话历史存储

*产出物*：
- `planToAiDevelper/llm_stream_api.py` - 流式 LLM API

*预计时间*：3-4 小时

---

**Day 4：MCP 协议概念理解**

*学习目标*：
- 理解 MCP（Model Context Protocol）是什么
- 了解 MCP 的核心概念：Resources、Tools、Prompts
- 区分 STDIO 和 HTTP 两种传输方式

*任务清单*：
- [ ] 阅读 MCP 官方文档 Introduction
- [ ] 理解 MCP 架构
  - [ ] Host（宿主应用，如 Claude Desktop）
  - [ ] Client（客户端）
  - [ ] Server（工具提供者）
- [ ] 理解 MCP 核心能力
  - [ ] Resources：文件、数据源
  - [ ] Tools：可调用的函数
  - [ ] Prompts：预定义提示词
- [ ] 安装 MCP SDK：`pip install mcp`
- [ ] 运行官方示例 Server

*产出物*：
- `planToAiDevelper/mcp_notes.md` - MCP 学习笔记

*预计时间*：3-4 小时

---

**Day 5：CS146S Week 3 - 完成 MCP Server 作业**

*学习目标*：
- 完成课程作业
- 理解 MCP Server 的完整实现流程

*任务清单*：
- [ ] 完成 CS146S Week 3 作业
  - [ ] 阅读 `week3/` README
  - [ ] 实现要求的 MCP Server
  - [ ] 测试通过
- [ ] 理解 STDIO 传输方式的实现
- [ ] 用 Claude Desktop 测试自己的 MCP Server

*产出物*：
- `modern-software-dev-assignments/week3/` 作业完成

*预计时间*：4-5 小时

---

**Day 6：实战 - 写一个实用的 MCP Server**

*学习目标*：
- 独立开发一个完整的 MCP Server
- 解决实际问题

*任务清单*：
- [ ] 选择一个实用场景（二选一）：
  - [ ] **文件搜索工具**：搜索指定目录下的文件
  - [ ] **代码片段工具**：读取和管理代码片段
- [ ] 实现 MCP Server
  - [ ] 定义 Tools
  - [ ] 实现核心逻辑
  - [ ] 添加错误处理
- [ ] 在 Claude Desktop 中配置并测试
- [ ] 记录使用效果

*产出物*：
- `planToAiDevelper/mcp_servers/file_search/` - 文件搜索 MCP Server
- 或 `planToAiDevelper/mcp_servers/code_snippets/` - 代码片段 MCP Server

*预计时间*：4-5 小时

---

**Day 7：本周总结 + 整合练习**

*学习目标*：
- 巩固本周所学
- 整合 FastAPI + MCP

*任务清单*：
- [ ] 复盘本周学习内容
  - [ ] FastAPI 核心概念
  - [ ] MCP 协议理解
  - [ ] 遇到的问题和解决方案
- [ ] 整合练习
  - [ ] 用 FastAPI 提供 MCP Server 的 HTTP 接口
  - [ ] 或写一篇技术博客
- [ ] 更新 `notes.md` 学习笔记
- [ ] Git 提交本周代码

*产出物*：
- 本周学习总结（更新到 `notes.md`）
- 所有代码已提交到 Git

*预计时间*：2-3 小时

---

**本周产出清单**：

| 产出物 | 文件路径 | 状态 |
|--------|----------|------|
| FastAPI 基础 Demo | `planToAiDevelper/fastapi_demo.py` | [ ] |
| LLM API 服务 | `planToAiDevelper/llm_api.py` | [ ] |
| 流式 LLM API | `planToAiDevelper/llm_stream_api.py` | [ ] |
| MCP 学习笔记 | `planToAiDevelper/mcp_notes.md` | [ ] |
| CS146S Week 3 作业 | `modern-software-dev-assignments/week3/` | [ ] |
| 实用 MCP Server | `planToAiDevelper/mcp_servers/` | [ ] |

**第3周：RAG 基础 + Claude Code 深度使用**

> ⚠️ 注意：本周 RAG 只需建立基础认知，深度学习放在项目一（Week 4-5）

*主线（AI 应用开发）*：
- RAG 概念与实践（跑通 demo 即可）
- 向量数据库（会用就行）
- LlamaIndex 入门（知道流程即可）

*CS146S 整合*：
- Week 4: Claude Code → Slash Commands、SubAgents、CLAUDE.md

*学习资源*：
- CS146S Week 4 作业：`modern-software-dev-assignments/week4/`
- LlamaIndex 官方文档：https://docs.llamaindex.ai/
- ChromaDB 文档：https://docs.trychroma.com/

*每日任务*：
- [ ] Day 1：RAG 概念理解（为什么需要 RAG）
- [ ] Day 2：文档加载 + 分块（知道有这回事就行，优化留到项目一）
- [ ] Day 3：Embedding 向量化 + ChromaDB（能用即可）
- [ ] Day 4：LlamaIndex 基础（跑通完整流程即可）
- [ ] Day 5：**上下文工程 + 模型记忆** ⭐ 新增
- [ ] Day 6：CS146S Week 4 - Claude Code Slash Commands
- [ ] Day 7：CS146S Week 4 - SubAgents 实践 + CLAUDE.md 配置

**Day 5：上下文工程 + 模型记忆** ⭐ 新增

*学习目标*：
- 理解上下文窗口限制及应对策略
- 掌握对话历史管理的高级技巧
- 了解记忆系统的设计模式

*任务清单*：
- [ ] **上下文工程**
  - [ ] 理解 Token 计算和上下文窗口限制
  - [ ] 对话历史截断策略（保留最近 N 轮 / 滑动窗口）
  - [ ] 上下文压缩和摘要技术
  - [ ] System Prompt 的位置和作用
- [ ] **模型记忆**
  - [ ] 短期记忆：会话级对话历史管理
  - [ ] 长期记忆：持久化存储方案
  - [ ] LangChain Memory 组件介绍
  - [ ] 记忆检索：从历史中找到相关信息
- [ ] **实践**
  - [ ] 实现一个带记忆的聊天机器人
  - [ ] 测试长对话场景

*产出物*：
- `planToAiDevelper/context_memory.py` - 上下文和记忆管理
- `planToAiDevelper/chat_with_memory.py` - 带记忆的聊天 Demo

*预计时间*：4-5 小时

*产出*：
- 能跑通的 RAG demo（不需要优化）
- 带记忆的聊天机器人 Demo
- Claude Code 自动化工作流

**阶段产出**：
- 熟练使用 Claude Code 进行开发
- 理解 RAG 基本原理（深度优化在项目一）
- 能调用大模型 API

**CS146S 资源使用**：
- ✅ Week 1 作业：`week1/` Prompt 工程（已完成部分）
- ✅ Week 2 作业：`week2/` LLM 集成
- ✅ Week 3 作业：`week3/` MCP Server
- ✅ Week 4 作业：`week4/` Claude Code 自动化
- ⚠️ Week 5 作业：`week5/` Warp（了解即可）
- ✅ Week 6 作业：`week6/` Semgrep 安全扫描
- ✅ Week 7 作业：`week7/` Graphite 代码审查
- ⚠️ Week 8 作业：`week8/` Bolt.new（体验即可）

#### 第二阶段详细计划（第4-5周）- 个人成长助手 MVP

**目标**：完成个人成长助手核心功能，MCP Server 可用

*主线（项目一：个人成长助手）*：
- Markdown 存储层
- SQLite 索引
- MCP Server（核心差异化）
- 基础 RAG 检索

*CS146S 整合*：
- Week 5: Warp → 了解终端 AI（可选）
- Week 6: Semgrep → 安全扫描实践

*每日任务*：

**第4周：MCP Server + 存储层**
- [ ] Day 1：项目结构重构（data/ 目录、Markdown 格式规范）
- [ ] Day 2：SQLite 索引表设计和实现
- [ ] Day 3：Markdown 文件解析器（YAML front matter）
- [ ] Day 4：MCP Server 开发 - list_entries, get_entry, create_entry
- [ ] Day 5：MCP Server 开发 - update_entry, delete_entry, search_entries
- [ ] Day 6：Claude Desktop 集成测试
- [ ] Day 7：本周进度检查 + 文档

**第5周：RAG 检索 + 记忆系统 + 前端对接**
- [ ] Day 1：ChromaDB 集成（向量化存储）
- [ ] Day 2：语义搜索实现
- [ ] Day 3：LLM 解析服务（自然语言 → 结构化）
- [ ] Day 4：**记忆系统实现** ⭐ 上下文工程实战
  - [ ] 用户偏好存储（长期记忆）
  - [ ] 对话历史持久化
  - [ ] 上下文窗口管理（Token 限制处理）
- [ ] Day 5：前端对接（React + 已有组件）
- [ ] Day 6：CS146S Week 5 - Warp 终端 AI（了解即可）
- [ ] Day 7：本地测试 + Demo 录制

*产出*：
- 可用的 MCP Server（Claude Code 可操作）
- 基础 RAG 检索功能
- **记忆系统**（用户偏好 + 对话历史）⭐
- 前后端联调完成

#### 第三阶段详细计划（第6-7周）- Agent 项目 + 个人成长助手完善

**目标**：完成多工具 Agent，同时完善个人成长助手

*主线（项目二：多工具 Agent）*：
- Agent 概念理解
- LangChain Agent 实践
- 多工具编排

*并行（个人成长助手）*：
- 时间统计
- AI 问答
- 部署上线

*CS146S 整合*：
- Week 6: Semgrep → 安全扫描实践
- Week 7: Graphite → AI 代码审查

*每日任务*：

**第6周：Agent 基础 + 安全扫描**
- [ ] Day 1：Agent 概念理解（ReAct、Plan-and-Execute）
- [ ] Day 2：LangChain Agent 入门
- [ ] Day 3：自定义 Tool 封装
- [ ] Day 4：CS146S Week 6 - Semgrep 安全扫描
- [ ] Day 5：用 Semgrep 扫描两个项目，修复安全问题
- [ ] Day 6：Tavily 搜索工具实现
- [ ] Day 7：本周总结 + 个人成长助手时间统计功能

**第7周：Agent 项目 + 代码审查 + 部署**
- [ ] Day 1：Python REPL 工具 + 多工具编排
- [ ] Day 2：Gradio 前端开发
- [ ] Day 3：CS146S Week 7 - Graphite AI 代码审查
- [ ] Day 4：Agent 项目部署 + Demo
- [ ] Day 5：个人成长助手部署（Railway + Vercel）
- [ ] Day 6：CS146S Week 8 - Bolt.new 快速原型体验
- [ ] Day 7：两个项目 Demo 视频

*产出*：
- **个人成长助手**（GitHub + 在线 Demo）- MCP Server 可用
- **多工具 Agent**（GitHub + 在线 Demo）- Agent 能力展示
- 安全扫描报告（面试加分项）

#### 第四阶段详细计划（第8周）- 求职准备

**目标**：整理简历，项目部署

*每日任务*：
- [ ] Day 1：个人成长助手 README 完善（技术栈、架构图、MCP 演示）
- [ ] Day 2：多工具 Agent README 完善
- [ ] Day 3：录制两个项目的 Demo 视频
- [ ] Day 4：简历优化（突出 9 年经验 + AI 新技能 + MCP 开发能力）
- [ ] Day 5：整理面试题（RAG、Agent、MCP、Prompt、安全）
- [ ] Day 6：模拟面试 + 项目难点梳理
- [ ] Day 7：项目整理 + 总结

*面试亮点*：
- **个人成长助手**（完整商业级项目 + MCP Server）
- **多工具 Agent**（Agent 编排能力）
- **MCP Server 开发**（市场稀缺，独一份）
- **RAG 系统**（语义搜索实现）
- **上下文工程 + 记忆系统**（长对话处理能力）⭐
- **Claude Code 熟练使用**（AI 辅助开发）
- **安全意识**（Semgrep 扫描经验）

#### 时间线总览（最终版）

```
         AI 应用开发（主线）              AI 辅助开发（CS146S）
         ─────────────────              ─────────────────
Week 1   Prompt 工程                   Week 1: Prompt ✅
Week 2   MCP + FastAPI                 Week 2-3: LLM + MCP
Week 3   RAG + 上下文工程⭐ + Claude    Week 4: Claude Code
Week 4   个人成长助手-MCP Server       Week 6: Semgrep 安全
Week 5   个人成长助手-RAG+记忆⭐       Week 5: Warp（了解）
Week 6   Agent基础+个人助手完善        Week 7: Graphite 审查
Week 7   Agent项目+部署                Week 8: Bolt.new
Week 8   求职准备                      整合总结
```

#### 岗位能力匹配

| 岗位要求 | 学习阶段 | 状态 |
|---------|---------|------|
| Python + FastAPI | Week 2 | ✅ |
| 大模型 API 调用 | Week 1 | ✅ |
| Prompt 工程 | Week 1 | ✅ |
| **上下文工程** | Week 3 Day 5 | ✅ |
| **模型记忆** | Week 3 Day 5 + 项目实践 | ✅ |
| RAG 系统 | 项目一 | ✅ |
| Agent 开发 | 项目二 | ✅ |
| **AI 辅助开发** | CS146S 全程 | ✅ |
| **安全意识** | Week 6 Semgrep | ✅ |

#### 技能地图

```
AI 应用开发工程师技能
├── AI 应用能力（主线）
│   ├── Python + FastAPI      → Week 2
│   ├── 大模型 API 调用       → Week 1
│   ├── Prompt 工程           → Week 1
│   ├── 上下文工程 + 记忆     → Week 3 Day 5 ⭐ 新增
│   ├── RAG 系统              → 项目一
│   └── Agent 开发            → 项目二
│
├── AI 辅助开发（CS146S）
│   ├── Claude Code 熟练      → Week 3-4
│   ├── MCP Server 开发       → Week 2
│   ├── 安全扫描（Semgrep）   → Week 5-6
│   └── AI 代码审查           → Week 6-7
│
├── 加分
│   ├── 前端/移动端           → 工程经验
│   └── 快速原型能力          → Week 7 Bolt.new
│
└── 不需要
    ├── 模型训练              → 应用岗不要求
    ├── 论文发表              → 应用岗不要求
    └── 硕士学历              → 社招看重经验
```

#### 每日检验清单

- [ ] 今天是否用了 AI 辅助开发？
- [ ] 是否有代码产出或文档进展？
- [ ] 是否理解今天学的内容？（能复述/实践）
- [ ] 遇到的问题是否解决了？

#### 推荐资源

**CS146S 相关**：
- 课程官网：[themodernsoftware.dev](https://themodernsoftware.dev)
- 作业仓库：[GitHub](https://github.com/mihail911/modern-software-dev-assignments)
- PPT 和阅读材料（官网公开）

**其他资源**：
- OpenAI / Claude API 文档
- LangChain / LlamaIndex 官方文档
- DeepLearning.AI 短期课程

#### 实战项目规划

> 两个核心项目，证明 RAG 和 Agent 能力

---

## 项目一：个人成长助手（第4-7周完成）⭐ 核心项目

> **口号**：过程属于自己
>
> **品牌故事**：在 AI 时代，你的工作成果属于公司，但你的成长过程、学习笔记、决策思考——这些才是真正属于你的财富。

### 产品定位

| 维度 | 内容 |
|------|------|
| **目标用户** | 知识工作者、终身学习者、AI 工具使用者 |
| **核心价值** | 记录成长，掌控数据 |
| **商业模式** | 免费基础版 + AI 功能付费（¥29-49/月） |

### 差异化卖点

| 卖点 | 说明 | 竞品对比 |
|------|------|---------|
| **本地 Markdown 存储** | 数据透明，用户可直接编辑 | Mem/Reflect 是黑盒 |
| **原生 MCP 支持** | Claude Code/Cursor 可直接操作数据 | 独一份 |
| **AI First** | 自动整理、智能检索 | 国内产品 AI 弱 |
| **个人成长场景** | 任务+笔记+项目+决策闭环 | 通用笔记无此场景 |

### 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户可见/可编辑                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Markdown 文件（Source of Truth）               │   │
│  │  - projects/ai-transition.md                    │   │
│  │  - tasks/2026-03-12.md                          │   │
│  │  - notes/rag-learning.md                        │   │
│  │  - decisions/choose-framework.md                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓ 解析/索引
┌─────────────────────────────────────────────────────────┐
│                    系统索引（用户不可见）                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ SQLite 索引   │  │ ChromaDB     │  │ 概念标签表   │  │
│  │ (元数据查询)  │  │ (向量检索)   │  │ (知识关联)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                          ↑ MCP 协议
┌─────────────────────────────────────────────────────────┐
│                    AI 工具集成                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Claude Code  │  │ Cursor       │  │ Codex        │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 核心功能

| 功能模块 | 说明 | 优先级 |
|---------|------|--------|
| **自然语言输入** | 说出想法，AI 自动解析分类 | MVP |
| **语义搜索（RAG）** | "上周关于 RAG 的笔记" | MVP |
| **项目/任务管理** | 任务归属项目，进度追踪 | MVP |
| **时间统计** | 时间花在哪了 | MVP |
| **MCP Server** | AI 工具直接操作数据 | MVP ⭐ |
| **决策记录** | 为什么选 A 不选 B | 增强 |
| **AI 问答** | "我这周干了啥" | 增强 |
| **知识关联** | 概念标签，关联推荐 | 增强 |

### 数据模型

**Markdown 文件格式**：
```markdown
---
id: proj-001
type: project
status: doing
priority: high
created_at: 2026-03-01
tags: [AI, 转型]
related: [note-001, task-015]
---

# AI 应用开发转型

## 目标
8周内转型为 AI 应用开发工程师

## 当前状态
- Week 2 进行中
...
```

**SQLite 索引表**：
- `entries` - 主索引（id, type, status, file_path）
- `tags` - 标签表
- `entry_tags` - 条目-标签关联
- `relations` - 知识图谱关联

### 技术栈

| 层级 | 技术选型 |
|------|---------|
| 后端 | FastAPI + Python 3.11 |
| 存储 | Markdown + SQLite + ChromaDB |
| MCP | mcp SDK（Python） |
| 前端 | React + TypeScript + shadcn/ui |
| LLM | OpenAI 兼容 API（通义千问/DeepSeek） |

### 开发计划（Week 4-7）

| 周次 | 目标 | 产出 |
|------|------|------|
| Week 4 | MCP Server + 基础存储 | 可读写 Markdown 文件 |
| Week 5 | RAG 检索 + AI 解析 | 语义搜索可用 |
| Week 6 | 前端完善 + 时间统计 | 可演示版本 |
| Week 7 | 优化 + 部署 | 上线 + Demo |

### GitHub 仓库

`personal-growth-assistant`（已有基础结构）

---

## 项目二：多工具协作 Agent（第8周完成）

> 作为面试展示的补充项目，重点展示 Agent 编排能力

| 属性 | 内容 |
|------|------|
| 类型 | Agent 应用 |
| 周期 | 1 周 |
| 面试价值 | 证明 Agent 能力 |

**核心功能**：
- 联网搜索（Tavily API）
- 代码执行（Python REPL）
- 多工具编排

**技术栈**：
- 框架：LangChain Agent
- 工具：Tavily API、Python REPL
- 前端：Gradio
- 模型：GPT-4o / Claude

**GitHub 仓库**：`multi-tool-agent`

---

#### 里程碑节点

| 节点 | 时间 | 交付物 |
|------|------|--------|
| M1 | 第 3 周末 | 基础技能完成 |
| M2 | 第 5 周末 | 项目一完成 |
| M3 | 第 7 周末 | 项目二完成 |
| M4 | 第 8 周末 | 项目完成 |

---

## 已完成的项目

| 项目 | 完成日期 | 成果 |
|------|----------|------|
| 个人成长管理系统 | 2025-03-01 | Claude Code 记录机制搭建 |

---

## 未来计划的项目

> 想做但尚未开始

- 待补充...
