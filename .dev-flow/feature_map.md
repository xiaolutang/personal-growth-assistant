# 功能图

> 项目：personal-growth-assistant
> 活跃需求包：R015 review-enhancement
> 最后更新：2026-04-17

## 活跃需求包

### R015 回顾增强

| 任务 | 类型 | 模块 | 优先级 | 依赖 | 状态 |
|------|------|------|--------|------|------|
| B52 | 后端 | review | P1 | 无 | completed |
| B53 | 后端 | review | P1 | 无 | completed |
| F40 | 前端 | review | P1 | B52 | completed |
| F41 | 前端 | review | P1 | B53 | completed |
| F42 | 前端 | review | P2 | 无 | pending |

**依赖关系**：
```
B52 ──→ F40（趋势多维）
B53 ──→ F41（热力图升级）
F42（晨报集成，独立）
```

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

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 765 passed | 全绿 |
| 前端测试 | 245 passed | 全绿 |
| E2E 测试 | 8 passed (page-context) | 全绿 |
