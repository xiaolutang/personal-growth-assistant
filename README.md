# Personal Growth Assistant

个人成长管理助手 - 整合任务管理、灵感收集、学习笔记、项目追踪

## 项目结构

```
personal-growth-assistant/
├── backend/                   # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # API 入口
│   │   ├── config.py         # 配置管理
│   │   ├── models/           # 数据模型
│   │   │   └── task.py       # Task 模型
│   │   ├── callers/          # LLM 调用层
│   │   │   ├── base.py       # 抽象接口
│   │   │   ├── api_caller.py # API 调用实现
│   │   │   └── mock_caller.py# Mock 实现（测试用）
│   │   └── services/         # 业务服务
│   │       └── task_parser.py# 任务解析服务
│   ├── tests/                # 测试
│   │   ├── test_callers.py
│   │   └── test_task_parser.py
│   ├── pyproject.toml        # 依赖管理
│   └── .env.example
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/       # 组件
│   │   ├── pages/            # 页面
│   │   ├── stores/           # 状态管理
│   │   └── services/         # API 服务
│   ├── design-system.md      # ⭐ UI 设计规范
│   └── package.json
└── README.md
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/parse` | 解析自然语言 → 结构化任务 |

### 示例

```bash
# 健康检查
curl http://localhost:8000/health

# 解析任务
curl -X POST "http://localhost:8000/parse?text=明天下午3点开会，讨论项目进度"
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
docker/
├── Dockerfile.backend      # 后端镜像
├── Dockerfile.frontend     # 前端镜像
├── docker-compose.dev.yml  # 开发环境
├── docker-compose.prod.yml # 生产环境
└── nginx/
    ├── nginx.conf          # Nginx 主配置
    └── templates/          # 配置模板（支持环境变量）

scripts/
├── dev.sh                  # 开发环境启动
└── deploy.sh               # 生产部署
```

### 开发环境

```bash
# 快速启动
./scripts/dev.sh

# 或手动启动
docker compose -f docker/docker-compose.dev.yml up -d

# 访问
# 前端: http://localhost:8888/growth/
# Neo4j: http://localhost:17474
# Qdrant: http://localhost:16333
```

### 生产部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 2. 一键部署
./scripts/deploy.sh

# 3. 不使用缓存构建
./scripts/deploy.sh --no-cache

# 访问
# 前端: http://localhost/growth/
# Neo4j: http://localhost:7474
# Qdrant: http://localhost:6333
```

### 常用命令

```bash
# 查看日志
docker compose -f docker/docker-compose.prod.yml logs -f

# 停止服务
docker compose -f docker/docker-compose.prod.yml down

# 重启服务
docker compose -f docker/docker-compose.prod.yml restart

# 进入后端容器
docker exec -it pga-backend /bin/bash
```

## 技术栈

- **后端**: FastAPI + Pydantic
- **LLM**: OpenAI 兼容 API（通义千问、DeepSeek 等）
- **包管理**: uv
- **测试**: pytest + pytest-asyncio
- **前端**: React 18 + TypeScript + Vite + shadcn/ui + Tailwind CSS
- **数据库**: 待定（SQLite）

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
