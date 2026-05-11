# 测试覆盖清单

## R057: 导航重构（底部 Tab + FAB + Today 仪表盘）

| Module | Task IDs | Test Type | Required Scenarios | Status | Gaps |
|--------|----------|-----------|--------------------|--------|------|
| 命令栏下线+仪表盘+FAB 简化 | F01 | F2 | Today 无 command UI（成功态+空态+错误态保留 ErrorStateWidget）/FAB 只有 2 子按钮/记灵感+建任务含失败路径/grep 零引用 | completed | — |
| Tab 重构+菜单精简 | F02 | F2 | 5 Tab 名称+图标正确/我的菜单 3 项各入口跳转正确/路由高亮含 /explore /review /goals /settings /notes /inbox/bottom_nav_test 全覆盖 | completed | — |
| QuickActions 死代码清理+CreateTaskSheet 迁出 | F03 | F2 | CreateTaskSheet 独立文件渲染/提交/失败可重试/grep QuickActions/quick_actions 零引用/Today 刷新回归（记灵感+建任务成功触发 loadData） | completed | — |
