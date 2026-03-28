# 前后端对齐清单

| Module | Feature | Contract | Backend | Frontend | Integration | Notes |
|--------|---------|----------|---------|----------|-------------|-------|
| 日志服务 | 批量写入 | CONTRACT-001 | planned | not_applicable | planned | ingest API，无前端 |
| 日志服务 | 日志查询 | CONTRACT-002 | planned | planned | planned | logs-ui 使用 |
| 日志服务 | 日志统计 | CONTRACT-003 | planned | planned | planned | logs-ui 统计卡片 |
| 日志服务 | 日志清理 | CONTRACT-004 | planned | not_applicable | planned | 可通过 API 调用 |
| 日志服务 | 健康检查 | CONTRACT-005 | planned | not_applicable | planned | 运维使用 |
| Python SDK | RemoteLogHandler | CONTRACT-001 | planned | not_applicable | planned | SDK 直连后端 |
| Python SDK | 快捷初始化 | - | planned | not_applicable | planned | 封装 Handler |
| logs-ui | 日志列表+筛选 | CONTRACT-002 | planned | planned | planned | 含 service_name 筛选 |
| logs-ui | 统计卡片 | CONTRACT-003 | planned | planned | planned | 含按服务分组 |
| logs-ui | 日志详情 | CONTRACT-002 | planned | planned | planned | 弹窗组件 |
| 项目改造 | 移除本地模块 | - | planned | not_applicable | planned | 后端改动 |
| 项目改造 | SDK 接入 | CONTRACT-001 | planned | not_applicable | planned | main.py 改造 |
