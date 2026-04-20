# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.16.0

## 目标

- R020 E2E 测试补齐 + CI PR 增强 — 补齐 Goals、新类型、导出的全面 E2E 覆盖，CI 在 PR 中运行 E2E 关键子集

## 前置依赖（R001-R019 已完成）

- 条目 CRUD + 7 种类型（R001-R004, R013）
- 知识图谱 + 向量搜索（R005-R008）
- 认证隔离（R002, R009）
- 目标追踪闭环（R012）
- 页面级上下文 AI + Cmd+K 搜索（R014, R016）
- 离线 PWA（R019）
- 已有 Playwright E2E 基础设施 + 40 个用例（B35-B39, F39, B42）

## 基线分析

当前 E2E 覆盖：
- 认证流程 ✓（auth.spec.ts）
- 条目 CRUD ✓（entries.spec.ts）
- Chat SSE ✓（chat.spec.ts）
- 回顾统计 ✓（review.spec.ts）
- UI 渲染 ✓（ui.spec.ts）
- 页面上下文 ✓（page-context.spec.ts）

**缺失**：
- Goals（目标追踪）— 无 E2E 覆盖
- 新类型（decision/reflection/question）— 无 E2E 覆盖
- 导出功能 — 无 E2E 覆盖
- CI PR 不跑 E2E — 仅 main push 触发

## 范围

### 包含（9 个任务）

- S05: E2E Helper 扩展（Goals + Export + 新类型 API）
- B74: Goals API E2E（~15 tests）
- F63: Goals 页面 E2E（~12 tests）
- B75: 新类型条目 API E2E（~12 tests）
- F64: 探索页新类型 E2E（~8 tests）
- B76: 导出 API E2E（~8 tests）
- F65: 导出 UI E2E（~5 tests）
- S06: CI PR E2E + test_coverage 状态同步
- B77: 质量收口

### 不包含

- Safari/Firefox 浏览器兼容性测试
- 性能基线测试（手动验证）
- Mobile 视口测试
- 离线 PWA E2E（需要网络拦截，复杂度高）

## 用户路径

1. 创建目标 → 关联条目 → 进度更新 → 完成目标（E2E 覆盖到目标页/首页卡片；回顾页目标进度由已有 F36 覆盖，不在 R020 范围）
2. 创建决策/复盘/疑问 → 探索页 Tab 切换筛选 → 搜索命中
3. 点击导出 → 选择格式 → 下载文件

## 技术约束

- E2E 使用 Playwright + Chromium
- 假 LLM 配置（LLM_BASE_URL=http://localhost:19999）
- 独立 DATA_DIR 隔离
- PR E2E 只跑关键子集（auth + entries + goals-api + new-types-api），控制运行时间
- workflow: B/codex_plugin/skill_orchestrated
