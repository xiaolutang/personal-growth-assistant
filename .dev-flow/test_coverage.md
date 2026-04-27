# 测试覆盖清单

## R041: Flutter 页面补齐 + 工程健康

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| Priority 后端 | B117 | unit | priority 筛选/排序/默认排序 | completed | — |
| Inbox API 层 | F163 | unit+integration | fetchInbox/createInboxItem/convertCategory/error | completed | — |
| Notes 页面 | F164 | widget+provider | 空态/错误/加载/列表/搜索/预览 | completed | — |
| Inbox 页面 | F167 | widget+provider | 空态/错误/加载/列表/底部输入 | completed | — |
| Review 页面 | F168 | widget+provider | 加载/错误/周期切换/概览卡片/趋势图 | completed | — |
| Goals 页面 | F170 | widget+provider | 空态/错误/加载/列表/进度条/里程碑 | completed | — |
| 路由+导航 | F171 | widget | 5 Tab/更多菜单/5 个菜单项/子路由状态 | completed | — |
| Provider 集成 | F163-F170 | integration | GoalsNotifier CRUD/ReviewNotifier loadAll/NotesNotifier/InboxNotifier + mock HTTP | completed | — |
| 质量收口 | S42 | integration+smoke | pytest 1375/vitest 612/flutter test 310/build/Docker | completed | — |

## R039: Flutter Explore + 工程维护

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 分支清理 | S38 | manual+review | git branch 干净/architecture.md 4-tab/project_spec R039 | pending | L1 |
| Explore API 层 | F151 | unit+smoke | 条目列表 param mapping/搜索 param mapping/删除 404/更新 category/搜索历史去重截断/批量编排/超时/malformed JSON/smoke 完整流程 | pending | L2 |
| Explore 页面框架 | F152 | widget+smoke | 5 Tab 渲染/Tab 过滤(灵感→inbox)/加载态/空态/错误态/条目点击跳转/导航栏 4-tab/smoke 完整路径 | pending | F2 |
| Explore 搜索 | F153 | unit+widget | 搜索触发/历史去重截断/空搜索/空历史/API 失败不记历史/搜索栏UI交互/历史面板显示隐藏/清空搜索恢复Tab | pending | F2 |
| Explore 批量操作 | F154 | unit+widget+smoke | 批量删除成功+确认/批量转分类+分类选择/搜索模式下批量操作/部分失败保留选中+重试/全部失败/0 条禁用/重试成功后退出/多选模式UI进出/smoke 完整批量路径 | pending | F2 |
| 质量收口 | S39 | integration+smoke | pytest/vitest/flutter test/build/Docker | pending | L4 |

## R038: 工程健康收口 + 小功能补齐

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| architecture.md 更新 | B108 | review | 版本号正确/R037 内容包含/≤120 行/不变量完整 | pending | L1 |
| .gitignore 修复 | B109 | unit+manual | gitignore 条目正确/git status 干净/pytest+vitest 回归 | pending | L1 |
| plan 文档清理 | S36 | review | api_contracts R037=done+R038=planned/归档快照存在/project_spec R038/feature_map 数据正确 | pending | L1 |
| 笔记模板后端 | B110 | unit | GET 模板列表/category 过滤/POST 带 template_id/POST 不带/无效 template_id/不匹配/category 优先/认证隔离 | pending | L2 |
| 笔记模板前端 | F148 | unit | 模板列表渲染/content 预填/非 note 不显示/默认行为不变/API 失败降级/空列表/category 切换/已有 content 不覆盖 | pending | F2 |
| 成功指标后端 | B111 | unit | POST 存储/user_id 隔离/metadata 可选/401/写入失败不影响/表自动创建/422 无效 event_type/422 非 object metadata | pending | L2 |
| 成功指标前端 | F149 | unit | trackEvent 调用/API 失败静默/6 埋点位置正确/离线丢弃不发请求 | pending | F2 |
| 质量收口 | S37 | integration+smoke | pytest 全量/vitest 全量/build/scripts/test-docker.sh | pending | L4 |
