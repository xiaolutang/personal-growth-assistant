# 个人成长助手 - 发布版本

## 目录结构

```
release/
├── deploy.sh              # 部署脚本
├── docker-compose.yml     # Docker Compose 配置
├── .env.example           # 环境变量示例
├── backend/
│   └── Dockerfile         # 后端镜像构建文件
├── nginx/
│   ├── nginx.conf         # Nginx 主配置
│   └── conf.d/
│       └── default.conf   # 站点配置
└── frontend/
    └── dist/              # 前端构建产物 (需手动复制)
```

## 部署步骤

### 1. 准备发布包

```bash
# 在项目根目录执行

# 1. 构建前端
cd frontend && npm run build

# 2. 复制前端构建产物到 release 目录
cp -r dist ../release/frontend/

# 3. 复制后端代码到 release 目录
cp -r backend ../release/
```

### 2. 配置环境变量

```bash
# 复制环境变量示例
cp .env.example .env

# 编辑 .env 文件，填写实际值
vim .env
```

必填项：
- `LLM_API_KEY` - LLM API 密钥

### 3. 部署

```bash
# 赋予执行权限
chmod +x deploy.sh

# 执行部署
./deploy.sh
```

### 4. 验证

- 前端页面: http://localhost
- API 文档: http://localhost/docs
- Neo4j 控制台: http://localhost:7474
- Qdrant 控制台: http://localhost:6333

## 常用命令

```bash
# 查看日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 进入容器
docker compose exec backend sh
```

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| nginx | 80, 443 | HTTP/HTTPS 入口 |
| backend | 8001 | API 服务 (内部) |
| neo4j | 7474, 7687 | HTTP 控制台, Bolt 协议 |
| qdrant | 6333, 6334 | HTTP API, gRPC API |
