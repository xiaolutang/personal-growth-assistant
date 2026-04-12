#!/bin/bash
# Docker 构建验证脚本
# 验证单容器部署（deploy/ 标准）
# 使用方式: ./scripts/test-docker.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Docker 构建验证 - 单容器模式                     ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}=== 步骤 1/4: 构建单容器镜像 ===${NC}"
bash deploy/build.sh

echo ""
echo -e "${YELLOW}=== 步骤 2/4: 启动容器 ===${NC}"
docker rm -f pga-test 2>/dev/null || true

docker run -d --name pga-test \
    -p 8001:8001 \
    -v "$PROJECT_ROOT/data:/app/data" \
    -e DATA_DIR=/app/data \
    -e LLM_API_KEY=test \
    -e LLM_BASE_URL=http://localhost \
    -e LLM_MODEL=test \
    personal-growth-assistant:latest

echo ""
echo -e "${YELLOW}=== 步骤 3/4: 健康检查 ===${NC}"
echo "等待服务启动..."
sleep 10

MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 健康检查通过${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "重试 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ 健康检查失败${NC}"
    echo ""
    echo "=== 容器日志 ==="
    docker logs pga-test --tail 50
    docker rm -f pga-test
    exit 1
fi

# 测试端点
echo ""
echo -e "${YELLOW}=== 步骤 4/4: 端点验证 ===${NC}"

# API 健康检查
HEALTH_RESPONSE=$(curl -s http://localhost:8001/health)
echo "GET /health: $HEALTH_RESPONSE"

# 前端静态文件
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/)
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ 前端页面可达 (HTTP $FRONTEND_STATUS)${NC}"
else
    echo -e "${RED}❌ 前端页面不可达 (HTTP $FRONTEND_STATUS)${NC}"
    docker logs pga-test --tail 20
    docker rm -f pga-test
    exit 1
fi

# API 文档
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/docs)
if [ "$DOCS_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ API 文档可达 (HTTP $DOCS_STATUS)${NC}"
else
    echo -e "${RED}❌ API 文档不可达 (HTTP $DOCS_STATUS)${NC}"
fi

# SPA 深链路由（核心验证：/tasks 应返回 index.html 而非 404）
SPA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/tasks)
SPA_CONTENT_TYPE=$(curl -sI http://localhost:8001/tasks | grep -i content-type | tr -d '\r')
if [ "$SPA_STATUS" = "200" ] && echo "$SPA_CONTENT_TYPE" | grep -q "text/html"; then
    echo -e "${GREEN}✅ SPA 深链 /tasks 返回 HTML (HTTP $SPA_STATUS)${NC}"
else
    echo -e "${RED}❌ SPA 深链 /tasks 未返回 HTML (HTTP $SPA_STATUS, $SPA_CONTENT_TYPE)${NC}"
    docker rm -f pga-test
    exit 1
fi

# 静态资源 MIME 类型
ASSET_FILE=$(curl -s http://localhost:8001/ | grep -o '/assets/[^"]*\.js' | head -1 | sed 's/^\///')
if [ -n "$ASSET_FILE" ]; then
    ASSET_CONTENT_TYPE=$(curl -sI "http://localhost:8001/$ASSET_FILE" | grep -i content-type | tr -d '\r')
    if echo "$ASSET_CONTENT_TYPE" | grep -q "javascript"; then
        echo -e "${GREEN}✅ 静态资源 MIME 正确 ($ASSET_FILE)${NC}"
    else
        echo -e "${RED}❌ 静态资源 MIME 异常: $ASSET_CONTENT_TYPE${NC}"
        docker rm -f pga-test
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ 跳过静态资源 MIME 检查（未找到 JS 文件引用）${NC}"
fi

# 路由优先级隔离（/health 返回 JSON，/ 返回 HTML）
HEALTH_CT=$(curl -sI http://localhost:8001/health | grep -i content-type | tr -d '\r')
if echo "$HEALTH_CT" | grep -q "application/json"; then
    echo -e "${GREEN}✅ 路由隔离正确：/health → JSON, / → HTML${NC}"
else
    echo -e "${RED}❌ 路由隔离失败：/health 返回 $HEALTH_CT（期望 JSON）${NC}"
    docker rm -f pga-test
    exit 1
fi

# 清理
echo ""
echo -e "${YELLOW}=== 清理测试容器 ===${NC}"
docker rm -f pga-test

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ Docker 构建验证通过                        ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  可以执行 ./deploy/deploy.sh 进行正式部署                ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
