# R036 残留问题全面收口

> 创建时间：2026-04-25
> 完成时间：2026-04-26
> 状态：completed
> 分支：chore/R036-residual-cleanup

## 概要

处理所有已记录但未解决的残留风险和技术债务，包括架构修复、性能优化、代码组织和测试补齐。

## 任务清单

| ID | 模块 | 名称 | 状态 |
|----|------|------|------|
| B100 | backend | 消除 deps.py 私有属性访问 | completed |
| B101 | backend | get_growth_curve SQL 聚合 | completed |
| B102 | backend | review_service 拆分（1845→子模块） | completed |
| F128 | frontend | 503 降级共享 hook（7 页覆盖） | completed |
| F129 | frontend | EntryDetail 组件拆分（1201→子模块） | completed |
| F130 | frontend | Home+Explore 组件拆分 | completed |
| F131 | frontend | Review+Tasks+Goals ProgressRing 去重 | completed |
| M100 | mobile | 移动端拖拽排序 | completed |
| S33 | quality | R032+R027 测试补齐（63 tests） | completed |
| S34 | quality | 质量收口 | completed |

## 提交记录

| 提交 | 说明 |
|------|------|
| f971935 | merge: R018 缺陷修复+质量收口 |
| e49ebd6 | fix(tests): 修复 code-review 发现的测试结构问题 |
| 68b2cf7 | test(quality): F57 前端组件测试补充 + B70 质量收口验证 |
| dd3655d | test(quality): B69 补充 API 集成测试覆盖缺口 |
| 182b638 | fix(frontend): B68 任务页和探索页加载态添加 spinner |
| ed28828 | test(quality): S33 R032+R027 测试覆盖补齐 |
| da291ac | chore(tracking): F131 完成状态回写 |
| 0de5047 | feat(frontend): F131 Review+Tasks+Goals 拆分去重 |
| 1903a70 | chore(tracking): F130 完成状态回写 |
| 160a535 | feat(frontend): F130 Explore.tsx 组件拆分 |
| da52153 | chore(tracking): F129 完成状态回写 |
| 158a3fe | feat(frontend): F129 EntryDetail.tsx 组件拆分 |
| 0a50c99 | feat(frontend): F128 503 降级共享 hook |
| bcc50eb | refactor(backend): B102 review_service 拆分 |
| fbcf9f3 | refactor(backend): B101 get_growth_curve SQL 聚合 |
| d48e2f4 | refactor(backend): B100 消除私有属性访问 |
| 7da9494 | feat(mobile): M100 任务页拖拽排序 |
| 9f26a2e | chore(quality): S34 质量收口 |
| 1b7fcd3 | fix(tracking): S34 codex plugin code-review + audit 修复 |

## 验证结果

- pytest: 1133 passed
- vitest: 475 passed
- flutter test: 170 passed
- build: success
- Docker smoke: 7 endpoints verified

## Codex Plugin 审查

- M100 code-review: 5 rounds (R1-R4 fail → R5 pass)
- S34 code-review: 5 rounds (R1-R4 fail → R5 pass)
- S34 audit: partial → fixes → committed
