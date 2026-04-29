---
date: 2026-04-29
type: tech_selection
status: superseded
requirement_cycle: R045
architecture_impact: false
supersedes: null
---

# 智能体评估 HTML 报告生成（已更新）

> 原方案 B（Jinja2 + Chart.js）因 Jinja2 在当前环境不可用，已变更为方案 A（Python string.Template + Chart.js CDN）。

## 原方案（已废弃）

- 选择：**方案 B（Jinja2 + Chart.js CDN）**
- 废弃原因：Jinja2 未在 pyproject.toml 中声明，当前 uv 环境不可用

## 变更后方案

- 选择：**方案 A'（Python string.Template + Chart.js CDN）**
- 理由：string.Template 零依赖，模板只有 1 个 HTML 文件，用占位符替换即可。Chart.js CDN 加载图表（离线时图表不显示，文字内容正常）。
- 后续集成到 Web 应用时再按需引入 Jinja2
