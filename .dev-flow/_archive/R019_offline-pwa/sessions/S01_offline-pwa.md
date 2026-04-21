# S01: R019 离线增强 + PWA

> 日期：2026-04-13 ~ 2026-04-20
> 状态：completed

## 需求

修复 SW 缓存策略、离线状态检测、离线写入队列、PWA 安装引导。

## 结论

8 个任务全部完成，合并到 main（commit 52bbe93）。后端 857 tests + 前端 321 tests 全绿。

## 关键决策

- 离线队列使用 IndexedDB，不引入重量级依赖
- 离线写入仅支持 inbox 创建（最小验证）
- 不做 Background Sync API，用 online 事件 + initSync() 替代
- 登出即丢弃未同步数据，不承诺恢复
