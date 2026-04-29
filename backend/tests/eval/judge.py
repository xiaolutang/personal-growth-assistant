"""LLM-as-Judge 评分器

10 维度评分系统（7 基础 + 3 多轮专用），每维度 1-5 分。

核心组件:
- JudgeDimension: 10 个评分维度枚举
- JudgeScore: 单维度评分结果
- JudgeResult: 完整评分结果（10 维度 + 总分 + 加权平均）
- LLMJudge: LLM-as-Judge 执行器（mock LLM 调用）
- PartialScorer: 部分评分（60%/70%/100% 梯度）
- OutcomeGrader: state_check grader，验证 Agent 操作后的环境状态
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


# ── 维度定义 ──


class JudgeDimension(str, Enum):
    """10 个评分维度

    7 个基础维度（单轮 + 多轮均适用）:
    - tool_selection: 工具选择是否正确
    - param_extraction: 参数提取是否完整准确
    - response_quality: 回复是否自然、有帮助
    - error_handling: 异常场景是否优雅处理
    - efficiency: 是否在不必要的步骤上浪费时间
    - user_experience: 整体交互是否流畅
    - directness: 是否直接给出结果，不啰嗦不绕弯

    3 个多轮专用维度:
    - context_retention: 是否记住前文信息
    - follow_up_quality: 追问是否必要且合理
    - conversation_coherence: 多轮对话是否逻辑一致
    """

    # 基础维度
    TOOL_SELECTION = "tool_selection"
    PARAM_EXTRACTION = "param_extraction"
    RESPONSE_QUALITY = "response_quality"
    ERROR_HANDLING = "error_handling"
    EFFICIENCY = "efficiency"
    USER_EXPERIENCE = "user_experience"
    DIRECTNESS = "directness"

    # 多轮专用维度
    CONTEXT_RETENTION = "context_retention"
    FOLLOW_UP_QUALITY = "follow_up_quality"
    CONVERSATION_COHERENCE = "conversation_coherence"

    @classmethod
    def base_dimensions(cls) -> List["JudgeDimension"]:
        """获取 7 个基础维度"""
        return [
            cls.TOOL_SELECTION,
            cls.PARAM_EXTRACTION,
            cls.RESPONSE_QUALITY,
            cls.ERROR_HANDLING,
            cls.EFFICIENCY,
            cls.USER_EXPERIENCE,
            cls.DIRECTNESS,
        ]

    @classmethod
    def multi_turn_dimensions(cls) -> List["JudgeDimension"]:
        """获取 3 个多轮专用维度"""
        return [
            cls.CONTEXT_RETENTION,
            cls.FOLLOW_UP_QUALITY,
            cls.CONVERSATION_COHERENCE,
        ]

    @classmethod
    def all_dimensions(cls) -> List["JudgeDimension"]:
        """获取全部 10 个维度"""
        return cls.base_dimensions() + cls.multi_turn_dimensions()


# ── 评分 Prompt 模板 ──

JUDGE_PROMPT_TEMPLATE = """你是一个评估 AI Agent 回复质量的专家评委。请对以下 Agent 回复在指定维度上进行 1-5 分评分。

## 评分标准

### 基础维度

1. **tool_selection** (工具选择): Agent 是否选择了正确的工具？
   - 1分: 完全错误的工具
   - 2分: 工具方向大致正确但选择不当
   - 3分: 基本正确但有更优选择
   - 4分: 正确选择，微小瑕疵
   - 5分: 完美选择最合适的工具

2. **param_extraction** (参数提取): 参数是否完整准确？
   - 1分: 关键参数缺失或错误
   - 2分: 多个参数不准确
   - 3分: 大部分参数正确，个别遗漏
   - 4分: 参数基本完整，微小遗漏
   - 5分: 所有参数完整准确

3. **response_quality** (回复质量): 回复是否自然、有帮助？
   - 1分: 回复不相关或令人困惑
   - 2分: 回复相关但质量低
   - 3分: 基本有用但可以改进
   - 4分: 自然流畅，有帮助
   - 5分: 完美回复，超出预期

4. **error_handling** (错误处理): 异常场景是否优雅处理？
   - 1分: 未处理错误，直接崩溃
   - 2分: 处理了但给用户错误信息
   - 3分: 基本处理，信息不清晰
   - 4分: 良好的错误处理和引导
   - 5分: 优雅处理并提供替代方案

5. **efficiency** (效率): 是否有不必要的步骤？
   - 1分: 大量冗余操作
   - 2分: 有明显的多余步骤
   - 3分: 基本高效，个别冗余
   - 4分: 高效执行，可接受
   - 5分: 路径最短，完美高效

6. **user_experience** (用户体验): 整体交互是否流畅？
   - 1分: 体验极差，用户困惑
   - 2分: 体验不佳，需要改进
   - 3分: 一般体验，可接受
   - 4分: 良好体验，流畅自然
   - 5分: 极佳体验，符合预期

7. **directness** (直接性): 回复是否直接了当？
   - 1分: 大量废话（打招呼、寒暄）后才回应核心问题
   - 2分: 有明显的不必要铺垫或反问（如"要不要帮你查？"）
   - 3分: 基本直接，但有少量可省略的用语
   - 4分: 直接回应，无废话
   - 5分: 精准命中用户需求，信息完整且无多余内容

### 多轮专用维度

7. **context_retention** (上下文保持): 是否记住前文信息？
   - 1分: 完全忽略前文
   - 2分: 记住了部分但有明显遗漏
   - 3分: 基本记住，偶尔遗忘
   - 4分: 很好地保持上下文
   - 5分: 完美利用前文所有信息

8. **follow_up_quality** (追问质量): 追问是否必要且合理？
   - 1分: 无追问或追问完全不相关
   - 2分: 追问存在但质量低
   - 3分: 追问基本合理
   - 4分: 追问精准，帮助理解需求
   - 5分: 追问恰到好处，引导用户

9. **conversation_coherence** (对话连贯性): 多轮对话是否逻辑一致？
   - 1分: 对话前后矛盾
   - 2分: 逻辑不一致处较多
   - 3分: 基本连贯，个别不一致
   - 4分: 对话逻辑清晰
   - 5分: 完美连贯，如真人对话

## 评估输入

### 用户输入
{user_input}

### Agent 回复
{agent_response}

### 工具调用记录
{tool_calls}

### 对话历史（如有）
{conversation_history}

## 输出格式

请以 JSON 格式输出评分，格式如下：
```json
{{
  "dimension_scores": {{
    "tool_selection": {{"score": <1-5>, "reasoning": "<理由>"}},
    "param_extraction": {{"score": <1-5>, "reasoning": "<理由>"}},
    "response_quality": {{"score": <1-5>, "reasoning": "<理由>"}},
    "error_handling": {{"score": <1-5>, "reasoning": "<理由>"}},
    "efficiency": {{"score": <1-5>, "reasoning": "<理由>"}},
    "user_experience": {{"score": <1-5>, "reasoning": "<理由>"}},
    "directness": {{"score": <1-5>, "reasoning": "<理由>"}},
    "context_retention": {{"score": <1-5>, "reasoning": "<理由>"}},
    "follow_up_quality": {{"score": <1-5>, "reasoning": "<理由>"}},
    "conversation_coherence": {{"score": <1-5>, "reasoning": "<理由>"}}
  }}
}}
```

仅输出 JSON，不要有其他内容。"""


# ── 维度权重 ──

DEFAULT_DIMENSION_WEIGHTS: Dict[str, float] = {
    # 基础维度权重
    "tool_selection": 0.14,
    "param_extraction": 0.11,
    "response_quality": 0.11,
    "error_handling": 0.09,
    "efficiency": 0.07,
    "user_experience": 0.09,
    "directness": 0.10,
    # 多轮专用维度权重
    "context_retention": 0.11,
    "follow_up_quality": 0.09,
    "conversation_coherence": 0.09,
}


# ── 数据结构 ──


@dataclass
class JudgeScore:
    """单维度评分结果

    Attributes:
        dimension: 评分维度
        score: 分数（1-5）
        reasoning: 评分理由
    """

    dimension: JudgeDimension
    score: int
    reasoning: str = ""

    def __post_init__(self):
        if not 1 <= self.score <= 5:
            raise ValueError(
                f"Score must be between 1 and 5, got {self.score} "
                f"for dimension {self.dimension.value}"
            )


@dataclass
class JudgeResult:
    """完整评分结果

    Attributes:
        scores: 各维度评分
        test_id: 测试用例 ID
        raw_llm_output: LLM 原始输出（用于调试）
    """

    scores: Dict[str, JudgeScore] = field(default_factory=dict)
    test_id: str = ""
    raw_llm_output: str = ""
    metadata: Optional[Dict[str, Any]] = None

    @property
    def total_score(self) -> int:
        """所有维度分数之和"""
        return sum(s.score for s in self.scores.values())

    @property
    def max_possible_score(self) -> int:
        """最大可能分数"""
        return len(self.scores) * 5 if self.scores else 50

    @property
    def average_score(self) -> float:
        """简单平均分"""
        if not self.scores:
            return 0.0
        return self.total_score / len(self.scores)

    @property
    def weighted_average(self) -> float:
        """加权平均分（1-5 分范围）"""
        if not self.scores:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0
        for dim, score in self.scores.items():
            weight = DEFAULT_DIMENSION_WEIGHTS.get(dim, 0.05)
            weighted_sum += score.score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    @property
    def percentage(self) -> float:
        """得分百分比（0-100）"""
        if self.max_possible_score == 0:
            return 0.0
        return (self.total_score / self.max_possible_score) * 100

    def get_score(self, dimension: JudgeDimension) -> Optional[JudgeScore]:
        """获取指定维度的评分"""
        return self.scores.get(dimension.value)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "test_id": self.test_id,
            "total_score": self.total_score,
            "max_possible_score": self.max_possible_score,
            "average_score": round(self.average_score, 2),
            "weighted_average": round(self.weighted_average, 2),
            "percentage": round(self.percentage, 1),
            "dimension_scores": {
                dim: {
                    "score": s.score,
                    "reasoning": s.reasoning,
                }
                for dim, s in self.scores.items()
            },
            "metadata": self.metadata,
        }


# ── LLM-as-Judge 执行器 ──


class LLMJudge:
    """LLM-as-Judge 执行器

    使用 LLM 对 Agent 输出进行多维度评分。
    在测试中通过 inject_llm_response 进行 mock，不依赖真实 API。

    用法:
        # 生产环境
        judge = LLMJudge()
        result = await judge.evaluate(user_input, agent_response, tool_calls)

        # 测试环境（mock）
        judge = LLMJudge(inject_llm_response=mock_response)
        result = await judge.evaluate(user_input, agent_response, tool_calls)
    """

    def __init__(
        self,
        inject_llm_response: Optional[str] = None,
        dimensions: Optional[List[JudgeDimension]] = None,
        use_real_llm: bool = False,
    ):
        """初始化 LLM Judge

        Args:
            inject_llm_response: 注入的 LLM 回复（用于测试 mock）
            dimensions: 要评估的维度列表，默认全部 9 个
            use_real_llm: 是否使用真实 LLM 进行评分（集成测试用）
        """
        self.inject_llm_response = inject_llm_response
        self.dimensions = dimensions or JudgeDimension.all_dimensions()
        self._llm_caller = None
        self._real_llm_degraded = False

        if use_real_llm and inject_llm_response is None:
            try:
                from app.infrastructure.llm.api_caller import APICaller
                self._llm_caller = APICaller()
            except Exception as e:
                self._real_llm_degraded = True
                self._degraded_reason = f"APICaller 初始化失败: {e}"

    def _build_prompt(
        self,
        user_input: str,
        agent_response: str,
        tool_calls: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """构建评分 prompt"""
        tool_calls_str = json.dumps(tool_calls, ensure_ascii=False, indent=2)
        history_str = (
            json.dumps(conversation_history, ensure_ascii=False, indent=2)
            if conversation_history
            else "（无对话历史）"
        )

        return JUDGE_PROMPT_TEMPLATE.format(
            user_input=user_input,
            agent_response=agent_response,
            tool_calls=tool_calls_str,
            conversation_history=history_str,
        )

    def _parse_llm_output(self, raw_output: str) -> Dict[str, Dict[str, Any]]:
        """解析 LLM 输出的 JSON 评分"""
        # 尝试提取 JSON（处理 markdown 代码块包裹的情况）
        text = raw_output.strip()
        if text.startswith("```"):
            # 去除 markdown 代码块标记
            lines = text.split("\n")
            # 去掉首行 ```json 和末行 ```
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
            return data.get("dimension_scores", {})
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON 部分
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    data = json.loads(text[start:end])
                    return data.get("dimension_scores", {})
                except json.JSONDecodeError:
                    pass
            return {}

    def _build_result_from_parsed(
        self,
        parsed: Dict[str, Dict[str, Any]],
        test_id: str = "",
        raw_output: str = "",
    ) -> JudgeResult:
        """从解析后的数据构建 JudgeResult"""
        scores: Dict[str, JudgeScore] = {}
        for dim in self.dimensions:
            dim_key = dim.value
            if dim_key in parsed:
                dim_data = parsed[dim_key]
                score_val = dim_data.get("score", 3)
                reasoning = dim_data.get("reasoning", "")
                # 确保 score 在有效范围
                score_val = max(1, min(5, int(score_val)))
                scores[dim_key] = JudgeScore(
                    dimension=dim,
                    score=score_val,
                    reasoning=reasoning,
                )
            else:
                # 缺失维度给默认中间分
                scores[dim_key] = JudgeScore(
                    dimension=dim,
                    score=3,
                    reasoning="维度评分缺失，使用默认值",
                )

        return JudgeResult(
            scores=scores,
            test_id=test_id,
            raw_llm_output=raw_output,
        )

    async def evaluate(
        self,
        user_input: str,
        agent_response: str,
        tool_calls: List[Dict[str, Any]],
        test_id: str = "",
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> JudgeResult:
        """对 Agent 输出进行评分

        Args:
            user_input: 用户输入文本
            agent_response: Agent 回复文本
            tool_calls: Agent 的工具调用记录
            test_id: 测试用例 ID
            conversation_history: 对话历史（多轮评估时使用）

        Returns:
            JudgeResult 完整评分结果
        """
        # 构建 prompt（实际调用时使用）
        _prompt = self._build_prompt(
            user_input, agent_response, tool_calls, conversation_history
        )

        # 获取 LLM 回复（mock 或真实调用）
        if self.inject_llm_response is not None:
            raw_output = self.inject_llm_response
        elif self._llm_caller is not None:
            # 使用真实 LLM 评分
            messages = [
                {"role": "system", "content": "你是 AI Agent 评估专家，只输出 JSON。"},
                {"role": "user", "content": _prompt},
            ]
            raw_output = await self._llm_caller.call(
                messages, response_format={"type": "json_object"}
            )
        else:
            # 无注入且无 LLM 时，返回默认中间分
            raw_output = self._generate_default_response()

        # 解析输出
        parsed = self._parse_llm_output(raw_output)
        result = self._build_result_from_parsed(parsed, test_id, raw_output)

        # 标记降级模式
        if self._real_llm_degraded:
            result.metadata = {"degraded": True, "degraded_reason": self._degraded_reason}

        return result

    def _generate_default_response(self) -> str:
        """生成默认回复（无 LLM 调用时）"""
        scores = {}
        for dim in self.dimensions:
            scores[dim.value] = {"score": 3, "reasoning": "默认评分（无 LLM 调用）"}

        return json.dumps({"dimension_scores": scores})

    async def evaluate_multi_turn(
        self,
        turns: List[Dict[str, Any]],
        test_id: str = "",
    ) -> JudgeResult:
        """对多轮对话进行评分

        Args:
            turns: 多轮对话记录，每条包含 role/content/tool_calls 等
            test_id: 测试用例 ID

        Returns:
            JudgeResult
        """
        # 构建对话历史
        conversation_history = []
        all_tool_calls: List[Dict[str, Any]] = []
        last_user_input = ""
        last_agent_response = ""

        for turn in turns:
            role = turn.get("role", "")
            content = turn.get("content", "")
            conversation_history.append({"role": role, "content": content})

            if role == "user":
                last_user_input = content
            elif role == "agent":
                last_agent_response = content
                if "tool_calls" in turn:
                    all_tool_calls.extend(turn["tool_calls"])

        return await self.evaluate(
            user_input=last_user_input,
            agent_response=last_agent_response,
            tool_calls=all_tool_calls,
            test_id=test_id,
            conversation_history=conversation_history,
        )


# ── 部分评分 ──


@dataclass
class PartialScoreThreshold:
    """部分评分阈值

    Attributes:
        threshold: 百分比阈值（0-100）
        label: 标签
        score: 对应分数（0-5）
    """

    threshold: float
    label: str
    score: float


# 默认梯度阈值
DEFAULT_PARTIAL_THRESHOLDS: List[PartialScoreThreshold] = [
    PartialScoreThreshold(threshold=0.0, label="完全失败", score=0.0),
    PartialScoreThreshold(threshold=40.0, label="严重不足", score=1.0),
    PartialScoreThreshold(threshold=50.0, label="明显不足", score=2.0),
    PartialScoreThreshold(threshold=60.0, label="基本及格", score=3.0),
    PartialScoreThreshold(threshold=70.0, label="良好", score=3.5),
    PartialScoreThreshold(threshold=80.0, label="优秀", score=4.0),
    PartialScoreThreshold(threshold=90.0, label="卓越", score=4.5),
    PartialScoreThreshold(threshold=95.0, label="完美", score=5.0),
]


class PartialScorer:
    """部分评分器

    根据得分百分比映射到梯度分数。
    支持 60%/70%/100% 等梯度得分。

    用法:
        scorer = PartialScorer()
        grade = scorer.score(judge_result)
        # grade = {"label": "良好", "score": 3.5, "percentage": 75.0}
    """

    def __init__(
        self,
        thresholds: Optional[List[PartialScoreThreshold]] = None,
    ):
        self.thresholds = thresholds or DEFAULT_PARTIAL_THRESHOLDS

    def score(self, judge_result: JudgeResult) -> Dict[str, Any]:
        """计算部分评分

        Args:
            judge_result: Judge 评分结果

        Returns:
            包含 label、score、percentage 的字典
        """
        percentage = judge_result.percentage

        # 找到匹配的最高阈值
        matched = self.thresholds[0]
        for threshold in self.thresholds:
            if percentage >= threshold.threshold:
                matched = threshold

        return {
            "label": matched.label,
            "score": matched.score,
            "percentage": round(percentage, 1),
            "total_score": judge_result.total_score,
            "max_possible_score": judge_result.max_possible_score,
        }

    def grade(self, judge_result: JudgeResult) -> str:
        """返回等级标签

        Args:
            judge_result: Judge 评分结果

        Returns:
            等级标签字符串
        """
        return self.score(judge_result)["label"]

    def batch_score(
        self, results: List[JudgeResult]
    ) -> List[Dict[str, Any]]:
        """批量评分

        Args:
            results: JudgeResult 列表

        Returns:
            评分字典列表
        """
        return [self.score(r) for r in results]

    def statistics(
        self, results: List[JudgeResult]
    ) -> Dict[str, Any]:
        """统计评分分布

        Args:
            results: JudgeResult 列表

        Returns:
            统计信息字典
        """
        if not results:
            return {
                "total": 0,
                "average_percentage": 0.0,
                "grade_distribution": {},
            }

        scores = self.batch_score(results)
        percentages = [s["percentage"] for s in scores]
        grade_counts: Dict[str, int] = {}
        for s in scores:
            grade_counts[s["label"]] = grade_counts.get(s["label"], 0) + 1

        return {
            "total": len(results),
            "average_percentage": round(sum(percentages) / len(percentages), 1),
            "min_percentage": round(min(percentages), 1),
            "max_percentage": round(max(percentages), 1),
            "grade_distribution": grade_counts,
        }


# ── Outcome Grader ──


@dataclass
class StateCheck:
    """最终状态检查

    Attributes:
        tool: 期望调用的工具
        args_contain: 参数中应包含的关键词列表
        args_exact: 参数中应精确匹配的键值对
        should_not_call: 不应调用的工具列表
    """

    tool: str = ""
    args_contain: List[str] = field(default_factory=list)
    args_exact: Dict[str, Any] = field(default_factory=dict)
    should_not_call: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateCheck":
        return cls(
            tool=data.get("tool", ""),
            args_contain=data.get("args_contain", []),
            args_exact=data.get("args_exact", {}),
            should_not_call=data.get("should_not_call", []),
        )


@dataclass
class OutcomeGrade:
    """Outcome 评分结果

    Attributes:
        passed: 是否通过状态检查
        tool_matched: 工具是否匹配
        args_contained: 参数包含检查结果
        args_exact_matched: 参数精确匹配结果
        no_violations: 未违反 should_not_call 约束
        details: 详细信息
    """

    passed: bool = False
    tool_matched: bool = False
    args_contained: bool = True
    args_exact_matched: bool = True
    no_violations: bool = True
    details: str = ""


class OutcomeGrader:
    """state_check grader

    验证 Agent 操作后的最终环境状态。
    检查 Agent 是否调用了正确的工具、参数是否正确、
    是否避免了不应调用的工具。

    用法:
        grader = OutcomeGrader()
        grade = grader.grade(state_check, actual_tool_calls)
    """

    def grade(
        self,
        state_check: StateCheck,
        actual_tool_calls: List[Dict[str, Any]],
    ) -> OutcomeGrade:
        """验证最终环境状态

        Args:
            state_check: 期望的最终状态
            actual_tool_calls: Agent 实际的工具调用记录

        Returns:
            OutcomeGrade 评分结果
        """
        details_parts: List[str] = []

        # 1. 检查工具是否匹配
        tool_matched = False
        if state_check.tool:
            for call in actual_tool_calls:
                if call.get("tool") == state_check.tool:
                    tool_matched = True
                    break
            if not tool_matched:
                actual_tools = [c.get("tool", "") for c in actual_tool_calls]
                details_parts.append(
                    f"期望工具 '{state_check.tool}' 未被调用，"
                    f"实际调用: {actual_tools}"
                )
        else:
            tool_matched = True  # 无工具要求

        # 2. 检查参数包含
        args_contained = True
        if state_check.args_contain and state_check.tool:
            target_call = self._find_tool_call(
                actual_tool_calls, state_check.tool
            )
            if target_call:
                call_args_str = json.dumps(
                    target_call.get("args", {}), ensure_ascii=False
                )
                missing = []
                for keyword in state_check.args_contain:
                    if keyword not in call_args_str:
                        missing.append(keyword)
                if missing:
                    args_contained = False
                    details_parts.append(
                        f"参数缺少关键词: {missing}"
                    )
            else:
                args_contained = False
                details_parts.append(
                    f"无法检查参数：工具 '{state_check.tool}' 未被调用"
                )

        # 3. 检查参数精确匹配
        args_exact_matched = True
        if state_check.args_exact and state_check.tool:
            target_call = self._find_tool_call(
                actual_tool_calls, state_check.tool
            )
            if target_call:
                call_args = target_call.get("args", {})
                for key, expected_val in state_check.args_exact.items():
                    actual_val = call_args.get(key)
                    if actual_val != expected_val:
                        args_exact_matched = False
                        details_parts.append(
                            f"参数 '{key}' 不匹配: "
                            f"期望 {expected_val}, 实际 {actual_val}"
                        )
            else:
                args_exact_matched = False

        # 4. 检查不应调用的工具
        no_violations = True
        if state_check.should_not_call:
            actual_tools = [c.get("tool", "") for c in actual_tool_calls]
            violated = [
                t for t in actual_tools if t in state_check.should_not_call
            ]
            if violated:
                no_violations = False
                details_parts.append(f"违反约束，调用了: {violated}")

        # 综合判定
        passed = (
            tool_matched and args_contained and args_exact_matched and no_violations
        )

        if not details_parts:
            details_parts.append("所有检查通过")

        return OutcomeGrade(
            passed=passed,
            tool_matched=tool_matched,
            args_contained=args_contained,
            args_exact_matched=args_exact_matched,
            no_violations=no_violations,
            details="; ".join(details_parts),
        )

    def grade_from_dict(
        self,
        state_check_dict: Dict[str, Any],
        actual_tool_calls: List[Dict[str, Any]],
    ) -> OutcomeGrade:
        """从字典构建 StateCheck 并验证

        Args:
            state_check_dict: 状态检查配置字典
            actual_tool_calls: 实际工具调用

        Returns:
            OutcomeGrade
        """
        state_check = StateCheck.from_dict(state_check_dict)
        return self.grade(state_check, actual_tool_calls)

    def _find_tool_call(
        self,
        tool_calls: List[Dict[str, Any]],
        tool_name: str,
    ) -> Optional[Dict[str, Any]]:
        """在工具调用列表中找到指定工具的调用"""
        for call in tool_calls:
            if call.get("tool") == tool_name:
                return call
        return None
