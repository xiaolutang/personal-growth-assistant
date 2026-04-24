# R031: 对话式 Onboarding

## 概述

移除静态 OnboardingFlow 弹窗，改为在 Home 页通过 PageChatPanel 实现对话式引导。新用户首次进入时，日知自动打招呼并提供引导建议，用户首次对话后自动标记 onboarding 完成。

## 任务清单

| ID | 名称 | 类型 | 状态 |
|----|------|------|------|
| B88 | Onboarding AI Prompt | 后端 | completed |
| F118 | 对话式 Onboarding 前端 | 前端 | completed |
| S28 | 质量收口+全量验证 | 质量收口 | completed |

## 依赖图

```
B88 → F118 → S28
```

## 提交记录

- `4070e44` feat(onboarding): B88 Onboarding AI Prompt 注入
- `f4df466` feat(onboarding): F118 对话式 Onboarding 前端
- `87d4123` test(quality): S28 R031 质量收口全量验证

## 测试结果

| Suite | Tests | Result |
|-------|-------|--------|
| pytest | 998 | 0 failed |
| vitest | 360 | 0 failed |
| build | - | success |

## 改动文件

- `backend/app/services/ai_chat_service.py` — 新增 ONBOARDING_PROMPT + is_new_user 上下文注入
- `backend/tests/unit/api/test_onboarding_prompt.py` — 15 个单元测试
- `frontend/src/pages/Home.tsx` — onboarding 状态管理 + PageChatPanel 双模式
- `frontend/src/components/PageChatPanel.tsx` — greetingMessage + onFirstResponse props
- `frontend/src/components/FloatingChat.tsx` — 新用户首页隐藏
- `frontend/src/App.tsx` — 移除 OnboardingFlow 弹窗
- `frontend/src/services/api.ts` — AIChatContext 增加 is_new_user
- `frontend/src/components/PageChatPanel.test.tsx` — 6 个新测试

## 时间线

- 开始: 2026-04-24
- 完成: 2026-04-24
