# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
ARG FRONTEND_BASE_PATH=/growth/
ENV FRONTEND_BASE_PATH=$FRONTEND_BASE_PATH
RUN npm run build

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 3: Runtime
FROM python:3.12-slim

# 本地构建传 RUN_USER=root（绕过 volume 权限），远端默认 appuser
ARG RUN_USER=appuser

WORKDIR /app

# 始终创建非 root 用户和 /data 目录
RUN useradd -r -s /bin/false appuser && \
    mkdir -p /app/data && chown appuser:appuser /app/data

COPY --from=builder /app/.venv /app/.venv
COPY backend/app /app/app
COPY backend/scripts /app/scripts

# Copy frontend build output
COPY --from=frontend-builder /app/dist /app/static/frontend

# Copy static file server entry
COPY deploy/static_app.py /app/static_app.py

# 设置文件所有权（非 root 时）
RUN if [ "$RUN_USER" != "root" ]; then chown -R appuser:appuser /app; fi

ENV PATH="/app/.venv/bin:$PATH"
ENV STATIC_DIR=/app/static/frontend

USER ${RUN_USER}

EXPOSE 8001

CMD ["uvicorn", "static_app:app", "--host", "0.0.0.0", "--port", "8001"]
