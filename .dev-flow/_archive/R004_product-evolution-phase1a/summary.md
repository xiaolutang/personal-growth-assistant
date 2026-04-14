# R004 — 产品演进 Phase 1A：补闭环

## 状态：completed
## 分支：feat/R004-product-evolution-phase1a
## 完成时间：2026-04-14

## 范围
补齐核心闭环 — 回顾趋势 API、灵感转化、反馈闭环、首页改版「今天」

## 任务清单

| ID | 类型 | 模块 | 名称 | 验证级别 |
|----|------|------|------|----------|
| S05 | 契约 | review | Phase 1A 契约与模型定义 | L1 |
| B14 | 后端 | review | 回顾趋势 API + ReviewService user_id 修复 | L2 |
| B15 | 后端 | entry-management | 灵感转化 API — category 变更 + 文件迁移 | L2 |
| B16 | 后端 | feedback-loop | 反馈闭环后端 — feedback 表 + 双写 + 列表查询 | L2 |
| F05 | 前端 | home | 首页改版「今天」— 行动中心 | F2 |
| F06 | 前端 | feedback-loop | FeedbackButton 双 Tab — 提交 + 我的反馈 | F1 |
| B17 | 后端 | content-recovery | 修复 R003 迁移遗漏 — inbox 文件未复制到用户目录 | L2 |

## Commit 日志

| Commit | 任务 ID | 摘要 |
|--------|---------|------|
| 852307f | S05 | Phase 1A 契约与模型定义 |
| 3e919fc | B14 | 回顾趋势 API + ReviewService user_id 修复 |
| f2a4861 | B15 | 灵感转化 API — category 变更 + 文件迁移 |
| bcc17b5 | B16 | 反馈闭环后端 — feedback 表 + 双写 + 列表查询 |
| fd71dbc | F05 | 首页改版「今天」— 行动中心 |
| ddbc07b | F06 | FeedbackButton 双 Tab — 提交 + 我的反馈 |
| f11b87f | B17 | 修复 R003 迁移遗漏 — inbox Markdown 文件未复制到用户目录 |
| a78c9ac | simplify | 收敛清理 — 移除死代码 + 修正测试断言 |

## 关键决策

- 灵感转化不使用 os.rename 原子移动，而是 write_new + delete_old（更安全）
- read_entry 新增 data/ 根目录回退兜底（防御 R003 类迁移遗漏）
- 反馈 API 使用 raw fetch 而非 openapi-fetch（测试 mock 兼容性）

## 下一阶段

Phase 1B：
- T04 [前端] 灵感转化 UI — Inbox 页操作入口
- T06 [前端] 回顾页趋势折线图
