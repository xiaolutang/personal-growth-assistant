# 构建阶段
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 构建
RUN npm run build

# 输出阶段 - 仅包含静态文件
FROM alpine:latest

WORKDIR /usr/share/nginx/html

# 从构建阶段复制静态文件
COPY --from=builder /app/dist .

# 这个镜像只用于输出静态文件到 volume
CMD ["sh", "-c", "echo 'Logs UI build complete' && sleep infinity"]
