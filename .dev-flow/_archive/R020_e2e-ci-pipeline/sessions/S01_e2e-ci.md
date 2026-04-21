# S01: R020 E2E 测试补齐 + CI PR 增强

> 日期：2026-04-20
> 状态：planning

## 需求

全面覆盖 E2E 测试 + CI PR 增强。覆盖 Goals、新类型（decision/reflection/question）、导出功能的 E2E 测试，并将 E2E 纳入 PR 流水线。

## 确认范围

1. Goals E2E — API + 页面全面覆盖（~22 tests）
2. 新类型 E2E — API + 探索页全面覆盖（~18 tests）
3. 导出 E2E — API + UI 全面覆盖（~13 tests）
4. CI PR 增强 — PR 运行 E2E 关键子集 + test_coverage 状态同步

## 执行模式

B / codex_plugin / skill_orchestrated
