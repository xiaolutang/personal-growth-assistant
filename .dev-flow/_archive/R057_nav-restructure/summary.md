# R057 导航重构 归档

- 归档时间: 2026-05-11
- 状态: completed
- 总任务: 4
- 分支: feat/R057-nav-restructure
- workflow: B/skill_orchestrated
- providers: codex_plugin/codex_plugin/codex_plugin

## 仓库提交
- personal-growth-assistant: f0d178f (HEAD on feat/R057-nav-restructure)

## Phase 1 (命令栏下线)
| 任务 | 描述 | commit |
|------|------|--------|
| F01 | 命令栏体系下线 + Today 纯仪表盘 + FAB 简化 | 48f8479 |

## Phase 2 (Tab 重构)
| 任务 | 描述 | commit |
|------|------|--------|
| F02 | 底部 Tab 重构 + 菜单精简 | d1fc35b |

## Phase 3 (代码收敛)
| 任务 | 描述 | commit |
|------|------|--------|
| F03 | QuickActions 死代码清理 + CreateTaskSheet 迁出 | 16f0101 |
| F04 | 路由常量提取 + build 优化 + doneTasks 去重 | f0d178f |

## 关键交付
- Today 页从命令栏交互回归为纯仪表盘（晨报/进度/任务/动态），命令栏体系完全移除
- 底部 Tab 从 5 个（今天/日知/笔记/探索/更多）重构为（今天/对话/任务/探索/我的），菜单从 6 项精简为 3 项
- QuickActions 死代码清除，CreateTaskSheet 迁出为独立文件
- 路由常量提取到 AppRoutes 独立类，消除循环依赖和硬编码路由字符串
