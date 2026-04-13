#!/bin/bash
# personal-growth-assistant 远端一键部署
# 使用方式: ./deploy/remote-deploy.sh [--skip-build] [--no-cache]
#
# 服务器配置共享: ai_rules/infrastructure/.remote.env
set -euo pipefail

# 加载共享部署库 + 服务器配置
INFRA_DIR="$(cd "$(dirname "$0")" && pwd)/../../ai_rules/infrastructure"
source "${INFRA_DIR}/deploy-lib.sh"
_load_remote_env

# 项目参数
PROJECT_NAME="personal-growth-assistant"
COMPOSE_FILE="deploy/docker-compose.yml"
HEALTH_PATH="/growth/api/health"
DISPLAY_NAME="personal-growth-assistant"
REMOTE_DEPLOY_DIR="/home/ubuntu/project/personal-growth-assistant"
IMAGES=("personal-growth-assistant:latest")
ACCESS_URLS=(
  "前端|http://${REMOTE_HOST}/growth/"
  "API|http://${REMOTE_HOST}/growth/api/docs"
  "健康|http://${REMOTE_HOST}/growth/api/health"
)

run_remote_data_check() {
  local username="${1:-}"
  local apply_flag="${2:-}"
  local remote_cmd="cd ${REMOTE_DEPLOY_DIR} && docker exec pga python /app/scripts/claim_default_data.py --data-dir /app/data"

  if [[ -n "$username" ]]; then
    remote_cmd="${remote_cmd} --username ${username}"
  fi
  if [[ "$apply_flag" == "apply" ]]; then
    remote_cmd="${remote_cmd} --apply"
  fi

  ssh "${REMOTE_USER}@${REMOTE_HOST}" "$remote_cmd"
}

# 自定义构建：带 FRONTEND_BASE_PATH 构建参数
custom_remote_build() {
  docker buildx build --platform "$REMOTE_PLATFORM" \
    -f deploy/Dockerfile \
    -t "personal-growth-assistant:latest" \
    --build-arg FRONTEND_BASE_PATH="/growth/" \
    $BUILD_CACHE_FLAG --load .
}

if [[ "${1:-}" == "--check-data" ]]; then
  run_remote_data_check "${2:-}" ""
  exit 0
fi

if [[ "${1:-}" == "--claim-default-data" ]]; then
  if [[ -z "${2:-}" ]]; then
    echo "用法: ./deploy/remote-deploy.sh --claim-default-data <username>"
    exit 1
  fi
  run_remote_data_check "$2" "apply"
  exit 0
fi

run_remote_deploy "$@"
