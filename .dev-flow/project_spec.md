# 项目说明

> 项目：log-service
> 版本：v0.1.0

## 目标
- 将 personal-growth-assistant 的日志模块抽取为独立的可复用日志服务
- 支持多项目、多语言通过 HTTP REST 接入
- 提供统一的日志查看界面
- 在 personal-growth-assistant 中补充用户反馈提交通道，接入 log-service Issue API

## 范围

### 包含
- log-service 独立仓库（FastAPI 服务端）
- SQLite 日志存储（含扩展接口）
- ingest API（接收外部日志）
- query API（查询、统计、清理）
- 通用中间件（RequestID / RequestLogging / ErrorHandler）
- Python SDK（RemoteLogHandler）
- logs-ui（React 前端，含 service_name 筛选）
- Docker 部署配置
- personal-growth-assistant 改造为 SDK 接入
- personal-growth-assistant 反馈提交入口（前端按钮 + 后端代理）

### 不包含
- Java SDK（后续补充）
- LangSmith 集成（留在各项目内部）
- 告警/通知功能
- 用户认证/鉴权

## 用户路径
1. 项目接入：各项目安装对应语言 SDK → 配置 endpoint → 日志自动上报
2. 日志查看：访问 logs-ui → 按项目/级别/时间筛选 → 查看详情
3. 日志管理：查看统计 → 清理过期日志
4. 用户反馈：点击右下角反馈按钮 → 填写标题/描述/严重程度 → 提交到 log-service Issue API

## 技术约束
- 后端：Python 3.11+ / FastAPI / SQLite（默认）
- 前端：React 18 / Tailwind CSS / Vite
- 跨语言接入：HTTP REST（JSON）
- 部署：Docker Compose

## 交付边界
- 后端：独立 FastAPI 应用，暴露 ingest + query API
- 前端：独立 SPA，通过 API 代理访问后端
- SDK：Python 包，通过 pip 安装
- 集成：personal-growth-assistant 作为首个接入方完成端到端验证
