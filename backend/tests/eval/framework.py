"""Golden Dataset 评估框架核心

组件:
- TestCase / NegativeTestCase: 测试用例数据类
- DatasetLoader: JSON 文件加载器
- pass_at_k / pass_hat_k: 通过率指标
- EvaluationResult: 单次评估结果
- EvaluationReport: 聚合报告
- GoldenDatasetRunner: 执行器（mock Agent，环境隔离）
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# ── 数据类 ──


@dataclass
class ReferenceSolution:
    """标准答案：期望 Agent 调用的 tool 及参数"""

    tool: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCase:
    """单轮正向测试用例

    Attributes:
        id: 唯一标识，如 ST-001
        category: 分类维度（tool_selection / param_extraction / multi_step / ask_user / pure_chat / boundary）
        user_input: 用户输入文本
        expected_tools: 期望调用的 tool 名称列表（有序）
        expected_args: 期望的参数键值对（部分匹配）
        reference_solution: 标准答案
        acceptable_alternatives: 可接受的替代 tool 列表
        unacceptable: 不可接受的 tool 列表
    """

    id: str
    category: str
    user_input: str
    expected_tools: List[str] = field(default_factory=list)
    expected_args: Dict[str, Any] = field(default_factory=dict)
    reference_solution: ReferenceSolution = field(default_factory=lambda: ReferenceSolution(tool=""))
    acceptable_alternatives: List[str] = field(default_factory=list)
    unacceptable: List[str] = field(default_factory=list)
    behavior_checks: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        ref_data = data.get("reference_solution", {})
        reference = ReferenceSolution(
            tool=ref_data.get("tool", ""),
            args=ref_data.get("args", {}),
        )
        return cls(
            id=data["id"],
            category=data["category"],
            user_input=data["user_input"],
            expected_tools=data.get("expected_tools", []),
            expected_args=data.get("expected_args", {}),
            reference_solution=reference,
            acceptable_alternatives=data.get("acceptable_alternatives", []),
            unacceptable=data.get("unacceptable", []),
            behavior_checks=data.get("behavior_checks", {}),
        )


@dataclass
class NegativeTestCase:
    """负面测试用例：Agent 不应该做的行为

    Attributes:
        id: 唯一标识，如 NEG-001
        category: 分类（no_tool / no_ask / no_multi_step）
        user_input: 用户输入
        should_not_call: 不应调用的 tool 列表
        reason: 为什么不该调用的原因说明
    """

    id: str
    category: str
    user_input: str
    should_not_call: List[str] = field(default_factory=list)
    reason: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegativeTestCase":
        return cls(
            id=data["id"],
            category=data["category"],
            user_input=data["user_input"],
            should_not_call=data.get("should_not_call", []),
            reason=data.get("reason", ""),
        )


# ── 指标计算 ──


def pass_at_k(results: List[bool], k: int = 3) -> float:
    """计算 pass@k 指标

    k 次独立采样中至少通过一次的概率。
    公式: 1 - ((n - c) choose k) / (n choose k)
    其中 n = 总尝试次数, c = 通过次数。

    如果 n < k，返回 1.0（数据不足时不做判断）。

    Args:
        results: 每次 trial 的通过/失败列表
        k: 采样次数

    Returns:
        pass@k 概率值 [0.0, 1.0]
    """
    n = len(results)
    if n == 0:
        return 0.0
    if n < k:
        # 数据不足 k 次：只要有一次通过就算通过
        return 1.0 if any(results) else 0.0

    c = sum(results)
    if n - c < k:
        # (n-c) < k 意味着失败次数少于 k，所以 k 次采样必然命中至少一个成功
        return 1.0

    # 精确计算: 1 - C(n-c, k) / C(n, k)
    # 使用连乘避免大数溢出
    numerator = 1.0
    denominator = 1.0
    for i in range(k):
        numerator *= (n - c - i)
        denominator *= (n - i)

    return 1.0 - numerator / denominator


def pass_hat_k(results: List[bool], k: int = 3) -> float:
    """计算 pass^k (pass-hat-k) 指标

    最好 k 次采样中至少通过 1 次的概率（best-of-k）。
    即从 n 次结果中取最好的 k 次，看是否包含通过。

    等价于: 如果有 >= 1 次通过，则 pass^k = 1.0。
    实际语义：对单条用例，跑 k 次，看最好的结果是否通过。

    对于已有结果列表，我们用连续 k 次的滑动窗口来近似。
    如果任何连续 k 次窗口中有至少 1 次通过，则算通过。

    Args:
        results: 每次 trial 的通过/失败列表
        k: 窗口大小

    Returns:
        pass^k 概率值 [0.0, 1.0]
    """
    n = len(results)
    if n == 0:
        return 0.0

    # 如果有任何一次通过，best-of-k 必然通过
    if any(results):
        return 1.0

    return 0.0


# ── 加载器 ──

DATASETS_DIR = Path(__file__).parent / "datasets"


class DatasetLoader:
    """从 JSON 文件加载测试用例"""

    @staticmethod
    def load_test_cases(filepath: str | Path) -> List[TestCase]:
        """加载正向测试用例

        Args:
            filepath: JSON 文件路径（相对于 datasets/ 目录或绝对路径）

        Returns:
            TestCase 列表
        """
        path = Path(filepath)
        if not path.is_absolute():
            path = DATASETS_DIR / path

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [TestCase.from_dict(item) for item in data]

    @staticmethod
    def load_negative_cases(filepath: str | Path) -> List[NegativeTestCase]:
        """加载负面测试用例

        Args:
            filepath: JSON 文件路径（相对于 datasets/ 目录或绝对路径）

        Returns:
            NegativeTestCase 列表
        """
        path = Path(filepath)
        if not path.is_absolute():
            path = DATASETS_DIR / path

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [NegativeTestCase.from_dict(item) for item in data]

    @staticmethod
    def load_single_turn() -> List[TestCase]:
        """快捷方法：加载单轮 63 条测试数据"""
        return DatasetLoader.load_test_cases("single_turn_68.json")

    @staticmethod
    def load_negative() -> List[NegativeTestCase]:
        """快捷方法：加载负面 24 条测试数据"""
        return DatasetLoader.load_negative_cases("negative_24.json")


# ── 评估结果 ──


@dataclass
class EvaluationResult:
    """单次评估结果

    Attributes:
        test_id: 测试用例 ID
        passed: 是否通过
        actual_tools: Agent 实际调用的 tool 列表
        actual_args: Agent 实际的参数
        error: 错误信息（如果异常）
        trial_index: 第几次 trial
        thread_id: 本次 trial 的 thread_id
    """

    test_id: str
    passed: bool = False
    actual_tools: List[str] = field(default_factory=list)
    actual_args: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    trial_index: int = 0
    thread_id: str = ""


@dataclass
class NegativeEvalResult:
    """负面测试评估结果

    Attributes:
        test_id: 测试用例 ID
        violated: 是否违反了约束（True = 不应该调用但调用了）
        actual_tools: Agent 实际调用的 tool 列表
        violated_tools: 具体违反的 tool
        trial_index: 第几次 trial
        thread_id: 本次 trial 的 thread_id
    """

    test_id: str
    violated: bool = False
    actual_tools: List[str] = field(default_factory=list)
    violated_tools: List[str] = field(default_factory=list)
    trial_index: int = 0
    thread_id: str = ""


# ── 判定逻辑 ──


def judge_test_case(
    test_case: TestCase,
    actual_tools: List[str],
    actual_args: List[Dict[str, Any]],
    agent_response: str = "",
) -> bool:
    """判定正向测试用例是否通过

    判定逻辑:
    1. 如果期望的 tool 在 expected_tools 中且被调用 → 检查通过
    2. 如果 reference_solution 的 tool 被调用 → 通过
    3. 如果调用了 unacceptable 中的 tool → 失败
    4. acceptable_alternatives 中的 tool 也算通过
    5. 如果有 behavior_checks，额外检查回复文本的行为约束

    Args:
        test_case: 测试用例
        actual_tools: 实际调用的 tool 列表
        actual_args: 实际参数列表
        agent_response: Agent 的文本回复（用于 behavior_checks 检查）

    Returns:
        是否通过
    """
    # behavior_checks 检查（基于回复文本）
    if test_case.behavior_checks:
        checks = test_case.behavior_checks
        resp = agent_response.strip()

        if checks.get("no_greeting"):
            # 用词边界匹配，避免 "this"/"highlight" 误判
            import re
            greeting_patterns = [
                r"^你好", r"^嗨[，,！!]", r"^hello[!!,.\s]",
                r"^hi[!!,.\s]", r"^嘿[，,！!]",
            ]
            resp_lower = resp.lower()
            for pat in greeting_patterns:
                if re.search(pat, resp_lower):
                    return False
        if checks.get("no_ask_to_search"):
            ask_patterns = ["要不要帮你查", "需要我帮你查", "要不要查一下", "要不要搜索"]
            if any(p in resp for p in ask_patterns):
                return False
        if checks.get("must_show_details"):
            # 回复不能太短（说明没展示详细内容）
            if len(resp) < 20:
                return False

    if not actual_tools:
        # 没有调用任何 tool — 如果期望也没有 tool，则正确
        if not test_case.expected_tools and not test_case.reference_solution.tool:
            return True
        # 对于 pure_chat 类别，不调用 tool 是正确的
        if test_case.category == "pure_chat":
            return True
        return False

    # 检查是否调用了 unacceptable 的 tool
    for tool in actual_tools:
        if tool in test_case.unacceptable:
            return False

    # 构建允许的 tool 集合
    allowed_tools = set(test_case.expected_tools)
    if test_case.reference_solution.tool:
        allowed_tools.add(test_case.reference_solution.tool)
    allowed_tools.update(test_case.acceptable_alternatives)

    # 检查是否至少调用了期望的 tool
    for tool in actual_tools:
        if tool in allowed_tools:
            return True

    return False


def judge_negative_case(
    test_case: NegativeTestCase,
    actual_tools: List[str],
) -> tuple[bool, List[str]]:
    """判定负面测试用例是否违反约束

    Returns:
        (violated, violated_tools)
        violated=True 表示违反了约束（不应该调用但调用了）
    """
    violated_tools = [t for t in actual_tools if t in test_case.should_not_call]
    return len(violated_tools) > 0, violated_tools


# ── 报告 ──


@dataclass
class CategoryStats:
    """单个分类维度的统计"""

    category: str
    total: int = 0
    passed: int = 0
    pass_at_k_value: float = 0.0
    pass_hat_k_value: float = 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0


@dataclass
class EvaluationReport:
    """评估聚合报告

    按分类维度统计 pass@k 和 pass^k 指标。
    """

    dataset_name: str = ""
    total_cases: int = 0
    total_passed: int = 0
    k: int = 3
    category_stats: Dict[str, CategoryStats] = field(default_factory=dict)
    results: List[EvaluationResult] = field(default_factory=list)

    @property
    def overall_pass_rate(self) -> float:
        return self.total_passed / self.total_cases if self.total_cases > 0 else 0.0

    @property
    def overall_pass_at_k(self) -> float:
        if not self.results:
            return 0.0
        # 按用例分组
        by_case: Dict[str, List[bool]] = {}
        for r in self.results:
            by_case.setdefault(r.test_id, []).append(r.passed)
        case_pass_at_k = [pass_at_k(v, self.k) for v in by_case.values()]
        return sum(case_pass_at_k) / len(case_pass_at_k) if case_pass_at_k else 0.0

    @property
    def overall_pass_hat_k(self) -> float:
        if not self.results:
            return 0.0
        by_case: Dict[str, List[bool]] = {}
        for r in self.results:
            by_case.setdefault(r.test_id, []).append(r.passed)
        case_pass_hat_k = [pass_hat_k(v, self.k) for v in by_case.values()]
        return sum(case_pass_hat_k) / len(case_pass_hat_k) if case_pass_hat_k else 0.0

    def to_text(self) -> str:
        """生成人类可读的文本报告"""
        lines = [
            f"=== Evaluation Report: {self.dataset_name} ===",
            f"Total cases: {self.total_cases}",
            f"Total passed: {self.total_passed}",
            f"Overall pass rate: {self.overall_pass_rate:.2%}",
            f"Overall pass@{self.k}: {self.overall_pass_at_k:.2%}",
            f"Overall pass^{self.k}: {self.overall_pass_hat_k:.2%}",
            "",
            "--- By Category ---",
        ]

        for cat, stats in sorted(self.category_stats.items()):
            lines.append(
                f"  {cat}: {stats.passed}/{stats.total} "
                f"(rate={stats.pass_rate:.2%}, "
                f"pass@{self.k}={stats.pass_at_k_value:.2%}, "
                f"pass^{self.k}={stats.pass_hat_k_value:.2%})"
            )

        return "\n".join(lines)


@dataclass
class NegativeReport:
    """负面测试报告"""

    dataset_name: str = ""
    total_cases: int = 0
    total_violations: int = 0
    results: List[NegativeEvalResult] = field(default_factory=list)

    @property
    def violation_rate(self) -> float:
        return self.total_violations / self.total_cases if self.total_cases > 0 else 0.0

    def to_text(self) -> str:
        lines = [
            f"=== Negative Test Report: {self.dataset_name} ===",
            f"Total cases: {self.total_cases}",
            f"Total violations: {self.total_violations}",
            f"Violation rate: {self.violation_rate:.2%}",
            "",
            "--- By Category ---",
        ]

        by_cat: Dict[str, List[NegativeEvalResult]] = {}
        for r in self.results:
            cat = r.test_id.split("-")[0]  # 从 ID 推断分类前缀
            by_cat.setdefault(cat, []).append(r)

        # 用更清晰的分类名
        cat_names = {
            "NEG": "negative",
        }

        for cat, cat_results in sorted(by_cat.items()):
            violated = sum(1 for r in cat_results if r.violated)
            total = len(cat_results)
            cat_label = cat_names.get(cat, cat)
            lines.append(f"  {cat_label}: {violated}/{total} violations")

        return "\n".join(lines)


# ── 执行器 ──


class GoldenDatasetRunner:
    """Golden Dataset 评估执行器

    特性:
    - 环境隔离：每次 trial 使用独立 thread_id
    - Mock Agent：通过注入的 invoke_fn 模拟 Agent 调用
    - 支持 pass@k 多次 trial 评估
    """

    def __init__(
        self,
        invoke_fn: Any = None,
        k: int = 3,
        num_trials: int = 3,
    ):
        """初始化执行器

        Args:
            invoke_fn: 异步函数，接收 (user_input, thread_id) 返回 Agent 输出
                       如果为 None，使用 mock 默认行为
            k: pass@k 的 k 值
            num_trials: 每条用例执行次数
        """
        self.invoke_fn = invoke_fn
        self.k = k
        self.num_trials = num_trials

    def _generate_thread_id(self) -> str:
        """生成独立的 thread_id，确保环境隔离"""
        return f"eval-{uuid.uuid4().hex[:12]}"

    async def run_single_case(
        self,
        test_case: TestCase,
    ) -> List[EvaluationResult]:
        """对单条用例执行多次 trial

        每次 trial 使用独立的 thread_id，确保环境隔离。

        Args:
            test_case: 正向测试用例

        Returns:
            EvaluationResult 列表（长度 = num_trials）
        """
        results = []

        for trial_idx in range(self.num_trials):
            thread_id = self._generate_thread_id()

            try:
                if self.invoke_fn is not None:
                    agent_output = await self.invoke_fn(
                        test_case.user_input, thread_id
                    )
                    actual_tools = agent_output.get("tools", [])
                    actual_args = agent_output.get("args", [])
                    agent_response = agent_output.get("content", "")
                else:
                    # 无 invoke_fn：返回空结果（纯框架模式）
                    actual_tools = []
                    actual_args = []
                    agent_response = ""

                passed = judge_test_case(test_case, actual_tools, actual_args, agent_response)

                results.append(
                    EvaluationResult(
                        test_id=test_case.id,
                        passed=passed,
                        actual_tools=actual_tools,
                        actual_args=actual_args,
                        trial_index=trial_idx,
                        thread_id=thread_id,
                    )
                )
            except Exception as e:
                results.append(
                    EvaluationResult(
                        test_id=test_case.id,
                        passed=False,
                        error=str(e),
                        trial_index=trial_idx,
                        thread_id=thread_id,
                    )
                )

        return results

    async def run_negative_case(
        self,
        test_case: NegativeTestCase,
    ) -> List[NegativeEvalResult]:
        """对单条负面用例执行多次 trial

        Args:
            test_case: 负面测试用例

        Returns:
            NegativeEvalResult 列表
        """
        results = []

        for trial_idx in range(self.num_trials):
            thread_id = self._generate_thread_id()

            try:
                if self.invoke_fn is not None:
                    agent_output = await self.invoke_fn(
                        test_case.user_input, thread_id
                    )
                    actual_tools = agent_output.get("tools", [])
                else:
                    actual_tools = []

                violated, violated_tools = judge_negative_case(
                    test_case, actual_tools
                )

                results.append(
                    NegativeEvalResult(
                        test_id=test_case.id,
                        violated=violated,
                        actual_tools=actual_tools,
                        violated_tools=violated_tools,
                        trial_index=trial_idx,
                        thread_id=thread_id,
                    )
                )
            except Exception as e:
                results.append(
                    NegativeEvalResult(
                        test_id=test_case.id,
                        violated=False,
                        actual_tools=[],
                        violated_tools=[],
                        trial_index=trial_idx,
                        thread_id=thread_id,
                    )
                )

        return results

    async def run_dataset(
        self,
        test_cases: List[TestCase],
        dataset_name: str = "single_turn",
    ) -> EvaluationReport:
        """执行完整数据集评估

        Args:
            test_cases: 测试用例列表
            dataset_name: 数据集名称

        Returns:
            EvaluationReport 聚合报告
        """
        all_results: List[EvaluationResult] = []
        category_results: Dict[str, List[EvaluationResult]] = {}

        for tc in test_cases:
            case_results = await self.run_single_case(tc)
            all_results.extend(case_results)

            for r in case_results:
                category_results.setdefault(tc.category, []).append(r)

        # 构建分类统计
        category_stats: Dict[str, CategoryStats] = {}
        for cat, cat_results in category_results.items():
            # 按用例 ID 分组计算 pass@k
            by_case_id: Dict[str, List[bool]] = {}
            for r in cat_results:
                by_case_id.setdefault(r.test_id, []).append(r.passed)

            case_pass_rates = [pass_at_k(v, self.k) for v in by_case_id.values()]
            case_pass_hat_rates = [pass_hat_k(v, self.k) for v in by_case_id.values()]

            total = len(by_case_id)
            passed = sum(1 for v in by_case_id.values() if any(v))

            category_stats[cat] = CategoryStats(
                category=cat,
                total=total,
                passed=passed,
                pass_at_k_value=(
                    sum(case_pass_rates) / len(case_pass_rates)
                    if case_pass_rates
                    else 0.0
                ),
                pass_hat_k_value=(
                    sum(case_pass_hat_rates) / len(case_pass_hat_rates)
                    if case_pass_hat_rates
                    else 0.0
                ),
            )

        # 计算总体
        by_case_all: Dict[str, List[bool]] = {}
        for r in all_results:
            by_case_all.setdefault(r.test_id, []).append(r.passed)
        total_passed = sum(1 for v in by_case_all.values() if any(v))

        return EvaluationReport(
            dataset_name=dataset_name,
            total_cases=len(test_cases),
            total_passed=total_passed,
            k=self.k,
            category_stats=category_stats,
            results=all_results,
        )

    async def run_negative_dataset(
        self,
        test_cases: List[NegativeTestCase],
        dataset_name: str = "negative",
    ) -> NegativeReport:
        """执行负面测试数据集

        Args:
            test_cases: 负面测试用例列表
            dataset_name: 数据集名称

        Returns:
            NegativeReport
        """
        all_results: List[NegativeEvalResult] = []

        for tc in test_cases:
            case_results = await self.run_negative_case(tc)
            all_results.extend(case_results)

        total_violations = sum(1 for r in all_results if r.violated)

        return NegativeReport(
            dataset_name=dataset_name,
            total_cases=len(test_cases),
            total_violations=total_violations,
            results=all_results,
        )
