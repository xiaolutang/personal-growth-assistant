# 功能图

> 项目：personal-growth-assistant
> 活跃需求包：R012 goal-tracking
> 最后更新：2026-04-17

## 任务树

```
R012 (goal-tracking)
├── P1: 后端 API
│   ├── [completed] B45 目标 CRUD + 衡量方式 — count/checklist/tag_auto 三种类型
│   ├── [completed] B46 目标条目关联 + 进度计算 — link/unlink/progress-summary
│   └── [completed] B47 Tag 自动追踪触发 — entry tag 变更时异步重算进度 ← B45+B46
└── P2: 前端页面
    ├── [completed] F34 目标管理页面 — GoalsPage + GoalDetail ← B45+B46
    ├── [completed] F35 首页目标进度卡片 — 前3活跃目标 ← B45
    └── [completed] F36 回顾页目标概览 — progress_delta + weekly/monthly ← B45+B46+B47
```

## 依赖图

```
B45 ──→ B47
B46 ──→ B47
B45+B46 ──→ F34
B45 ──→ F35
B45+B46+B47 ──→ F36

无依赖的起点：B45, B46
```

## 统计

| 状态 | 数量 |
|------|------|
| pending | 0 |
| in_progress | 0 |
| completed | 6 |
| **总计** | **6** |

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

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 715 passed | 全部通过 |
| 前端测试 | 231 passed | 全部通过 |
