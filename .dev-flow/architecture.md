# 架构文档

> 项目：log-service（从 personal-growth-assistant 抽取）
> 版本：v0.1.0
> 更新：2026-04-10

## 系统总览

```
personal-growth-assistant          log-service (独立仓库)
┌─────────────────────┐           ┌──────────────────────────┐
│  FastAPI 后端        │           │  FastAPI 服务端           │
│  ├── routers/       │  SDK      │  ├── routers/             │
│  ├── services/      │──────────>│  │   POST /api/logs/ingest│
│  ├── infrastructure/│  HTTP     │  │   GET  /api/logs        │
│  └── graphs/        │  POST     │  │   GET  /api/logs/stats  │
│                     │           │  │   DELETE /api/logs/cleanup│
│  React 前端         │           │  ├── storage/ (SQLite)     │
│  ├── pages/         │           │  └── middleware/            │
│  └── stores/        │           │                             │
└─────────────────────┘           │  logs-ui (React SPA)       │
                                  │  └── service_name 筛选      │
                                  └──────────────────────────┘
```

## 三层存储架构（personal-growth-assistant）

| 层 | 技术 | 职责 |
|----|------|------|
| Source of Truth | Markdown (.md) | 数据主源，data/ 目录 |
| 知识图谱 | Neo4j | 概念关系 |
| 向量检索 | Qdrant | 语义搜索 |

SyncService 负责三层存储的同步。

## log-service 架构

### 服务端

- **框架**: FastAPI + Uvicorn
- **存储**: SQLite（默认），预留扩展接口
- **API**:
  - `POST /api/logs/ingest` - 批量日志写入
  - `GET /api/logs` - 日志查询（支持 service_name 筛选）
  - `GET /api/logs/stats` - 统计（含 count_by_service）
  - `DELETE /api/logs/cleanup` - 过期日志清理
  - `GET /health` - 健康检查

### Python SDK

- **位置**: `log-service/sdks/python/`
- **依赖**: httpx
- **核心类**: `RemoteLogHandler`（logging.Handler 子类）
- **特性**: 内存队列、后台攒批（50条/2秒）、HTTP POST、失败重试（3次）、优雅关闭
- **入口函数**: `setup_remote_logging(endpoint, service_name, level)`

### 前端 (logs-ui)

- **框架**: React 18 + Tailwind CSS + Vite
- **功能**: 日志列表、统计面板、service_name 筛选

## personal-growth-assistant 后端结构

```
backend/app/
├── main.py              # FastAPI 入口 + 生命周期
├── routers/             # API 路由（entries, search, knowledge, intent, parse, review）
├── services/            # 业务服务（sync_service, entry_service, intent_service）
├── infrastructure/      # 基础设施（storage/, llm/）
├── graphs/              # LangGraph 图（task_parser_graph）
├── models/              # 数据模型（Task, Category, Status）
└── mcp/                 # MCP Server（9 个 Tools）
```

## 关键设计模式

| 模式 | 说明 |
|------|------|
| 依赖注入 | deps.py 全局变量 + getter 函数 |
| LangGraph 任务解析 | InMemorySaver + thread_id 会话隔离 + SSE 流式 |
| OpenAPI 类型同步 | 后端 schema → openapi-typescript → 前端类型 |
| 跨项目日志 | log-service 独立部署，各项目通过 SDK 接入 |

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / Pydantic |
| 存储 | SQLite（默认）/ Neo4j / Qdrant |
| 前端 | React 18 / Tailwind CSS / Vite / Zustand |
| LLM | LangGraph / LangSmith |
| 日志服务 | FastAPI / SQLite / httpx SDK |
| 部署 | Docker Compose |

## 环境变量

| 变量 | 用途 |
|------|------|
| LLM_API_KEY / LLM_BASE_URL / LLM_MODEL | LLM 调用 |
| NEO4J_URI / USERNAME / PASSWORD | 知识图谱 |
| QDRANT_URL / API_KEY | 向量检索 |
| DATA_DIR | Markdown 数据目录 |
| FRONTEND_BASE_PATH | 前端基础路径 |
| LOG_LEVEL | 日志级别（保留） |

## 跨语言接入约束

- 协议：HTTP REST（JSON），不使用 gRPC
- 不依赖外部消息队列
- 不包含 LangSmith（留在各项目内部）
- Java SDK 后续补充
