# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.15.0

## 目标

- R019 离线增强 + PWA — 修复 SW 缓存策略、离线状态检测、离线写入队列、PWA 安装引导

## 前置依赖（R001-R018 已完成）

- 条目 CRUD、分类管理、搜索（R001-R004）
- 知识图谱 + 图谱可视化（R005-R008）
- 认证隔离 + 用户数据隔离（R002, R009）
- 条目关联 + 知识上下文 + AI晨报（R011）
- 目标追踪闭环（R012）
- 月报 AI 总结 + 决策/复盘/疑问条目类型（R013）
- 页面级上下文 AI + 快捷建议 Chips（R014）
- 回顾增强：多维趋势、Neo4j 热力图、晨报集成（R015）
- 全局 Cmd+K 搜索 + 首页灵感转化（R016）
- 代码审计加固：注入防护、认证加固、N+1 优化（R017）
- 缺陷修复 + 质量收口（R018）

## 基线分析

当前 PWA 状态：
- 静态资源 precache ✓
- API runtime caching URL pattern 不匹配（正则用路径而非完整 URL）
- 无离线状态检测 UI
- 无离线写入队列
- 无 Background Sync
- 无 PWA 安装引导

## 范围

### 包含（8 个任务）

- S03: 修复 SW 缓存策略 + URL pattern
- S04: useOnlineStatus hook + OfflineIndicator 组件
- F58: 离线回退页面
- F59: IndexedDB 离线队列服务
- F60: 离线同步：上线后自动回放队列
- F61: API 层离线拦截集成
- F62: PWA 安装引导
- B73: 质量收口

### 不包含

- 离线编辑已有条目（仅支持离线创建 inbox）
- Background Sync API（Safari 不支持，用 online 事件替代）
- 离线搜索（搜索依赖后端 LLM）
- 离线知识图谱（依赖 Neo4j）

## 用户路径

1. 地铁离线 → 打开应用 → 看到离线提示 → 可查看已缓存条目
2. 离线时在首页输入灵感 → 创建成功（本地）→ 上线后自动同步
3. 首次使用后出现安装引导 → 点击安装 → 桌面图标可用

## 技术约束

- 离线队列使用 IndexedDB，不引入重量级依赖
- 离线写入仅支持 inbox 创建（最小验证）
- SW 缓存策略不缓存搜索和流式请求
- workflow: B/codex_plugin/skill_orchestrated
