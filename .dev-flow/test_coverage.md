# 测试覆盖清单

## R051: 项目代码优化

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| goalsProvider 隔离 | S01 | unit+F1 | goalDetailProvider 独立创建/GoalsPage loading 隔离/GoalsPage error 隔离/详情页正常渲染/详情页变更同步回列表（mutation-sync-back） | done | — |
| copyWith sentinel | S02 | unit+F1 | 不传 error 保持原值/传 null 清除/Provider 行为回归 | done | — |
| 弃用 API + HybridSearch 复用 | B03 | unit+L2 | asyncio 替换回归/HybridSearchService 注入行为验证 | done | — |
| feedback sync 并发 + 连接管理 | B04 | unit+L2+network | gather 并发/semaphore 限流/timeout/non-200/unknown status/mixed success-failure/连接管理回归 | done | — |
| taskStore 优化 + React.memo | F05 | unit+F1 | store 移除 isFetching 回归/Tasks.tsx 加载状态/Explore 页面加载状态(useExploreSearch)/Home.tsx 加载状态/React.memo 渲染/TaskCard selector | done | — |
| 死代码清理 | F06 | build | build 成功/FloatingChat 不受影响/现有测试通过 | done | — |
| 共享组件提取 | F07 | unit+F1 | EmptyState/ErrorState 渲染测试/ErrorState retry 回调/9 页面渲染回归（含 goal_detail/entry_detail） | done | — |
| formatDate 统一 | F07b | unit+F1 | 各格式输出测试/边界值（刚刚/跨年）/6 处替换（含 entry_detail_page/review_page） | done | — |
| ExplorePage + sseService | F08 | unit+F1+smoke | per-tab 缓存隔离(含 loading/error)/首次 API → 缓存命中无重复请求/下拉刷新清缓存/加载失败 error 处理/失败后刷新恢复/SSE 单订阅回归/smoke 链路 | done | — |
| MorningDigestCard + BaseDialog | F09 | unit+F2 | 合并后两种模式渲染/ESC 关闭/focus trap/backdrop-click 关闭/backdrop-click 禁用/BaseDialog 消费方回归（CreateDialog/ConvertDialog/ExportDialog） | done | — |
| Neo4j 降级 + JSON 去重 | B10 | unit+L2 | 5 方法 Neo4j fallback 矩阵（get_knowledge_graph/get_related_concepts/get_learning_path/get_entry_knowledge_context/get_knowledge_map）/goal_service JSON 去重回归 | done | — |
| 质量收口 | S11 | integration | pytest/vitest/flutter test/analyze/build | done | — |

## R050: Flutter 日常可用

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 注册页 + 忘记密码 | F01 | unit+F2 | 注册页渲染/注册成功流程/注册失败/表单校验/忘记密码提示 | done | 10 tests |
| 全局 FAB 快速捕获 | F02 | unit+F1 | FAB 可见性/BottomSheet 交互/输入提交/空输入禁用/API 失败 | done | 13 tests (quick_capture_fab_test) |
| 首页升级 | F03 | unit+F2 | 晨报四态/快捷录入提交/下拉刷新 | done | 23 tests (today_provider) |
| 目标详情独立页 | F04 | unit+F2 | 目标信息/里程碑 CRUD/关联条目/空态 | done | 13 tests |
| 到期通知 + 设置 | F05 | unit+F2+first_use | 通知去重/查询/权限/设置页渲染/退出登录/通知开关 | done | 18 tests (notification + settings) |
| 质量收口 | S06 | integration | flutter analyze 0 warnings/flutter test 全绿/pytest 1431/vitest 905/build | done | — |

## R048: 创建体验升级

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| CreateDialog 通用组件 | S01 | unit+F1 | 7 种类型动态字段渲染/inbox 回车快速创建/task 优先级日期/project 描述/decision 内容/note 内容/reflection 内容/question 描述/类型切换字段显隐/空标题校验/创建失败不关闭/ESC 关闭重置/再次打开字段清空/依赖 store 内置刷新/移动端全屏适配 | done | 32 tests, 763/763 suite pass |
| 任务页 +New | F02 | unit+F2 | 子 Tab 感知类型/创建后列表刷新/网络失败错误提示可重试/提交中防重复 | pending | — |
| 首页智能输入栏 | F03 | unit+F2+network | 默认模式回车创建 inbox/展开模式创建 task+优先级+日期/空输入 disabled/网络失败恢复可用 | done | 16 tests + 5 tests |
| 探索页创建 | F04 | unit+F2+integration | inbox/reflection/question tab +New 创建/搜索结果态不显示 +New | done | 18 tests + 2 integration |
| 智能提示 | F05 | unit | 日期解析/决策建议/任务建议/点击建议切换类型 | pending | — |

## R047: 任务/探索 Tab 边界重新划分

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| type_history + convert API | S01 | unit+L2 | 正常转换/非法转换/旧文件兼容/带字段转换 | pending | — |
| category_group 查询 | B02 | unit+L2 | actionable 只返回 task+decision+project/knowledge 只返回 inbox+note+reflection+question | pending | — |
| Tasks 数据层 + 子 Tab | F03 | unit+F2 | actionable 列表加载/子 Tab 切换/URL 恢复 | pending | — |
| Decision/Project 卡片 | F04-F05 | unit+F2 | 未决定按钮/进度显示/展开子任务 | pending | — |
| 探索 Tab 精简 | F06 | unit+F2 | 5 个 tab/列表过滤/搜索全类型 | pending | — |
| 转化对话框 | F07 | unit+F2+network | 单条/批量转化/网络超时 | pending | — |
| 视图选择器 + 分组 | F08-F09 | unit+F2 | 分组头/时间线视图 | pending | — |
| task→reflection 流 | F10 | unit+F2 | 完成弹框/写复盘跳转 | pending | — |
| 详情页类型感知 | F11 | unit+F2 | 类型操作栏/type_history 时间线 | pending | — |
| 搜索分组展示 | F12 | unit+F2+network | 全类型分组/跳转 | pending | — |
| 集成验证 | S13 | L4+smoke | 3 条用户旅程 E2E | pending | — |
