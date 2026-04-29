# R046: 聊天面板重构

- 状态: 已完成
- 分支: `feat/R046-chat-panel-refactor`
- 主题: FloatingChat 悬浮按钮折叠 + 反馈收敛进聊天面板 + 首次引导 greeting + 会话列表集成
- 完成时间: 2026-04-29
- 任务数: 4 (B196, F188, F189, F190) + 1 补充 (F191)
- 提交数: 8

## 任务清单

| ID | 名称 | Commit | 状态 |
|----|------|--------|------|
| B196 | greeting 消息识别 + is_new_user 判断 | e6708cf | completed |
| F188 | FloatingChat 折叠为悬浮按钮模式 | c7a7601 | completed |
| F189 | 反馈表单集成到聊天面板 | 8517c09 | completed |
| F190 | 前端首次打开聊天自动发送 greeting | 4c7b20e | completed |
| F191 | 会话列表集成到 FloatingChat 面板 | c5326bc | completed |

## 关键改动

### 后端
- `parse.py`: __greeting__ 消息识别，临时 thread_id 不污染对话历史
- `agent_service.py`: is_new_user 方法，skip_touch_session 参数
- `session_meta_store.py`: count_sessions 方法
- `prompts.py`: ONBOARDING_PROMPT 在 is_new_user=True 时注入

### 前端
- `FloatingChat.tsx`: 从全宽底栏改为右下角悬浮按钮 + 展开面板，集成 SessionList 和 FeedbackPanel
- `SessionList.tsx`: 新增 onSwitchSession 回调，controlled 模式
- `Sidebar.tsx`: 移除对话历史区块，不再依赖 agentStore
- `App.tsx`: 移除 FeedbackButton，移除 paddingBottom

### 收敛修复
- switchSession 双重调用 → SessionList controlled 模式
- showSessionList 面板关闭时状态残留清理
- fetchSessions 加载时序不依赖面板展开
- 图标尺寸统一

## 验证

- 后端测试: 1394 passed
- 前端测试: 577 passed
- 前端构建: 通过
- Docker 部署: healthy
