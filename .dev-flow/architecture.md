# 架构文档

> 项目：personal-growth-assistant | 版本：v0.39.0 | 更新：2026-04-26

## 系统总览

```
FastAPI 后端 (routers/services/infrastructure/graphs) ──SDK──> log-service (FastAPI+SQLite)
React 前端 (pages/stores)   │                                 logs-ui (React SPA)
Flutter 移动端 (lib/, MVVM) │
```
协议：HTTP REST (JSON)，不使用 gRPC，不依赖外部消息队列。

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
├── routers/             # entries, search, knowledge, intent, parse, review, chat
├── services/            # sync_service, entry_service, ai_chat_service
│   └── review/          # R037: review 子模块 (insights.py, morning_digest.py)
├── infrastructure/      # storage/, llm/
├── graphs/              # task_parser_graph (LangGraph)
├── models/              # Task, Category, Status
└── mcp/                 # MCP Server (14 Tools)
```

### R037 新增

**note_references 表**：source_id (TEXT), target_id (TEXT), user_id (TEXT) — 存储笔记双向引用关系，由 MarkdownStorage 解析 `[[id]]` 语法时写入。

**新增端点**：
- `GET /entries/{id}/backlinks` — 返回引用当前条目的其他条目列表
- `GET /entries?due=today` — 过滤今日截止条目
- `GET /entries?due=overdue` — 过滤已逾期条目

## 关键设计模式

| 模式 | 说明 |
|------|------|
| 依赖注入 | deps.py 全局变量 + getter + get_current_user |
| 存储工厂 | StorageFactory 按 user_id 创建隔离存储实例 |
| LangGraph | AsyncSqliteSaver + thread_id 会话隔离 + SSE 流式 |
| OpenAPI 同步 | 后端 schema → openapi-typescript → 前端类型 |

## 前端结构

```
frontend/src/
├── pages/          # Home, Tasks, Projects, Notes, Inbox, Review, EntryDetail
├── stores/         # Zustand (chatStore, taskStore)
├── lib/dueDate.ts  # R037: 截止日期工具函数
└── types/          # TypeScript (含 OpenAPI 生成)
```

## Flutter 移动端（R024）

| 维度 | 方案 |
|------|------|
| 框架 | Flutter (iOS + Android) |
| 状态管理 | Riverpod |
| 网络层 | Dio + SSE 客户端 |
| 路由 | go_router |
| 本地存储 | flutter_secure_storage (JWT) |
| 认证 | JWT Bearer，与 Web 端共享 |

MVVM：View → ViewModel(Riverpod) → Model(Services+API)。**禁止**：Widget 调 ApiClient；Provider 含 UI 导航；页面间传对象；Provider 持可变 List；多 Provider 监听同一 SSE。设计约束：纯 API 消费层；4 Tab 底栏（今天/日知/探索/任务）；AI 对话核心；零摩擦输入；MVP 无本地缓存。例外：搜索历史使用内存 List<String> 存储（会话级生命周期），MVP 阶段不引入 SharedPreferences 等本地持久化依赖。

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / Pydantic |
| 存储 | SQLite（默认）/ Neo4j / Qdrant |
| Web 前端 | React 18 / Tailwind / Vite / Zustand |
| 移动端 | Flutter / Riverpod / Dio / go_router |
| LLM | LangGraph / LangSmith |
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
