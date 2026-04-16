# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.9.0

## 目标

- R012 目标追踪闭环 — 目标 CRUD + 三种衡量方式（手动计数/检查清单/Tag自动追踪）+ 进度计算 + 首页/回顾页集成

## 前置依赖（R001-R011 已完成）

- 用户认证 + 数据隔离 + 路由守卫
- 条目关联（entry_links）和知识上下文（R011）
- AI 晨报增强（R011）
- 所有核心功能模块已就绪

## 范围

### 包含
- B45: Goals CRUD API（goals 表 + 5 个端点 + 三种 metric_type）
- B46: Goal 条目关联 + 进度计算（goal_entries 表 + count/checklist/tag_auto 三种进度）
- B47: Goal 自动追踪触发（entry_service 异步触发 tag_auto 重算）
- F34: Goals 页面 + 详情（/goals 路由 + 创建弹窗 + 详情页 + Sidebar 6 项）
- F35: 首页目标进度卡片（活跃目标 Top 3）
- F36: 回顾页目标完成概览（progress-summary API + 进度变化）

### 不包含
- 目标模板 / 预设目标
- 目标分享 / 协作
- 目标提醒 / 推送通知
- 进度历史趋势图（仅当前值）

## 用户路径

1. 创建目标 → 选择衡量方式 → 设定目标值 → 查看目标列表
2. count 目标 → 关联条目 → 进度自动更新 → 达标自动完成
3. checklist 目标 → 勾选检查项 → 进度更新 → 达标自动完成
4. tag_auto 目标 → 创建带 tag 条目 → 后台自动追踪 → 进度实时计算
5. 首页 → 查看活跃目标进度 → 点击跳转详情
6. 回顾页 → 查看目标进展概览 → 本周期完成情况

## 技术约束

- goals 属于 SQLite 元数据层（与 entry_links 同级），不写入 Markdown
- 进度为查询时计算，不依赖物化字段
- tag_auto 触发为异步 fire-and-forget，不阻塞条目操作
- 前端遵循现有 api.ts + 类型定义模式
- 进度环形图使用纯 SVG，不引入新图表库
