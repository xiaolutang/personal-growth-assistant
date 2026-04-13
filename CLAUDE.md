# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Personal Growth Assistant - 个人成长管理助手，整合任务管理、灵感收集、学习笔记、项目追踪。

## 常用命令

### 后端 (backend/)

```bash
# 安装依赖
cd backend && uv sync

# 安装开发依赖（测试）
uv pip install -e ".[dev]"

# 运行开发服务
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest                          # 所有测试
uv run pytest tests/unit/              # 单元测试
uv run pytest tests/integration/       # 集成测试（需要网络）
uv run pytest -m "not slow"            # 跳过慢测试

# 访问 API 文档
open http://localhost:8000/docs
```

### 前端 (frontend/)

```bash
# 安装依赖
cd frontend && npm install

# 运行开发服务
npm run dev

# 构建
npm run build

# 代码检查
npm run lint

# 运行测试
npm run test              # 监听模式
npm run test:run          # 单次运行

# 生成 OpenAPI 类型（从后端 API 自动生成 TypeScript 类型）
npm run gen:types
```

### Docker

```bash
# 生产部署
./deploy/deploy.sh
# 或 bash deploy/build.sh && docker compose -f deploy/docker-compose.yml up -d
```

## 架构概览

### 三层存储架构

```
Markdown (.md 文件)  →  Neo4j (知识图谱)  →  Qdrant (向量检索)
    ↓                       ↓                       ↓
Source of Truth         概念关系               语义搜索
```

- **MarkdownStorage**: 数据主源，存储在 `data/` 目录
- **Neo4jClient**: 知识图谱，存储概念和关系
- **QdrantClient**: 向量检索，支持语义搜索
- **SyncService**: 负责三层存储的同步

### 后端目录结构

```
backend/app/
├── main.py              # FastAPI 入口 + 生命周期管理
├── routers/             # API 路由
│   ├── entries.py       # CRUD /entries
│   ├── search.py        # POST /search
│   ├── knowledge.py     # 知识图谱
│   ├── intent.py        # 意图识别
│   ├── parse.py         # LLM 解析（SSE 流式）
│   ├── review.py        # 统计回顾
│   ├── feedback.py      # 用户反馈
│   ├── playground.py    # Playground 调试
│   └── deps.py          # 依赖注入
├── services/            # 业务服务
│   ├── sync_service.py  # 存储同步
│   ├── entry_service.py # 条目操作
│   ├── intent_service.py# 意图识别
│   └── ...
├── infrastructure/      # 基础设施
│   ├── storage/         # Markdown/SQLite/Neo4j/Qdrant
│   └── llm/             # LLM 调用层
├── graphs/              # LangGraph 图
│   └── task_parser_graph.py  # 任务解析图
├── models/              # 数据模型 (Task, Category, Status)
└── mcp/                 # MCP Server (9 个 Tools)
```

### 前端目录结构

```
frontend/src/
├── pages/               # 页面组件
│   ├── Home.tsx         # 首页（AI 对话）
│   ├── Tasks.tsx        # 任务列表
│   ├── Projects.tsx     # 项目列表
│   ├── Notes.tsx        # 笔记列表
│   ├── Inbox.tsx        # 灵感收集
│   ├── Review.tsx       # 统计回顾
│   └── EntryDetail.tsx  # 条目详情
├── components/          # 通用组件
├── stores/              # Zustand 状态管理
│   ├── chatStore.ts     # 对话状态
│   └── taskStore.ts     # 任务状态
├── services/            # API 调用
├── types/               # TypeScript 类型（含 OpenAPI 生成）
└── lib/                 # 工具函数
```

## 关键设计模式

### 依赖注入 (deps.py)

服务通过全局变量 + getter 函数注入，避免循环依赖：

```python
from app.routers import deps

storage = deps.get_storage()      # SyncService
entry_service = deps.get_entry_service()
```

### LangGraph 任务解析

`TaskParserGraph` 使用 LangGraph 实现对话式任务解析：
- 支持 SSE 流式输出
- 使用 `AsyncSqliteSaver` 保存对话历史（SQLite 存储）
- 通过 `thread_id` 隔离不同会话

### OpenAPI 类型同步

前端类型由后端 OpenAPI 自动生成：
1. 后端 `app.main:app` 导出 OpenAPI schema
2. `openapi-typescript` 生成 `src/types/api.generated.ts`
3. 前端使用类型安全的 API 调用

## UI 设计规范

参考 `frontend/design-system.md`，关键规范：

| 项目 | 规范 |
|------|------|
| 主色调 | `#6366F1` (靛蓝) |
| 圆角 | 按钮 8px / 卡片 12px |
| 间距基准 | 4px |
| 字号 | 正文 14px / 标题 16-24px |
| 图标库 | Lucide React |

## 环境变量

| 变量 | 说明 |
|------|------|
| `FRONTEND_BASE_PATH` | 前端基础路径，如 `/growth/` |
| `JWT_SECRET` | JWT 认证密钥（生产环境必填） |
| `LLM_API_KEY` | LLM API 密钥 |
| `LLM_BASE_URL` | API 地址 |
| `LLM_MODEL` | 模型名称 |
| `NEO4J_URI/USERNAME/PASSWORD` | Neo4j 连接 |
| `QDRANT_URL/API_KEY` | Qdrant 连接 |
| `DATA_DIR` | Markdown 数据目录 |
| `LOG_SERVICE_URL` | 日志服务地址 |
| `LOG_LEVEL` | 日志级别 |

## MCP Tools

项目提供 MCP Server，支持 Claude Code 直接调用：

| Tool | 说明 |
|------|------|
| `list_entries` | 查询条目列表 |
| `get_entry` | 获取单个条目 |
| `create_entry` | 创建新条目 |
| `update_entry` | 更新条目 |
| `delete_entry` | 删除条目 |
| `search_entries` | 语义搜索 |
| `get_knowledge_graph` | 获取知识图谱 |
| `get_related_concepts` | 获取相关概念 |
| `get_project_progress` | 获取项目进度 |
