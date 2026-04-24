# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.31.0
> 状态：规划中（R031）
> 活跃分支：feat/R031-conversational-onboarding

## 当前范围

R031 对话式 Onboarding（Phase 0）：用日知对话引导代替静态弹窗，新用户首次进入时通过真实对话完成首个条目创建。

1. **B88 Onboarding AI Prompt**：AI chat 注入 is_new_user 上下文，新用户对话时使用引导性系统提示
2. **F118 对话式 Onboarding 前端**：移除静态弹窗，PageChatPanel 自动展开 + 日知欢迎消息 + 引导建议
3. **S28 质量收口**：全量测试 + 构建

## 技术约束

- 不新增 API 端点，is_new_user 通过现有 chat context 透传
- 不改 User 模型（已有 onboarding_completed 字段）
- 不改 PageChatPanel 核心架构，只增加 greetingMessage prop
- workflow: B/codex_plugin/skill_orchestrated

## 用户路径

```
新用户注册 → 登录 → 进入首页
         → 无静态弹窗
         → PageChatPanel 自动展开，日知打招呼：
           "你好，我是日知。帮你把每天的想法记下来..."
         → 显示建议：记灵感 / 做任务 / 记笔记
         → 用户点击建议或输入内容
         → AI 创建条目并回应
         → 自动标记 onboarding 完成
         → 后续访问恢复正常模式

老用户（onboarding_completed=true）：
         → 进入首页，PageChatPanel 默认折叠
         → 正常使用，无任何变化
```
