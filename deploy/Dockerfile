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

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY backend/app /app/app

# Copy frontend build output
COPY --from=frontend-builder /app/dist /app/static/frontend

# Copy static file server entry
COPY deploy/static_app.py /app/static_app.py

RUN mkdir -p /app/data

ENV PATH="/app/.venv/bin:$PATH"
ENV STATIC_DIR=/app/static/frontend

EXPOSE 8001

CMD ["uvicorn", "static_app:app", "--host", "0.0.0.0", "--port", "8001"]
