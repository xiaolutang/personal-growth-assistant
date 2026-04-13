# 个人成长助手 - 发布流程

## 架构概述

```
Traefik 网关 (localhost:443 HTTPS)
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

项目根目录 `.env` 文件需包含：

```bash
# 必填
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=glm-4.7
JWT_SECRET=your-jwt-secret    # 认证密钥

# 基础设施（与 ai_rules/infrastructure 保持一致）
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=changeme123
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
curl -sk https://localhost/growth/api/health
# 期望: {"status":"ok"}

# 前端页面
curl -sk -o /dev/null -w "%{http_code}" https://localhost/growth/
# 期望: 200

# API 文档
curl -sk -o /dev/null -w "%{http_code}" https://localhost/growth/api/docs
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
| 前端 | https://localhost/growth/ |
| API 文档 | https://localhost/growth/api/docs |
| 健康检查 | https://localhost/growth/api/health |
| 日志面板 | https://localhost/logs/ |
