---
session_id: S001
date: 2026-05-06
topic: R049 Agent 评估体系运营化
requirement_cycle: R049
status: confirmed
---

# S001: 需求确认 — 评估体系运营化

## 背景

R044 决策文档（`decisions/2026-04-28--agent-refactoring.md`）规划了完整的 Agent 评估体系，代码层面已基本实现（framework/judge/transcript/report），但实际运营存在缺口：

1. LLM-as-Judge 只在单元测试中以 mock 方式运行，真实 eval 产出 `judge_result: null`
2. 195 个 bad cases 堆积无回流
3. 只在 4/29 手动跑过一次评估（5 轮，pass_rate 从 78% 爬到 88%）
4. 无定期评估管道

## 用户确认的范围

- P0: 让 Judge 跑起来 + Bad Cases 回流管道
- P1: 定期评估管道（脚本化定期跑 eval，产出趋势报告）
- 执行模式: B（codex_plugin 自动审核）

## 当前状态数据

- 历史评估 5 轮（2026-04-29），通过率 78% → 88%
- 342 条转录（judge_result 全为 null）
- 195 个 bad cases（3 个 message_id，各约 18-20 条反馈）
- 122 条 Golden Dataset（68 单轮 + 24 负面 + 30 多轮）

## 关键技术发现

### Judge 为什么没跑

- `LLMJudge` 有 `use_real_llm=True` 参数可接入真实 APICaller
- `run_eval.py` 的 `run_single_turn()` 只保存了 `outcome_grade`，没有调用 `LLMJudge.evaluate()`
- 需要在 run_eval 流程中集成 Judge 调用，将结果写入 transcript

### Bad Cases 格式

```json
{
  "feedback_id": 1,
  "message_id": "msg-abc123",
  "reason": "信息不准确",
  "detail": "Agent 说今天有 5 个任务，实际只有 2 个",
  "title": "Agent 回复不准确",
  "user_id": "test-user",
  "created_at": "..."
}
```

来自 `POST /feedback` 的用户反馈导出，需要分类后决定：补充到 Golden Dataset 或创建 Issue。

### 定期评估管道

- 当前 `run_eval.py` 需要登录凭证和 Agent 在线
- 需要一个包装脚本：Docker 健康检查 → 登录 → 跑 eval → 产出报告 → 告警
