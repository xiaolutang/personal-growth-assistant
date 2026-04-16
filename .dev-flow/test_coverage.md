# 测试覆盖清单

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 月报AI总结 | B48 | unit | 正常生成/超时返回null/LLM失败其他字段正常/无数据月份 | pending | — |
| 新类型后端 | B49 | unit | 创建decision/reflection/question+模板/GET过滤/搜索/意图识别/已有类型不受影响/401/空模板 | pending | — |
| 新类型后端 smoke | B49 | smoke | 新用户首次创建决策→列表筛选→搜索命中→详情返回正确类型 | pending | — |
| 类型同步链路 | B49 | unit | Category枚举扩展/schema校验/构建通过/gen:types无报错 | pending | — |
| 月报AI展示 | F37 | unit+manual | 月报Tab显示AI总结/空值显示生成中/API错误降级/构建通过 | pending | — |
| 新类型前端 | F38 | unit+manual | 探索页Tab/首页快捷操作/详情差异化渲染/空数据Tab/构建通过 | pending | — |
| 新类型前端 smoke | F38 | smoke | 首页记决策→探索页筛选→搜索命中→详情页结构正确 | pending | — |
| 条目关联 API | B42 | unit | CRUD/双向/唯一约束/级联删除/事务/422枚举 | pending | — |
| 知识上下文 API | B43 | unit | 正常子图/空tags/Neo4j降级/404 | pending | — |
| AI 晨报增强 | B44 | unit | streak计算/LLM降级/兼容性/悬挂entry | pending | — |
| 图谱缩略图 | F31 | manual | 渲染/跳转?focus=/空态/移动端/API失败降级 | pending | — |
| 手动关联 UI | F32 | manual | 搜索创建/删除/分区/API失败toast | pending | — |
| 晨报展示 | F33 | manual | 连续天数/聚焦卡片/洞察/字段缺失降级 | pending | — |
| 项目初始化 | S001 | unit | 默认值/环境变量覆盖 | completed | log-service repo commit e7a9b08 |
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
| 项目改造-移除 | B010 | integration+runtime | 项目启动无报错/业务 API 正常/日志目录已删除 | completed | evidence/B010.md |
| 项目改造-接入 | B011 | integration+runtime | SDK 初始化/Handler 挂载/中间件日志链路/失败不阻塞 | completed | evidence/B011.md |
| Docker 部署 | B012 | manual | docker compose up 正常启动 | completed | log-service repo commit 9d1c360 |
| 端到端 | S003 | integration | 完整链路/服务重启恢复 | completed | log-service repo commit 9d1c360 |
| 死代码清理 | TD01 | unit | 构建通过/无残留引用 | completed | - |
| nginx 配置统一 | TD02 | integration | nginx -t 通过/compose 路径正确 | completed | - |
| CORS 配置收紧 | TD11 | unit | 预检/非法源/非法方法/GET CORS 头 | completed | 4 tests in test_cors.py |
| Docker sed hack | TD03 | integration | Docker build + 容器健康检查 | completed | deploy-lib |
| deps.py 统一化 | TD06 | unit | 构造注入/无副作用/reset重建/503 | completed | 9 tests in test_deps.py |
| 503 降级提示 | TD10 | unit+integration | 503检测/非503不触发/重试恢复 + UI文案/重试按钮 | completed | 多项测试覆盖 |
| MCP Server 拆分 | TD04 | unit | 导入/路由映射/常量/handler可调用/call_tool分发 | completed | 14 tests |
| E2E 测试加强 | TD09 | integration | 硬断言/导航/数据闭环/响应式/容错 | completed | 8 tests |
| 前端 API 类型安全 | TD05 | unit | TypeScript 编译/CRUD 类型推导/搜索保留 | completed | openapi-fetch |
| taskStore 单元测试 | TD07 | unit | fetchEntries/addTasks/updateTaskStatus/deleteTask/searchEntries/getTodayTasks | completed | 32 tests |
| hooks 和 lib 测试 | TD08 | unit | useChatActions/ApiError/reviewFormatter | completed | 76 tests |
| 反馈 SDK 契约确认 | S004 | manual | report_issue 签名/返回结构/severity 枚举核对 | completed | python3 inspect 校验 |
| 后端反馈路由 | FB01 | unit+flow | 正常提交/SDK不可达/title 422/severity 422 + 全链路集成8项 | completed | 12 tests |
| 前端反馈按钮 | FB02 | manual+unit | UI交互/构建通过/组件交互测试/浮层避让 | completed | 4 tests |
| 前端反馈 API | FB03 | unit | fetch 200/503/422 | completed | 3 tests |
| 单容器部署文件 | DP01 | integration | Docker 构建/static_app 导入/构建产物验证 | completed | bash deploy/build.sh |
| 切换+清理旧文件 | DP02 | integration | deploy.sh 路径/旧文件删除/文档同步 | completed | scripts/deploy.sh |
| 构建与运行态验证 | DP03 | integration+smoke | 健康检查/SPA深链/静态资源/API文档/路由隔离/API端点 | completed | 9/9 验证通过 |
| 用户模型 | B01 | unit | 创建用户/重复username/密码哈希/get_by_username | completed | evidence/B01.md |
| 认证API | B02 | unit+integration | 注册成功/重复注册/登录成功/错误密码/获取me/token过期 | completed | evidence/B02.md |
| 认证测试 | B03 | unit | 注册成功失败/登录成功失败/token创建验证过期/密码哈希 | completed | evidence/B03.md |
| SQLite隔离 | B04 | unit | entry带user_id/list_entries过滤/数据迁移/多用户隔离 | completed | evidence/B04.md |
| Markdown隔离 | B05 | unit | 新用户目录创建/多用户目录隔离/迁移完整性/工厂缓存 | completed | evidence/B05.md |
| Neo4j隔离 | B06 | unit | 节点带user_id/查询过滤/迁移 | completed | evidence/B06_B07.md |
| Qdrant隔离 | B07 | unit | payload带user_id/搜索过滤/迁移 | completed | evidence/B06_B07.md |
| 服务层改造 | B08 | integration | 创建sync带user_id/跨用户不可见/删除隔离 | completed | evidence/B08.md |
| 会话隔离 | B09 | unit | 会话关联user_id/列表过滤/迁移 | completed | evidence/B09.md |
| 认证中间件 | B10 | unit | 有效token/过期token/无效token/无token | completed | evidence/B10.md |
| 路由守卫 | B11 | integration | 带token成功/不带token401/search隔离/SSE带token | completed | evidence/B11.md |
| 用户状态管理 | F01 | unit | login状态/logout状态/刷新恢复/token过期清除 | completed | evidence/F01.md |
| 登录注册页 | F02 | manual+unit | 正常登录/错误提示/注册流程/验证失败 | completed | evidence/F02.md |
| 路由守卫+拦截器 | F03 | unit | 未登录跳转/已登录正常/401自动登出/token注入 | completed | evidence/F03.md |
| 侧边栏用户信息 | F04 | unit | 显示username/登出流程/X-UID替换 | completed | evidence/F04.md |
| Phase 1A 契约 | S05 | unit | 模型定义/schema 更新/类型生成/测试通过 | completed | - |
| 回顾趋势 API | B14 | unit+integration | trend 正确统计/空数据/user_id 修复/隔离验证/参数边界 | completed | risk: auth, smoke_required |
| 灵感转化 API | B15 | unit+integration | inbox→task/note 文件移动/front matter 更新/SQLite 同步/旧文件删除 | completed | - |
| 反馈闭环后端 | B16 | unit+integration | feedback 表创建/双写/列表查询/状态追踪/用户隔离/启动幂等 | completed | risk: auth, startup |
| 首页改版「今天」 | F05 | manual+unit | 任务状态切换/灵感角标/快速操作/空状态引导/构建通过 | completed | 194 frontend tests |
| FeedbackButton 双 Tab | F06 | manual+unit | 双 Tab 切换/反馈列表/状态标识/提交后跳转/构建通过 | completed | 201 frontend tests |
| 灵感转化 UI | F07 | manual+unit | 转为任务/转为笔记/loading 防重复/成功 toast/失败 toast/构建通过 | completed | 209 frontend tests |
| 回顾页趋势折线图 | F08 | manual+unit | 有数据渲染/日周切换/空数据引导/平均完成率/API 错误隔离/1天边界/构建通过 | completed | 222 frontend tests |
| Export 导出 API | B18 | unit+integration | markdown 导出返回 zip/json 导出返回数组/type 过滤/日期范围/空数据/用户隔离/无效 format 422 | completed | 22 tests in test_export.py, 493 total backend tests |
| 条目关联 API | B19 | unit+integration | 关联列表含 relevance_reason/同项目优先/无关联空数组/最多5条/用户隔离/不存在404 | completed | 7 tests in test_related_entries.py, 493 backend tests pass |
| Onboarding 引导 | F09 | manual+unit | 新用户显示引导/完成更新状态/Skip 跳过/已有用户不显示/刷新不重复/PUT 失败不卡/构建通过 + inbox-{id}.md 全链路收敛 | completed | risk: first_use, startup, 493 backend tests + 231 frontend tests |
| 探索页基础 | F10 | manual+unit | 混合列表展示/类型 Tab 切换/debounce 搜索+Enter/Sidebar 4项/旧路由重定向/空状态引导/构建通过 | completed | 493 backend + 231 frontend + build pass |
| 搜索增强 | F11 | manual+unit | debounce 300ms/Cmd+K 聚焦/关键词高亮/无结果引导/构建通过 | completed | 6 HighlightText tests + 231 frontend + build pass |
| Export 导出 UI | F12 | manual+unit | Sidebar 导出入口/格式选择/下载文件/loading 态/构建通过 | completed | 493 backend + 231 frontend + build pass |
| 条目关联面板 | F13 | manual+unit | 关联条目列表/点击跳转/无关联引导/API 失败不影响详情页/构建通过 | completed | 231 frontend + build pass |
| Health check 增强 | B34 | unit+integration | /health 返回服务状态/SQLite 不可达 503/Neo4j 降级 200 | pending | risk: startup |
| E2E 基础设施 | B35 | integration | 双服务启停/认证 fixture/API helper/假 LLM 配置 | pending | risk: startup, config |
| 认证流程 E2E | B36 | e2e | 注册→登录→访问→登出/未认证重定向/临时 DATA_DIR 回收 | pending | risk: auth |
| 条目 CRUD E2E | B37 | e2e | 创建/列表/搜索/更新/删除/空状态 | pending | - |
| Chat E2E (read/delete) | B38 | e2e | Chat read 搜索/Chat delete 删除/不依赖 LLM | pending | risk: network |
| 回顾页 E2E | B39 | e2e | daily/weekly/monthly/trend/knowledge-heatmap/growth-curve/activity-heatmap | pending | - |
| CI Pipeline | B40 | integration | PR=backend+frontend+build; main=+E2E(B36/B37); docker-build-test 独立保留 | pending | risk: config |
| 性能基线 | B41 | manual | bundle 大小/API 响应时间/SSE 首字节延迟 | pending | - |
| Goals CRUD API | B45 | unit | 创建三种类型/列出过滤/更新状态/completed→active 重新激活/删除保护/401/403/metric_type 422/auto_tags 必填/checklist_items 必填 | covered | risk: auth |
| Goal 条目关联 + 进度 | B46 | unit | count 关联进度（关联即计数）/checklist 勾选进度/tag_auto SQL 进度/100% 自动完成/进度下降不自动回退/progress-summary 概览/关联到非 count 返回 400/重复关联 409/401/403/时间范围外不计 | covered | — |
| Goal 自动追踪触发 | B47 | unit | create 触发重算/update tags 触发重算（含原来匹配现在不匹配的回退）/不匹配不触发/时间范围外不计/重算失败不影响条目/10 目标 <100ms | covered | — |
| Goals 页面 + 详情 | F34 | manual | 目标列表进度条/创建弹窗（含 checklist 项输入）/tag 选择/详情页环形图/检查项勾选/count 关联条目搜索+关联+取消关联/completed→active 重新激活/无目标引导/API 失败降级/移动端适配/npm run build 通过 | covered | — |
| 首页目标进度卡片 | F35 | manual | 活跃目标卡片/点击跳转/无目标引导/3 个不截断/API 失败不阻塞/npm run build 通过 | covered | — |
| 回顾页目标概览 | F36 | manual | 目标进展卡片/进度变化/无目标隐藏/API 失败不阻塞/npm run build 通过 | covered | — |
