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
| 项目改造-移除 | B010 | integration+runtime | 项目启动无报错/业务 API 正常/日志目录已删除 | completed | evidence/B010.md, 4 task-level tests, 305 backend tests (commit d47cfaf) |
| 项目改造-接入 | B011 | integration+runtime | SDK 初始化/RemoteLogHandler 挂载/中间件日志链路/失败不阻塞 | completed | evidence/B011.md, 7 task-level tests, 305 backend tests (commit d47cfaf) |
| Docker 部署 | B012 | manual | docker compose up 正常启动 | completed | log-service repo commit 9d1c360 |
| 端到端 | S003 | integration | 完整链路/服务重启恢复 | completed | log-service repo commit 9d1c360 |
| 死代码清理 | TD01 | unit | 构建通过/无残留引用 | completed | - |
| nginx 配置统一 | TD02 | integration | nginx -t 通过/compose 路径正确 | completed | - |
| CORS 配置收紧 | TD11 | unit | 预检/非法源/非法方法/GET CORS 头 | completed | 4 tests in backend/tests/unit/api/test_cors.py |
| Docker sed hack | TD03 | integration | Docker build + 容器健康检查 | completed | deploy.sh 生成 docker-pyproject.toml |
| deps.py 统一化 | TD06 | unit | 构造注入/无副作用/reset重建/503 | completed | 8 tests in backend/tests/unit/test_deps.py |
| 503 降级提示 | TD10 | unit+integration | 503检测/非503不触发/重试恢复 + UI文案/重试按钮 + GET /entries 503集成 | completed | 3 store tests + 3 component tests + 3 deps 503 tests + 1 GET /entries 503 integration test |
| MCP Server 拆分 | TD04 | unit | 导入/路由映射/常量/handler可调用 | completed | 8 tests in backend/tests/unit/test_mcp_split.py |
| E2E 测试加强 | TD09 | integration | 硬断言/导航/数据闭环/响应式/容错 | completed | 8 tests in e2e/tests/user_flows.spec.ts |
| 前端 API 类型安全 | TD05 | unit | TypeScript 编译/CRUD 类型推导/搜索保留 | completed | openapi-fetch CRUD migration |
| taskStore 单元测试 | TD07 | unit | fetchEntries/addTasks/updateTaskStatus/deleteTask/searchEntries/getTodayTasks | completed | 32 tests in frontend/src/stores/taskStore.test.ts |
| hooks 和 lib 测试 | TD08 | unit | useChatActions/ApiError/reviewFormatter | completed | 58 tests across 3 test files |
