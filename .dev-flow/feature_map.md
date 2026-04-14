# 功能图

> 项目：personal-growth-assistant
> 活跃需求包：R004 Phase 2
> 最后更新：2026-04-15

## 任务树

```
R004 Phase 2 (product-evolution-phase2)
├── P2A: Onboarding
│   └── [pending] F09 Onboarding 对话引导 — 新用户首次登录引导
├── P2B: 统一探索 + Export
│   ├── [completed] B18 Export 导出 API — zip/json 双格式
│   ├── [pending] F10 探索页基础 — 灵感/笔记/项目统一浏览 + Sidebar 改造
│   ├── [pending] F11 搜索增强 — 实时搜索 + Cmd+K 全局聚焦 ← F10
│   └── [pending] F12 Export 导出 UI — 导出对话框 + Sidebar 入口 ← B18
└── P2C: 条目关联
    ├── [pending] B19 条目关联 API — GET /entries/:id/related
    └── [pending] F13 条目详情页关联面板 — 相关条目推荐 ← B19
```

## 依赖图

```
B18 ──────→ F12
F10 ──────→ F11
B19 ──────→ F13

无依赖的起点：B18, B19, F09, F10
```

## 统计

| 状态 | 数量 |
|------|------|
| pending | 6 |
| in_progress | 0 |
| completed | 1 |
| **总计** | **7** |

## 归档需求包

| 需求包 | 归档目录 | 状态 |
|--------|---------|------|
| R001 Personal Growth Assistant v1 | _archive/R001_personal-growth-assistant-v1 | completed |
| R003 Production Content Recovery | _archive/R003_production-content-recovery | completed |
| R004 Phase 1A Product Evolution | _archive/R004_product-evolution-phase1a | completed |
| R004 Phase 1B Product Evolution | _archive/R004_product-evolution-phase1b | completed |

## 测试汇总

| 项目 | 测试数 | 状态 |
|------|--------|------|
| 后端测试 | 313+ | 全部通过 |
| 前端测试 | 222 | 全部通过 |
| E2E tests | 8 (6 pass, 2 skip) | 全部通过 |
