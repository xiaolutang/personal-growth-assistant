# S001: R030 需求讨论

> 日期：2026-04-24
> 参与者：用户, Claude Code

## 需求来源

R029 归档后，`next_cycle_preview` 预置了 R030（AI 晨报增强），用户确认"全部三个方向"。

## 需求确认

### 三个方向

1. **晨报缓存** — 后端按 (user_id, date) 缓存晨报数据，同天重复请求不重新计算/LLM 调用
2. **AI 建议个性化** — LLM prompt 注入用户活跃目标、高频标签、学习偏好
3. **模式洞察 LLM 增强** — 将纯规则引擎增强为 LLM 驱动行为分析，保留规则降级

### 约束

- 不引入外部缓存依赖（不用 Redis）
- 不改 API 端点路径，仅 MorningDigestResponse 添加可选 cached_at 字段
- 所有 LLM 改动保留现有降级机制
- workflow: B/codex_plugin/skill_orchestrated

### 当前晨报系统分析

- 8 个内容模块（todos, overdue, stale_inbox, weekly_summary, ai_suggestion, learning_streak, daily_focus, pattern_insights）
- 3 个 LLM 集成点（ai_suggestion, daily_focus, pattern_insights 为规则引擎非 LLM）
- 无缓存机制
- 约 18 个后端测试覆盖

## 任务拆解

5 个任务，预估总时长 ~80 分钟：

| ID | 名称 | Phase | 预计 |
|----|------|-------|------|
| B85 | 晨报缓存机制 | P1 | 15min |
| B86 | AI 建议个性化 | P1 | 20min |
| B87 | 模式洞察 LLM 增强 | P1 | 20min |
| F117 | 晨报展示优化 | P2 | 15min |
| S27 | 质量收口+全量验证 | P3 | 10min |

## 决策记录

- 用户选择执行模式 B（Codex Plugin 自动审核）
- 用户确认全部三个方向
- B86 和 B87 可并行（都依赖 B85，互不依赖）
