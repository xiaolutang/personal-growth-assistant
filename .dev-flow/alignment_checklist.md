# 对齐清单

## R057: 导航重构（底部 Tab + FAB + Today 仪表盘）

### 用户路径对齐

- [x] F01: 打开 Today 页 → 无底部输入栏 → 只有晨报/进度/任务/动态
- [x] F01: Today 成功态、空态为纯仪表盘；页面加载失败时标准错误态+刷新（无命令执行错误条）
- [x] F01: 任意页面点 FAB → 展开只有记灵感+建任务（无 AI 创建）
- [x] F01: 建任务失败时显示错误提示
- [x] F01: 记灵感/建任务成功后 Today 最近动态自动刷新
- [x] F01: flutter analyze + flutter test 通过
- [x] F01: grep commandBarProvider/CommandResult 零引用
- [x] F02: 底部 Tab 显示 今天/对话/任务/探索/我的
- [x] F02: 点探索 Tab → 进入 /explore 页面（已有内容不变）
- [x] F02: /notes 和 /inbox 深层链接渲染各自 Page 并高亮探索 Tab
- [x] F02: 点我的 Tab → 弹出菜单只有 回顾/目标/设置
- [x] F02: 点我的→回顾 → /review；我的→目标 → /goals；我的→设置 → /settings（高亮我的 Tab）
- [x] F02: 点对话 Tab → 进入 chat 页面（完整 AI 对话）
- [x] F02: flutter analyze + flutter test 通过
- [x] F03: quick_actions.dart 已删除，QuickActions 零引用
- [x] F03: CreateTaskSheet 迁出为独立文件 create_task_sheet.dart
- [x] F03: 建任务失败时 BottomSheet 保持可重试（回归 F01 契约）
- [x] F03: 记灵感/建任务成功后 Today 自动刷新（回归 F01 契约，有自动化断言）
- [x] F03: flutter analyze + flutter test 通过
