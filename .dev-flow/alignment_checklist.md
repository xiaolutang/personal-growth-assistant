# 前后端对齐清单

| Module | Feature | Contract | Backend | Frontend | Integration | Notes |
|--------|---------|----------|---------|----------|-------------|-------|
| 日志服务 | 批量写入 | CONTRACT-001 | completed | not_applicable | completed | log-service commit ee26119 |
| 日志服务 | 日志查询 | CONTRACT-002 | completed | completed | completed | log-service commit ddb6a3e, logs-ui |
| 日志服务 | 日志统计 | CONTRACT-003 | completed | completed | completed | log-service commit ddb6a3e |
| 日志服务 | 日志清理 | CONTRACT-004 | completed | not_applicable | completed | log-service commit ddb6a3e |
| 日志服务 | 健康检查 | CONTRACT-005 | completed | not_applicable | completed | log-service commit e7a9b08 |
| Python SDK | RemoteLogHandler | CONTRACT-001 | completed | not_applicable | completed | log-service commit 3dc7634 |
| Python SDK | 快捷初始化 | - | completed | not_applicable | completed | log-service commit 3dc7634 |
| logs-ui | 日志列表+筛选 | CONTRACT-002 | completed | completed | completed | log-service commit d4b87dc |
| logs-ui | 统计卡片 | CONTRACT-003 | completed | completed | completed | log-service commit d4b87dc |
| logs-ui | 日志详情 | CONTRACT-002 | completed | completed | completed | log-service commit d4b87dc |
| 项目改造 | 移除本地模块 | - | completed | not_applicable | completed | commit 2810a6e, evidence/B010.md |
| 项目改造 | SDK 接入 | CONTRACT-001 | completed | not_applicable | completed | commit 2810a6e, evidence/B011.md |
| 反馈功能 | SDK 契约确认 | CONTRACT-006 | completed | not_applicable | not_applicable | S004，已核对 report_issue() 签名、返回结构、severity 枚举 |
| 反馈功能 | 后端反馈路由 | CONTRACT-006 | completed | not_applicable | completed | FB01，/feedback 已实现并完成 4 个 API 单测 |
| 反馈功能 | 反馈按钮+API | CONTRACT-006 | completed | completed | completed | FB02 + FB03，前后端 severity 枚举统一，已验证与 FloatingChat 避让 |
