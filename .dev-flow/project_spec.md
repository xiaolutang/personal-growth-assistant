# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.7.0

## 目标

- R009 Chat 用户 ID 透传 — 修复 chat_service 所有 entry 操作未传递 user_id 的架构债务

## 前置依赖（R001-R008 已完成）

- 用户认证：JWT + get_current_user + 路由守卫
- 数据隔离：SyncService 按 user_id 隔离 + MCP 用户隔离
- Chat 基础：ChatService + 意图检测 + LangGraph 任务解析 + SSE 流式

## 范围

### 包含
- B32: ChatService user_id 透传 — 签名扩展 + 调用链改造
- B33: Chat 用户隔离单元测试

### 不包含
- 前端改动（user_id 从 JWT 自动获取）
- detect_intent 改造（纯意图分类，不访问用户数据）
- MCP 改造（已在 R008 完成用户隔离）

## 用户路径

1. 用户 A 通过浮动聊天说「记一个任务：xxx」→ 创建的条目属于用户 A（而非 _default）
2. 用户 A 通过聊天说「把 xxx 标记完成」→ 只能搜到并更新自己的条目
3. 用户 A 通过聊天说「删掉 xxx」→ 只能搜到并删除自己的条目
4. 用户 A 通过聊天说「查看 xxx」→ 只能看到自己的条目

## 问题根因

`parse.py /chat` 端点通过 `Depends(get_current_user)` 获取 `user.id`，但只用于构造 LangGraph 的 `thread_id`，未传递给 `_chat_service.process_intent()`。`ChatService` 所有 handler 调用 `entry_service` 方法时省略 `user_id` 参数，导致默认走 `_default` 命名空间。

## 技术约束

- 不改变 ChatService 之外的任何服务签名（entry_service、sync_service 等不变）
- 不改变 SSE 事件格式
- 所有改动在 `chat_service.py` 和 `parse.py` 内完成
