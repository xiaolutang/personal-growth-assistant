#!/bin/bash
# 开发环境快速启动脚本
# 使用方式: ./scripts/dev.sh

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

echo -e "${BLUE}🚀 启动开发环境...${NC}"

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 检测 docker compose 命令
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}❌ 未找到 Docker Compose${NC}"
    exit 1
fi

# 构建前端
echo -e "${YELLOW}📦 构建前端...${NC}"
cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
mkdir -p "$PROJECT_ROOT/dist"
cp -r dist/* "$PROJECT_ROOT/dist/"

# 启动 Docker 服务
echo -e "${YELLOW}🐳 启动 Docker 服务...${NC}"
cd "$PROJECT_ROOT"
$DOCKER_COMPOSE -f docker/docker-compose.dev.yml up -d

echo ""
echo -e "${GREEN}✅ 开发环境已启动！${NC}"
echo -e "${GREEN}   前端页面: http://localhost:8888/growth/${NC}"
echo -e "${GREEN}   查看日志: $DOCKER_COMPOSE -f docker/docker-compose.dev.yml logs -f${NC}"
