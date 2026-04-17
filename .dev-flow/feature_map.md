# 功能图

> 项目：personal-growth-assistant
> 活跃需求包：R014 page-context-ai
> 最后更新：2026-04-17

## 任务树

```
R014 (page-context-ai)
├── P1: 后端上下文增强
│   ├── [completed] B50 页面上下文数据注入+更新路径打通 — _build_page_context_hint 改实例方法，Entry/Home 数据注入，_handle_update page_context fallback
│   └── [completed] B51 LLM页面感知系统提示词 — task_parser_graph 接受 page_context_hint，intent_service extra_system_hint 增强页面指导
└── P2: 前端交互增强
    └── [completed] F39 快捷建议Chips+页面状态同步 — PageSuggestions组件，chatStore.pageExtra，Explore页状态同步
```

## 依赖图

```
B50 ──→ B51 ──→ F39

起点：B50（无外部依赖）
```

## 统计

| 状态 | 数量 |
|------|------|
| pending | 0 |
| in_progress | 0 |
| completed | 3 |
| **总计** | **3** |

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

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 815 passed | B50 相关 22 unit + 12 API 全通过 |
| 前端测试 | 231 passed | 全部通过 |
