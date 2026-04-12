#!/bin/bash
# 个人成长助手 部署脚本
# 使用方式: ./scripts/deploy.sh [--no-cache]
set -euo pipefail

# ===== 引用共享部署库 =====
INFRA_DIR="${INFRA_DIR:-$(cd "$(dirname "$0")" && pwd)/../../ai_rules/infrastructure}"
source "$INFRA_DIR/deploy-lib.sh"

# ===== 项目声明 =====
PROJECT_NAME="personal-growth-assistant"
DISPLAY_NAME="个人成长助手"
COMPOSE_FILE="docker/docker-compose.prod.yml"
HEALTH_PATH="/growth/api/health"
ACCESS_URLS=(
  "前端页面|http://localhost/growth/"
  "API 文档|http://localhost/growth/api/docs"
  "日志面板|http://localhost/logs/"
)

# ===== 执行 =====
run_deploy "$@"
