# 功能图

> 项目：rizhi
> 活跃需求包：R057 导航重构
> 最后更新：2026-05-11

## 活跃需求包

| 需求包 | 状态 | 任务数 |
|--------|------|--------|
| R057 导航重构 | active | 4 tasks (3 completed, 1 pending) |

### R057: 导航重构 — 模块映射

| 任务 ID | 模块 | 描述 | 状态 | 文件 |
|---------|------|------|------|------|
| F01 | mobile | 命令栏体系下线 + Today 纯仪表盘 + FAB 简化 | completed | today_page.dart, quick_capture_fab.dart, bottom_nav.dart, auth_provider.dart |
| F02 | mobile | 底部 Tab 重构 + 菜单精简 | completed | bottom_nav.dart, bottom_nav_test.dart |
| F03 | mobile | QuickActions 死代码清理 + CreateTaskSheet 迁出 | completed | create_task_sheet.dart, quick_capture_fab.dart, quick_capture_fab_test.dart |
| F04 | mobile | 路由常量提取 + build 优化 + doneTasks 去重 | pending | app_routes.dart, bottom_nav.dart, today_page.dart |

## 归档需求包

| 需求包 | 归档目录 | 状态 |
|--------|---------|------|
| R056 品牌更名为日知 | _archive/R056_brand-rename-to-rizhi | completed |
| R055 交互基础 | _archive/R055_interaction-basics | completed |
| R054 FAB 混合升级 | _archive/R054_fab-hybrid-upgrade | completed |
| R053 Today 命令栏 | _archive/R053_today-command-bar | completed |
| R052 对话隔离+Today 输入 | _archive/R052_chat-isolation-and-today-input | completed |
| R051 代码质量优化 | _archive/R051_code-quality-optimization | completed |
| R050 Flutter 日常可用 | _archive/R050_flutter-daily-usable | completed |
| R049 评估运营化 | _archive/R049_eval-operationalization | completed |
| R048 创建体验升级 | _archive/R048_creation-experience-upgrade | completed |
| R047 任务/探索 Tab 边界重新划分 | _archive/R047_task-explore-reboundary | completed |
| R046 对话面板重构 | _archive/R046_chat-panel-refactor | completed |
| R045 评估 HTML 报告 | _archive/R045_eval-html-report | completed |
| R044 统一 React Agent | _archive/R044_unified-react-agent | completed |

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 1495 passed | 全绿 |
| 前端测试 | 923 passed | 全绿 |
| Flutter 测试 | 19 passed (quick_capture_fab) + 16 passed (bottom_nav) | 全绿 |
