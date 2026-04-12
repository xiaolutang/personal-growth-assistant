# 个人成长助手 - 发布流程

## 架构概述

```
Traefik 网关 (localhost:80)
├── /growth/api/* (priority=100) → StripPrefix /growth/api → pga:8001 (FastAPI)
└── /growth/*    (priority=50)  → StripPrefix /growth    → pga:8001 (StaticFiles)
```

单容器模式：FastAPI + Starlette StaticFiles 同时服务 API 和前端 SPA。

## 服务依赖

| 服务 | 容器名 | 网络 | 说明 |
|------|--------|------|------|
| Traefik | traefik | gateway | 统一入口网关（基础设施层） |
| 个人成长助手 | pga | gateway + infra-network | 单容器（API + 前端） |
| Neo4j | neo4j | infra-network | 知识图谱（基础设施层） |
| Qdrant | qdrant | infra-network | 向量检索（基础设施层） |
| log-service | log-service | gateway + infra-network | 日志服务（基础设施层） |

## 发布步骤

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL 等配置
```

### 2. 一键部署

```bash
./deploy/deploy.sh
```

### 3. 不使用缓存构建

```bash
./deploy/deploy.sh --no-cache
```

### 4. 验证发布

```bash
# 健康检查
curl http://localhost/growth/api/health
# 期望: {"status":"ok"}

# 前端页面
curl -s -o /dev/null -w "%{http_code}" http://localhost/growth/
# 期望: 200

# API 文档
curl -s -o /dev/null -w "%{http_code}" http://localhost/growth/api/docs
# 期望: 200
```

## 关键配置文件

| 文件 | 说明 |
|------|------|
| `deploy/Dockerfile` | 3-stage 单容器构建（前端 + 后端） |
| `deploy/static_app.py` | FastAPI + StaticFiles 入口 |
| `deploy/build.sh` | 镜像构建脚本 |
| `deploy/docker-compose.yml` | 生产部署配置（Traefik 路由） |
| `deploy/deploy.sh` | 一键部署脚本（共享部署库） |
| `frontend/vite.config.ts` | 前端构建配置 (base: '/growth/') |

## 常见问题

### 白屏问题

1. 检查 Traefik 路由是否正确
   ```bash
   docker logs traefik --tail 20
   ```

2. 检查前端 base 路径
   - `vite.config.ts` 中 `base: '/growth/'`

### 404 问题

1. API 返回 404：检查 Traefik StripPrefix 配置
2. 前端页面 404：检查 SPA catch-all 路由是否生效

### 后端连接问题

```bash
docker logs pga --tail 20
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost/growth/ |
| API 文档 | http://localhost/growth/api/docs |
| 健康检查 | http://localhost/growth/api/health |
| 日志面板 | http://localhost/logs/ |
