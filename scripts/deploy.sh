#!/bin/bash
# 生产环境一键部署脚本
# 使用方式: ./scripts/deploy.sh [--no-cache]
# 依赖: infrastructure/ 层已部署（Traefik + 共享数据库 + log-service）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认值
NO_CACHE=""
FRONTEND_BASE_PATH="/growth/"

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         个人成长助手 - 部署脚本 v3.0                      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${YELLOW}📁 项目目录: $PROJECT_ROOT${NC}"
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
echo ""

# 检查 infrastructure 层依赖
echo -e "${YELLOW}📋 检查基础设施依赖...${NC}"
if ! docker network inspect gateway &> /dev/null; then
    echo -e "${RED}❌ gateway 网络不存在，请先部署 infrastructure 层${NC}"
    exit 1
fi
if ! docker network inspect infra-network &> /dev/null; then
    echo -e "${RED}❌ infra-network 网络不存在，请先部署 infrastructure 层${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 基础设施依赖检查通过${NC}"
echo ""

# 加载环境变量
if [ -f .env ]; then
    echo -e "${YELLOW}📋 加载环境变量...${NC}"
    set -a
    source .env
    set +a
    FRONTEND_BASE_PATH="${FRONTEND_BASE_PATH:-/growth/}"
fi

echo -e "${YELLOW}📍 前端基础路径: ${FRONTEND_BASE_PATH}${NC}"
echo ""

COMPOSE_FILE="docker/docker-compose.prod.yml"

# ===== 步骤 1: 停止旧容器 =====
echo -e "${BLUE}=== 步骤 1/3: 停止旧容器 ===${NC}"
$DOCKER_COMPOSE -f $COMPOSE_FILE down 2>/dev/null || true
echo -e "${GREEN}✅ 旧容器已停止${NC}"
echo ""

# ===== 步骤 2: 构建并启动 =====
echo -e "${BLUE}=== 步骤 2/3: 构建并启动服务 ===${NC}"

# 复制 log-service SDK 到项目内（后端本地 path 依赖）
LOG_SERVICE_SDK_SRC="${LOG_SERVICE_SDK_SRC:-$PROJECT_ROOT/../../log-service/sdks/python}"
cleanup_sdk() { rm -rf "$PROJECT_ROOT/log-service-sdk"; }
trap cleanup_sdk EXIT

if [ -d "$LOG_SERVICE_SDK_SRC" ]; then
    cp -r "$LOG_SERVICE_SDK_SRC" "$PROJECT_ROOT/log-service-sdk"
    echo -e "${GREEN}✅ log-service SDK 已准备${NC}"
else
    echo -e "${YELLOW}⚠️  log-service SDK 未找到: $LOG_SERVICE_SDK_SRC${NC}"
    echo -e "${YELLOW}   设置 LOG_SERVICE_SDK_SRC 环境变量指定路径${NC}"
fi

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

# ===== 步骤 3: 健康检查 =====
echo -e "${BLUE}=== 步骤 3/3: 健康检查 ===${NC}"
echo -e "${YELLOW}⏳ 等待服务就绪...${NC}"

# 通过 Traefik 网关检查
HEALTH_OK=false
for i in {1..30}; do
    if curl -sf "http://localhost:80/growth/api/health" > /dev/null 2>&1; then
        HEALTH_OK=true
        break
    fi
    sleep 2
done

if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}✅ 健康检查通过${NC}"
else
    echo -e "${RED}❌ 健康检查失败，请检查日志${NC}"
    echo -e "${YELLOW}   $DOCKER_COMPOSE -f $COMPOSE_FILE logs${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     部署完成！                            ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  前端页面:    http://localhost${FRONTEND_BASE_PATH}              ${NC}"
echo -e "${GREEN}║  API 文档:    http://localhost/growth/api/docs             ${NC}"
echo -e "${GREEN}║  日志面板:    http://localhost/logs/                       ${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  查看日志:    $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f     ${NC}"
echo -e "${GREEN}║  停止服务:    $DOCKER_COMPOSE -f $COMPOSE_FILE down        ${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
