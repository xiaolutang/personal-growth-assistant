#!/bin/bash
# 单容器镜像构建脚本（唯一构建入口）
# 使用方式: bash deploy/build.sh [--no-cache]
set -euo pipefail

CACHE_FLAG=""
if [[ "${1:-}" == "--no-cache" ]]; then
  CACHE_FLAG="--no-cache"
fi

cd "$(dirname "$0")/.."

docker buildx build \
  -f deploy/Dockerfile \
  -t personal-growth-assistant:latest \
  --build-arg FRONTEND_BASE_PATH="${FRONTEND_BASE_PATH:-/growth/}" \
  --build-arg RUN_USER=root \
  $CACHE_FLAG \
  --load \
  .
