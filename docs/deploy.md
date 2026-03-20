# 个人成长助手 - 发布流程

## 架构概述

```
统一 Nginx 入口 (localhost:8080)
├── /growth/          → 个人成长助手前端
├── /growth/api/      → 个人成长助手后端 API
├── /proxy/ui/        → 代理管理界面
└── /                 → 代理服务
```

## 服务依赖

| 服务 | 容器名 | 网络 | 说明 |
|------|--------|------|------|
| 统一 Nginx | claude-proxy-nginx | proxy-server_proxy-network | 入口代理 |
| 后端 API | pga-backend | personal-growth-assistant_pga-network + proxy-server_proxy-network | FastAPI 服务 |
| Neo4j | pga-neo4j | personal-growth-assistant_pga-network | 知识图谱 |
| Qdrant | pga-qdrant | personal-growth-assistant_pga-network | 向量检索 |

## 发布步骤

### 1. 构建前端

```bash
cd /Users/tangxiaolu/project/personal-growth-assistant/frontend
npm run build
```

### 2. 复制前端文件到统一 Nginx

```bash
docker exec claude-proxy-nginx rm -rf /usr/share/nginx/html/growth
docker exec claude-proxy-nginx mkdir -p /usr/share/nginx/html/growth
docker cp dist/. claude-proxy-nginx:/usr/share/nginx/html/growth/
```

### 3. 确保后端在代理网络中

```bash
docker network connect proxy-server_proxy-network pga-backend 2>/dev/null || true
```

### 4. 重启后端（如有代码更新）

```bash
cd /Users/tangxiaolu/project/personal-growth-assistant
docker compose build backend
docker compose up -d backend
```

### 5. 验证发布

```bash
# 测试前端页面
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/growth/
# 期望输出: 200

# 测试 API
curl -s "http://localhost:8080/growth/api/entries?limit=1" | jq '.total'
# 期望输出: 条目数量

# 测试健康检查
curl -s http://localhost:8080/growth/api/health
# 期望输出: {"status":"ok"}
```

## 一键发布脚本

```bash
#!/bin/bash
# deploy.sh - 一键发布脚本

set -e

PROJECT_DIR="/Users/tangxiaolu/project/personal-growth-assistant"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=== 1. 构建前端 ==="
cd "$FRONTEND_DIR"
npm run build

echo "=== 2. 部署前端到统一 Nginx ==="
docker exec claude-proxy-nginx rm -rf /usr/share/nginx/html/growth
docker exec claude-proxy-nginx mkdir -p /usr/share/nginx/html/growth
docker cp dist/. claude-proxy-nginx:/usr/share/nginx/html/growth/

echo "=== 3. 确保后端在代理网络中 ==="
docker network connect proxy-server_proxy-network pga-backend 2>/dev/null || true

echo "=== 4. 验证发布 ==="
echo -n "前端状态: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/growth/
echo ""

echo -n "API 状态: "
curl -s "http://localhost:8080/growth/api/health"
echo ""

echo "✅ 发布完成！访问 http://localhost:8080/growth/"
```

## 关键配置文件

| 文件 | 说明 |
|------|------|
| `/Users/tangxiaolu/project/ai_rules/proxy-server/nginx.conf` | 统一 Nginx 配置 |
| `/Users/tangxiaolu/project/personal-growth-assistant/frontend/vite.config.ts` | 前端构建配置 (base: '/growth/') |
| `/Users/tangxiaolu/project/personal-growth-assistant/frontend/src/config/api.ts` | API 基础路径配置 |
| `/Users/tangxiaolu/project/personal-growth-assistant/docker-compose.yml` | Docker Compose 配置 |

## Nginx 路由配置

```nginx
# 个人成长助手 - 重定向无斜杠路径
location = /growth {
    return 301 /growth/;
}

# 个人成长助手 - 前端静态文件
location /growth/ {
    alias /usr/share/nginx/html/growth/;
    try_files $uri $uri/ /growth/index.html;
}

# 个人成长助手 - API 接口
location /growth/api/ {
    rewrite ^/growth/api/(.*) /$1 break;
    proxy_pass http://pga-backend:8001;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Connection "";

    # SSE 支持
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400s;
}
```

## 常见问题

### 白屏问题

1. **检查 JS Content-Type**
   ```bash
   curl -sI http://localhost:8080/growth/assets/index-*.js | grep Content-Type
   # 应该是 application/javascript，不是 text/plain
   ```

2. **检查 base 路径**
   - `vite.config.ts` 中 `base: '/growth/'`
   - `App.tsx` 中 `BrowserRouter basename={import.meta.env.BASE_URL}`

### 404 问题

1. **检查路径是否有尾部斜杠**
   - `/growth` 会 301 重定向到 `/growth/`
   - API 路径 `/growth/api/...` 不需要尾部斜杠

### 后端连接问题

1. **确保后端在代理网络中**
   ```bash
   docker network connect proxy-server_proxy-network pga-backend
   ```

2. **检查后端状态**
   ```bash
   docker logs pga-backend --tail 20
   ```

## 向量搜索同步

如果 Qdrant 数据需要重新同步：

```bash
curl -X POST http://localhost:8080/growth/api/entries/admin/sync-vectors
```

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:8080/growth/ |
| API | http://localhost:8080/growth/api/ |
| 健康检查 | http://localhost:8080/growth/api/health |
| Neo4j | http://localhost:17474/ |
| Qdrant | http://localhost:16333/dashboard |
