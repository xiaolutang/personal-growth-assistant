# 功能图

> 项目：personal-growth-assistant
> 活跃需求包：R013 decision-reflection-entries
> 最后更新：2026-04-17

## 任务树

```
R013 (decision-reflection-entries)
├── P1: 后端
│   ├── [completed] B48 月报 AI 总结补齐 — monthly 接入 _generate_ai_summary
│   └── [completed] B49 思考/决策记录后端 — decision/reflection/question 三种新类型
└── P2: 前端
    ├── [completed] F37 月报 AI 总结展示 — Review.tsx 月报 Tab 展示 AI 总结卡片
    └── [completed] F38 思考/决策记录前端 — Tab/快捷操作/差异化渲染/专属图标颜色
```

## 依赖图

```
B48 ──→ F37
B49 ──→ F38

无依赖的起点：B48, B49
```

## 统计

| 状态 | 数量 |
|------|------|
| pending | 0 |
| in_progress | 0 |
| completed | 4 |
| **总计** | **4** |

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

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 733 passed | 全部通过 |
| 前端测试 | 231 passed | 全部通过 |
| Codex Review | 4 rounds | conditional_pass → simplify → pass |
