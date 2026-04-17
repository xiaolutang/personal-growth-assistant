# S001 R014 页面级上下文 AI 规划

> 日期：2026-04-17
> 阶段：xlfoundry-plan

## 需求来源

R013 归档后，基于 `docs/product-design-analysis.md` 三阶段收敛策略确定下一步优先级。图谱独立页已存在（GraphPage.tsx 832行），转向「页面级上下文 AI」。

## 需求确认

用户选择「页面级上下文 AI」，确认范围：
1. 后端 chat API 的 page_context 增强（数据注入）
2. 页面类型感知的系统提示词
3. 页面相关的快捷建议 chips
4. 探索页搜索上下文注入

## 现状分析

已有基础设施：
- `PageContext` 模型 + `ChatRequest.page_context` 透传
- `_build_page_context_hint()` 基础文本生成
- `FloatingChat.tsx` 路由感知 pageContext
- `useStreamParse.ts` 透传 page_context

差距：
- 上下文只含页面类型，不含业务数据
- LLM 系统提示词固定，不随页面变化
- 无页面级快捷建议
- update 意图不消费 page_context（条目页"补充"无法直达当前条目）
- Explore 页 local state 无法被 FloatingChat 读取

## 任务拆解

| ID | 模块 | 名称 | Phase | depends_on |
|----|------|------|-------|-----------|
| B50 | chat | 页面上下文数据注入 + 更新路径打通 | P1 | — |
| B51 | chat | LLM 页面感知系统提示词 | P1 | B50 |
| F39 | chat | 快捷建议 Chips + 页面状态同步 | P2 | B51 |

## Plan Review 历史

### Round 1 (2026-04-17): fail

5 项发现，已全部修复：

1. **[Critical] update 路径未打通** → B50 扩展：_handle_update 接受 page_context，条目页用 entry_id 直达
2. **[Critical] Explore 状态不可达** → F39 改为：页面主动写 chatStore.pageExtra，FloatingChat 合并发送
3. **[High] user_id 路径不明确** → B50 planning_notes 明确数据源：Entry→EntryService.get_entry(user_id)，Home→EntryService.list_entries(user_id, date_filter)
4. **[Medium] 测试设计不足** → 补充失败降级、跨用户隔离、state_sync 测试场景；B50 补 risk_tags: ["auth"]
5. **[Medium] alignment_checklist 缺失** → 已补充 R014 章节

## workflow

mode: B, runtime: skill_orchestrated, providers: codex_plugin
