# 后端服务 Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml ./

# 安装 Python 依赖
RUN pip install --no-cache-dir fastapi uvicorn pydantic python-dotenv pyyaml neo4j qdrant-client mcp langchain-core langgraph openai

# 复制应用代码
COPY app ./app

# 创建数据目录
RUN mkdir -p /app/data/projects /app/data/tasks /app/data/notes

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
