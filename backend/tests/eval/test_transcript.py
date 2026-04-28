"""评估转录系统测试

覆盖:
- EvalTranscript 创建、序列化、反序列化
- TranscriptStore 保存/加载/列表/删除（使用 tmp_path fixture）
- TranscriptReviewer 筛选和标签功能
- SaturationMonitor 趋势计算和建议
- JSON 格式正确性
- 边界情况：空转录列表、无 judge_result 等
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from tests.eval.transcript import (
    AgentTrace,
    DimensionTrend,
    EvalTranscript,
    HumanLabel,
    LLMCallRecord,
    SaturationMonitor,
    ToolCallRecord,
    TranscriptReviewer,
    TranscriptStore,
    TrendPoint,
    _generate_transcript_id,
)


# ── Fixtures ──


@pytest.fixture
def sample_agent_trace() -> AgentTrace:
    """创建示例 Agent Trace"""
    return AgentTrace(
        input="帮我记录一个想法：学习 Rust",
        output="好的，已为你创建灵感记录。",
        tool_calls=[
            ToolCallRecord(
                tool="create_entry",
                args={"type": "inbox", "content": "学习 Rust"},
                result={"id": "inbox-abc123", "status": "created"},
                latency_ms=120.5,
            )
        ],
        llm_calls=[
            LLMCallRecord(
                input_tokens=150,
                output_tokens=80,
                latency_ms=500.0,
                model="gpt-4",
            )
        ],
        total_latency_ms=620.5,
        iteration_count=1,
    )


@pytest.fixture
def sample_transcript(sample_agent_trace: AgentTrace) -> EvalTranscript:
    """创建示例转录记录"""
    return EvalTranscript(
        transcript_id="eval-001",
        timestamp="2026-04-28T10:30:00",
        test_case_id="ST-001",
        test_case_category="tool_selection",
        agent_trace=sample_agent_trace,
        judge_result={
            "test_id": "ST-001",
            "total_score": 38,
            "max_possible_score": 45,
            "average_score": 4.22,
            "weighted_average": 4.15,
            "percentage": 84.4,
            "dimension_scores": {
                "tool_selection": {"score": 5, "reasoning": "完美选择"},
                "param_extraction": {"score": 4, "reasoning": "参数基本完整"},
                "response_quality": {"score": 4, "reasoning": "自然流畅"},
                "error_handling": {"score": 3, "reasoning": "无错误场景"},
                "efficiency": {"score": 4, "reasoning": "高效执行"},
                "user_experience": {"score": 4, "reasoning": "良好体验"},
            },
        },
        outcome_grade={
            "passed": True,
            "tool_matched": True,
            "args_contained": True,
            "args_exact_matched": True,
            "no_violations": True,
            "details": "所有检查通过",
        },
        metadata={"trial_index": 0, "thread_id": "eval-abc123"},
    )


@pytest.fixture
def sample_transcript_low_score() -> EvalTranscript:
    """创建低分转录记录"""
    return EvalTranscript(
        transcript_id="eval-002",
        timestamp="2026-04-28T11:00:00",
        test_case_id="ST-010",
        test_case_category="param_extraction",
        agent_trace=AgentTrace(
            input="记录一条笔记关于 Python 装饰器",
            output="我不确定你想做什么。",
            tool_calls=[],
            llm_calls=[LLMCallRecord(input_tokens=100, output_tokens=30, latency_ms=300)],
            total_latency_ms=300,
            iteration_count=1,
        ),
        judge_result={
            "test_id": "ST-010",
            "total_score": 12,
            "max_possible_score": 30,
            "average_score": 2.0,
            "weighted_average": 2.1,
            "percentage": 40.0,
            "dimension_scores": {
                "tool_selection": {"score": 1, "reasoning": "未选择任何工具"},
                "param_extraction": {"score": 1, "reasoning": "未提取参数"},
                "response_quality": {"score": 2, "reasoning": "回复无帮助"},
                "error_handling": {"score": 3, "reasoning": "无错误处理"},
                "efficiency": {"score": 3, "reasoning": "未执行操作"},
                "user_experience": {"score": 2, "reasoning": "用户困惑"},
            },
        },
        outcome_grade={
            "passed": False,
            "tool_matched": False,
            "args_contained": False,
            "args_exact_matched": False,
            "no_violations": True,
            "details": "期望工具 'create_entry' 未被调用",
        },
    )


@pytest.fixture
def sample_transcript_no_judge() -> EvalTranscript:
    """创建无 judge_result 的转录"""
    return EvalTranscript(
        transcript_id="eval-003",
        timestamp="2026-04-28T12:00:00",
        test_case_id="ST-005",
        test_case_category="pure_chat",
        agent_trace=AgentTrace(
            input="你好",
            output="你好！有什么可以帮你的吗？",
        ),
    )


@pytest.fixture
def store(tmp_path: Path) -> TranscriptStore:
    """创建临时存储"""
    return TranscriptStore(base_dir=tmp_path / "eval_transcripts")


# ── ToolCallRecord 测试 ──


class TestToolCallRecord:
    def test_to_dict(self):
        tc = ToolCallRecord(
            tool="create_entry",
            args={"type": "inbox", "content": "test"},
            result={"id": "abc"},
            latency_ms=100.0,
        )
        d = tc.to_dict()
        assert d["tool"] == "create_entry"
        assert d["args"]["type"] == "inbox"
        assert d["latency_ms"] == 100.0

    def test_from_dict(self):
        data = {
            "tool": "update_entry",
            "args": {"status": "done"},
            "result": None,
            "latency_ms": 50.0,
        }
        tc = ToolCallRecord.from_dict(data)
        assert tc.tool == "update_entry"
        assert tc.args["status"] == "done"
        assert tc.latency_ms == 50.0

    def test_roundtrip(self):
        tc = ToolCallRecord(tool="search", args={"q": "test"}, result=[1, 2], latency_ms=200)
        d = tc.to_dict()
        tc2 = ToolCallRecord.from_dict(d)
        assert tc2.tool == tc.tool
        assert tc2.args == tc.args
        assert tc2.result == tc.result
        assert tc2.latency_ms == tc.latency_ms


# ── LLMCallRecord 测试 ──


class TestLLMCallRecord:
    def test_to_dict(self):
        lc = LLMCallRecord(input_tokens=100, output_tokens=50, latency_ms=300, model="gpt-4")
        d = lc.to_dict()
        assert d["input_tokens"] == 100
        assert d["output_tokens"] == 50
        assert d["model"] == "gpt-4"

    def test_from_dict(self):
        data = {"input_tokens": 200, "output_tokens": 100, "latency_ms": 600, "model": "claude"}
        lc = LLMCallRecord.from_dict(data)
        assert lc.input_tokens == 200
        assert lc.model == "claude"

    def test_defaults(self):
        lc = LLMCallRecord()
        assert lc.input_tokens == 0
        assert lc.output_tokens == 0
        assert lc.latency_ms == 0.0
        assert lc.model == ""


# ── AgentTrace 测试 ──


class TestAgentTrace:
    def test_token_totals(self, sample_agent_trace: AgentTrace):
        assert sample_agent_trace.total_input_tokens == 150
        assert sample_agent_trace.total_output_tokens == 80
        assert sample_agent_trace.total_tokens == 230

    def test_to_dict_and_from_dict(self, sample_agent_trace: AgentTrace):
        d = sample_agent_trace.to_dict()
        trace2 = AgentTrace.from_dict(d)
        assert trace2.input == sample_agent_trace.input
        assert trace2.output == sample_agent_trace.output
        assert len(trace2.tool_calls) == 1
        assert trace2.tool_calls[0].tool == "create_entry"
        assert trace2.total_latency_ms == 620.5

    def test_empty_trace(self):
        trace = AgentTrace()
        d = trace.to_dict()
        assert d["tool_calls"] == []
        assert d["llm_calls"] == []
        assert trace.total_tokens == 0


# ── EvalTranscript 测试 ──


class TestEvalTranscript:
    def test_create_with_defaults(self):
        t = EvalTranscript()
        assert t.transcript_id  # 自动生成
        assert t.timestamp  # 自动填充
        assert t.human_label is None
        assert isinstance(t.agent_trace, AgentTrace)

    def test_to_dict(self, sample_transcript: EvalTranscript):
        d = sample_transcript.to_dict()
        assert d["transcript_id"] == "eval-001"
        assert d["test_case_id"] == "ST-001"
        assert d["test_case_category"] == "tool_selection"
        assert "agent_trace" in d
        assert d["judge_result"]["average_score"] == 4.22
        assert d["outcome_grade"]["passed"] is True

    def test_to_json(self, sample_transcript: EvalTranscript):
        json_str = sample_transcript.to_json()
        # 验证是合法 JSON
        parsed = json.loads(json_str)
        assert parsed["transcript_id"] == "eval-001"
        # 验证中文不被转义
        assert "完美选择" in json_str

    def test_from_dict(self, sample_transcript: EvalTranscript):
        d = sample_transcript.to_dict()
        t = EvalTranscript.from_dict(d)
        assert t.transcript_id == "eval-001"
        assert t.test_case_id == "ST-001"
        assert t.agent_trace.input == "帮我记录一个想法：学习 Rust"
        assert t.judge_result["average_score"] == 4.22

    def test_from_json(self, sample_transcript: EvalTranscript):
        json_str = sample_transcript.to_json()
        t = EvalTranscript.from_json(json_str)
        assert t.transcript_id == "eval-001"

    def test_roundtrip(self, sample_transcript: EvalTranscript):
        """序列化 → 反序列化往返测试"""
        json_str = sample_transcript.to_json()
        restored = EvalTranscript.from_json(json_str)
        assert restored.transcript_id == sample_transcript.transcript_id
        assert restored.timestamp == sample_transcript.timestamp
        assert restored.test_case_id == sample_transcript.test_case_id
        assert restored.agent_trace.input == sample_transcript.agent_trace.input
        assert len(restored.agent_trace.tool_calls) == len(sample_transcript.agent_trace.tool_calls)

    def test_judge_average_score(self, sample_transcript: EvalTranscript):
        assert sample_transcript.judge_average_score == 4.22

    def test_judge_average_score_none(self, sample_transcript_no_judge: EvalTranscript):
        assert sample_transcript_no_judge.judge_average_score is None

    def test_is_passed_with_outcome_grade(self, sample_transcript: EvalTranscript):
        assert sample_transcript.is_passed is True

    def test_is_failed_with_outcome_grade(self, sample_transcript_low_score: EvalTranscript):
        assert sample_transcript_low_score.is_passed is False

    def test_is_passed_no_results(self, sample_transcript_no_judge: EvalTranscript):
        # 无 judge_result 也无 outcome_grade
        assert sample_transcript_no_judge.is_passed is False

    def test_date_str(self, sample_transcript: EvalTranscript):
        assert sample_transcript.date_str == "2026-04-28"

    def test_human_label_constants(self):
        assert HumanLabel.PASS == "pass"
        assert HumanLabel.AGENT_ERROR == "agent_error"
        assert HumanLabel.JUDGE_ERROR == "judge_error"
        assert HumanLabel.AMBIGUOUS == "ambiguous"
        assert set(HumanLabel.valid_labels()) == {
            "pass", "agent_error", "judge_error", "ambiguous"
        }


# ── TranscriptStore 测试 ──


class TestTranscriptStore:
    def test_save_and_load(self, store: TranscriptStore, sample_transcript: EvalTranscript):
        path = store.save(sample_transcript)
        assert "eval-001.json" in path

        loaded = store.load("eval-001", "2026-04-28")
        assert loaded.transcript_id == "eval-001"
        assert loaded.test_case_id == "ST-001"
        assert loaded.agent_trace.input == "帮我记录一个想法：学习 Rust"

    def test_save_auto_assigns_id(self, store: TranscriptStore):
        t = EvalTranscript(
            timestamp="2026-04-28T10:00:00",
            test_case_id="ST-001",
            agent_trace=AgentTrace(input="test"),
        )
        path = store.save(t)
        assert "eval-001.json" in path
        assert t.transcript_id == "eval-001"

    def test_save_sequential_ids(self, store: TranscriptStore):
        for i in range(3):
            t = EvalTranscript(
                timestamp=f"2026-04-28T10:0{i}:00",
                test_case_id=f"ST-{i:03d}",
                agent_trace=AgentTrace(input=f"test {i}"),
            )
            store.save(t)

        all_t = store.list("2026-04-28")
        assert len(all_t) == 3
        ids = [t.transcript_id for t in all_t]
        assert ids == ["eval-001", "eval-002", "eval-003"]

    def test_list_empty(self, store: TranscriptStore):
        result = store.list("2026-04-28")
        assert result == []

    def test_list_sorted(self, store: TranscriptStore):
        # 保存顺序颠倒
        for seq in [3, 1, 2]:
            t = EvalTranscript(
                transcript_id=f"eval-{seq:03d}",
                timestamp="2026-04-28T10:00:00",
                test_case_id=f"ST-{seq:03d}",
            )
            store.save(t)

        all_t = store.list("2026-04-28")
        ids = [t.transcript_id for t in all_t]
        assert ids == ["eval-001", "eval-002", "eval-003"]

    def test_delete(self, store: TranscriptStore, sample_transcript: EvalTranscript):
        store.save(sample_transcript)
        assert store.delete("eval-001", "2026-04-28") is True
        assert store.list("2026-04-28") == []

    def test_delete_nonexistent(self, store: TranscriptStore):
        assert store.delete("eval-999", "2026-04-28") is False

    def test_load_nonexistent(self, store: TranscriptStore):
        with pytest.raises(FileNotFoundError):
            store.load("eval-999", "2026-04-28")

    def test_json_format(self, store: TranscriptStore, sample_transcript: EvalTranscript):
        """验证存储的 JSON 格式正确"""
        store.save(sample_transcript)
        date_dir = store._date_dir("2026-04-28")
        filepath = date_dir / "eval-001.json"

        # 读取并解析
        content = filepath.read_text(encoding="utf-8")
        data = json.loads(content)

        # 验证结构完整性
        assert data["transcript_id"] == "eval-001"
        assert "agent_trace" in data
        assert "tool_calls" in data["agent_trace"]
        assert "llm_calls" in data["agent_trace"]
        assert data["agent_trace"]["tool_calls"][0]["tool"] == "create_entry"
        assert data["agent_trace"]["tool_calls"][0]["latency_ms"] == 120.5

    def test_creates_directory_structure(self, store: TranscriptStore, sample_transcript: EvalTranscript):
        store.save(sample_transcript)
        assert (store.base_dir / "2026-04-28").is_dir()

    def test_list_dates(self, store: TranscriptStore):
        for date_str in ["2026-04-27", "2026-04-28", "2026-04-29"]:
            t = EvalTranscript(
                timestamp=f"{date_str}T10:00:00",
                test_case_id="ST-001",
            )
            store.save(t)

        dates = store.list_dates()
        assert dates == ["2026-04-27", "2026-04-28", "2026-04-29"]

    def test_different_dates_independent_seq(self, store: TranscriptStore):
        """不同日期的序号独立"""
        t1 = EvalTranscript(timestamp="2026-04-27T10:00:00", test_case_id="ST-001")
        t2 = EvalTranscript(timestamp="2026-04-28T10:00:00", test_case_id="ST-002")
        store.save(t1)
        store.save(t2)

        assert t1.transcript_id == "eval-001"
        assert t2.transcript_id == "eval-001"


# ── TranscriptReviewer 测试 ──


class TestTranscriptReviewer:
    def test_filter_failed(
        self,
        sample_transcript: EvalTranscript,
        sample_transcript_low_score: EvalTranscript,
    ):
        reviewer = TranscriptReviewer()
        transcripts = [sample_transcript, sample_transcript_low_score]
        failed = reviewer.filter_failed(transcripts)
        assert len(failed) == 1
        assert failed[0].transcript_id == "eval-002"

    def test_filter_failed_empty(self):
        reviewer = TranscriptReviewer()
        assert reviewer.filter_failed([]) == []

    def test_filter_failed_no_judge(self, sample_transcript_no_judge: EvalTranscript):
        reviewer = TranscriptReviewer()
        # 无 judge_result 也无 outcome_grade 的不算失败
        failed = reviewer.filter_failed([sample_transcript_no_judge])
        assert len(failed) == 0

    def test_filter_unlabeled(
        self,
        sample_transcript: EvalTranscript,
        sample_transcript_low_score: EvalTranscript,
    ):
        sample_transcript.human_label = "pass"
        reviewer = TranscriptReviewer()
        transcripts = [sample_transcript, sample_transcript_low_score]
        unlabeled = reviewer.filter_unlabeled(transcripts)
        assert len(unlabeled) == 1
        assert unlabeled[0].transcript_id == "eval-002"

    def test_filter_by_label(self, sample_transcript: EvalTranscript):
        sample_transcript.human_label = "pass"
        reviewer = TranscriptReviewer()
        result = reviewer.filter_by_label([sample_transcript], "pass")
        assert len(result) == 1

        result = reviewer.filter_by_label([sample_transcript], "agent_error")
        assert len(result) == 0

    def test_add_human_label(self, store: TranscriptStore, sample_transcript: EvalTranscript):
        store.save(sample_transcript)

        reviewer = TranscriptReviewer()
        updated = reviewer.add_human_label(
            store, "eval-001", "2026-04-28", "pass", "评分准确"
        )
        assert updated.human_label == "pass"
        assert updated.human_notes == "评分准确"

        # 验证持久化
        loaded = store.load("eval-001", "2026-04-28")
        assert loaded.human_label == "pass"

    def test_add_human_label_invalid(self, store: TranscriptStore, sample_transcript: EvalTranscript):
        store.save(sample_transcript)
        reviewer = TranscriptReviewer()
        with pytest.raises(ValueError, match="Invalid label"):
            reviewer.add_human_label(store, "eval-001", "2026-04-28", "invalid")

    def test_review_summary(
        self,
        sample_transcript: EvalTranscript,
        sample_transcript_low_score: EvalTranscript,
        sample_transcript_no_judge: EvalTranscript,
    ):
        sample_transcript.human_label = "pass"
        sample_transcript_low_score.human_label = "agent_error"

        reviewer = TranscriptReviewer()
        summary = reviewer.review_summary([
            sample_transcript,
            sample_transcript_low_score,
            sample_transcript_no_judge,
        ])

        assert summary["total"] == 3
        assert summary["labeled"] == 2
        assert summary["unlabeled"] == 1
        assert summary["failed"] == 1
        assert summary["label_counts"]["pass"] == 1
        assert summary["label_counts"]["agent_error"] == 1

    def test_review_summary_empty(self):
        reviewer = TranscriptReviewer()
        summary = reviewer.review_summary([])
        assert summary["total"] == 0
        assert summary["labeled"] == 0
        assert summary["unlabeled"] == 0


# ── SaturationMonitor 测试 ──


@pytest.fixture
def multi_day_transcripts() -> list[EvalTranscript]:
    """多天多维度转录记录"""
    transcripts = []
    base_scores_high = {
        "tool_selection": {"score": 5, "reasoning": ""},
        "param_extraction": {"score": 4, "reasoning": ""},
        "response_quality": {"score": 4, "reasoning": ""},
    }
    base_scores_low = {
        "tool_selection": {"score": 2, "reasoning": ""},
        "param_extraction": {"score": 3, "reasoning": ""},
        "response_quality": {"score": 2, "reasoning": ""},
    }

    # Day 1: 2 high + 1 low
    for i, (scores, cat) in enumerate([
        (base_scores_high, "tool_selection"),
        (base_scores_high, "param_extraction"),
        (base_scores_low, "response_quality"),
    ]):
        transcripts.append(EvalTranscript(
            transcript_id=f"eval-{i+1:03d}",
            timestamp=f"2026-04-26T10:0{i}:00",
            test_case_id=f"ST-{i+1:03d}",
            test_case_category=cat,
            agent_trace=AgentTrace(input=f"test {i}"),
            judge_result={
                "test_id": f"ST-{i+1:03d}",
                "total_score": 30,
                "average_score": 3.5,
                "dimension_scores": scores,
            },
        ))

    # Day 2: 3 high
    for i in range(3):
        transcripts.append(EvalTranscript(
            transcript_id=f"eval-{i+4:03d}",
            timestamp=f"2026-04-27T10:0{i}:00",
            test_case_id=f"ST-{i+4:03d}",
            test_case_category="tool_selection",
            agent_trace=AgentTrace(input=f"test {i+3}"),
            judge_result={
                "test_id": f"ST-{i+4:03d}",
                "total_score": 40,
                "average_score": 4.5,
                "dimension_scores": base_scores_high,
            },
        ))

    # Day 3: 3 high
    for i in range(3):
        transcripts.append(EvalTranscript(
            transcript_id=f"eval-{i+7:03d}",
            timestamp=f"2026-04-28T10:0{i}:00",
            test_case_id=f"ST-{i+7:03d}",
            test_case_category="tool_selection",
            agent_trace=AgentTrace(input=f"test {i+6}"),
            judge_result={
                "test_id": f"ST-{i+7:03d}",
                "total_score": 42,
                "average_score": 4.7,
                "dimension_scores": base_scores_high,
            },
        ))

    return transcripts


class TestSaturationMonitor:
    def test_compute_trend(self, multi_day_transcripts: list[EvalTranscript]):
        monitor = SaturationMonitor()
        trend = monitor.compute_trend(multi_day_transcripts, "tool_selection")

        assert trend.dimension == "tool_selection"
        assert len(trend.points) == 3  # 3 days
        # Day 1: 2/3 passed (score >= 4)
        assert trend.points[0].pass_rate == pytest.approx(2 / 3, abs=0.01)
        # Day 2: 3/3 passed
        assert trend.points[1].pass_rate == pytest.approx(1.0)
        # Day 3: 3/3 passed
        assert trend.points[2].pass_rate == pytest.approx(1.0)
        assert trend.current_rate == pytest.approx(1.0)
        # Day2→Day3 都是 1.0，差异为 0，趋势 stable
        assert trend.trend_direction == "stable"

    def test_compute_trend_empty(self):
        monitor = SaturationMonitor()
        trend = SaturationMonitor().compute_trend([], "tool_selection")
        assert trend.dimension == "tool_selection"
        assert trend.points == []
        assert trend.current_rate == 0.0

    def test_overall_trend(self, multi_day_transcripts: list[EvalTranscript]):
        monitor = SaturationMonitor()
        overall = monitor.overall_trend(multi_day_transcripts)

        # 应包含 3 个维度
        assert "tool_selection" in overall
        assert "param_extraction" in overall
        assert "response_quality" in overall

    def test_suggest_difficulty_increase(self, multi_day_transcripts: list[EvalTranscript]):
        monitor = SaturationMonitor()
        overall = monitor.overall_trend(multi_day_transcripts)
        suggestions = monitor.suggest_difficulty_increase(overall)

        # tool_selection 和 param_extraction 通过率应该 > 90%
        suggested_dims = [s["dimension"] for s in suggestions]
        assert "tool_selection" in suggested_dims

    def test_no_suggestion_below_threshold(self):
        monitor = SaturationMonitor()
        # 创建通过率低于 90% 的趋势数据
        trend_data = {
            "tool_selection": DimensionTrend(
                dimension="tool_selection",
                points=[TrendPoint(date="2026-04-28", pass_rate=0.80, count=10)],
                current_rate=0.80,
                trend_direction="stable",
            ),
        }
        suggestions = monitor.suggest_difficulty_increase(trend_data)
        assert len(suggestions) == 0

    def test_trend_report(self, multi_day_transcripts: list[EvalTranscript]):
        monitor = SaturationMonitor()
        report = monitor.trend_report(multi_day_transcripts)

        assert report["total_transcripts"] == len(multi_day_transcripts)
        assert "dimensions" in report
        assert "difficulty_suggestions" in report
        assert isinstance(report["saturated_dimensions"], int)

    def test_trend_report_empty(self):
        monitor = SaturationMonitor()
        report = monitor.trend_report([])

        assert report["total_transcripts"] == 0
        assert report["dimensions"] == {}
        assert report["difficulty_suggestions"] == []

    def test_trend_direction_stable(self):
        monitor = SaturationMonitor()
        transcripts = []
        for day in ["2026-04-26", "2026-04-27"]:
            transcripts.append(EvalTranscript(
                transcript_id="eval-001",
                timestamp=f"{day}T10:00:00",
                test_case_id="ST-001",
                judge_result={
                    "dimension_scores": {
                        "tool_selection": {"score": 4, "reasoning": ""},
                    },
                },
            ))

        trend = monitor.compute_trend(transcripts, "tool_selection")
        # 两天通过率一样，趋势为 stable
        assert trend.trend_direction == "stable"

    def test_trend_direction_down(self):
        monitor = SaturationMonitor()
        transcripts = [
            EvalTranscript(
                timestamp="2026-04-26T10:00:00",
                test_case_id="ST-001",
                judge_result={"dimension_scores": {"tool_selection": {"score": 5}}},
            ),
            EvalTranscript(
                timestamp="2026-04-26T11:00:00",
                test_case_id="ST-002",
                judge_result={"dimension_scores": {"tool_selection": {"score": 5}}},
            ),
            EvalTranscript(
                timestamp="2026-04-27T10:00:00",
                test_case_id="ST-003",
                judge_result={"dimension_scores": {"tool_selection": {"score": 2}}},
            ),
            EvalTranscript(
                timestamp="2026-04-27T11:00:00",
                test_case_id="ST-004",
                judge_result={"dimension_scores": {"tool_selection": {"score": 2}}},
            ),
        ]

        trend = monitor.compute_trend(transcripts, "tool_selection")
        assert trend.trend_direction == "down"


# ── 序号生成测试 ──


class TestGenerateTranscriptId:
    def test_with_seq(self):
        assert _generate_transcript_id(1) == "eval-001"
        assert _generate_transcript_id(42) == "eval-042"
        assert _generate_transcript_id(999) == "eval-999"

    def test_without_seq(self):
        assert _generate_transcript_id() == "eval-000"
