# 测试覆盖清单

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 项目初始化 | S001 | unit | 默认值/环境变量覆盖 | completed | log-service repo commit e7a9b08 |
| 存储层 | B001 | unit | 建表/批量插入/按 service 查询/统计分组 | completed | log-service repo commit fec7f42 |
| Handler | B002 | unit | 注册写入/批量 flush/进程退出 flush | completed | log-service repo commit d88b205 |
| 初始化入口 | B003 | unit | setup/shutdown 生命周期 | completed | log-service repo commit 293fce7 |
| ingest API | B004 | unit | 正常写入/service 缺失/空数组/大批量 | completed | log-service repo commit ee26119 |
| 查询 API | B005 | unit | 按 service 筛选/stats 分组/cleanup 按天数 | completed | log-service repo commit ddb6a3e |
| 中间件 | B006 | unit | RequestID 生成/请求日志/异常捕获 | completed | log-service repo commit 870e30d |
| 服务集成 | B007 | integration | 完整写入-查询-统计-清理链路/混合数据 | completed | log-service repo commit 8a7b879 |
| SDK Handler | B008 | unit | 正常发送/不可达不阻塞/重试/退出 flush | completed | log-service repo commit 3dc7634 |
| SDK 初始化 | B009 | unit | 快捷函数默认参数 | completed | log-service repo commit 3dc7634 |
| logs-ui 迁移 | F001 | manual | 页面加载/筛选/分页正常 | completed | log-service repo commit d4b87dc |
| logs-ui 统计 | F002 | manual | 统计卡片显示 service 分组 | completed | log-service repo commit d4b87dc |
| 项目改造-移除 | B010 | integration+runtime | 项目启动无报错/业务 API 正常/日志目录已删除 | completed | evidence/B010.md, 5 task-level tests (含 lifespan 启动), 307 backend tests, 运行态验证通过 (commit 2810a6e) |
| 项目改造-接入 | B011 | integration+runtime | SDK 初始化/RemoteLogHandler 挂载/中间件日志链路/失败不阻塞 | completed | evidence/B011.md, 8 task-level tests (含日志到达 handler 验证), 307 backend tests, E2E 链路验证通过 (commit 2810a6e) |
| Docker 部署 | B012 | manual | docker compose up 正常启动 | completed | log-service repo commit 9d1c360 |
| 端到端 | S003 | integration | 完整链路/服务重启恢复 | completed | log-service repo commit 9d1c360 |
| 死代码清理 | TD01 | unit | 构建通过/无残留引用 | completed | - |
| nginx 配置统一 | TD02 | integration | nginx -t 通过/compose 路径正确 | completed | - |
| CORS 配置收紧 | TD11 | unit | 预检/非法源/非法方法/GET CORS 头 | completed | 4 tests in backend/tests/unit/api/test_cors.py |
| Docker sed hack | TD03 | integration | Docker build + 容器健康检查 | completed | deploy-lib 共享部署库 + git source 引用 |
| deps.py 统一化 | TD06 | unit | 构造注入/无副作用/reset重建/503 | completed | 9 tests in backend/tests/unit/test_deps.py |
| 503 降级提示 | TD10 | unit+integration | 503检测/非503不触发/重试恢复 + UI文案/重试按钮 + GET /entries 503集成 | completed | 3 store tests + 3 component tests + 3 deps 503 tests + 1 GET /entries 503 integration test |
| MCP Server 拆分 | TD04 | unit | 导入/路由映射/常量/handler可调用/call_tool分发 | completed | 14 tests in backend/tests/unit/test_mcp_split.py (commit b248277) |
| E2E 测试加强 | TD09 | integration | 硬断言/导航/数据闭环/响应式/容错 | completed | 8 tests, 6 passed + 2 skipped (runtime verified 2026-04-12) |
| 前端 API 类型安全 | TD05 | unit | TypeScript 编译/CRUD 类型推导/搜索保留 | completed | openapi-fetch CRUD migration |
| taskStore 单元测试 | TD07 | unit | fetchEntries/addTasks/updateTaskStatus/deleteTask/searchEntries/getTodayTasks | completed | 32 tests in frontend/src/stores/taskStore.test.ts |
| hooks 和 lib 测试 | TD08 | unit | useChatActions/ApiError/reviewFormatter | completed | 76 tests across 3 test files (25+22+29) |
| 反馈 SDK 契约确认 | S004 | manual | report_issue 签名/返回结构/severity 枚举核对 | completed | 通过 python3 inspect 校验 SDK 签名 |
| 后端反馈路由 | FB01 | unit+flow | 正常提交/SDK不可达/title 422/severity 422 + 全链路集成8项 | completed | 4 unit + 8 flow tests in test_feedback_api.py + test_feedback_flow.py |
| 前端反馈按钮 | FB02 | manual+unit | UI交互/构建通过/组件交互测试/浮层避让 | completed | 4 tests in frontend/src/components/FeedbackButton.test.tsx + npm run build |
| 前端反馈 API | FB03 | unit | fetch 200/503/422 | completed | 3 tests in frontend/src/services/api.feedback.test.ts |
| 单容器部署文件 | DP01 | integration | Docker 构建/static_app 导入/构建产物验证 | completed | bash deploy/build.sh 构建成功 |
| 切换+清理旧文件 | DP02 | integration | deploy.sh 路径/旧文件删除(生产+开发)/文档同步 | completed | scripts/deploy.sh + 旧文件全部删除 + docker/ 目录移除 |
| 构建与运行态验证 | DP03 | integration+smoke | 健康检查/SPA深链/静态资源/API文档/路由隔离/API端点 | completed | 容器级 9/9 验证通过 + dev/prod compose config 验证 + dev build 验证 |
| 用户模型 | B01 | unit | 创建用户/重复username/密码哈希/get_by_username | completed | evidence/B01.md |
| 认证API | B02 | unit+integration | 注册成功/重复注册/登录成功/错误密码/获取me/token过期 | completed | evidence/B02.md, risk: auth, first_use |
| 认证测试 | B03 | unit | 注册成功失败/登录成功失败/token创建验证过期/密码哈希 | completed | evidence/B03.md |
| SQLite隔离 | B04 | unit | entry带user_id/list_entries过滤/数据迁移/多用户隔离 | completed | evidence/B04.md |
| Markdown隔离 | B05 | unit | 新用户目录创建/多用户目录隔离/迁移完整性/工厂缓存 | completed | evidence/B05.md, risk: first_use, startup |
| Neo4j隔离 | B06 | unit | 节点带user_id/查询过滤/迁移 | completed | evidence/B06_B07.md |
| Qdrant隔离 | B07 | unit | payload带user_id/搜索过滤/迁移 | completed | evidence/B06_B07.md |
| 服务层改造 | B08 | integration | 创建sync带user_id/跨用户不可见/删除隔离 | completed | evidence/B08.md |
| 会话隔离 | B09 | unit | 会话关联user_id/列表过滤/迁移 | completed | evidence/B09.md |
| 认证中间件 | B10 | unit | 有效token/过期token/无效token/无token | completed | evidence/B10.md, risk: auth, first_use |
| 路由守卫 | B11 | integration | 带token成功/不带token401/search隔离/SSE带token | completed | evidence/B11.md |
| 用户状态管理 | F01 | unit | login状态/logout状态/刷新恢复/token过期清除 | completed | evidence/F01.md, risk: auth, first_use |
| 登录注册页 | F02 | manual+unit | 正常登录/错误提示/注册流程/验证失败 | completed | evidence/F02.md, risk: auth, first_use |
| 路由守卫+拦截器 | F03 | unit | 未登录跳转/已登录正常/401自动登出/token注入 | completed | evidence/F03.md, risk: auth, first_use |
| 侧边栏用户信息 | F04 | unit | 显示username/登出流程/X-UID替换 | completed | evidence/F04.md |
| 全链路联调 | S02 | integration+smoke | 注册→登录→创建→隔离→登出→重登录/双用户/迁移数据 | partial | 已验证 `_default` 迁移成立，但缺少真实线上账号认领与远程部署数据存在性 smoke |
| 生产恢复契约 | S03 | unit+review | `_default` 归属规则/冲突规则/回填验收标准 | planned | 需补明确 claim 策略 |
| 数据认领与回填 | B12 | unit+integration | SQLite/Markdown/session 迁移幂等/冲突不覆盖/审计输出 | planned | risk: auth, first_use, startup |
| 部署探针与回填命令 | B13 | integration+runtime | DATA_DIR/卷挂载/dry-run/实际回填/失败阻断 | planned | risk: startup, config |
| 生产恢复回归 | S04 | smoke+manual | 目标账号历史内容可见/非目标账号隔离/失败阻断验收 | planned | risk: auth, first_use, startup, config, network |
| Phase 1A 契约 | S05 | unit | 模型定义/schema 更新/类型生成/测试通过 | completed | - |
| 回顾趋势 API | B14 | unit+integration | trend 正确统计/空数据/user_id 修复/隔离验证/参数边界（invalid period, days=0）/smoke 首次请求 | completed | risk: auth, smoke_required |
| 灵感转化 API | B15 | unit+integration | inbox→task/note 文件移动/front matter 更新/SQLite 同步/旧文件删除 | pending | - |
| 反馈闭环后端 | B16 | unit+integration | feedback 表创建/双写/列表查询/状态追踪/用户隔离/启动幂等/冷启动首次提交/log-service 不可达 smoke | pending | risk: auth, startup, smoke_required |
| 首页改版「今天」 | F05 | manual+unit | 任务状态切换/灵感角标/快速操作/空状态引导/Sidebar 标签/构建通过/切换失败回滚/loading 态 | pending | risk: first_use |
| FeedbackButton 双 Tab | F06 | manual+unit | 双 Tab 切换/反馈列表/状态标识/提交后跳转/构建通过 | pending | - |
