# 功能图

> 项目：personal-growth-assistant
> 活跃需求包：R030 AI 晨报增强
> 最后更新：2026-04-24

## 活跃需求包

### R030: AI 晨报增强

```
R030 (feat/R030-ai-morning-report)
├── P1: 后端增强
│   ├── B85 晨报缓存机制 [completed]
│   ├── B86 AI 建议个性化 [completed]
│   └── B87 模式洞察 LLM 增强 [completed]
├── P2: 前端优化
│   └── F117 晨报展示优化 [completed]
└── P3: 质量收口
    └── S27 全量验证 [completed]
```

**依赖图：**
```
B85 → B86 → B87 → F117 → S27
```
（串行执行，B86/B87 共享 review_service.py 不并行）

## 归档需求包

| 需求包 | 归档目录 | 状态 |
|--------|---------|------|
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

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 1082 passed | 全绿 |
| 前端测试 | 347 passed | 全绿 |
| E2E 测试 | 113 passed | 全绿 |
