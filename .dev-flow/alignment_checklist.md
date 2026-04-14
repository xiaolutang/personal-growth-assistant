# 前后端对齐清单

| Module | Feature | Contract | Backend | Frontend | Integration | Notes |
|--------|---------|----------|---------|----------|-------------|-------|
| 日志服务 | 批量写入 | CONTRACT-001 | completed | not_applicable | completed | log-service commit ee26119 |
| 日志服务 | 日志查询 | CONTRACT-002 | completed | completed | completed | log-service commit ddb6a3e |
| 日志服务 | 日志统计 | CONTRACT-003 | completed | completed | completed | log-service commit ddb6a3e |
| 日志服务 | 日志清理 | CONTRACT-004 | completed | not_applicable | completed | log-service commit ddb6a3e |
| 日志服务 | 健康检查 | CONTRACT-005 | completed | not_applicable | completed | log-service commit e7a9b08 |
| Python SDK | RemoteLogHandler | CONTRACT-001 | completed | not_applicable | completed | log-service commit 3dc7634 |
| logs-ui | 日志列表+筛选 | CONTRACT-002 | completed | completed | completed | log-service commit d4b87dc |
| 反馈功能 | SDK 契约确认 | CONTRACT-006 | completed | not_applicable | not_applicable | S004 |
| 反馈功能 | 后端反馈路由 | CONTRACT-006 | completed | not_applicable | completed | FB01 |
| 反馈功能 | 反馈按钮+API | CONTRACT-006 | completed | completed | completed | FB02 + FB03 |
| 用户认证 | 注册/登录/登出 | CONTRACT-A01/A02/A03 | completed | completed | completed | S01 → B02 → F02 |
| 用户认证 | 获取当前用户 | CONTRACT-A04 | completed | completed | completed | S01 → B02 → F01 |
| 用户认证 | 路由守卫 | All contracts | completed | completed | completed | B10 → B11 |
| 数据隔离 | 四层存储 user_id | All data contracts | completed | not_applicable | completed | B04 → B07 |
| 前端认证 | 登录注册页面 | CONTRACT-A01/A02 | not_applicable | completed | completed | F02 |
| 前端认证 | 路由守卫+拦截器 | All contracts | not_applicable | completed | completed | F03 |
| 前端认证 | 侧边栏用户信息 | CONTRACT-A04 | not_applicable | completed | completed | F04 |
| 回顾模块 | 趋势数据 API | CONTRACT-R01 | completed | completed | completed | B14 → F08 |
| 条目管理 | 灵感转化 category | CONTRACT-E01 | completed | completed | completed | B15 → F07 |
| 反馈闭环 | Feedback 双写+列表 | CONTRACT-006/FB01/FB02 | completed | completed | completed | B16 → F06 |
| 首页模块 | 首页改版「今天」 | - | not_applicable | completed | completed | F05 |
| 导出模块 | Export 导出 API | CONTRACT-E02 | completed | not_applicable | completed | B18, 22 tests |
| 导出模块 | Export 导出 UI | CONTRACT-E02 | completed | completed | completed | B18 → F12 |
| 条目关联 | 关联推荐 API | CONTRACT-E03 | completed | not_applicable | completed | B19 |
| 条目关联 | 关联面板 UI | CONTRACT-E03 | completed | completed | completed | B19 → F13 |
| Onboarding | onboarding_completed 字段 | CONTRACT-O01 | completed | not_applicable | completed | F09 后端部分 |
| Onboarding | Onboarding 引导 UI | CONTRACT-O01/O02 | completed | completed | completed | F09 前端部分 |
| 探索模块 | 探索页统一浏览 | - | not_applicable | completed | completed | F10 |
| 探索模块 | 搜索增强 | - | not_applicable | completed | completed | F10 → F11 |
