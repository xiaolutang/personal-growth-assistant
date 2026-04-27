# 归档索引

## 进行中需求包

（无）

## 已完成需求包

### R040: Web 功能增强 + 工程清理

- 状态: 已完成
- 分支: `feat/R040-web-enhancement`
- 主题: 任务优先级筛选 + 目标进度可视化 + 里程碑系统 + 知识推荐引擎 + AI 上下文持久化 + 移动端体验 + 质量收口
- 目录: `R040_web-enhancement-cleanup/`
- 完成时间: 2026-04-27
- 任务数: 15 (completed: 13, cancelled: 1, blocked: 1 → S40 cancelled)
- Code Review: 13 任务逐个 Agent review + 16 项 finding 全部修复
- 验证: pytest 1395(1 flaky) + vitest 612 + build + Docker smoke

### R039: Flutter Explore + 工程维护

- 状态: 已完成
- 分支: `feat/R039-flutter-explore`
- 主题: Flutter Explore 页面完整功能 + 工程维护
- 目录: `R039_flutter-explore-maintenance/`
- 完成时间: 2026-04-27
- 任务数: 6 (S38, F151, F152, F153, F154, S39)
- Codex 审核: Round 1 11 finding → 全部修复 → Round 2 PASS
- 验证: pytest 1200 + vitest 612 + flutter test + build + Docker smoke

### R038: 工程健康与功能增强

- 状态: 已完成
- 分支: `chore/R038-engineering-health`
- 主题: 架构文档更新 + gitignore修复 + 笔记模板 + 用户埋点 + 质量收口
- 目录: `R038_engineering-health-and-features/`
- 完成时间: 2026-04-26
- 任务数: 8 (B108, B109, S36, B110, F148, B111, F149, S37)
- Codex 审核: code-review 4 项 finding 全部修复
- 验证: pytest 1299 + vitest 612 + build + Docker smoke

### R036: 残留问题全面收口

- 状态: 已完成
- 分支: `chore/R036-residual-cleanup`
- 主题: 处理所有已记录但未解决的残留风险和技术债务
- 目录: `R036_residual-cleanup/`
- 完成时间: 2026-04-26
- 任务数: 10 (B100-B102, F128-F131, M100, S33-S34)
- 范围: 架构修复 + 503降级 + 性能优化 + 页面拆分 + 移动端拖拽 + 测试补齐
- Codex 审核: M100 5轮 code-review + S34 5轮 code-review + audit
- 验证: pytest 1133 + vitest 475 + flutter test 170 + build + Docker smoke

### R037: 全面补齐与功能增强

- 状态: 已完成
- 分支: `feat/R037-comprehensive-completion`
- 主题: 技术债清理 + UX打磨 + 离线批量 + P1功能(任务到期/笔记双链) + 质量收口
- 目录: `R037_comprehensive-completion/`
- 完成时间: 2026-04-26
- 任务数: 18 (completed: 14, cancelled: 4)
- 范围: B104 tech-debt, F132 search, F134-F141 ux-polish, F142-F144 offline-batch, B105/F145 task-due-date, B107/F147 note-link, S35 quality
- Codex 审核: xlfoundry-code-review conditional_pass + xlfoundry-audit (6 issues found & fixed)
- 验证: pytest 1180 + vitest 597 + build OK

### R026: 收敛修复

- 状态: 已完成
- 分支: `feat/R026-convergence-fixes`
- 主题: Simplify 发现的 5 个残留收敛问题
- 目录: `R026_convergence-fixes/`
- 完成时间: 2026-04-22
- 任务数: 6 (S18, S19, B82, F112, F113, S20)
- 关键改动: 掌握度算法统一、N+1 查询消除、错误脱敏、重复请求消除、状态拆分
- Codex 审核: partial → 证据补齐后通过
- 额外修复: static_app.py trailing slash 路由中间件
- 验证: 923 后端 + 347 前端测试通过, Docker E2E 验证通过

### R025: 第三阶段收口

- 状态: 已完成
- 分支: `feat/R025-stage3-completion`
- 主题: Phase 8 图谱增强 + Phase 10 回顾 AI 总结增强
- 目录: `R025_stage3-completion/`
- 完成时间: 2026-04-22
- 任务数: 8 (S15-S17, B81, F108-F111)
- Phase: 洞察API → 洞察卡片 → 能力地图API → 能力地图视图 → 图谱AI → 总结增强 → 测试收口

### R024: Flutter 移动端 MVP

- 状态: 已完成
- 分支: `feat/R024-flutter-mobile-mvp`
- 主题: 录入优先的独立 Flutter 移动端应用
- 目录: `R024_flutter-mobile-mvp/`
- 完成时间: 2026-04-22
- 任务数: 12 (S11-S14, F99-F107)
- Phase: Foundation → Infrastructure+Auth → Today → Chat → Tasks+Detail → Quality
- Codex 审核: code-review 6 项 finding 全部修复
- 新增测试: 158 Flutter 测试
- 验证: 866 后端 + 347 前端 + 158 Flutter 测试通过

### R023: AI 页面内嵌 + 交互模式升级

- 状态: 已完成
- 分支: `feat/R023-ai-page-embedded`
- 主题: AI 交互从全局浮动面板改为各页面内嵌，每个页面有独立 AI 角色
- 目录: `R023_ai-page-embedded/`
- 完成时间: 2026-04-22
- 任务数: 8 (B87, F93-F98, S10)
- 关键改动: PageChatPanel 通用组件、4 页面 AI 内嵌、PageAIAssistant 移除
- Codex 审核: 首轮 fail 3 项 → 修复后通过
- 新增测试: 9 后端 + 10 前端
- 验证: 866 后端 + 347 前端测试通过

### R022: 体验打磨 + 遗留项

- 状态: 已完成
- 分支: `feat/R021-tech-debt-cleanup`
- 主题: 代码质量 + 性能优化 + 架构整理 + 测试质量，11 项技术债整改
- 目录: `R021_tech-debt-cleanup/`
- 完成时间: 2026-04-21
- 任务数: 11 (S07, B78, F66-F72, B79, S08)
- 验证: 857 后端 + 326 前端测试通过

### R015: Review Enhancement

- 状态: 已完成
- 分支: `feat/R015-review-enhancement`
- 主题: 回顾增强 — 趋势多维扩展 + 知识热力图 Neo4j 升级 + 晨报集成
- 目录: `R015_review-enhancement/`
- 完成时间: 2026-04-18
- 任务数: 5 (B52, B53, F40, F41, F42)
- 新增测试: 45 个后端测试 (B52 13 + B53 32)
- 关键改动: TrendPeriod 多分类 + 周环比、Neo4j 热力图降级、多线趋势图、晨报卡片

### R011: Entry Context & Morning Report

- 状态: 已完成
- 分支: `feat/R011-entry-context-and-morning-report`
- 主题: 条目关联增强 + AI 晨报升级 — 知识图谱缩略图 + 手动关联 + 学习连续天数 + 每日聚焦 + 模式洞察
- 目录: `R011_entry-context-and-morning-report/`
- 完成时间: 2026-04-16
- 任务数: 6 (B42, B43, B44, F31, F32, F33)
- Codex 审核: 代码质量通过 + 2 项 gitignore 防护修复
- 新增测试: 38 个后端测试 + 231 前端测试全通过
- 新增 API: 5 个 (entry links CRUD + knowledge context)
- 新增前端组件: KnowledgeGraphThumbnail + LinkEntryDialog

### R010: Engineering Foundation

- 状态: 已完成
- 分支: `feat/R010-engineering-foundation`
- 主题: 工程化提升 — E2E 测试覆盖 + API 可观测性 + CI/CD + 性能基线
- 目录: `R010_engineering-foundation/`
- 完成时间: 2026-04-16
- 任务数: 8 (B34-B41)
- Codex 代码审核轮次: 6 轮（4 项 finding 全部修复并通过）
- 关键修复: force_intent DEBUG 门控、Neo4j/Qdrant 真实连接探测、E2E DATA_DIR 隔离、浏览器级 UI 测试

### R008: Intelligence Omni

- 状态: 已完成
- 分支: `feat/R008-intelligence-omni`
- 主题: 智能全栈增强 — 知识图谱+AI摘要+MCP+移动端
- 目录: `R008_intelligence-omni/`
- 完成时间: 2026-04-16
- 任务数: 8 (B28, B29, B30, B31, F27, F28, F29, F30)
- Codex 审核轮次: 4 轮（计划审核 3 轮 + 代码审核 4 轮）
- 关键修复: MCP 用户隔离、Neo4j 降级、AI 摘要缓存失效、时区统一

### R004: Product Evolution Phase 1B

- 状态: 已完成
- 分支: `feat/R004-product-evolution-phase1b`
- 主题: 前端功能交付 — 灵感转化 UI + 回顾页趋势折线图
- 目录: `R004_product-evolution-phase1b/`
- 完成时间: 2026-04-15
- 任务数: 2 (F07, F08)

### R004: Product Evolution Phase 1A

- 状态: 已完成
- 分支: `feat/R004-product-evolution-phase1a`
- 主题: 补闭环 — 趋势 API、灵感转化、反馈闭环、首页改版
- 目录: `R004_product-evolution-phase1a/`
- 完成时间: 2026-04-14
- 任务数: 7 (S05, B14, B15, B16, F05, F06, B17)

### R003: Production Content Recovery

- 状态: 已完成
- 分支: `fix/R003-production-content-recovery`
- 主题: 修复认证上线后历史内容在线上不可见的问题
- 目录: `R003_production-content-recovery/`
- 完成时间: 2026-04-14

### R001: Personal Growth Assistant v1

- 状态: 已完成
- 分支: —
- 主题: 个人成长助手 v1 核心功能
- 目录: `R001_personal-growth-assistant-v1/`
- 完成时间: 2026-04-13
- 任务数: 36 (P1 → P11)

## R030: AI 晨报增强
- 归档目录: _archive/R030_ai-morning-report
- 状态: completed (2026-04-24)
- 分支: feat/R030-ai-morning-report → main
- 任务: B85(缓存), B86(AI个性化), B87(模式洞察LLM), F117(前端优化), S27(质量收口)
- 测试: pytest 1082 + vitest 354 + build success
- Simplify: 5 项收敛修复（反向依赖消除、tag 统计去重、LLM 降级逻辑修正、日志补充、导入清理）

## R029: Simplify 收敛检查
- 归档目录: _archive/R029_simplify-convergence
- 状态: completed (2026-04-23)
- 任务: S26a(审查报告), S26b(收敛修复+全量验证)
