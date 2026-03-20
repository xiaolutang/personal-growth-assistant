#!/bin/bash
# 生产环境一键部署脚本
# 使用方式: ./scripts/deploy.sh [--no-cache] [--dev]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认值
NO_CACHE=""
ENV="prod"
FRONTEND_BASE_PATH="/growth/"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --dev)
            ENV="dev"
            shift
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         个人成长助手 - 部署脚本 v2.0                      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}📁 项目目录: $PROJECT_ROOT${NC}"
echo -e "${YELLOW}🌍 环境: $ENV${NC}"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 未安装 Docker，请先安装${NC}"
    exit 1
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

echo -e "${GREEN}✅ 使用命令: $DOCKER_COMPOSE${NC}"
echo -e "${GREEN}✅ Docker 环境检查通过${NC}"
echo ""

# 加载环境变量
if [ -f .env ]; then
    echo -e "${YELLOW}📋 加载环境变量...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
    # 读取 FRONTEND_BASE_PATH
    if grep -q "^FRONTEND_BASE_PATH=" .env; then
        FRONTEND_BASE_PATH=$(grep "^FRONTEND_BASE_PATH=" .env | cut -d'=' -f2)
    fi
fi

echo -e "${YELLOW}📍 前端基础路径: ${FRONTEND_BASE_PATH}${NC}"
echo ""

# 设置 compose 文件
if [ "$ENV" = "dev" ]; then
    COMPOSE_FILE="docker/docker-compose.dev.yml"
else
    COMPOSE_FILE="docker/docker-compose.prod.yml"
fi

# ===== 步骤 1: 构建前端 =====
echo -e "${BLUE}=== 步骤 1/4: 构建前端 ===${NC}"
echo -e "${YELLOW}🔨 构建前端 (base: ${FRONTEND_BASE_PATH})...${NC}"

cd "$PROJECT_ROOT/frontend"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 安装前端依赖...${NC}"
    npm install
fi

FRONTEND_BASE_PATH=$FRONTEND_BASE_PATH npm run build
mkdir -p "$PROJECT_ROOT/dist"
cp -r dist/* "$PROJECT_ROOT/dist/"

echo -e "${GREEN}✅ 前端构建完成${NC}"
echo ""

# ===== 步骤 2: 停止旧容器 =====
echo -e "${BLUE}=== 步骤 2/4: 停止旧容器 ===${NC}"
cd "$PROJECT_ROOT"
$DOCKER_COMPOSE -f $COMPOSE_FILE down 2>/dev/null || true
echo -e "${GREEN}✅ 旧容器已停止${NC}"
echo ""

# ===== 步骤 3: 构建并启动 Docker 服务 =====
echo -e "${BLUE}=== 步骤 3/4: 构建并启动 Docker 服务 ===${NC}"

if [ -n "$NO_CACHE" ]; then
    echo -e "${YELLOW}🔨 构建镜像 (不使用缓存)...${NC}"
else
    echo -e "${YELLOW}🔨 构建镜像...${NC}"
fi

$DOCKER_COMPOSE -f $COMPOSE_FILE build $NO_CACHE

echo -e "${YELLOW}🚀 启动服务...${NC}"
$DOCKER_COMPOSE -f $COMPOSE_FILE up -d

echo -e "${GREEN}✅ 服务已启动${NC}"
echo ""

# ===== 步骤 4: 健康检查 =====
echo -e "${BLUE}=== 步骤 4/4: 健康检查 ===${NC}"
echo -e "${YELLOW}⏳ 等待服务就绪...${NC}"

# 根据环境设置端口
if [ "$ENV" = "dev" ]; then
    PORT="8888"
else
    PORT="80"
fi

# 轮询健康检查（最多 30 次，每次 1 秒）
HEALTH_OK=false
for i in {1..30}; do
    if curl -sf "http://localhost:${PORT}/health" > /dev/null 2>&1; then
        HEALTH_OK=true
        break
    fi
    sleep 1
done

if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}✅ 健康检查通过${NC}"
else
    echo -e "${RED}❌ 健康检查失败，请检查日志${NC}"
    echo -e "${YELLOW}   $DOCKER_COMPOSE -f $COMPOSE_FILE logs backend${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     部署完成！                            ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"

if [ "$ENV" = "dev" ]; then
    echo -e "${GREEN}║  前端页面:    http://localhost:${PORT}${FRONTEND_BASE_PATH}              ${NC}"
    echo -e "${GREEN}║  API 文档:    http://localhost:${PORT}/api/docs             ${NC}"
    echo -e "${GREEN}║  Neo4j 控制台: http://localhost:17474                       ${NC}"
    echo -e "${GREEN}║  Qdrant 控制台: http://localhost:16333                      ${NC}"
else
    echo -e "${GREEN}║  前端页面:    http://localhost${FRONTEND_BASE_PATH}              ${NC}"
    echo -e "${GREEN}║  API 文档:    http://localhost/api/docs                 ${NC}"
    echo -e "${GREEN}║  Neo4j 控制台: http://localhost:7474                       ${NC}"
    echo -e "${GREEN}║  Qdrant 控制台: http://localhost:6333                      ${NC}"
fi

echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  查看日志:    $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f     ${NC}"
echo -e "${GREEN}║  停止服务:    $DOCKER_COMPOSE -f $COMPOSE_FILE down        ${NC}"
echo -e "${GREEN}║  重启服务:    $DOCKER_COMPOSE -f $COMPOSE_FILE restart     ${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
