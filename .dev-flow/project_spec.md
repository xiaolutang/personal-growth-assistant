# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.10.0

## 目标

- R013 月报AI总结 + 思考/决策记录 — 补齐月报AI总结，新增 decision/reflection/question 三种条目类型

## 前置依赖（R001-R012 已完成）

- 条目 CRUD、分类管理、搜索（R001-R004）
- 知识图谱 + 图谱可视化（R005-R008）
- 认证隔离 + 用户数据隔离（R002, R009）
- 条目关联 + 知识上下文 + AI晨报（R011）
- 目标追踪闭环（R012）
- 探索页、导出、回顾页（R004-R006）

## 范围

### 包含
- B48: 月报AI总结补齐（review_service 调用 _generate_ai_summary）
- B49: 思考/决策记录后端（Category 扩展 + 模板 + 目录 + 意图识别 + 类型同步链路）
- F37: 月报AI总结展示（Review.tsx 月报 Tab 展示 AI 总结卡片）
- F38: 思考/决策记录前端（探索页 Tab + 快捷操作 + 详情页差异化渲染）

### 不包含
- 决策/复盘/疑问的专门页面（与探索页共享）
- 新类型的目标追踪集成
- 新类型的导出格式差异
- AI 自动生成决策/复盘模板内容

## 用户路径

1. 首页 → 快捷操作「记决策」→ AI 对话或直接创建 → 决策条目出现在探索页
2. 探索页 → 切换「决策」Tab → 浏览决策日志列表 → 点击查看详情（选项对比结构）
3. 回顾页 → 月报 Tab → 看到 AI 生成的月度总结（与日报/周报一致）
4. 条目详情 → 决策类型显示决策背景/选项/选择/理由结构化渲染
5. AI 对话 → "记个决策：选了 Rust 而不是 Go" → 意图识别创建 decision 条目

## 技术约束

- 新类型复用现有 entries 表和 Markdown 存储架构
- Category 枚举扩展需同步：后端 enums.py → schemas/entry.py → OpenAPI → 前端 types/task.ts + constants.ts
- 每种类型有固定 Markdown 模板（heading 结构），不新增结构化字段
- 目录映射：decision→decisions/、reflection→reflections/、question→questions/
- ID 前缀：decision-xxx、reflection-xxx、question-xxx
- 所有操作按 user_id 隔离
- 前端遵循现有 api.ts + 类型定义模式
