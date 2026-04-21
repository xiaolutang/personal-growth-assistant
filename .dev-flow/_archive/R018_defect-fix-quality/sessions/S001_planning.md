# S001: R018 缺陷修复 + 质量收口规划

> 日期：2026-04-19
> 状态：规划中

## 背景

R017 审计加固完成后，920 个测试通过但仍有 15 个 flow 测试因 Python 3.13 兼容性问题失败。
同时 defect_feedback.md 中有 1 条待处理缺陷（项目详情页无内容），以及 R017 审计 4 项 Deferred。

## 本轮需求

1. 修复 15 个失效 flow 测试（Python 3.13 asyncio 兼容性）
2. 验证并修复项目详情页内容缺陷
3. 处理 R017 Deferred 项中可行的部分
4. 补充测试覆盖缺口

## 运行模式

- workflow.mode: B
- workflow.runtime: skill_orchestrated
- review/audit/risk_provider: codex_plugin

## 关键决策

1. Flow 测试 fixture 统一迁移到 async fixture（conftest.py 已有 httpx AsyncClient 模式）
2. 项目详情页需先验证是否仍有问题，再决定修复方案
3. Deferred 项中 logout token 失效和混合搜索不纳入本轮（增强功能，非缺陷）
4. 聚焦可验证的缺陷修复，不做架构改动
