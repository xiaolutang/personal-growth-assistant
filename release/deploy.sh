#!/bin/bash
set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         个人成长助手 - 部署脚本                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未安装 Docker，请先安装"
    exit 1
fi

# 检测 docker compose 命令
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ 未找到 Docker Compose"
    exit 1
fi

echo "✅ 使用命令: $DOCKER_COMPOSE"
echo "✅ Docker 环境检查通过"
echo ""

# 加载环境变量
if [ -f .env ]; then
    echo "📋 加载环境变量..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# 停止旧容器
echo "🛑 停止旧容器..."
$DOCKER_COMPOSE down 2>/dev/null || true

# 构建并启动
echo "🔨 构建镜像..."
$DOCKER_COMPOSE build

echo "🚀 启动服务..."
$DOCKER_COMPOSE up -d

# 等待服务启动
sleep 5

# 显示状态
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                     部署完成！                            ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  前端页面:    http://localhost:80                         ║"
echo "║  API 文档:    http://localhost:80/docs                    ║"
echo "║  Neo4j 控制台: http://localhost:7474                       ║"
echo "║  Qdrant 控制台: http://localhost:6333                      ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  查看日志:    docker compose logs -f                      ║"
echo "║  停止服务:    docker compose down                         ║"
echo "║  重启服务:    docker compose restart                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
