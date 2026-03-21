#!/bin/bash
# Docker 构建验证脚本
# 用于重大改动后的本地 Docker 测试
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
echo -e "${BLUE}║         Docker 构建验证 - 本地测试                       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检测 docker compose 命令
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}❌ 未找到 Docker Compose${NC}"
    exit 1
fi

echo -e "${YELLOW}=== 步骤 1/4: 构建后端镜像 ===${NC}"
docker build -f docker/Dockerfile.backend -t pga-backend:test .

echo ""
echo -e "${YELLOW}=== 步骤 2/4: 构建前端镜像 ===${NC}"
docker build -f docker/Dockerfile.frontend -t pga-frontend:test .

echo ""
echo -e "${YELLOW}=== 步骤 3/4: 启动后端容器 ===${NC}"
# 停止并删除旧容器
docker rm -f pga-backend-test 2>/dev/null || true

# 启动后端容器（使用测试配置）
docker run -d --name pga-backend-test \
    -p 8001:8001 \
    -e LLM_API_KEY=test \
    -e LLM_BASE_URL=http://localhost \
    -e LLM_MODEL=test \
    pga-backend:test

echo ""
echo -e "${YELLOW}=== 步骤 4/4: 健康检查 ===${NC}"
echo "等待服务启动..."
sleep 10

# 健康检查
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 后端健康检查通过${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "重试 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 3
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ 后端健康检查失败${NC}"
    echo ""
    echo "=== 容器日志 ==="
    docker logs pga-backend-test --tail 50
    docker rm -f pga-backend-test
    exit 1
fi

# 测试 API 端点
echo ""
echo -e "${YELLOW}=== API 端点测试 ===${NC}"

# 测试 sessions API
SESSIONS_RESPONSE=$(curl -s http://localhost:8001/sessions)
echo "GET /sessions: $SESSIONS_RESPONSE"

# 清理
echo ""
echo -e "${YELLOW}=== 清理测试容器 ===${NC}"
docker rm -f pga-backend-test

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ Docker 构建验证通过                        ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  可以执行 ./scripts/deploy.sh 进行正式部署               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
