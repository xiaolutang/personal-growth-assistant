# Personal Growth Assistant

个人成长管理助手 - 整合任务管理、灵感收集、学习笔记、项目追踪

## 项目结构

```
personal-growth-assistant/
├── backend/                   # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # API 入口 + 生命周期
│   │   ├── routers/          # API 路由
│   │   ├── services/         # 业务服务（sync/entry/intent）
│   │   ├── infrastructure/   # 基础设施（storage/llm）
│   │   ├── graphs/           # LangGraph 图（task_parser_graph）
│   │   ├── models/           # 数据模型（Task/Category/Status）
│   │   ├── mcp/              # MCP Server（9 个 Tools）
│   │   └── core/             # 配置与异常
│   ├── tests/                # 单元测试 + 集成测试
│   └── pyproject.toml
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── pages/            # 页面（Home/Tasks/Projects/Notes/Inbox/Review）
│   │   ├── components/       # 组件
│   │   ├── stores/           # Zustand 状态管理
│   │   └── services/         # API 服务
│   └── design-system.md      # UI 设计规范
├── deploy/                    # 单容器部署（Dockerfile + docker-compose + build.sh）
├── scripts/                   # 部署与验证脚本
└── docs/                      # 文档
```

## API 端点

完整 API 文档请访问 `/docs`（Swagger UI）。

| 主要端点 | 说明 |
|---------|------|
| `/entries` | 条目 CRUD（任务/笔记/灵感/项目） |
| `/parse` | LLM 解析自然语言（SSE 流式） |
| `/search` | 语义搜索 |
| `/knowledge-graph` | 知识图谱与概念关系 |
| `/intent` | 意图识别 |
| `/feedback` | 用户反馈 |
| `/review` | 统计回顾（日/周/月） |
| `/sessions` | 对话会话管理 |

### 示例

```bash
# 健康检查
curl http://localhost:8000/health

# 条目列表
curl http://localhost:8000/entries?limit=5
```

## 快速开始

### 后端

```bash
# 1. 进入后端目录
cd backend

# 2. 创建环境变量文件
cp .env.example .env
# 编辑 .env 填入 API 配置

# 3. 安装依赖
uv sync

# 4. 安装开发依赖（测试）
uv pip install -e ".[dev]"

# 5. 运行服务
uv run uvicorn app.main:app --reload

# 6. 访问 API 文档
open http://localhost:8000/docs
```

### 前端

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 运行开发服务
npm run dev

# 4. 访问前端
open http://localhost:5173
```

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| FRONTEND_BASE_PATH | 前端基础路径 | /growth/ |
| LLM_API_KEY | LLM API 密钥 | sk-xxx |
| LLM_BASE_URL | API 地址 | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| LLM_MODEL | 模型名称 | qwen-plus |
| NEO4J_USERNAME | Neo4j 用户名 | neo4j |
| NEO4J_PASSWORD | Neo4j 密码 | your_password |

## Docker 部署

### 目录结构

```
deploy/
├── Dockerfile              # 3-stage 单容器构建（前端 + 后端）
├── static_app.py           # FastAPI + StaticFiles 入口
├── build.sh                # 镜像构建脚本
├── deploy.sh               # 一键部署（共享部署库）
└── docker-compose.yml      # 生产部署（单容器 + Traefik）

scripts/
└── test-docker.sh          # Docker 构建验证
```

### 生产部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 2. 一键部署（构建镜像 + 启动容器）
./deploy/deploy.sh

# 3. 不使用缓存构建
./deploy/deploy.sh --no-cache

# 访问
# 前端: http://localhost/growth/
# API 文档: http://localhost/growth/api/docs
```

### 常用命令

```bash
# 查看日志
docker compose -f deploy/docker-compose.yml logs -f

# 停止服务
docker compose -f deploy/docker-compose.yml down

# 重启服务
docker compose -f deploy/docker-compose.yml restart

# 进入容器
docker exec -it pga /bin/bash
```

## 技术栈

- **后端**: FastAPI + Pydantic + LangGraph
- **存储**: Markdown（主数据源）+ Neo4j（知识图谱）+ Qdrant（向量检索）
- **LLM**: OpenAI 兼容 API（通义千问、DeepSeek 等）
- **前端**: React 18 + TypeScript + Vite + shadcn/ui + Tailwind CSS + Zustand
- **部署**: Docker 单容器 + Traefik 网关
- **测试**: pytest + pytest-asyncio + Vitest + Playwright

## UI 设计规范

新增或修改 UI 时，请参考 [`frontend/design-system.md`](frontend/design-system.md) 保持风格统一。

**关键规范**：
| 项目 | 规范 |
|------|------|
| 主色调 | `#6366F1` (靛蓝) |
| 圆角 | 按钮 8px / 卡片 12px |
| 间距基准 | 4px |
| 字号 | 正文 14px / 标题 16-24px |

**使用方式**：
> "按照 `frontend/design-system.md` 的设计规范，实现一个 [组件名] 组件"
