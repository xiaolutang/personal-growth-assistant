# R027 — 数据导出 + 反馈追踪闭环

## 概述

数据导出（Phase 6）+ 反馈追踪闭环（Phase 3 补全），产品演进规划第三阶段最后缺口。

## 任务清单

| ID | 模块 | 名称 | 状态 |
|----|------|------|------|
| B83 | export | 导出 API 增强 | completed |
| B84 | feedback | 反馈状态同步 | completed |
| F114 | export | 条目详情页导出按钮 | completed |
| F115 | export | Review 页导出入口 | completed |
| F116 | feedback | FeedbackButton 状态增强 | completed |
| S21 | quality | 质量收口验证 | completed |

## 提交记录

- `f3b2875` feat(feedback): B84 反馈状态同步
- `d575eeb` feat(export): B83 导出 API 增强
- `0cb4f65` feat(frontend): F114+F115+F116 导出+反馈状态增强
- `6d97bec` chore(quality): S21 质量收口 + R027 全部完成

## 验证结果

- 后端: 1052 passed, 20 skipped
- 前端: 347 passed (33 test files)
- 构建: 成功 (PWA 38 entries)

## 关键改动

### 后端
- `GET /entries/{id}/export` — 单条目 Markdown 文件下载
- `GET /review/growth-report` — 成长报告 Markdown 下载（4 个 section）
- `POST /feedback/sync` — 从 log-service 同步 issue 状态
- SQLite feedback 表新增 `updated_at` 字段
- 状态扩展为 4 态：pending/reported/in_progress/resolved

### 前端
- EntryDetail 页面添加导出按钮
- Review 页面添加全量导出 + 成长报告按钮
- FeedbackButton 4 态颜色标签 + 自动同步 + updated_at 显示
