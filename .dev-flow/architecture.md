# 架构文档

> 项目：personal-growth-assistant | 版本：v0.44.0 | 更新：2026-04-28

## 系统总览

```
FastAPI 后端 (routers/services/infrastructure/agent) ──SDK──> log-service (FastAPI+SQLite)
React 前端 (pages/stores)   │                                 logs-ui (React SPA)
Flutter 移动端 (lib/, MVVM) │                                 Langfuse (自部署可观测性)
```
协议：HTTP REST (JSON) + SSE 流式，不使用 gRPC，不依赖外部消息队列。

## 三层存储架构

| 层 | 技术 | 职责 |
|----|------|------|
| Source of Truth | Markdown (.md) | 数据主源，data/users/{user_id}/ |
| 知识图谱 | Neo4j | 概念关系，节点带 user_id |
| 向量检索 | Qdrant | 语义搜索，payload 带 user_id |

SyncService 负责三层同步，所有操作按 user_id 隔离。

## 认证不变量与禁止模式

- 所有数据操作必须携带 user_id（/health 除外）
- JWT secret 必须通过环境变量配置，不硬编码；密码使用 bcrypt 哈希
- **禁止**：前端存储敏感信息；日志记录 token/密码；客户端生成 user_id；refresh_token

## 后端结构

```
backend/app/
├── main.py              # FastAPI 入口 + 生命周期
├── routers/             # entries, search, knowledge, parse, review, feedback, goals
├── services/            # agent_service, sync_service, entry_service, review/
├── agent/               # R044: ReAct Agent (react_agent, tools, prompts, schemas)
├── infrastructure/
│   ├── storage/         # 按领域拆分 (base/entries/goals/feedback/links)
│   └── llm/
├── models/              # Task, Category, Status, Review, Knowledge
└── mcp/                 # MCP Server (14 Tools) — 必须通过 deps 获取 service
```

### 分层不变量

- **调用方向**：`routers/mcp → services → infrastructure`，严格单向
- **Agent 调用链**：`routers → AgentService → ReAct Agent → Tools → Services → Infrastructure`
- **MCP = 另一种 router**：MCP handlers 必须通过 `deps.get_*_service()` 获取 service 实例
- **service 不依赖 router**：service 层禁止 `from app.routers import deps`，依赖通过构造函数/setter 注入
- **Tools 不直接访问 storage**：Tools 封装 service 调用，不绕过 service 层

## 关键设计模式

| 模式 | 说明 |
|------|------|
| 依赖注入 | deps.py 全局变量 + getter + get_current_user |
| 存储工厂 | StorageFactory 按 user_id 创建隔离存储实例 |
| ReAct Agent | LangGraph StateGraph + Agent/ToolNode 循环，循环上限 5 轮，AsyncSqliteSaver 持久化 |
| Tools 模式 | 7 个 Tools 封装 service 调用，Pydantic schema 校验，function calling 驱动 |
| SSE 流式 | thinking/tool_call/tool_result/content/created/updated/error/done 8 种事件 |
| OpenAPI 同步 | 后端 schema → openapi-typescript → 前端类型 |

## 前端结构

```
frontend/src/
├── pages/               # Home, Tasks, Projects, Notes, Inbox, Review, EntryDetail
├── components/AgentChat/ # R044: AgentChat, MessageList, ToolCallCard, ThinkingIndicator
├── components/          # 通用共享组件 (TaskCard, ProgressRing, LinkEntryDialog...)
├── lib/                 # 纯工具函数 (cn, toLocalDateString, getProgressColor...)
├── config/              # 常量配置 (categoryConfig, statusConfig...)
├── stores/              # Zustand (agentStore, taskStore)
├── services/            # API 调用层 (api.ts)
└── types/               # TypeScript (含 OpenAPI 生成)
```

### 前端分层不变量

- **依赖方向**：`pages/ → components/ → lib/`，严格单向；`components/` 禁止 import 任何 `pages/` 下的模块
- **跨页面共享**：当 pages 下的组件被 2 个以上页面使用时，提升到 `components/`
- **API 调用边界**：组件和页面允许直接调用 `services/api.ts`（通过 store 或直接调用均可）；写操作优先通过 store，读操作可直接调用 API
- **类型权威**：后端 OpenAPI schema → `npm run gen:types` → `types/api.generated.ts`，前端不硬编码后端枚举值

## Flutter 移动端

| 维度 | 方案 |
|------|------|
| 框架 | Flutter (iOS + Android) |
| 状态管理 | Riverpod |
| 网络层 | Dio + SSE 客户端 |
| 认证 | JWT Bearer，与 Web 端共享 |

MVVM：View → ViewModel(Riverpod) → Model(Services+API)。**禁止**：Widget 调 ApiClient；Provider 含 UI 导航；页面间传对象；Provider 持可变 List；多 Provider 监听同一 SSE。

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / Pydantic |
| 存储 | SQLite（默认）/ Neo4j / Qdrant |
| Web 前端 | React 18 / Tailwind / Vite / Zustand |
| 移动端 | Flutter / Riverpod / Dio / go_router |
| LLM | LangGraph ReAct / Langfuse |
| 部署 | Docker Compose |

## 环境变量

| 变量 | 用途 |
|------|------|
| LLM_API_KEY / LLM_BASE_URL / LLM_MODEL | LLM 调用 |
| JWT_SECRET / JWT_ALGORITHM / ACCESS_TOKEN_EXPIRE_DAYS | 认证（默认 HS256 / 7天） |
| NEO4J_URI / USERNAME / PASSWORD | 知识图谱 |
| QDRANT_URL / API_KEY | 向量检索 |
| DATA_DIR / FRONTEND_BASE_PATH / LOG_LEVEL | 通用配置 |

## 部署架构

```
Traefik (:80) → /growth/api/* (priority=100) → FastAPI
             → /growth/*    (priority=50)  → StaticFiles
```

- 反馈：后端双写（本地 SQLite + log-service 异步上报），前端 FeedbackButton
- 移动端：独立安装，BaseURL 配置连接后端，复用同一套 FastAPI
- 可观测性：Langfuse 自部署，LangGraph CallbackHandler 接入
