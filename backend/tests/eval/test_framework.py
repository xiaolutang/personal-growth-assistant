"""Golden Dataset 框架单元测试

验证框架核心组件：
- 数据加载
- 指标计算 (pass@k, pass^k)
- 判定逻辑
- 执行器环境隔离
- 报告生成
"""

import asyncio
import json
from pathlib import Path

import pytest

from tests.eval.framework import (
    CategoryStats,
    DatasetLoader,
    EvaluationReport,
    EvaluationResult,
    GoldenDatasetRunner,
    NegativeEvalResult,
    NegativeReport,
    NegativeTestCase,
    ReferenceSolution,
    TestCase,
    judge_negative_case,
    judge_test_case,
    pass_at_k,
    pass_hat_k,
)

DATASETS_DIR = Path(__file__).parent / "datasets"


# ── 数据加载测试 ──


class TestDatasetLoader:
    """测试数据集加载器"""

    def test_load_single_turn_has_68_cases(self):
        cases = DatasetLoader.load_single_turn()
        assert len(cases) == 68

    def test_load_negative_has_24_cases(self):
        cases = DatasetLoader.load_negative()
        assert len(cases) == 24

    def test_single_turn_categories(self):
        cases = DatasetLoader.load_single_turn()
        from collections import Counter

        cats = Counter(c.category for c in cases)
        assert cats["tool_selection"] == 15
        assert cats["param_extraction"] == 12
        assert cats["multi_step"] == 10
        assert cats["ask_user"] == 8
        assert cats["pure_chat"] == 10
        assert cats["boundary"] == 8
        assert cats["directness"] == 5

    def test_negative_categories(self):
        cases = DatasetLoader.load_negative()
        from collections import Counter

        cats = Counter(c.category for c in cases)
        assert cats["no_tool"] == 10
        assert cats["no_ask"] == 8
        assert cats["no_multi_step"] == 6

    def test_test_case_from_dict(self):
        data = {
            "id": "TEST-001",
            "category": "tool_selection",
            "user_input": "test input",
            "expected_tools": ["create_entry"],
            "expected_args": {"category": "inbox"},
            "reference_solution": {
                "tool": "create_entry",
                "args": {"category": "inbox"},
            },
            "acceptable_alternatives": [],
            "unacceptable": ["delete_entry"],
        }
        tc = TestCase.from_dict(data)
        assert tc.id == "TEST-001"
        assert tc.category == "tool_selection"
        assert tc.user_input == "test input"
        assert tc.expected_tools == ["create_entry"]
        assert tc.reference_solution.tool == "create_entry"
        assert tc.unacceptable == ["delete_entry"]

    def test_negative_test_case_from_dict(self):
        data = {
            "id": "NEG-TEST-001",
            "category": "no_tool",
            "user_input": "hello",
            "should_not_call": ["create_entry"],
            "reason": "test reason",
        }
        tc = NegativeTestCase.from_dict(data)
        assert tc.id == "NEG-TEST-001"
        assert tc.should_not_call == ["create_entry"]
        assert tc.reason == "test reason"

    def test_all_single_turn_have_reference_solution(self):
        cases = DatasetLoader.load_single_turn()
        for tc in cases:
            assert isinstance(tc.reference_solution, ReferenceSolution), (
                f"{tc.id}: missing reference_solution"
            )

    def test_all_cases_have_unique_ids(self):
        cases = DatasetLoader.load_single_turn()
        ids = [c.id for c in cases]
        assert len(ids) == len(set(ids)), "Duplicate IDs found in single_turn_68"

        neg_cases = DatasetLoader.load_negative()
        neg_ids = [c.id for c in neg_cases]
        assert len(neg_ids) == len(set(neg_ids)), "Duplicate IDs found in negative_24"

    def test_load_from_absolute_path(self):
        path = DATASETS_DIR / "single_turn_68.json"
        cases = DatasetLoader.load_test_cases(path)
        assert len(cases) == 68

    def test_load_from_relative_path(self):
        cases = DatasetLoader.load_test_cases("single_turn_68.json")
        assert len(cases) == 68


# ── 指标计算测试 ──


class TestMetrics:
    """测试 pass@k 和 pass^k 指标计算"""

    def test_pass_at_k_all_pass(self):
        assert pass_at_k([True, True, True], k=3) == 1.0

    def test_pass_at_k_all_fail(self):
        assert pass_at_k([False, False, False], k=3) == 0.0

    def test_pass_at_k_one_pass(self):
        result = pass_at_k([True, False, False], k=3)
        assert result == 1.0  # 至少有一个 True，3次采样必然命中

    def test_pass_at_k_empty(self):
        assert pass_at_k([], k=3) == 0.0

    def test_pass_at_k_fewer_than_k(self):
        # n < k: 只要有一次通过就返回 1.0
        assert pass_at_k([True], k=3) == 1.0
        assert pass_at_k([False], k=3) == 0.0

    def test_pass_at_k_large_n(self):
        # 10 次中 7 次通过
        results = [True] * 7 + [False] * 3
        result = pass_at_k(results, k=3)
        assert 0.0 < result <= 1.0
        # 应该很高
        assert result > 0.9

    def test_pass_at_k_5_trials_1_pass(self):
        # 5 次中 1 次通过
        results = [True, False, False, False, False]
        result = pass_at_k(results, k=3)
        # 1 - C(4,3)/C(5,3) = 1 - 4/10 = 0.6
        assert abs(result - 0.6) < 0.01

    def test_pass_hat_k_all_pass(self):
        assert pass_hat_k([True, True, True], k=3) == 1.0

    def test_pass_hat_k_all_fail(self):
        assert pass_hat_k([False, False, False], k=3) == 0.0

    def test_pass_hat_k_one_pass(self):
        # best-of-k: 只要有一次通过就返回 1.0
        assert pass_hat_k([True, False, False], k=3) == 1.0

    def test_pass_hat_k_empty(self):
        assert pass_hat_k([], k=3) == 0.0


# ── 判定逻辑测试 ──


class TestJudge:
    """测试用例判定逻辑"""

    def test_judge_tool_selection_pass(self):
        tc = TestCase(
            id="TEST",
            category="tool_selection",
            user_input="test",
            expected_tools=["create_entry"],
            reference_solution=ReferenceSolution(tool="create_entry"),
        )
        assert judge_test_case(tc, ["create_entry"], [{}]) is True

    def test_judge_tool_selection_fail_unacceptable(self):
        tc = TestCase(
            id="TEST",
            category="tool_selection",
            user_input="test",
            expected_tools=["create_entry"],
            reference_solution=ReferenceSolution(tool="create_entry"),
            unacceptable=["delete_entry"],
        )
        assert judge_test_case(tc, ["delete_entry"], [{}]) is False

    def test_judge_tool_selection_fail_no_tool(self):
        tc = TestCase(
            id="TEST",
            category="tool_selection",
            user_input="test",
            expected_tools=["create_entry"],
            reference_solution=ReferenceSolution(tool="create_entry"),
        )
        assert judge_test_case(tc, [], []) is False

    def test_judge_pure_chat_pass(self):
        tc = TestCase(
            id="TEST",
            category="pure_chat",
            user_input="hello",
            expected_tools=[],
            reference_solution=ReferenceSolution(tool=""),
            unacceptable=["create_entry"],
        )
        # 纯对话：没有调用 tool → 通过
        assert judge_test_case(tc, [], []) is True

    def test_judge_pure_chat_fail_called_tool(self):
        tc = TestCase(
            id="TEST",
            category="pure_chat",
            user_input="hello",
            expected_tools=[],
            reference_solution=ReferenceSolution(tool=""),
            unacceptable=["create_entry"],
        )
        assert judge_test_case(tc, ["create_entry"], [{}]) is False

    def test_judge_acceptable_alternative(self):
        tc = TestCase(
            id="TEST",
            category="tool_selection",
            user_input="test",
            expected_tools=["search_entries"],
            reference_solution=ReferenceSolution(tool="search_entries"),
            acceptable_alternatives=["get_entry"],
        )
        assert judge_test_case(tc, ["get_entry"], [{}]) is True

    def test_judge_negative_case_violated(self):
        tc = NegativeTestCase(
            id="NEG-TEST",
            category="no_tool",
            user_input="hello",
            should_not_call=["create_entry", "delete_entry"],
        )
        violated, violated_tools = judge_negative_case(tc, ["create_entry"])
        assert violated is True
        assert "create_entry" in violated_tools

    def test_judge_negative_case_not_violated(self):
        tc = NegativeTestCase(
            id="NEG-TEST",
            category="no_tool",
            user_input="hello",
            should_not_call=["create_entry"],
        )
        violated, violated_tools = judge_negative_case(tc, [])
        assert violated is False
        assert violated_tools == []


# ── 执行器测试 ──


class TestRunner:
    """测试执行器和环境隔离"""

    @pytest.fixture
    def mock_invoke_fn(self):
        """Mock Agent 调用函数"""

        async def _invoke(user_input: str, thread_id: str) -> dict:
            # 简单 mock：根据输入返回固定的 tool 调用
            if "记录" in user_input or "创建" in user_input:
                return {"tools": ["create_entry"], "args": [{"category": "inbox"}]}
            elif "搜索" in user_input or "找" in user_input:
                return {"tools": ["search_entries"], "args": [{"query": "test"}]}
            elif "删除" in user_input:
                return {"tools": ["delete_entry"], "args": [{"entry_id": "test"}]}
            else:
                return {"tools": [], "args": []}

        return _invoke

    @pytest.mark.asyncio
    async def test_runner_single_case(self, mock_invoke_fn):
        runner = GoldenDatasetRunner(invoke_fn=mock_invoke_fn, k=3, num_trials=2)
        tc = TestCase(
            id="TEST-001",
            category="tool_selection",
            user_input="记录一个想法",
            expected_tools=["create_entry"],
            reference_solution=ReferenceSolution(tool="create_entry"),
        )
        results = await runner.run_single_case(tc)
        assert len(results) == 2
        assert all(r.test_id == "TEST-001" for r in results)
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_runner_environment_isolation(self, mock_invoke_fn):
        """每次 trial 使用独立 thread_id"""
        runner = GoldenDatasetRunner(invoke_fn=mock_invoke_fn, k=3, num_trials=3)
        tc = TestCase(
            id="TEST-ISO",
            category="tool_selection",
            user_input="记录",
            expected_tools=["create_entry"],
            reference_solution=ReferenceSolution(tool="create_entry"),
        )
        results = await runner.run_single_case(tc)
        thread_ids = [r.thread_id for r in results]
        # 所有 thread_id 都是独立的
        assert len(set(thread_ids)) == 3
        # thread_id 格式正确
        for tid in thread_ids:
            assert tid.startswith("eval-")

    @pytest.mark.asyncio
    async def test_runner_dataset(self, mock_invoke_fn):
        runner = GoldenDatasetRunner(invoke_fn=mock_invoke_fn, k=3, num_trials=1)
        cases = [
            TestCase(
                id="T1",
                category="tool_selection",
                user_input="记录想法",
                expected_tools=["create_entry"],
                reference_solution=ReferenceSolution(tool="create_entry"),
            ),
            TestCase(
                id="T2",
                category="pure_chat",
                user_input="你好",
                expected_tools=[],
                reference_solution=ReferenceSolution(tool=""),
                unacceptable=["create_entry"],
            ),
        ]
        report = await runner.run_dataset(cases, dataset_name="test")
        assert report.total_cases == 2
        assert report.dataset_name == "test"
        assert report.k == 3
        assert len(report.results) == 2

    @pytest.mark.asyncio
    async def test_runner_no_invoke_fn(self):
        """无 invoke_fn 时返回空结果"""
        runner = GoldenDatasetRunner(k=3, num_trials=1)
        tc = TestCase(
            id="TEST-NOOP",
            category="pure_chat",
            user_input="hello",
            expected_tools=[],
            reference_solution=ReferenceSolution(tool=""),
        )
        results = await runner.run_single_case(tc)
        assert len(results) == 1
        assert results[0].actual_tools == []

    @pytest.mark.asyncio
    async def test_runner_negative_case(self, mock_invoke_fn):
        runner = GoldenDatasetRunner(invoke_fn=mock_invoke_fn, k=3, num_trials=1)
        tc = NegativeTestCase(
            id="NEG-TEST",
            category="no_tool",
            user_input="你好",
            should_not_call=["create_entry", "delete_entry"],
        )
        results = await runner.run_negative_case(tc)
        assert len(results) == 1
        # "你好" 不匹配 mock 中的任何关键词，返回空 tools
        assert results[0].violated is False

    @pytest.mark.asyncio
    async def test_runner_negative_violated(self, mock_invoke_fn):
        runner = GoldenDatasetRunner(invoke_fn=mock_invoke_fn, k=3, num_trials=1)
        tc = NegativeTestCase(
            id="NEG-VIOLATE",
            category="no_tool",
            user_input="记录一下今天的想法",
            should_not_call=["create_entry"],
        )
        results = await runner.run_negative_case(tc)
        assert len(results) == 1
        # mock 会对 "记录" 返回 create_entry，违反约束
        assert results[0].violated is True

    @pytest.mark.asyncio
    async def test_runner_negative_dataset(self, mock_invoke_fn):
        runner = GoldenDatasetRunner(invoke_fn=mock_invoke_fn, k=3, num_trials=1)
        cases = [
            NegativeTestCase(
                id="NEG-001",
                category="no_tool",
                user_input="你好",
                should_not_call=["create_entry"],
            ),
            NegativeTestCase(
                id="NEG-002",
                category="no_ask",
                user_input="记录想法学习 Docker",
                should_not_call=["ask_user"],
            ),
        ]
        report = await runner.run_negative_dataset(cases, dataset_name="test_neg")
        assert report.total_cases == 2
        assert report.dataset_name == "test_neg"


# ── 报告测试 ──


class TestReport:
    """测试报告生成"""

    def test_evaluation_report_text(self):
        report = EvaluationReport(
            dataset_name="test",
            total_cases=10,
            total_passed=8,
            k=3,
            category_stats={
                "tool_selection": CategoryStats(
                    category="tool_selection",
                    total=5,
                    passed=4,
                    pass_at_k_value=0.8,
                    pass_hat_k_value=0.9,
                ),
            },
        )
        text = report.to_text()
        assert "test" in text
        assert "10" in text
        assert "tool_selection" in text

    def test_negative_report_text(self):
        report = NegativeReport(
            dataset_name="test_neg",
            total_cases=5,
            total_violations=1,
            results=[
                NegativeEvalResult(
                    test_id="NEG-001",
                    violated=False,
                ),
                NegativeEvalResult(
                    test_id="NEG-002",
                    violated=True,
                    violated_tools=["create_entry"],
                ),
            ],
        )
        text = report.to_text()
        assert "test_neg" in text
        assert "5" in text

    def test_category_stats_pass_rate(self):
        stats = CategoryStats(category="test", total=10, passed=8)
        assert abs(stats.pass_rate - 0.8) < 0.001

    def test_category_stats_zero_total(self):
        stats = CategoryStats(category="test", total=0, passed=0)
        assert stats.pass_rate == 0.0

    def test_evaluation_report_overall_pass_rate(self):
        report = EvaluationReport(
            dataset_name="test",
            total_cases=10,
            total_passed=8,
        )
        assert abs(report.overall_pass_rate - 0.8) < 0.001


# ── 数据完整性测试 ──


class TestDataIntegrity:
    """测试数据文件完整性"""

    def test_single_turn_json_valid(self):
        path = DATASETS_DIR / "single_turn_68.json"
        with open(path, "r") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 68

    def test_negative_json_valid(self):
        path = DATASETS_DIR / "negative_24.json"
        with open(path, "r") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 24

    def test_single_turn_required_fields(self):
        cases = DatasetLoader.load_single_turn()
        required_fields = [
            "id",
            "category",
            "user_input",
            "expected_tools",
            "reference_solution",
            "acceptable_alternatives",
            "unacceptable",
        ]
        path = DATASETS_DIR / "single_turn_68.json"
        with open(path, "r") as f:
            raw_data = json.load(f)
        for item in raw_data:
            for field in required_fields:
                assert field in item, f"{item.get('id', 'unknown')}: missing {field}"

    def test_negative_required_fields(self):
        required_fields = [
            "id",
            "category",
            "user_input",
            "should_not_call",
            "reason",
        ]
        path = DATASETS_DIR / "negative_24.json"
        with open(path, "r") as f:
            raw_data = json.load(f)
        for item in raw_data:
            for field in required_fields:
                assert field in item, f"{item.get('id', 'unknown')}: missing {field}"

    def test_all_tool_names_valid(self):
        """验证所有 expected_tools 中的 tool 名称都是有效的"""
        valid_tools = {
            "create_entry",
            "update_entry",
            "delete_entry",
            "search_entries",
            "get_entry",
            "get_review_summary",
            "ask_user",
        }
        cases = DatasetLoader.load_single_turn()
        for tc in cases:
            for tool in tc.expected_tools:
                assert tool in valid_tools, f"{tc.id}: invalid tool '{tool}'"
            if tc.reference_solution.tool:
                assert tc.reference_solution.tool in valid_tools or tc.reference_solution.tool == "", (
                    f"{tc.id}: invalid reference tool '{tc.reference_solution.tool}'"
                )
            for tool in tc.acceptable_alternatives:
                assert tool in valid_tools, f"{tc.id}: invalid alternative '{tool}'"
            for tool in tc.unacceptable:
                assert tool in valid_tools, f"{tc.id}: invalid unacceptable '{tool}'"
