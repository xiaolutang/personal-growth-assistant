# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.24.0

## 目标

- R024 Flutter 移动端 MVP — 录入优先的独立移动端应用，补齐「随时记录」核心体验

## 前置依赖（R001-R023 已完成）

- 完整 REST API + JWT 认证体系（R002, R009）
- 条目 CRUD + 7 种类型（R001-R004, R013）
- AI 对话 SSE 流式接口 + 页面感知角色（R014, R023）
- 知识图谱 + 向量搜索（R005-R008）
- 目标追踪闭环（R012）
- 离线 PWA（R019）
- E2E 测试 + CI（R020）

## 基线分析

**后端 API 现状**：
- 完整 REST API：entries CRUD, auth JWT, chat SSE, search, goals, review reports
- 认证：POST /auth/login + JWT Bearer token
- AI 对话：POST /chat SSE 流式，支持 page_context 和 page_data
- 搜索：POST /search 语义搜索 + GET /entries?keyword 全文搜索
- 后端完全不需要改动，Flutter 端是纯消费层

**移动端产品设计**：
- 3 Tab 底栏导航：今天 / 日知 / 任务
- P0：登录、AI 对话 SSE、灵感快记、今日任务、最近动态
- P1：任务状态切换、搜索、条目详情
- 不做：探索页、知识图谱、回顾报告、条目编辑、离线模式（V2+）

## 范围

### 包含（12 个任务）

**Phase 1 Foundation**（3 项）：S11 项目脚手架 + F99 主题 + F100 路由导航
**Phase 2 Infrastructure + Auth**（3 项）：S12 API 客户端 + S13 SSE 客户端 + F101 登录页
**Phase 3 Today**（2 项）：F102 今天页布局 + F103 快速操作
**Phase 4 Chat**（2 项）：F104 AI 对话界面 + F105 灵感快记
**Phase 5 Tasks + Detail**（2 项）：F106 任务列表 + F107 条目详情
**Phase 6 Quality**（1 项）：S14 构建验证

### 不包含

- 注册（通过 Web 端完成，移动端仅登录）
- 语音输入（P2，需要语音识别 SDK 集成）
- 离线模式（V2，需要本地 SQLite 缓存策略）
- 条目编辑（V2，如果用户反馈强烈再加）
- 灵感转化操作（V2）
- 全局搜索（P1 但 MVP 排除，V2 考虑）
- 探索页、知识图谱、回顾报告（V3+）
- 推送通知（V2）

## 用户路径

**核心路径：快速记录**
- 打开 App → 日知 Tab → 输入灵感 → AI 解析 → 自动创建 inbox 条目 → 关掉 App

**浏览路径：**
- 今天 Tab → 查看今日进度 + 任务列表 + 最近动态
- 任务 Tab → 按状态筛选 → 点击任务查看详情

**登录路径：**
- 首次打开 → 登录页 → 输入用户名密码 → JWT 存储 → 进入今天页

## 技术约束

- Flutter 代码位于 mobile/ 目录，不修改 backend/ 和 frontend/
- 后端 API 完全复用，不做改动
- JWT token 与 Web 端共享认证体系
- 状态管理使用 Riverpod
- 网络层使用 Dio + 自定义 SSE 客户端
- 移动端只做 P0+P1 功能，不做全功能移植
- workflow: B/codex_plugin/skill_orchestrated
