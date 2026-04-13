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
| 用户认证 | 注册 API | CONTRACT-A01 | completed | not_applicable | completed | S01 → B02 |
| 用户认证 | 登录 API | CONTRACT-A02 | completed | completed | completed | S01 → B02 → F02 |
| 用户认证 | 登出 API | CONTRACT-A03 | completed | completed | completed | S01 → B02 → F04 |
| 用户认证 | 获取当前用户 | CONTRACT-A04 | completed | completed | completed | S01 → B02 → F01 |
| 用户认证 | 路由守卫 | All contracts | completed | completed | completed | B10 → B11 |
| 数据隔离 | SQLite user_id | All data contracts | completed | not_applicable | completed | B04 |
| 数据隔离 | Markdown 用户目录 | All data contracts | completed | not_applicable | completed | B05 |
| 数据隔离 | Neo4j user_id | All data contracts | completed | not_applicable | completed | B06 |
| 数据隔离 | Qdrant user_id | All data contracts | completed | not_applicable | completed | B07 |
| 前端认证 | 登录注册页面 | CONTRACT-A01/A02 | not_applicable | completed | completed | F02 |
| 前端认证 | 路由守卫+拦截器 | All contracts | not_applicable | completed | completed | F03 |
| 前端认证 | 侧边栏用户信息 | CONTRACT-A04 | not_applicable | completed | completed | F04 |
| 全链路 | 认证+隔离联调 | All contracts | completed | completed | partial | S02 已验证认证与隔离主链路，未覆盖真实线上账号认领 |
| 内容恢复 | `_default` 数据认领 | CONTRACT-A04 / data contracts | planned | not_applicable | planned | S03 → B12 |
| 内容恢复 | 运维回填命令 | - | planned | not_applicable | planned | B13 |
| 内容恢复 | 远程部署 smoke | All affected contracts | planned | not_applicable | planned | S04 |
| 回顾模块 | 趋势数据 API | CONTRACT-R01 | pending | not_applicable | pending | S05 → B14 |
| 回顾模块 | Review user_id 修复 | All review contracts | pending | not_applicable | pending | B14 |
| 条目管理 | 灵感转化 category | CONTRACT-E01 | pending | not_applicable | pending | S05 → B15 |
| 反馈闭环 | Feedback 双写 | CONTRACT-006 | pending | not_applicable | pending | S05 → B16 |
| 反馈闭环 | Feedback 列表查询 | CONTRACT-FB01/FB02 | pending | not_applicable | pending | S05 → B16 |
| 反馈闭环 | FeedbackButton 双 Tab | CONTRACT-FB01 | pending | pending | pending | B16 → F06 |
| 首页模块 | 首页改版「今天」 | - | not_applicable | pending | pending | S05 → F05 |
