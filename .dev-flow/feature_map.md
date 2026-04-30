# 功能图

> 项目：personal-growth-assistant
> 活跃需求包：R048 创建体验升级
> 最后更新：2026-04-30

## 活跃需求包

| 需求包 | 状态 | 任务数 |
|--------|------|--------|
| R048 创建体验升级 | active | 5 tasks (1 completed, 4 pending) |
| R041 Flutter 页面补齐 + 工程健康 | completed | 11 tasks (pytest 1375, vitest 612, flutter test 310) |

### R048: 创建体验升级 — 模块映射

| 任务 ID | 模块 | 描述 | 状态 | 文件 |
|---------|------|------|------|------|
| S01 | shared-components | CreateDialog 通用创建对话框（7 种类型，动态字段，复用 categoryConfig + taskStore） | completed | frontend/src/components/CreateDialog.tsx |
| F02 | tasks-page | 任务页 '+New' 按钮 + 上下文感知创建 | pending | — |
| F03 | home-page | 首页智能输入栏（QuickCaptureBar） | pending | — |
| F04 | explore-page | 探索页创建入口 | pending | — |
| F05 | shared-components | 智能提示（dateParser + useSmartSuggestions） | pending | — |

## 归档需求包

| 需求包 | 归档目录 | 状态 |
|--------|---------|------|
| R035 预存问题修复 | _archive/R035_preexisting-fixes | completed |
| R001 Personal Growth Assistant v1 | _archive/R001_personal-growth-assistant-v1 | completed |
| R003 Production Content Recovery | _archive/R003_production-content-recovery | completed |
| R004 Phase 1A Product Evolution | _archive/R004_product-evolution-phase1a | completed |
| R004 Phase 1B Product Evolution | _archive/R004_product-evolution-phase1b | completed |
| R004 Phase 2 Product Evolution | _archive/R004_product-evolution-phase2 | completed |
| R005 Phase 3 | _archive/R005_product-evolution-phase3 | completed |
| R006 Product Polish | _archive/R006_product-polish | completed |
| R007 Engagement Experience | _archive/R007_engagement-experience | completed |
| R008 Intelligence Omni | _archive/R008_intelligence-omni | completed |
| R009 Chat User ID Threading | _archive/R009_chat-user-id-threading | completed |
| R010 Engineering Foundation | _archive/R010_engineering-foundation | completed |
| R011 Entry Context & Morning Report | _archive/R011_entry-context-and-morning-report | completed |
| R012 Goal Tracking | _archive/R012_goal-tracking | completed |
| R013 Decision Reflection Entries | _archive/R013_decision-reflection-entries | completed |
| R014 Page Context AI | _archive/R014_page-context-ai | completed |
| R015 Review Enhancement | _archive/R015_review-enhancement | completed |
| R019 离线增强 + PWA | _archive/R019_offline-pwa | completed |
| R020 E2E 测试补齐 + CI PR 增强 | _archive/R020_e2e-ci-pipeline | completed |
| R021 技术债清理 | _archive/R021_tech-debt-cleanup | completed |
| R022 体验打磨 + 遗留项 | _archive/R022_polish-deferred | completed |
| R025 第三阶段收口 | _archive/R025_stage3-completion | completed |
| R026 收敛修复 | _archive/R026_convergence-fixes | completed |
| R027 数据导出 + 反馈追踪 | _archive/R027_export-feedback-tracking | completed |
| R028 工程清理 | _archive/R028_engineering-cleanup | completed |
| R029 Simplify 收敛检查 | _archive/R029_simplify-convergence | completed |
| R030 AI 晨报增强 | _archive/R030_ai-morning-report | completed |
| R031 对话式 Onboarding | _archive/R031_conversational-onboarding | completed |
| R033 安全增强收口 | _archive/R033_security-hardening | completed |
| R034 技术债收敛 | _archive/R034_tech-debt-residual | completed |

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 1375 passed | 全绿 |
| 前端测试 | 763 passed | 全绿 |
| Flutter 测试 | 310 passed | 全绿 |
