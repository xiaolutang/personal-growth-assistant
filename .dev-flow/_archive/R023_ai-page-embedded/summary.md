# R023: AI 页面内嵌 + 交互模式升级

- 状态: 已完成
- 分支: `feat/R023-ai-page-embedded`
- 主题: 将 AI 从全局浮动面板改为各页面内嵌，每个页面有独立的 AI 角色
- 完成时间: 2026-04-22
- 任务数: 8 (B87, F93, F94, F95, F96, F97, F98, S10)
- Codex 审核: 首轮 fail（3 项 finding），修复后通过
- 新增测试: 9 后端 (PAGE_ROLE_PROMPTS 分支) + 10 前端 (PageChatPanel 组件)
- 关键改动:
  - 后端 ai_chat_service 新增 PAGE_ROLE_PROMPTS 字典（4 种页面角色）
  - 前端新建 PageChatPanel.tsx 通用内联 AI 对话面板（264 行）
  - Home/Review/EntryDetail/Explore 各页嵌入角色化 AI 面板
  - FloatingChat 保留为快捷入口，移除 PageAIAssistant
  - 各页面丰富 pageData 上下文（overdue/streak/环比/content_preview）
  - Explore 空结果自动展开搜索助手
- 验证: 866 后端 + 347 前端测试通过 + 生产构建通过
