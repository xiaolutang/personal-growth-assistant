# 测试覆盖清单

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
