# R028 — 工程整理

## 概述

文档同步 + Flutter 导航修复，工程维护轮次。

## 任务清单

| ID | 模块 | 名称 | 状态 |
|----|------|------|------|
| S22 | docs | CLAUDE.md + architecture.md MCP 文档更新 | completed |
| S23 | docs | product-design-analysis.md 状态更新 | completed |
| F117 | mobile | Flutter today_page.dart 导航 TODO 修复 | completed |
| S24 | docs | project_spec.md 版本更新 | completed |
| S25 | quality | 质量收口验证 | completed |

## 提交记录

- `xxx` chore(cleanup): R028 工程整理（文档同步 + Flutter 导航修复）

## 验证结果

- 后端: 1052 passed, 20 skipped
- 前端: 347 passed (33 test files)
- 构建: 成功 (PWA 38 entries)

## 关键改动

### 文档同步
- CLAUDE.md MCP Tools 表 9→14（新增 get_review_summary, get_knowledge_stats, batch_create_entries, batch_update_status, get_learning_path）
- CLAUDE.md 后端目录结构 MCP Server 描述 9→14
- architecture.md MCP Server 描述 9→14
- docs/product-design-analysis.md 功能评分表全面更新（AI 对话、灵感转化、知识图谱、回顾增强、反馈闭环、数据导出、多端支持等均反映实际完成状态）
- .dev-flow/project_spec.md 版本更新为 v0.28.0

### Flutter
- today_page.dart 两处 `// TODO: 导航到条目详情` 替换为 `context.go('/entries/${entry.id}')`
