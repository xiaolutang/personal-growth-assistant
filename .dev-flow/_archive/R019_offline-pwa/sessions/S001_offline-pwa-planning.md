# S001: R019 离线增强 + PWA 规划

> 日期：2026-04-19
> 状态：规划完成

## 用户输入

- 方向：离线增强 + PWA
- 执行模式：B/codex_plugin/skill_orchestrated

## 需求总结

增强 PWA 离线体验，使用户在无网络环境下可以：
1. 查看已缓存的条目/任务/笔记
2. 离线创建灵感（inbox），上线后自动同步
3. 感知到在线/离线状态变化
4. 获得原生级 PWA 安装引导

## 基线分析

当前 PWA 状态：
- 静态资源 precache ✓
- API runtime caching 有配置但 URL pattern 可能不匹配（正则用路径而非完整 URL）
- 无离线状态检测 UI
- 无离线写入队列
- 无 Background Sync
- 无安装引导
- 全局 fetch 拦截器和 authFetch 有功能重叠

## 任务设计

8 个任务，4 个 phase，约 3-4 小时工作量。

## 架构决策

- 离线队列使用 IndexedDB（通过 idb 轻量库）存储待同步 mutation
- SW 缓存策略分层：静态资源 precache / 条目列表 NetworkFirst(5min) / 条目详情 StaleWhileRevalidate / 搜索请求 NetworkOnly
- 离线创建灵感只支持 inbox 类型（最小验证），其他类型留后续
- 不引入新依赖（idb 是纯 JS 无构建依赖，若太大则手写 IndexedDB helper）
