# 项目说明

> 项目：personal-growth-assistant
> 版本：v0.49.0
> 状态：已完成（R049）
> 活跃分支：feat/R049-eval-operationalization

## 当前范围

R049 Agent 评估体系运营化：让已建成的评估基础设施真正运转起来，实现 P0（Judge 跑起来 + Bad Cases 回流）+ P1（定期评估管道）。

### 核心问题

评估代码已完整（framework/judge/transcript/report），但实际运营存在缺口：
1. LLM-as-Judge 只在 mock 中运行，342 条转录的 judge_result 全为 null
2. 195 个 bad cases 堆积无分类、无回流
3. 只在 4/29 手动跑过一次，无定期评估管道
4. 无法追踪 Agent 质量趋势

### 历史基线

- 2026-04-29 跑了 5 轮 eval，pass_rate: 78% → 88%
- 负面测试 24 条零违规
- model 环境变量未记录（显示 unknown）

### Phase 1: Judge 集成（2 tasks）

1. **B01 run_eval 集成 LLM-as-Judge**：在评估流程中启用真实 Judge，写入 10 维度评分
2. **B02 transcript 补填脚本**：回填 342 条历史转录的 judge_result

### Phase 2: Bad Cases 回流（2 tasks）

3. **B03 bad cases 分类脚本**：自动分类 195 个坏例，输出报告和可转化模板
4. **B04 补充 Golden Dataset**：将审核后的坏例转化为正式测试用例

### Phase 3: 定期管道（2 tasks）

5. **B05 定期评估包装脚本**：Docker 健康 → 登录 → eval → 报告 → 告警
6. **B06 评估趋势对比**：history.json 趋势分析 + 差异对比

### Phase 4: 质量收口（1 task）

7. **S07 全量验证**：所有 eval 测试 + 脚本 dry-run + 报告检查

## 技术约束

- 纯后端/脚本工作，不涉及前端
- eval 代码在 `backend/tests/eval/` 下
- 需要真实 Agent 在线（Docker）才能跑端到端
- Judge 依赖 LLM API（与 Agent 共用同一 API）
- 脚本需要登录凭证（通过环境变量或参数）

## 统计

| 指标 | 值 |
|------|-----|
| 总任务数 | 7 |
| P0 | 4（B01, B02, B03, B04）|
| P1 | 3（B05, B06, S07）|

## workflow

- mode: B（Codex Plugin 自动审核）
- runtime: skill_orchestrated
- review_provider: codex_plugin
- audit_provider: codex_plugin
- risk_provider: codex_plugin
