"""LLM-as-Judge + 多轮评估单元测试

测试覆盖:
- JudgeDimension 枚举完整性
- JudgeScore / JudgeResult 数据结构
- LLMJudge 评分逻辑（mock LLM）
- PartialScorer 梯度计算
- OutcomeGrader 状态验证
- 多轮数据集加载验证（30 条，4 类分布）
- SimulatedUser 两种模式（PresetReplyUser + LLMSimulatedUser）
- MultiTurnRunner 多轮编排
"""

import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.eval.judge import (
    DEFAULT_DIMENSION_WEIGHTS,
    DEFAULT_PARTIAL_THRESHOLDS,
    JudgeDimension,
    JudgeResult,
    JudgeScore,
    LLMJudge,
    OutcomeGrade,
    OutcomeGrader,
    PartialScoreThreshold,
    PartialScorer,
    StateCheck,
)
from tests.eval.simulated_user import (
    ConversationTurn,
    LLMSimulatedUser,
    MultiTurnResult,
    MultiTurnRunner,
    MultiTurnTestCase,
    PresetReplyUser,
    SimulatedUser,
    load_multi_turn_dataset,
)

DATASETS_DIR = Path(__file__).parent / "datasets"


# ── JudgeDimension 枚举测试 ──


class TestJudgeDimension:
    """测试评分维度枚举"""

    def test_total_dimensions(self):
        assert len(JudgeDimension) == 10

    def test_base_dimensions(self):
        base = JudgeDimension.base_dimensions()
        assert len(base) == 7
        assert JudgeDimension.TOOL_SELECTION in base
        assert JudgeDimension.PARAM_EXTRACTION in base
        assert JudgeDimension.RESPONSE_QUALITY in base
        assert JudgeDimension.ERROR_HANDLING in base
        assert JudgeDimension.EFFICIENCY in base
        assert JudgeDimension.USER_EXPERIENCE in base
        assert JudgeDimension.DIRECTNESS in base

    def test_multi_turn_dimensions(self):
        mt = JudgeDimension.multi_turn_dimensions()
        assert len(mt) == 3
        assert JudgeDimension.CONTEXT_RETENTION in mt
        assert JudgeDimension.FOLLOW_UP_QUALITY in mt
        assert JudgeDimension.CONVERSATION_COHERENCE in mt

    def test_all_dimensions(self):
        all_dims = JudgeDimension.all_dimensions()
        assert len(all_dims) == 10
        # 基础在前，多轮在后
        assert all_dims[:7] == JudgeDimension.base_dimensions()
        assert all_dims[7:] == JudgeDimension.multi_turn_dimensions()

    def test_dimension_values(self):
        expected_values = [
            "tool_selection",
            "param_extraction",
            "response_quality",
            "error_handling",
            "efficiency",
            "user_experience",
            "directness",
            "context_retention",
            "follow_up_quality",
            "conversation_coherence",
        ]
        actual_values = [d.value for d in JudgeDimension]
        assert sorted(actual_values) == sorted(expected_values)

    def test_no_overlap(self):
        all_list = JudgeDimension.all_dimensions()
        assert len(set(all_list)) == 10


# ── JudgeScore 数据结构测试 ──


class TestJudgeScore:
    """测试单维度评分"""

    def test_valid_score(self):
        score = JudgeScore(
            dimension=JudgeDimension.TOOL_SELECTION,
            score=5,
            reasoning="完美的工具选择",
        )
        assert score.score == 5
        assert score.reasoning == "完美的工具选择"

    def test_min_score(self):
        score = JudgeScore(dimension=JudgeDimension.EFFICIENCY, score=1)
        assert score.score == 1

    def test_max_score(self):
        score = JudgeScore(dimension=JudgeDimension.EFFICIENCY, score=5)
        assert score.score == 5

    def test_invalid_score_too_high(self):
        with pytest.raises(ValueError):
            JudgeScore(dimension=JudgeDimension.EFFICIENCY, score=6)

    def test_invalid_score_too_low(self):
        with pytest.raises(ValueError):
            JudgeScore(dimension=JudgeDimension.EFFICIENCY, score=0)

    def test_invalid_score_negative(self):
        with pytest.raises(ValueError):
            JudgeScore(dimension=JudgeDimension.EFFICIENCY, score=-1)


# ── JudgeResult 数据结构测试 ──


class TestJudgeResult:
    """测试完整评分结果"""

    def _make_result(self, score_value: int = 4) -> JudgeResult:
        scores = {}
        for dim in JudgeDimension.all_dimensions():
            scores[dim.value] = JudgeScore(
                dimension=dim, score=score_value, reasoning=f"{dim.value} 评分"
            )
        return JudgeResult(scores=scores, test_id="TEST-001")

    def test_total_score(self):
        result = self._make_result(4)
        assert result.total_score == 10 * 4  # 40

    def test_max_possible_score(self):
        result = self._make_result(5)
        assert result.max_possible_score == 50

    def test_average_score(self):
        result = self._make_result(4)
        assert abs(result.average_score - 4.0) < 0.001

    def test_weighted_average(self):
        result = self._make_result(3)
        # 所有维度都是 3 分，加权平均也应该接近 3
        assert abs(result.weighted_average - 3.0) < 0.001

    def test_percentage(self):
        result = self._make_result(4)
        expected_pct = (40 / 50) * 100
        assert abs(result.percentage - expected_pct) < 0.1

    def test_percentage_full(self):
        result = self._make_result(5)
        assert abs(result.percentage - 100.0) < 0.001

    def test_percentage_zero(self):
        result = self._make_result(1)
        expected_pct = (10 / 50) * 100
        assert abs(result.percentage - expected_pct) < 0.1

    def test_get_score(self):
        result = self._make_result(4)
        score = result.get_score(JudgeDimension.TOOL_SELECTION)
        assert score is not None
        assert score.score == 4

    def test_get_score_missing(self):
        result = JudgeResult(scores={}, test_id="TEST")
        score = result.get_score(JudgeDimension.TOOL_SELECTION)
        assert score is None

    def test_empty_result(self):
        result = JudgeResult()
        assert result.total_score == 0
        assert result.max_possible_score == 50  # 默认 9 维度 * 5 分
        assert result.average_score == 0.0
        assert result.weighted_average == 0.0
        assert result.percentage == 0.0  # 0 / 45 = 0%

    def test_to_dict(self):
        result = self._make_result(3)
        d = result.to_dict()
        assert d["test_id"] == "TEST-001"
        assert d["total_score"] == 30
        assert "dimension_scores" in d
        assert len(d["dimension_scores"]) == 10


# ── LLMJudge 评分逻辑测试 ──


class TestLLMJudge:
    """测试 LLM-as-Judge 执行器"""

    def _make_mock_response(self, score: int = 5) -> str:
        """构建 mock LLM 回复"""
        scores = {}
        for dim in JudgeDimension.all_dimensions():
            scores[dim.value] = {
                "score": score,
                "reasoning": f"Mock: {dim.value} 得分 {score}",
            }
        return json.dumps({"dimension_scores": scores})

    @pytest.mark.asyncio
    async def test_evaluate_with_mock(self):
        mock_response = self._make_mock_response(5)
        judge = LLMJudge(inject_llm_response=mock_response)
        result = await judge.evaluate(
            user_input="帮我记录一个想法",
            agent_response="好的，你想记录什么想法？",
            tool_calls=[{"tool": "ask_user", "args": {"prompt": "什么想法"}}],
            test_id="TEST-MOCK",
        )
        assert result.test_id == "TEST-MOCK"
        assert result.total_score == 50
        assert len(result.scores) == 10

    @pytest.mark.asyncio
    async def test_evaluate_with_partial_scores(self):
        mock_response = self._make_mock_response(3)
        judge = LLMJudge(inject_llm_response=mock_response)
        result = await judge.evaluate(
            user_input="搜索笔记",
            agent_response="好的，搜索中...",
            tool_calls=[{"tool": "search_entries"}],
        )
        assert result.total_score == 30  # 10 * 3
        assert abs(result.percentage - 60.0) < 0.1

    @pytest.mark.asyncio
    async def test_evaluate_no_injection(self):
        """无注入时返回默认中间分"""
        judge = LLMJudge()
        result = await judge.evaluate(
            user_input="test",
            agent_response="response",
            tool_calls=[],
        )
        assert result.total_score == 30  # 10 * 3（默认分）

    @pytest.mark.asyncio
    async def test_evaluate_custom_dimensions(self):
        """只评估部分维度"""
        mock_response = self._make_mock_response(4)
        judge = LLMJudge(
            inject_llm_response=mock_response,
            dimensions=JudgeDimension.base_dimensions(),
        )
        result = await judge.evaluate(
            user_input="test",
            agent_response="response",
            tool_calls=[],
        )
        assert len(result.scores) == 7

    @pytest.mark.asyncio
    async def test_parse_markdown_wrapped_json(self):
        """测试解析 markdown 代码块包裹的 JSON"""
        mock_with_md = """```json
{"dimension_scores": {"tool_selection": {"score": 4, "reasoning": "test"}}}
```"""
        judge = LLMJudge(inject_llm_response=mock_with_md)
        result = await judge.evaluate(
            user_input="test",
            agent_response="response",
            tool_calls=[],
        )
        # 应该能解析出 markdown 包裹的 JSON
        assert JudgeDimension.TOOL_SELECTION.value in result.scores

    @pytest.mark.asyncio
    async def test_parse_malformed_json(self):
        """测试解析格式错误的 JSON"""
        judge = LLMJudge(inject_llm_response="not json at all")
        result = await judge.evaluate(
            user_input="test",
            agent_response="response",
            tool_calls=[],
        )
        # 解析失败时所有维度使用默认分 3
        for score in result.scores.values():
            assert score.score == 3

    @pytest.mark.asyncio
    async def test_evaluate_multi_turn(self):
        mock_response = self._make_mock_response(4)
        judge = LLMJudge(inject_llm_response=mock_response)

        turns = [
            {"role": "user", "content": "帮我记录想法"},
            {"role": "agent", "content": "什么想法？", "tool_calls": [{"tool": "ask_user"}]},
            {"role": "user", "content": "关于 AI Agent 的想法"},
            {"role": "agent", "content": "已记录", "tool_calls": [{"tool": "create_entry"}]},
        ]

        result = await judge.evaluate_multi_turn(turns, test_id="MT-TEST")
        assert result.test_id == "MT-TEST"
        assert len(result.scores) == 10
        judge = LLMJudge()
        prompt = judge._build_prompt(
            user_input="帮我搜索",
            agent_response="搜索结果如下",
            tool_calls=[{"tool": "search_entries"}],
        )
        assert "帮我搜索" in prompt
        assert "搜索结果如下" in prompt
        assert "search_entries" in prompt
        assert "tool_selection" in prompt

    def test_build_prompt_with_history(self):
        judge = LLMJudge()
        history = [
            {"role": "user", "content": "你好"},
            {"role": "agent", "content": "你好！"},
        ]
        prompt = judge._build_prompt(
            user_input="帮我搜索",
            agent_response="好的",
            tool_calls=[],
            conversation_history=history,
        )
        assert "对话历史" in prompt
        assert "你好" in prompt


# ── PartialScorer 测试 ──


class TestPartialScorer:
    """测试部分评分器"""

    def _make_result(self, avg_score: int) -> JudgeResult:
        scores = {}
        for dim in JudgeDimension.all_dimensions():
            scores[dim.value] = JudgeScore(
                dimension=dim, score=avg_score, reasoning=""
            )
        return JudgeResult(scores=scores, test_id="TEST")

    def test_score_perfect(self):
        scorer = PartialScorer()
        result = self._make_result(5)
        score = scorer.score(result)
        assert score["label"] == "完美"
        assert score["score"] == 5.0
        assert abs(score["percentage"] - 100.0) < 0.1

    def test_score_good(self):
        scorer = PartialScorer()
        result = self._make_result(4)
        score = scorer.score(result)
        assert score["percentage"] >= 60.0
        assert score["score"] >= 3.0

    def test_score_failing(self):
        scorer = PartialScorer()
        result = self._make_result(2)
        score = scorer.score(result)
        assert score["percentage"] < 60.0

    def test_score_60_percent(self):
        """60% 阈值测试"""
        scorer = PartialScorer()
        # 10 维度，每维度 3 分 = 30/50 = 60%
        result = self._make_result(3)
        score = scorer.score(result)
        assert abs(score["percentage"] - 60.0) < 0.1
        assert score["label"] == "基本及格"
        assert score["score"] == 3.0

    def test_score_70_percent_approx(self):
        """约 70% 阈值测试"""
        scorer = PartialScorer()
        # 手动构建一个约 70% 的结果
        scores = {}
        dims = JudgeDimension.all_dimensions()
        for i, dim in enumerate(dims):
            # 前 7 个维度 4 分，后 3 个维度 2 分
            s = 4 if i < 7 else 2
            scores[dim.value] = JudgeScore(dimension=dim, score=s, reasoning="")
        result = JudgeResult(scores=scores, test_id="TEST")
        score = scorer.score(result)
        # 总分 = 7*4 + 3*2 = 34, 34/50 = 68%
        assert 60.0 <= score["percentage"] <= 70.0

    def test_grade(self):
        scorer = PartialScorer()
        result = self._make_result(5)
        assert scorer.grade(result) == "完美"

    def test_batch_score(self):
        scorer = PartialScorer()
        results = [self._make_result(3), self._make_result(5)]
        scores = scorer.batch_score(results)
        assert len(scores) == 2

    def test_statistics(self):
        scorer = PartialScorer()
        results = [self._make_result(3), self._make_result(5)]
        stats = scorer.statistics(results)
        assert stats["total"] == 2
        assert "average_percentage" in stats
        assert "grade_distribution" in stats

    def test_statistics_empty(self):
        scorer = PartialScorer()
        stats = scorer.statistics([])
        assert stats["total"] == 0
        assert stats["average_percentage"] == 0.0

    def test_custom_thresholds(self):
        thresholds = [
            PartialScoreThreshold(threshold=0.0, label="F", score=0.0),
            PartialScoreThreshold(threshold=50.0, label="D", score=1.0),
            PartialScoreThreshold(threshold=70.0, label="C", score=2.0),
            PartialScoreThreshold(threshold=85.0, label="B", score=3.0),
            PartialScoreThreshold(threshold=95.0, label="A", score=5.0),
        ]
        scorer = PartialScorer(thresholds=thresholds)
        result = self._make_result(3)  # 60%
        score = scorer.score(result)
        assert score["label"] == "D"

    def test_default_thresholds_order(self):
        """验证默认阈值按递增排列"""
        for i in range(len(DEFAULT_PARTIAL_THRESHOLDS) - 1):
            assert DEFAULT_PARTIAL_THRESHOLDS[i].threshold <= DEFAULT_PARTIAL_THRESHOLDS[i + 1].threshold

    def test_weighted_average_weights_sum(self):
        """验证权重总和接近 1.0"""
        total = sum(DEFAULT_DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01


# ── OutcomeGrader 测试 ──


class TestOutcomeGrader:
    """测试状态验证 grader"""

    def test_pass_all_checks(self):
        grader = OutcomeGrader()
        state_check = StateCheck(
            tool="create_entry",
            args_contain=["LangGraph"],
            args_exact={"category": "inbox"},
        )
        actual_calls = [
            {"tool": "create_entry", "args": {"category": "inbox", "content": "LangGraph 学习"}},
        ]
        grade = grader.grade(state_check, actual_calls)
        assert grade.passed is True
        assert grade.tool_matched is True
        assert grade.args_contained is True
        assert grade.args_exact_matched is True
        assert grade.no_violations is True

    def test_fail_wrong_tool(self):
        grader = OutcomeGrader()
        state_check = StateCheck(tool="create_entry")
        actual_calls = [{"tool": "delete_entry", "args": {}}]
        grade = grader.grade(state_check, actual_calls)
        assert grade.passed is False
        assert grade.tool_matched is False

    def test_fail_missing_args_contain(self):
        grader = OutcomeGrader()
        state_check = StateCheck(
            tool="create_entry",
            args_contain=["Python"],
        )
        actual_calls = [
            {"tool": "create_entry", "args": {"content": "学习 JavaScript"}},
        ]
        grade = grader.grade(state_check, actual_calls)
        assert grade.passed is False
        assert grade.args_contained is False

    def test_fail_args_exact_mismatch(self):
        grader = OutcomeGrader()
        state_check = StateCheck(
            tool="update_entry",
            args_exact={"status": "done"},
        )
        actual_calls = [
            {"tool": "update_entry", "args": {"status": "in_progress"}},
        ]
        grade = grader.grade(state_check, actual_calls)
        assert grade.passed is False
        assert grade.args_exact_matched is False

    def test_fail_violated_should_not_call(self):
        grader = OutcomeGrader()
        state_check = StateCheck(
            tool="search_entries",
            should_not_call=["delete_entry"],
        )
        actual_calls = [
            {"tool": "search_entries", "args": {"query": "test"}},
            {"tool": "delete_entry", "args": {"entry_id": "123"}},
        ]
        grade = grader.grade(state_check, actual_calls)
        assert grade.passed is False
        assert grade.no_violations is False

    def test_no_tool_requirement(self):
        grader = OutcomeGrader()
        state_check = StateCheck()  # 无工具要求
        actual_calls = [{"tool": "create_entry", "args": {}}]
        grade = grader.grade(state_check, actual_calls)
        assert grade.passed is True
        assert grade.tool_matched is True

    def test_empty_calls(self):
        grader = OutcomeGrader()
        state_check = StateCheck(tool="create_entry")
        grade = grader.grade(state_check, [])
        assert grade.passed is False
        assert grade.tool_matched is False

    def test_grade_from_dict(self):
        grader = OutcomeGrader()
        state_dict = {
            "tool": "create_entry",
            "args_contain": ["test"],
            "args_exact": {"category": "inbox"},
            "should_not_call": ["delete_entry"],
        }
        actual_calls = [
            {"tool": "create_entry", "args": {"category": "inbox", "content": "test content"}},
        ]
        grade = grader.grade_from_dict(state_dict, actual_calls)
        assert grade.passed is True

    def test_multiple_args_contain(self):
        grader = OutcomeGrader()
        state_check = StateCheck(
            tool="create_entry",
            args_contain=["LangGraph", "ReAct"],
        )
        actual_calls = [
            {"tool": "create_entry", "args": {"content": "学习 LangGraph 的 ReAct 模式"}},
        ]
        grade = grader.grade(state_check, actual_calls)
        assert grade.args_contained is True

    def test_details_message(self):
        grader = OutcomeGrader()
        state_check = StateCheck(tool="create_entry")
        grade = grader.grade(state_check, [])
        assert "create_entry" in grade.details


# ── StateCheck 数据结构测试 ──


class TestStateCheck:
    """测试 StateCheck 数据类"""

    def test_from_dict(self):
        data = {
            "tool": "create_entry",
            "args_contain": ["test"],
            "args_exact": {"category": "inbox"},
            "should_not_call": ["delete_entry"],
        }
        sc = StateCheck.from_dict(data)
        assert sc.tool == "create_entry"
        assert sc.args_contain == ["test"]
        assert sc.args_exact == {"category": "inbox"}
        assert sc.should_not_call == ["delete_entry"]

    def test_from_dict_defaults(self):
        sc = StateCheck.from_dict({})
        assert sc.tool == ""
        assert sc.args_contain == []
        assert sc.args_exact == {}
        assert sc.should_not_call == []


# ── 多轮数据集加载测试 ──


class TestMultiTurnDataset:
    """测试多轮数据集加载"""

    def test_load_has_30_cases(self):
        cases = load_multi_turn_dataset()
        assert len(cases) == 30

    def test_categories_distribution(self):
        cases = load_multi_turn_dataset()
        cats = Counter(c.category for c in cases)
        assert cats["follow_up_to_action"] == 10
        assert cats["context_reference"] == 8
        assert cats["interleaved_chat"] == 6
        assert cats["error_recovery"] == 6

    def test_all_ids_unique(self):
        cases = load_multi_turn_dataset()
        ids = [c.id for c in cases]
        assert len(ids) == len(set(ids)), "Duplicate IDs found"

    def test_all_ids_mt_prefix(self):
        cases = load_multi_turn_dataset()
        for c in cases:
            assert c.id.startswith("MT-"), f"{c.id}: should start with MT-"

    def test_all_have_turns(self):
        cases = load_multi_turn_dataset()
        for c in cases:
            assert len(c.turns) >= 2, f"{c.id}: should have at least 2 turns"
            user_turns = c.user_turns
            assert len(user_turns) >= 1, f"{c.id}: should have at least 1 user turn"

    def test_all_have_final_state_check(self):
        cases = load_multi_turn_dataset()
        for c in cases:
            assert "tool" in c.final_state_check, (
                f"{c.id}: missing 'tool' in final_state_check"
            )

    def test_all_have_reference_scores(self):
        cases = load_multi_turn_dataset()
        for c in cases:
            assert len(c.reference_scores) > 0, (
                f"{c.id}: should have reference_scores"
            )
            # 至少包含基础维度
            assert "tool_selection" in c.reference_scores, (
                f"{c.id}: missing tool_selection in reference_scores"
            )

    def test_reference_scores_range(self):
        cases = load_multi_turn_dataset()
        for c in cases:
            for dim, score in c.reference_scores.items():
                assert 1 <= score <= 5, (
                    f"{c.id}.{dim}: score {score} out of range [1,5]"
                )

    def test_agent_turns_have_expected_tools(self):
        cases = load_multi_turn_dataset()
        valid_tools = {
            "create_entry", "update_entry", "delete_entry",
            "search_entries", "get_entry", "get_review_summary",
            "ask_user",
        }
        for c in cases:
            for turn in c.expected_agent_turns:
                for tool in turn.get("expected_tools", []):
                    assert tool in valid_tools, (
                        f"{c.id}: invalid expected_tool '{tool}'"
                    )

    def test_json_file_valid(self):
        path = DATASETS_DIR / "multi_turn_30.json"
        with open(path, "r") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 30

    def test_required_json_fields(self):
        path = DATASETS_DIR / "multi_turn_30.json"
        with open(path, "r") as f:
            data = json.load(f)
        required = ["id", "category", "turns", "final_state_check", "reference_scores"]
        for item in data:
            for field in required:
                assert field in item, f"{item.get('id', '?')}: missing {field}"

    def test_multi_turn_test_case_from_dict(self):
        data = {
            "id": "MT-TEST",
            "category": "follow_up_to_action",
            "turns": [
                {"role": "user", "content": "test"},
                {"role": "agent", "expected_tools": ["ask_user"]},
            ],
            "final_state_check": {"tool": "create_entry"},
            "reference_scores": {"tool_selection": 5},
        }
        tc = MultiTurnTestCase.from_dict(data)
        assert tc.id == "MT-TEST"
        assert tc.category == "follow_up_to_action"
        assert len(tc.turns) == 2


# ── SimulatedUser 测试 ──


class TestPresetReplyUser:
    """测试预设回复模拟用户"""

    @pytest.mark.asyncio
    async def test_sequential_replies(self):
        user = PresetReplyUser(["回复1", "回复2", "回复3"])
        r1 = await user.get_reply("agent msg", [], 0)
        assert r1 == "回复1"
        r2 = await user.get_reply("agent msg", [], 1)
        assert r2 == "回复2"
        r3 = await user.get_reply("agent msg", [], 2)
        assert r3 == "回复3"

    @pytest.mark.asyncio
    async def test_exhaust_replies(self):
        user = PresetReplyUser(["only one"])
        r1 = await user.get_reply("msg", [], 0)
        assert r1 == "only one"
        r2 = await user.get_reply("msg", [], 1)
        assert r2 == "only one"  # 返回最后一个

    @pytest.mark.asyncio
    async def test_loop_mode(self):
        user = PresetReplyUser(["A", "B"], loop=True)
        r1 = await user.get_reply("msg", [], 0)
        r2 = await user.get_reply("msg", [], 1)
        r3 = await user.get_reply("msg", [], 2)
        assert r1 == "A"
        assert r2 == "B"
        assert r3 == "A"  # 循环回来

    @pytest.mark.asyncio
    async def test_empty_replies(self):
        user = PresetReplyUser([])
        reply = await user.get_reply("msg", [], 0)
        assert reply == ""

    def test_reset(self):
        user = PresetReplyUser(["A", "B", "C"])
        assert user.current_index == 0
        assert user.remaining_replies == 3

    @pytest.mark.asyncio
    async def test_reset_after_use(self):
        user = PresetReplyUser(["A", "B"])
        await user.get_reply("msg", [], 0)
        assert user.current_index == 1
        user.reset()
        assert user.current_index == 0
        r = await user.get_reply("msg", [], 0)
        assert r == "A"


class TestLLMSimulatedUser:
    """测试 LLM 模拟用户"""

    @pytest.mark.asyncio
    async def test_with_injection(self):
        user = LLMSimulatedUser(inject_llm_response="我想学习 Rust")
        reply = await user.get_reply("你好，有什么可以帮你？", [], 0)
        assert reply == "我想学习 Rust"

    @pytest.mark.asyncio
    async def test_without_injection(self):
        user = LLMSimulatedUser()
        reply = await user.get_reply("你好", [], 0)
        assert reply == "好的，谢谢"

    @pytest.mark.asyncio
    async def test_call_count(self):
        user = LLMSimulatedUser(inject_llm_response="test")
        assert user.call_count == 0
        await user.get_reply("msg", [], 0)
        assert user.call_count == 1
        await user.get_reply("msg", [], 1)
        assert user.call_count == 2

    @pytest.mark.asyncio
    async def test_reset(self):
        user = LLMSimulatedUser(inject_llm_response="test")
        await user.get_reply("msg", [], 0)
        await user.get_reply("msg", [], 1)
        assert user.call_count == 2
        user.reset()
        assert user.call_count == 0

    @pytest.mark.asyncio
    async def test_custom_persona(self):
        user = LLMSimulatedUser(
            user_persona="你是一个测试用户，只回复 '固定回复'",
            inject_llm_response="固定回复",
        )
        reply = await user.get_reply("msg", [], 0)
        assert reply == "固定回复"

    def test_prompt_contains_history(self):
        user = LLMSimulatedUser()
        history = [
            ConversationTurn(role="user", content="你好"),
            ConversationTurn(role="agent", content="你好！"),
        ]
        prompt = user._build_prompt("需要帮助吗？", history, 1)
        assert "你好" in prompt
        assert "需要帮助吗？" in prompt


# ── MultiTurnRunner 测试 ──


class TestMultiTurnRunner:
    """测试多轮执行器"""

    @pytest.fixture
    def mock_agent_fn(self):
        """Mock Agent 调用函数"""
        async def _invoke(
            user_input: str,
            history: List[ConversationTurn],
        ) -> Dict[str, Any]:
            if "记录" in user_input or "想法" in user_input:
                return {
                    "response": "好的，你想记录什么？",
                    "tool_calls": [{"tool": "ask_user", "args": {"prompt": "什么想法"}}],
                }
            elif "搜索" in user_input or "找" in user_input:
                return {
                    "response": "搜索结果如下...",
                    "tool_calls": [{"tool": "search_entries", "args": {"query": user_input}}],
                }
            elif "学习" in user_input:
                return {
                    "response": "已记录你的学习心得。",
                    "tool_calls": [{"tool": "create_entry", "args": {"category": "inbox", "content": user_input}}],
                }
            else:
                return {
                    "response": "收到",
                    "tool_calls": [],
                }

        return _invoke

    @pytest.mark.asyncio
    async def test_run_preset_basic(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        tc = MultiTurnTestCase(
            id="MT-TEST-001",
            category="follow_up_to_action",
            turns=[
                {"role": "user", "content": "帮我记录一个想法"},
                {"role": "agent", "expected_tools": ["ask_user"]},
                {"role": "user", "content": "学习 LangGraph"},
                {"role": "agent", "expected_tools": ["create_entry"]},
            ],
            final_state_check={"tool": "create_entry"},
        )
        result = await runner.run_preset(tc)
        assert result.test_id == "MT-TEST-001"
        assert result.total_turns >= 4
        assert len(result.final_tool_calls) > 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_preset_multi_round(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        tc = MultiTurnTestCase(
            id="MT-TEST-002",
            category="context_reference",
            turns=[
                {"role": "user", "content": "帮我记录想法"},
                {"role": "user", "content": "关于 Python 异步编程"},
                {"role": "user", "content": "搜索一下之前的内容"},
            ],
            final_state_check={},
        )
        result = await runner.run_preset(tc)
        assert result.error is None
        assert result.total_turns >= 6  # 3 user + 3 agent

    @pytest.mark.asyncio
    async def test_run_simulated_with_preset_user(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        user = PresetReplyUser(["学习 Python", "搜索之前的内容"])
        tc = MultiTurnTestCase(
            id="MT-SIM-001",
            category="follow_up_to_action",
            turns=[
                {"role": "user", "content": "帮我记录"},
                {"role": "user", "content": "学习 Python"},
                {"role": "user", "content": "搜索之前的内容"},
            ],
            final_state_check={},
        )
        result = await runner.run_simulated(tc, user)
        assert result.test_id == "MT-SIM-001"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_simulated_with_llm_user(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        user = LLMSimulatedUser(inject_llm_response="我想学 Rust")
        tc = MultiTurnTestCase(
            id="MT-SIM-002",
            category="follow_up_to_action",
            turns=[
                {"role": "user", "content": "你好"},
            ],
            final_state_check={},
        )
        result = await runner.run_simulated(tc, user)
        assert result.test_id == "MT-SIM-002"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_dataset(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        cases = [
            MultiTurnTestCase(
                id="MT-D-001",
                category="follow_up_to_action",
                turns=[
                    {"role": "user", "content": "帮我记录"},
                    {"role": "user", "content": "学习 Docker"},
                ],
                final_state_check={},
            ),
            MultiTurnTestCase(
                id="MT-D-002",
                category="context_reference",
                turns=[
                    {"role": "user", "content": "搜索笔记"},
                ],
                final_state_check={},
            ),
        ]
        results = await runner.run_dataset(cases, mode="preset")
        assert len(results) == 2
        assert all(r.error is None for r in results)

    @pytest.mark.asyncio
    async def test_run_no_agent_fn(self):
        runner = MultiTurnRunner()
        tc = MultiTurnTestCase(
            id="MT-NOOP",
            category="follow_up_to_action",
            turns=[
                {"role": "user", "content": "test"},
            ],
            final_state_check={},
        )
        result = await runner.run_preset(tc)
        assert result.error is None
        assert result.total_turns >= 2  # user + agent

    @pytest.mark.asyncio
    async def test_run_empty_turns(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        tc = MultiTurnTestCase(
            id="MT-EMPTY",
            category="follow_up_to_action",
            turns=[],
            final_state_check={},
        )
        result = await runner.run_preset(tc)
        assert result.error is None
        assert result.total_turns == 0

    @pytest.mark.asyncio
    async def test_run_simulated_empty_user_turns(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        user = PresetReplyUser(["test"])
        tc = MultiTurnTestCase(
            id="MT-EMPTY-SIM",
            category="follow_up_to_action",
            turns=[],
            final_state_check={},
        )
        result = await runner.run_simulated(tc, user)
        assert result.error is not None  # 没有用户轮次

    @pytest.mark.asyncio
    async def test_multi_turn_result_properties(self, mock_agent_fn):
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        tc = MultiTurnTestCase(
            id="MT-PROP",
            category="follow_up_to_action",
            turns=[
                {"role": "user", "content": "帮我记录"},
                {"role": "user", "content": "学习 Python"},
            ],
            final_state_check={},
        )
        result = await runner.run_preset(tc)
        assert result.total_turns > 0
        assert len(result.user_turns) > 0
        assert len(result.agent_turns) > 0

    @pytest.mark.asyncio
    async def test_run_full_dataset(self, mock_agent_fn):
        """运行完整 30 条多轮数据集"""
        runner = MultiTurnRunner(agent_invoke_fn=mock_agent_fn)
        cases = load_multi_turn_dataset()
        results = await runner.run_dataset(cases, mode="preset")
        assert len(results) == 30
        # 大部分应该没有错误
        error_count = sum(1 for r in results if r.error is not None)
        assert error_count == 0, f"{error_count} cases had errors"


# ── ConversationTurn 测试 ──


class TestConversationTurn:
    """测试对话轮次数据结构"""

    def test_basic_turn(self):
        turn = ConversationTurn(role="user", content="你好", turn_index=0)
        assert turn.role == "user"
        assert turn.content == "你好"
        assert turn.tool_calls == []

    def test_agent_turn_with_tools(self):
        turn = ConversationTurn(
            role="agent",
            content="已记录",
            tool_calls=[{"tool": "create_entry"}],
            turn_index=1,
        )
        assert len(turn.tool_calls) == 1


# ── MultiTurnResult 测试 ──


class TestMultiTurnResult:
    """测试多轮评估结果"""

    def test_properties(self):
        result = MultiTurnResult(
            test_id="TEST",
            turns=[
                ConversationTurn(role="user", content="a", turn_index=0),
                ConversationTurn(role="agent", content="b", turn_index=1),
                ConversationTurn(role="user", content="c", turn_index=2),
            ],
        )
        assert result.total_turns == 3
        assert len(result.user_turns) == 2
        assert len(result.agent_turns) == 1

    def test_empty_result(self):
        result = MultiTurnResult()
        assert result.total_turns == 0
        assert result.user_turns == []
        assert result.agent_turns == []
        assert result.passed is False
        assert result.error is None
