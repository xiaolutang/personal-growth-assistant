---
date: 2026-04-28
type: architecture_discussion
status: decided
requirement_cycle: R044
architecture_impact: true
supersedes: null
---

# 重构交互智能体

## 背景

当前存在两套并行的对话系统：
- `ChatService`：意图识别(IntentService) + 任务解析(TaskParserGraph) + 条目 CRUD，入口 `POST /chat`
- `AIChatService`：纯对话（教练/助手/镜子模式），入口 `POST /ai/chat`

核心痛点：
1. 双系统分裂，用户体验割裂
2. 意图识别是多余的串行开销（每次请求 2 次 LLM 调用）
3. LangGraph 单节点图（START→parse→END）未利用编排能力
4. Prompt 硬编码分散在 4+ 个文件中
5. 流式 JSON 拼接脆弱

目标：合并为统一智能体，具备多步推理 + 多轮对话 + 主动追问能力。

## 方案对比

### 方案 A': LangGraph ReAct Agent

- ReAct 模式（Reason→Act→Observe 循环）构建统一 Agent
- 一次 LLM 调用完成意图识别 + 动作规划
- 定义一组 Tools：create_entry, update_entry, delete_entry, search_entries, get_entry, get_review_summary, ask_user
- Agent 自主决定调用哪些 tools、调用几次、是否追问用户
- 保留 LangGraph checkpointer 做多轮对话持久化
- 页面上下文注入 system prompt

### 方案 B: 直出 Function Calling，去掉 LangGraph

- 去掉 LangGraph，直接用 OpenAI-compatible function calling
- 自行实现对话持久化（SQLite）
- 适合不需要多步推理的场景

### 方案 C': LangGraph Supervisor + 工具集

- Supervisor 模式，子 Agent 简化为同一 Agent 换不同工具集
- LLM 调用次数增加（Router 1次 + 子Agent 1次）
- 模式间切换不自然

### 方案 D: LLM 原生 Agent SDK

- 与特定模型提供商耦合
- 需自行实现基础设施

## 决策

- 选择：方案 A'（LangGraph ReAct Agent）
- 理由：
  1. ReAct 模式天然匹配多步推理、工具调用、主动追问
  2. LLM 调用效率最高（每轮 1 次，按需循环）
  3. 与现有架构延续（已有 LangGraph + checkpointer）
  4. 不过度工程（一个 Agent + 工具集）
- 前提条件：LLM 提供商支持 function calling / tool_use（已确认支持）
- 风险：
  1. Token 消耗增加（tools 定义 + 中间步骤占 token）
  2. Agent 循环失控（需设上限，建议最多 5 轮）
  3. 流式体验变化（ReAct 循环中需等工具执行）
  4. 纯对话和工具调用的 prompt 平衡

## 架构影响

### 后端架构变更

**分层设计：**
```
Routers (POST /chat 统一入口, SSE 流式响应)
  → AgentService (新: 会话管理, 页面上下文注入, SSE 事件编排)
    → LangGraph ReAct Agent (Agent Node ↔ ToolNode 循环)
      → Tools (create_entry, update_entry, delete_entry, search_entries, get_entry, get_review_summary, ask_user)
        → Services (现有, 不动: EntryService, SyncService, ...)
          → Infrastructure (现有, 不动: MarkdownStorage, Neo4j, Qdrant)
```

**新增 SSE 事件类型：**
| 事件 | 用途 |
|------|------|
| `thinking` | Agent 正在推理 |
| `tool_call` | Agent 调用了哪个工具及参数 |
| `tool_result` | 工具执行结果 |
| `content` | 流式文本输出（保留） |
| `created` | 条目创建通知（保留） |
| `updated` | 条目更新通知（保留） |
| `error` | 错误通知（保留） |
| `done` | 对话结束（保留） |

**Tools 与 Service 映射：**
```
create_entry        → entry_service.create_entry()
update_entry        → entry_service.update_entry()
delete_entry        → entry_service.delete_entry()
search_entries      → entry_service.search_entries()
get_entry           → entry_service.get_entry()
get_review_summary  → review_service.get_summary()
ask_user            → 中断 Agent，等待用户回复
```

### 前端架构变更

**新增组件：**
```
components/AgentChat/
  AgentChat.tsx          ← 主容器
  MessageList.tsx        ← 消息列表
  UserMessage.tsx        ← 用户消息气泡
  AgentMessage.tsx       ← Agent 回复（含工具调用展示）
  ToolCallCard.tsx       ← 工具调用卡片（loading/success/fail 三态）
  ThinkingIndicator.tsx  ← 思考动画
  ChatInput.tsx          ← 输入框
  AgentPrompt.tsx        ← Agent 追问提示

stores/
  agentStore.ts          ← 统一替换 chatStore + aiChatStore
```

**UI 设计关键决策：**
- 工具调用过程展示为折叠卡片（让用户知道 Agent 在做什么）
- Agent 思考时显示 loading 动画
- 追问复用输入框，不弹窗
- 条目变更通知保留 created/updated 事件触发列表刷新

### 删除的代码

- `ChatService` → 被 AgentService 替代
- `AIChatService` → 被 AgentService 替代
- `IntentService` → 不再需要独立意图识别
- `TaskParserGraph` → 被 ReAct Agent 替代
- `routers/parse.py` 中的 `/parse` 端点 → 统一到 `/chat`
- `routers/ai_chat.py` → 统一到 `/chat`

## 评估体系

### 分层测试策略

**LLM 层（快速、CI 友好）：**
- mock 掉所有 tools，只捕获 LLM 的 tool_calls 决策
- Golden Dataset：63 条测试用例，6 个维度
- LLM-as-Judge：对话质量多维度打分

**Agent 层（集成、端到端）：**
- 完整环境，真实执行 tools
- 端到端 CRUD、多轮对话、流式输出、边界情况
- 新旧对比基准：准确率、延迟、token 消耗

### 评估设计原则

**任务明确性（Anthropic Step 2）：**
- 每条测试用例必须包含参考解决方案（reference solution），即一个已知能通过评分器的完整 Agent 输出 trace
- 每条用例必须列出可接受的替代方案（acceptable_alternatives）和明确不接受的方案（unacceptable），消除歧义
- 对于有多种合理做法的场景，明确标注哪些都算 pass
- 参考解决方案验证任务是可解决的；如果跨多次试验 0% 通过率，优先检查任务规范而非 Agent 能力

**类别平衡（Anthropic Step 3）：**
- 每种行为必须同时测试「应该发生」和「不应该发生」两个方向
- 单方面评估导致单方面优化（如只测「该追问时追问」→ Agent 变成什么都追问）
- 目标比例：正面:反面 ≈ 2:1 到 1:1 之间

**非确定性处理（pass@k / pass^k）：**
- LLM 输出非确定性，单次 trial 的 pass/fail 有噪音
- pass@k：k 次尝试中至少成功 1 次的概率。条目操作用 pass@3（试几次有一次对可接受）
- pass^k：k 次全部成功的概率。纯对话质量用 pass^3（用户期望每次都好）
- 每个测试用例跑多次（建议 3-5 次），统计通过率而非单次结果

**能力评估 vs 回归评估：**
- 能力评估：问"Agent 能做这个吗？"，低通过率起点，持续爬坡。覆盖多步推理、边界情况、复杂多轮
- 回归评估：问"Agent 还能做这个吗？"，接近 100% 通过率，CI 每次提交跑。覆盖基础 CRUD、简单对话
- 能力评估通过率 > 90% 后，可"毕业"为回归评估，并补充更难的能力 case

**结果验证（outcome grading）：**
- 不仅检查 tool_calls 是否正确（过程），还验证最终状态（结果）
- create_entry 后验证条目是否真的存在于 Storage
- update_entry 后验证状态是否真的变了
- 需要一个 state_check grader 检查环境最终状态

**部分评分：**
- 不用二元 pass/fail，支持多维度部分得分
- 正确搜索到条目但参数有误 → 60%，不是 0%
- 正确理解意图但多余追问 → 70%，不是 0%
- 完全正确 → 100%

**多轮评估用户模拟：**
- 基础：预设用户回复（已设计，30 条固定对话序列）
- 进阶：LLM 模拟用户角色，生成多样化回复
- 模拟用户可以发现预设回复覆盖不到的交互路径

**环境隔离：**
- 每次 trial 从干净环境开始，重置 mock 数据
- 多轮评估使用独立 thread_id，不同 trial 不共享 checkpointer
- 避免共享状态导致评估结果关联性失败

**评估饱和度监控：**
- 监控各维度通过率趋势
- 通过率 > 90% 的维度 → 加入更难的 case 或升级难度
- 防止评估失去改进信号

### Golden Dataset 设计（117 条）

#### 单轮评估（63 条）

| 维度 | 条数 | 评估方式 |
|------|------|---------|
| 工具选择 | 15 | 自动化断言：LLM 选了哪个 tool |
| 参数提取 | 12 | 自动化断言：参数是否正确 |
| 多步推理 | 10 | 自动化断言：tool 调用序列 |
| 追问决策 | 8 | 自动化断言：该不该追问 |
| 纯对话质量 | 10 | LLM-as-Judge 多维打分 |
| 边界情况 | 8 | 自动化断言 + 人工检查 |

#### 反面测试（24 条）

防止单方面优化。每种行为必须同时测试「应该发生」和「不应该发生」。

**不该调用 tool（10 条）：**

| # | 用户输入 | 期望 | 容易误判为 |
|---|---------|------|-----------|
| 1 | "你觉得 Rust 和 Go 哪个好学" | 纯对话 | search_entries |
| 2 | "今天天气不错" | 纯闲聊 | create_entry |
| 3 | "谢谢你的帮助" | 礼貌回复 | 多余操作 |
| 4 | "我能问你一个问题吗" | 确认回复 | — |
| 5 | "你平时都做什么" | 自我介绍 | — |
| 6 | "学习有什么用呢" | 哲学讨论 | create_entry |
| 7 | "我不想学了" | 共情讨论 | update_entry |
| 8 | "算了" | 确认取消 | — |
| 9 | "你确定吗" | 解释/确认 | search_entries |
| 10 | "告诉我一个有趣的事实" | 纯对话 | search_entries |

**不该追问（8 条）：**

| # | 用户输入 | 期望 | 容易误追问 |
|---|---------|------|-----------|
| 1 | "记一个想法：要不要学 Rust" | create_entry | "什么类型？" |
| 2 | "把学 Rust 基础标完成" | update_entry | "你确定吗？" |
| 3 | "搜索关于 Python 的笔记" | search_entries | "搜多少条？" |
| 4 | "删除测试笔记" | delete_entry | "确定删除？" |
| 5 | "这周学了什么" | get_review_summary | "日报还是周报？" |
| 6 | "记个笔记：今天学了所有权" | create_entry | "要加标签吗？" |
| 7 | "把所有进行中的任务标完成" | search→update | "哪些任务？" |
| 8 | "帮我看看这个月的数据" | get_review_summary | "看什么数据？" |

**不该多步（6 条）：**

| # | 用户输入 | 期望 | 容易误多步 |
|---|---------|------|-----------|
| 1 | "记一个想法 xxx" | create_entry 直接创建 | 先 search 检查重复 |
| 2 | "把这周的数据给我" | get_review_summary | 先判断有没有数据 |
| 3 | "删除那条测试笔记" | search→delete（2步合理） | 反复确认 3+ 步 |
| 4 | "搜索 Rust" | search_entries | search→分析→推荐 |
| 5 | "新建任务：学 Rust" | create_entry | create→update→notify |
| 6 | "最近有什么任务" | search_entries | search→统计→建议 |

**平衡性统计：**

| 行为 | 应该发生 | 不应该发生 | 比例 |
|------|---------|-----------|------|
| 调用 tool | 52 | 21 | ~5:2 |
| 追问用户 | 8 | 8 | 1:1 |
| 多步操作 | 10 | 6 | ~5:3 |

#### 多轮评估（30 条）

测试 Agent 在多轮交互中的行为连贯性。单轮评估只验证单次决策，多轮评估验证上下文维护、追问后行动、对话中穿插操作、错误恢复等能力。

**测试数据结构：**
```python
multi_turn_test_case = {
    "id": "MT-001",
    "category": "ask_then_act",
    "turns": [
        {
            "role": "user",
            "content": "记个笔记"
        },
        {
            "role": "agent",
            "expected": {
                "tool_calls": [{"name": "ask_user"}],
                "should_contain": ["什么内容", "关于什么"]
            }
        },
        {
            "role": "user",
            "content": "关于 Rust 的所有权机制"
        },
        {
            "role": "agent",
            "expected": {
                "tool_calls": [{"name": "create_entry", "args": {"type": "note"}}],
                "args_checks": {
                    "content": "Rust 的所有权机制",
                    "tags": ["Rust"]
                }
            }
        }
    ],
    "context": {
        "page": "home",
        "existing_entries": []
    }
}
```

**执行方式：**
按轮次依次输入同一个 thread_id，逐轮评估 Agent 行为，验证后续轮是否利用前轮信息。

**类型 1：追问→用户回复→Agent 行动（10 条）**

每条用例均包含参考解决方案（reference_solution）、可接受替代方案（acceptable_alternatives）和不接受方案（unacceptable），格式同多轮评估测试数据结构。

测试 Agent 追问后能否正确利用用户回复执行操作。

| # | 对话序列 | 检查点 |
|---|---------|--------|
| 1 | "记个笔记" → Agent 追问 → "关于 Rust" | 第 3 轮应 create_entry 且参数来自第 2 轮 |
| 2 | "更新那个任务" → Agent 追问哪个 → "学 Rust 基础" | 第 3 轮应搜索后更新 |
| 3 | "帮我搜索" → Agent 追问搜什么 → "Rust 相关的" | 应 search_entries(keyword="Rust") |
| 4 | "新建一个项目" → Agent 追问 → 给名称和目标 | 应创建含名称和目标的项目 |
| 5 | "删除那个" → Agent 追问 → "测试笔记" | 应搜索确认后删除 |
| 6 | "记个笔记" → Agent 追问 → "算了不用了" | 应取消，不创建 |
| 7 | "更新状态" → Agent 追问 → "把 Rust 标完成" | 应识别出具体条目和目标状态 |
| 8 | "帮我整理" → Agent 追问整理什么 → "这周的笔记" | 应搜索后整理 |
| 9 | "复盘" → Agent 追问范围 → "这周的学习" | 应获取周报后分析 |
| 10 | "记个想法" → Agent 追问 → "嗯...要不要学 Zig" | 应创建 inbox，内容为用户回复 |

**类型 2：上下文引用（8 条）**

测试 Agent 能否理解代词/省略/指代，利用前轮上下文。

| # | 对话序列 | 检查点 |
|---|---------|--------|
| 1 | "搜索 Rust 任务" → 结果返回 → "把它标完成" | "它"指搜索结果中的条目 |
| 2 | "记一个关于 Rust 的笔记" → 创建成功 → "再加个标签系统编程" | 应更新刚创建的笔记 |
| 3 | "这周学了多少" → 回复数据 → "跟上周比怎么样" | 应获取上周数据对比 |
| 4 | "记个想法：学 Rust" → "不对，是学 Zig" | 应理解纠正，创建 Zig 的想法 |
| 5 | "搜索笔记" → 结果返回 → "第二条" | 应理解"第二条"指搜索结果第 2 条 |
| 6 | "新建任务：复习算法" → "再建一个：复习数据库" | 第二轮应独立创建，不依赖第一轮 |
| 7 | "这个月完成了多少任务" → "那笔记呢" | "那...呢"表示同维度不同类型查询 |
| 8 | "把 Rust 任务标完成" → "Go 的也标了" | 第二轮应复用操作逻辑搜索 Go 任务并更新 |

**类型 3：对话中穿插操作（6 条）**

测试聊天和工具调用的自然切换。

| # | 对话序列 | 检查点 |
|---|---------|--------|
| 1 | "今天学了 Rust" → Agent 聊天 → "记下来吧" | 第 3 轮应 create_entry，内容来自第 1 轮 |
| 2 | "最近感觉学不进去" → Agent 共情 → "看看我这周的数据" | 第 3 轮应调用 get_review_summary |
| 3 | "帮我看看这个任务" → Agent 搜索展示 → "给它加个标签重要" | 第 3 轮应更新该任务 |
| 4 | "这周表现怎么样" → Agent 分析 → "写个复盘吧" | 第 3 轮应基于分析创建复盘条目 |
| 5 | "我觉得 Rust 挺难的" → Agent 讨论 → "要不建个项目跟踪一下" | 第 3 轮应创建项目 |
| 6 | "搜索 Rust" → 结果展示 → "这些太旧了，有没有最近的" | 第 3 轮应带上时间过滤重新搜索 |

**类型 4：错误恢复（6 条）**

测试 Agent 处理操作失败或用户纠正后的恢复。

| # | 对话序列 | 检查点 |
|---|---------|--------|
| 1 | "把那个标完成" → Agent 找不到 → "可能叫 Rust 什么的" | 应根据线索重新搜索 |
| 2 | "删除所有笔记" → Agent 拒绝 → "那就删除测试笔记" | 应接受合理请求 |
| 3 | "更新任务" → Agent 追问 → "不对，我是要新建" | 应切换到创建模式 |
| 4 | "搜索 xyz" → 无结果 → "搜 xy 试试" | 应放宽条件重试 |
| 5 | "标记完成" → Agent 报错 → "算了跳过" | 应接受跳过 |
| 6 | "复盘" → Agent 给了周报 → "我要的是月报" | 应纠正时间范围 |

**多轮评估的 LLM-as-Judge 追加维度：**

| 维度 | 分值 | 说明 |
|------|------|------|
| 上下文一致性 (context_consistency) | 1-5 | 后续轮是否利用前轮信息 |
| 对话流畅度 (conversation_fluency) | 1-5 | 追问和回复是否自然 |
| 任务完成度 (task_completion) | 1-5 | 多轮交互后是否达成用户目标 |

### LLM-as-Judge 设计

**评分维度（每项 1-5 分）：**
1. 意图理解 (intent_accuracy)
2. 参数准确 (param_accuracy)
3. 操作合理性 (action_quality)
4. 追问恰当性 (ask_appropriateness)
5. 回复质量 (response_quality)
6. 安全性 (safety)
7. 上下文一致性 (context_consistency) — 多轮评估专用
8. 对话流畅度 (conversation_fluency) — 多轮评估专用
9. 任务完成度 (task_completion) — 多轮评估专用

**Judge 模型策略：**
- 日常：用同一个 LLM 快速评估（低成本）
- 每周/上线前：用更强模型做完整评估

**评分阈值与动作：**
| 分数 | 状态 | 动作 |
|------|------|------|
| ≥4.0 | 通过 | 无需处理 |
| 3.0-3.9 | 待观察 | 累积 3 次同类问题创建 Issue |
| 2.0-2.9 | 需修复 | 自动创建 Issue (high) |
| <2.0 | 严重 | 自动创建 Issue (critical)，告警 |

### 评估转录系统

**核心目标：** 不读转录就不知道评分器是否可靠。确信分数不上升是因为 Agent 性能而非评估缺陷。

**转录记录内容：**
- 测试用例（输入、期望）
- Agent 完整行为 trace（每步 LLM 调用的 input/output/tool_calls/token/延迟）
- 评分器结果（分数、理由）
- 最终判定（pass / agent_error / judge_error / ambiguous）

**存储位置：** `data/eval_transcripts/YYYY-MM-DD/eval-NNN.json`

**转录审查流程：**
1. 每周定期审查（30 分钟）
2. 筛选失败和低分（<3.0）的评估
3. 人工判定：Agent 错误 / 评分器错误 / 模糊
4. Agent 错误 → 创建 Issue，修 Agent
5. 评分器错误 → 校准评分标准/prompt，更新期望答案

**评分器校准指标：**
| 指标 | 目标值 |
|------|-------|
| 评分器准确率（与人工一致） | ≥90% |
| 假阳性率（误报错误） | <10% |
| 假阴性率（漏掉真实错误） | <5% |

## 问题追踪

### Issue 分类

| 类别 | 说明 |
|------|------|
| tool_selection_error | 选错工具 |
| param_extraction_error | 参数提取错 |
| missing_ask | 该追问没追问 |
| wrong_ask | 不该追问却追问 |
| multi_step_error | 多步编排错误 |
| conversation_quality | 对话质量差 |
| safety_violation | 安全问题 |

### 严重程度

| 级别 | 标准 | 处理时效 |
|------|------|---------|
| critical | 数据丢失/安全问题 | 立即修复 |
| high | 核心功能不可用 | 当天修复 |
| medium | 功能可用但体验差 | 本轮迭代 |
| low | 体验优化 | 下轮迭代 |

### 与 log-service 集成

- 评估失败 → `report_issue()`
- 修复中 → `update_issue_status("in_progress")`
- 验证通过 → `update_issue_status("resolved")`

## 监控

### 指标

| 指标 | 计算方式 | 数据来源 |
|------|---------|---------|
| 工具选择准确率 | 正确次数/总调用次数 | Golden Dataset |
| 参数提取准确率 | 参数完全匹配次数/总次数 | Golden Dataset |
| 平均延迟 | 首 token 时间 + 总耗时 | Langfuse trace |
| Token 消耗 | 每轮平均 in/out token | Langfuse trace |
| 追问准确率 | 正确追问+正确不追问/总次数 | Golden Dataset |
| 用户满意度 | thumbs_up/(thumbs_up+thumbs_down) | 用户反馈 |

### 监控频率

| 频率 | 动作 |
|------|------|
| 每次提交 | Golden Dataset LLM 层 |
| 每日 | 完整评估集日报 |
| 每周 | LLM-as-Judge 对话质量 + 趋势 |
| 实时 | Langfuse 记录真实请求 trace |

### 告警规则

- 工具选择准确率 < 85% → 告警
- 平均延迟 > 3s → 告警
- 用户满意度 < 3.5/5 持续 3 天 → 告警
- Token 消耗突增 > 2x → 告警

## 可观测性

- 选择：Langfuse 自部署
- 接入方式：LangGraph CallbackHandler
- 记录内容：每次 LLM 调用的 input/output、token 统计、延迟、完整 ReAct 循环 trace
- 部署方式：Docker 自部署，数据本地存储

## 用户反馈机制

### 反馈入口

每条 Agent 回复右侧：👍 👎 ⚑

### 👎 反馈面板选项

- 理解错了我的意思
- 操作不正确
- 回复没有帮助
- 应该追问但没追问
- 不应该追问但追问了
- 其他（含补充说明）

### 反馈闭环

```
用户反馈 👎
  → POST /feedback
    → 存储到 feedback 表
      → Langfuse 标记 trace 评分
      → 自动创建 Issue (medium)
      → 定期汇总到监控指标
      → bad case 补充到 Golden Dataset
```

## 开放问题

- Agent 循环上限设多少轮（建议 5，需实测调整）
- 对话模式 vs 操作模式的 system prompt 如何平衡
- 旧端点 (/parse, /ai/chat) 的兼容期多长
- 评分器校准的频率和负责人

## 后续动作

- 进入 xlfoundry-plan 拆解实现任务
- 定义 Tools 的 schema（入参/出参）
- 设计统一的 system prompt 模板
- 搭建评估基础设施（Golden Dataset + LLM-as-Judge + 转录系统）
