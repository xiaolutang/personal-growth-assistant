# 测试覆盖清单

## R036: 残留问题全面收口

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 消除私有属性访问 | B100 | unit | is_connected正确状态/ReviewService getter/初始化链路回归/entries导出回归/sync回归/main.py health check公共属性回归/pytest | done | L2, 8 tests, 1213 pytest total |
| get_growth_curve SQL 聚合 | B101 | unit | 有entries按周tag统计/无entries空结果/周边界/掌握度一致/user_id隔离/年边界一致性/跨周归属/同周去重/ISO标签确定性/回归 | done | L1, 19 tests, 1232 pytest total, code-review R4 pass, audit done |
| review_service 拆分 | B102 | unit | import正确/功能不变/路由链路/period校验/pytest | done | L1, 1229 pytest (拆分) + 1130 pytest + 386 vitest + build (修复), code-review pass, audit pending |
| 503 降级共享 hook | F128 | unit+integration | hook检测503+重试恢复/retry不双重嵌套/503→retry→503/503→retry→500/503→retry→success/GraphPage能力地图503降级/build | done | F2, 7 hook tests + 4 GraphPage集成 tests, 397 vitest total, code-review R5 pass |
| EntryDetail 拆分 | F129 | unit+manual | 详情页加载/编辑/关联条目/知识上下文/AI摘要/链接管理/build | pending | F2, ~7 tests |
| Home+Explore 拆分 | F130 | unit+manual | 首页加载/探索页搜索+筛选+批量操作/build | pending | F2, ~5 tests |
| Review+Tasks+Goals 拆分 | F131 | unit+manual | 回顾页切换/任务筛选/目标进度环/build | completed | F2, ~5 tests |
| 移动端拖拽 | M100 | unit | 长按触发/拖拽反馈/释放更新(本地)/刷新恢复默认/切换筛选恢复/analyze | pending | F2, ~5 tests |
| R032+R027 测试补齐 | S33 | unit | B89搜索(~16)/F119过滤UI(~7)/F120批量(~10)/B83导出(~10)/F114-F116导出反馈(~12) | pending | L2, ~55 tests |
| 质量收口 | S34 | integration+smoke | pytest全量/vitest全量/build/Docker smoke | pending | L4 |

## R035: 预存问题修复（R034 Simplify 发现）

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 趋势字段修复 | B96 | unit | 有趋势数据正确渲染/空趋势fallback/回归report导出 | done | L2, 3 tests, 1179 pytest total |
| 掌握度共享模块 | B97 | unit | 阈值矩阵(0/1/3/6+note)/relationship_count折算/KnowledgeService调用路径/ReviewService调用路径/回归 | done | L1, 15 tests, 1190 pytest total |
| heatmap SQL 聚合 | B98 | unit | 有entries正确tag统计/无entries空列表/计数一致/掌握度正确/回归 | done | L1, 5 service tests + 4 API tests + 7 regression fixes, 1213 pytest total |
| tag_stats SQL 聚合 | B99 | unit | 有entries频次排序/无entries空列表/时间范围边界/频次一致/user_id隔离跨用户/回归 | done | L1, 6 service tests + 8 storage tests (real SQLite), 1213 pytest total |
| 质量收口 | S32 | integration+smoke | pytest全量/vitest全量/build/Docker smoke(成长报告趋势+heatmap+AI洞察tag统计) | done | L4, pytest 1213, vitest 386, build success, Docker smoke 3 项全部通过 |

## R034: 技术债收敛 (R029 Residual Risks)

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| useMorningDigest 增强 | F122 | unit | error初始null/成功null/失败string/卸载不更新 | done | F1, 10 tests (7 existing + 3 new), 366 vitest total |
| 统一导出 | F123 | unit | 5组件移除default后build无报错/Review.tsx命名导入 | done | F1, 验收已满足无需代码变更 |
| 依赖注入 | B93 | unit | 构造函数参数/不调deps/growth-report回归200 | done | L2, 3 new tests, 1173 pytest total |
| 合并遍历 | F124 | unit | todayTasks/unprocessedInbox/recentInbox/todayStats等价 | done | F1, 366 vitest passed, build success |
| 定向查询 | B94 | unit | 匹配tag/无匹配/大小写不敏感/部分匹配/去重/最多5条/空tag/异常tag | done | L1, 1176 pytest passed |
| GraphPage 拆分 | F125 | unit+manual | 4 Tab功能不变/build无TS错误 | done | F2, 366 vitest, build success, 1016→304 行 |
| 模型拆分 | B95 | unit | 模型import正确(review_service+review.py)/pytest | done | L1, 1176 pytest passed, 2096→1900 行 |
| api.ts 类型迁移 | F126 | unit | API调用类型正确/gen:types无冲突/build | done | F2, 366 vitest, build success, 1189→500 行 |
| GraphPage Tab 测试 | F127 | unit | 4 Tab切换/focus高亮/搜索防抖/showAll/能力地图筛选+重试/详情面板/时间线 | done | F2, 20 new tests, 386 vitest total |
| 质量收口 | S31 | integration+smoke | pytest全量/vitest全量/build/Docker smoke | done | L4, 1176 pytest, 386 vitest, build success |

## R033: 安全增强收口

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| JWT 黑名单 | B90 | unit | logout后旧token返回401/新token正常/过期token幂等/cleanup清理/并发logout/无token→403/无效token→401/lifecycle启动+取消/回归 | done | L2, 11 new tests, 1125 pytest total |
| 前端 logout | F121 | unit | 有token调logout/无token跳过/500仍清理/pga_token移除/Sidebar await后跳转 | done | F2, 4 new + 2 fixed tests, 363 vitest total |
| Qdrant 懒重连 | B91 | unit | URL未配置启动/断连降级/可用回归/delete跳过/sync_entry断连/sync_to_graph_and_vector跳过/delete_entry双重检查 | done | L2, 23 new tests (16 qdrant + 7 sync), 1169 pytest total after code-review fix |
| Neo4j 降级+路由 | B92 | unit | _get_session ConnectionError/_with_neo4j_fallback空结构/knowledge-map空图200/knowledge-stats空统计200/knowledge-graph 503保留/ConnectionError传播/API层503/回归 | done | L2, 19 new + 4 补测 (2 service + 2 API), 1173 pytest total |
| 质量收口 | S30 | integration+smoke | pytest全量/vitest全量/build/logout+黑名单smoke/Neo4j+Qdrant降级smoke/Sidebar登出smoke/sync断连smoke | done | L4, 1070 pytest, 363 vitest, build success |

## R032: 搜索增强 + Explore 批量操作

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 搜索过滤增强 | B89 | unit | 时间过滤(start+end/只start/只end/不传/闭区间边界/start>end返回空)/标签过滤(有交集/无交集/不传/空数组)/组合过滤(时间+标签+filter_type)/空query+过滤/空query+无过滤/SQLite降级过滤/422非法日期/回归 | planned | L2, ~16 tests |
| 搜索过滤 UI | F119 | unit | 时间快选本周/全部/标签筛选/过滤chip显示/移除chip/清除全部/无过滤一致 | planned | F2, ~7 tests |
| Explore 批量操作 | F120 | unit | 编辑按钮进多选/checkbox可见+禁用单卡动作/批量删除+本地列表更新/删除取消确认/批量转分类+本地刷新/部分失败提示/ESC退出/Tab不清空/空列表禁用编辑 | planned | F2, ~10 tests |
| 质量收口 | S29 | integration+smoke | pytest全量/vitest全量/build/Explore搜索+时间+标签+批量操作smoke | planned | L4 |

## R031: 对话式 Onboarding

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| Onboarding AI Prompt | B88 | unit | is_new_user=true/false/缺失/prompt长度≤500字/page=home+is_new_user=true组合/内容关键词断言/回归 | done | L2, 15 tests, 1097 regression 0 failed |
| 对话式 Onboarding 前端 | F118 | unit | 新用户自动展开+欢迎消息/发送消息后updateMe调用一次/updateMe失败不阻塞/AI流失败不标记完成/老用户正常模式/完成后key重挂载消息清空/FloatingChat隐藏/is_new_user透传/收起展开/移动端<640px | done | F2, 6 new tests, 360 vitest total, build success |
| 质量收口 | S28 | integration+smoke | pytest全量/vitest全量/build/首用smoke(注册→登录→欢迎消息可见) | done | L4, pytest 998, vitest 360, build success |

## R030: AI 晨报增强

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 晨报缓存 | B85 | unit | 缓存命中/缓存失效(跨日)/cached_at字段/并发去重(asyncio.Lock)/缓存清理(LRU)/回归 | done | L2, 11 tests, 983 passed |
| AI 建议个性化 | B86 | unit | 有目标/无目标/高频标签/LLM降级/超时/5xx/异常结构 | done | L2, 9 tests |
| 模式洞察 LLM 增强 | B87 | unit | LLM正常(最多5条string[])/LLM降级(规则引擎)/超时/空数据/5xx/异常结构/回归/时间模式(weekday_activity) | done | L2, 10 tests |
| 晨报展示优化 | F117 | unit+manual | cached_at非null/null/缺失(旧后端)/5条洞察/空洞察/加载态 | done | F2, vitest 354 passed (含 7 个 hook 测试), build success |
| 质量收口 | S27 | integration+smoke | pytest全量/vitest全量/build/Docker smoke | done | L4, pytest 983, vitest 354, build success |

## R029: Simplify 收敛检查

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 四视角审查报告 | S26a | 四视角审查 | 复用/质量/效率/架构各一份报告 | done | L1, 16 findings |
| 收敛修复+全量验证 | S26b | unit+integration+smoke | must_fix逐条闭环/pytest全量/vitest全量/build/Docker smoke | done | L4, pytest 953, vitest 347, build success |

## R027: 数据导出 + 反馈追踪

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 导出 API 增强 | B83 | unit+integration | 单条目导出正常/404/跨用户/长文件名/成长报告/空数据/Neo4j降级/未认证401 | planned | L2, ~10 tests |
| 反馈状态同步 | B84 | unit+contract | 同步成功/pending→reported/in_progress映射/resolved映射/未变更不更新/首次写入updated_at/计数断言/GET回读/超时跳过/远程404/未知status/批量20+/幂等/认证隔离 | done | L2, 20 tests |
| 条目导出按钮 | F114 | unit+manual | 导出点击/loading/错误提示 | planned | F2, ~3 tests |
| Review 导出入口 | F115 | unit+manual | 全量ZIP/成长报告/loading/错误 | planned | F2, ~3 tests |
| 反馈状态增强 | F116 | unit+manual | 自动同步/4状态渲染/updated_at=null不显示时间/非null相对时间/synced_count=0降级/网络错误显示本地缓存 | planned | F2, ~6 tests |
| 质量收口 | S21 | integration+smoke | pytest全量/vitest全量/build/Docker E2E | planned | L4 |

## R026: 收敛修复

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 统一掌握度算法 | S18 | unit | 阈值矩阵/relationship_count折算/全量回归 | done | 13 tests |
| 消除 N+1 查询 | S19 | unit | mock验证/批量stats/死代码确认删除 | done | refactoring only |
| 错误信息脱敏 | B82 | unit | 9个泛化异常/3个ValueError/logger.error | done | error message change |
| 消除重复请求 | F112 | unit | InsightCard/AiSummaryCard消费props | done | refactoring |
| GraphPage 状态拆分 | F113 | unit+manual | Tab切换/领域展开/筛选/重试 | done | refactoring |
| 构建验证 | S20 | integration+smoke | pytest/vitest/build/Docker | done | 923+347+build+Docker |
