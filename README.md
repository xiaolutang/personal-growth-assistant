# Personal Growth Assistant

个人成长管理助手 - 整合任务管理、灵感收集、学习笔记、项目追踪

## 项目结构

```
personal-growth-assistant/
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── models/    # 数据模型
│   │   ├── providers/ # LLM 提供商
│   │   ├── services/  # 业务服务
│   │   └── api/       # API 路由
│   ├── pyproject.toml # uv 依赖管理
│   └── .env.example
├── frontend/          # 前端（待定）
└── README.md
```

## 快速开始

```bash
# 后端
cd backend
cp .env.example .env
# 编辑 .env 填入 OPENAI_API_KEY
uv sync
uv run uvicorn app.main:app --reload
```

## 技术栈

- 后端：FastAPI + Pydantic + OpenAI
- 包管理：uv
- 前端：待定
- 数据库：SQLite（后续）
