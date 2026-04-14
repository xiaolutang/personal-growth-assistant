# R004 — 产品演进 Phase 2：统一探索 + Export + 条目关联 + Onboarding

## 状态：completed
## 分支：feat/R004-product-evolution-phase2
## 完成时间：2026-04-15

## 范围

Phase 2 交付四个功能模块：Onboarding 引导、统一探索页（搜索增强）、Export 导出、条目关联推荐。

## 任务清单

| ID | 类型 | 模块 | 名称 | 验证级别 | Codex 审计轮次 |
|----|------|------|------|----------|---------------|
| B18 | 后端 | export | Export 导出 API — zip/json 双格式 | L2 | R1 partial → done |
| B19 | 后端 | entry-relations | 条目关联 API — GET /entries/:id/related | L2 | R4 pass |
| F09 | 全栈 | onboarding | Onboarding 对话引导 — 新用户首次登录引导 | F2 | R1 partial → done |
| F10 | 前端 | explore | 探索页基础 — 统一浏览 + Sidebar 改造 | F2 | R1 done |
| F11 | 前端 | explore | 搜索增强 — Cmd+K 全局聚焦 + 关键词高亮 | F2 | R4 pass |
| F12 | 前端 | export | Export 导出 UI — 导出对话框 + Sidebar 入口 | F1 | R2 pass |
| F13 | 前端 | entry-relations | 条目详情页关联面板 — 相关条目推荐 | F2 | R4 pass |

## Commit 日志

| Commit | 任务 ID | 摘要 |
|--------|---------|------|
| 48ba9eb | plan | Phase 2 规划 |
| 3d46fd1 | B18 | Export 导出 API — zip/json 双格式 |
| e4554ca | F09 | Onboarding 引导 + inbox-{id}.md 全链路收敛 |
| 83029f8 | F10 | 探索页基础 — 统一浏览 + Sidebar 改造 |
| 44a8b5a | F12 | Export 导出 UI — 导出对话框 + Sidebar 入口 |
| ae52c4e | F11 | 搜索增强 — Cmd+K + 关键词高亮 |
| ec9e739 | B19 | 条目关联 API — GET /entries/:id/related |
| 4cc90cd | F13 | 条目详情页关联面板 — 相关条目推荐 |
| e3a4193 | fix | F11/B19/F13 Codex Plugin 审查修复 |
| acef07c | fix | B19 隔离测试 + F12 日期范围 + evidence 审计 |
| 89ad3c7 | fix | B18/F09/F10 Codex Plugin 审计补齐 — 7/7 commit_ready |

## 关键决策

- 探索页使用独立本地状态管理列表数据，不复用全局 taskStore，避免筛选/搜索覆写影响其他页面
- Sidebar 从 6 项缩减为 4 项（今天/探索/任务/回顾），旧路由 /inbox /notes /projects 重定向到 /explore
- Export 双格式：markdown 真正流式（tempfile + 8KB 分块 yield + finally 清理），json 从 SQLite 查询
- 条目关联三层策略：同项目 → 标签重叠 → 向量相似，支持 Qdrant 不可用时降级到前两级
- Onboarding inbox 正则三处入口收敛（markdown.py 权威正则，user_storage/storage_factory 导入）
- 所有任务 Codex Plugin 审计通过，commit_ready: true

## 测试覆盖

- 后端：495 tests passed, 20 skipped
- 前端：231 tests passed
- npm run build: PASS

## 工作流

- 模式：XLFoundry Mode B (codex_plugin)
- review_provider / audit_provider / risk_provider: codex_plugin
- 7/7 任务经 Codex Plugin 代码审查 + 审计闭环
