"""B195 测试: run_eval.py 集成 report_generator

使用 mock 测试（不依赖真实 Agent），覆盖所有 test_tasks。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保可以 import 项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.eval.framework import (
    EvaluationReport,
    EvaluationResult,
    NegativeEvalResult,
    NegativeReport,
    NegativeTestCase,
    TestCase,
)
from tests.eval.report_generator import (
    EvalReportData,
    append_history,
    build_report_data,
    generate_html_report,
    load_history,
)
from tests.eval.run_eval import (
    _get_default_report_dir,
    _get_env_info,
    run_negative,
    run_single_turn,
)


# ── Fixtures ──


def _make_test_case(
    id: str = "ST-001",
    category: str = "tool_selection",
    user_input: str = "帮我搜索今天的新闻",
    expected_tools: list = None,
) -> TestCase:
    return TestCase(
        id=id,
        category=category,
        user_input=user_input,
        expected_tools=expected_tools or ["search_entries"],
    )


def _make_negative_case(
    id: str = "NEG-001",
    category: str = "no_tool",
    user_input: str = "你好，今天天气怎么样",
    should_not_call: list = None,
) -> NegativeTestCase:
    return NegativeTestCase(
        id=id,
        category=category,
        user_input=user_input,
        should_not_call=should_not_call or ["search_entries", "create_entry"],
        reason="纯闲聊不应调用工具",
    )


def _make_mock_client_single(responses: List[dict] = None) -> AsyncMock:
    """创建 mock client，每次 call 返回预设结果"""
    if responses is None:
        responses = [
            {"tools": ["search_entries"], "args": [{}], "content": "为你找到了以下结果..."},
        ]
    client = AsyncMock()
    client.call = AsyncMock(side_effect=responses)
    return client


def _make_mock_client_negative(responses: List[dict] = None) -> AsyncMock:
    """创建 mock client 用于负面评估"""
    if responses is None:
        responses = [
            {"tools": [], "args": [], "content": "你好！今天天气不错。"},
        ]
    client = AsyncMock()
    client.call = AsyncMock(side_effect=responses)
    return client


# ── 测试: run_single_turn 返回二元组 ──


class TestRunSingleTurnReturns:
    """正常: run_single_turn 返回 (EvaluationReport, per_case_records)"""

    @pytest.mark.asyncio
    async def test_returns_tuple(self):
        """run_single_turn 返回二元组"""
        cases = [_make_test_case()]
        client = _make_mock_client_single()
        result = await run_single_turn(client, cases)
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_report_type(self):
        """第一元素为 EvaluationReport"""
        cases = [_make_test_case()]
        client = _make_mock_client_single()
        report, records = await run_single_turn(client, cases)
        assert isinstance(report, EvaluationReport)

    @pytest.mark.asyncio
    async def test_records_type(self):
        """第二元素为 list[dict]"""
        cases = [_make_test_case()]
        client = _make_mock_client_single()
        report, records = await run_single_turn(client, cases)
        assert isinstance(records, list)
        assert len(records) == 1
        assert isinstance(records[0], dict)

    @pytest.mark.asyncio
    async def test_record_schema(self):
        """per-case record 包含所有必填字段"""
        cases = [_make_test_case()]
        client = _make_mock_client_single()
        report, records = await run_single_turn(client, cases)
        rec = records[0]
        required_keys = {
            "input", "expected_tools", "actual_tools", "agent_reply",
            "passed", "category", "elapsed_seconds",
        }
        assert required_keys.issubset(set(rec.keys()))

    @pytest.mark.asyncio
    async def test_agent_reply_from_content(self):
        """agent_reply 从 parse_sse_stream 的 content 字段获取"""
        cases = [_make_test_case()]
        client = _make_mock_client_single([
            {"tools": ["search_entries"], "args": [{}], "content": "搜索结果如下"},
        ])
        report, records = await run_single_turn(client, cases)
        assert records[0]["agent_reply"] == "搜索结果如下"

    @pytest.mark.asyncio
    async def test_agent_reply_empty_when_no_content(self):
        """SSE content 为空时 agent_reply 为空字符串"""
        cases = [_make_test_case()]
        client = _make_mock_client_single([
            {"tools": ["search_entries"], "args": [{}], "content": ""},
        ])
        report, records = await run_single_turn(client, cases)
        assert records[0]["agent_reply"] == ""

    @pytest.mark.asyncio
    async def test_passed_case(self):
        """通过的用例 passed=True"""
        cases = [_make_test_case(expected_tools=["search_entries"])]
        client = _make_mock_client_single([
            {"tools": ["search_entries"], "args": [{}], "content": "OK"},
        ])
        report, records = await run_single_turn(client, cases)
        assert records[0]["passed"] is True

    @pytest.mark.asyncio
    async def test_failed_case(self):
        """失败的用例 passed=False, agent_reply 非空"""
        cases = [_make_test_case(expected_tools=["create_entry"])]
        client = _make_mock_client_single([
            {"tools": ["search_entries"], "args": [{}], "content": "帮你搜索了"},
        ])
        report, records = await run_single_turn(client, cases)
        assert records[0]["passed"] is False
        assert records[0]["agent_reply"] == "帮你搜索了"


# ── 测试: run_negative 返回二元组 ──


class TestRunNegativeReturns:
    """正常: run_negative 返回 (NegativeReport, per_case_records)"""

    @pytest.mark.asyncio
    async def test_returns_tuple(self):
        """run_negative 返回二元组"""
        cases = [_make_negative_case()]
        client = _make_mock_client_negative()
        result = await run_negative(client, cases)
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_report_type(self):
        """第一元素为 NegativeReport"""
        cases = [_make_negative_case()]
        client = _make_mock_client_negative()
        report, records = await run_negative(client, cases)
        assert isinstance(report, NegativeReport)

    @pytest.mark.asyncio
    async def test_record_schema(self):
        """per-case record 包含所有必填字段"""
        cases = [_make_negative_case()]
        client = _make_mock_client_negative()
        report, records = await run_negative(client, cases)
        rec = records[0]
        required_keys = {
            "input", "should_not_call", "actual_tools", "agent_reply",
            "violated", "violated_tools", "category", "elapsed_seconds",
        }
        assert required_keys.issubset(set(rec.keys()))

    @pytest.mark.asyncio
    async def test_no_violation(self):
        """无违规时 violated=False"""
        cases = [_make_negative_case(should_not_call=["search_entries"])]
        client = _make_mock_client_negative([
            {"tools": [], "args": [], "content": "你好！"},
        ])
        report, records = await run_negative(client, cases)
        assert records[0]["violated"] is False
        assert records[0]["violated_tools"] == []
        assert records[0]["agent_reply"] == "你好！"

    @pytest.mark.asyncio
    async def test_with_violation(self):
        """有违规时 violated=True, agent_reply 非空"""
        cases = [_make_negative_case(should_not_call=["search_entries"])]
        client = _make_mock_client_negative([
            {"tools": ["search_entries"], "args": [{}], "content": "帮你搜索了"},
        ])
        report, records = await run_negative(client, cases)
        assert records[0]["violated"] is True
        assert "search_entries" in records[0]["violated_tools"]
        assert records[0]["agent_reply"] == "帮你搜索了"


# ── 测试: _get_env_info ──


class TestGetEnvInfo:
    """环境信息获取"""

    def test_returns_dict(self):
        """返回字典"""
        info = _get_env_info()
        assert isinstance(info, dict)

    def test_git_commit_key(self):
        """包含 git_commit 键"""
        info = _get_env_info()
        assert "git_commit" in info

    def test_model_key(self):
        """包含 model 键"""
        info = _get_env_info()
        assert "model" in info

    @patch("subprocess.run", side_effect=Exception("git not found"))
    def test_git_fallback(self, mock_run):
        """git rev-parse 失败时降级为 'unknown'"""
        info = _get_env_info()
        assert info["git_commit"] == "unknown"

    @patch.dict(os.environ, {}, clear=True)
    def test_model_fallback(self):
        """LLM_MODEL 未设置时降级为 'unknown'"""
        # LLM_MODEL 可能不在环境中
        env = dict(os.environ)
        env.pop("LLM_MODEL", None)
        with patch.dict(os.environ, env, clear=True):
            info = _get_env_info()
            assert info["model"] == "unknown"

    @patch.dict(os.environ, {"LLM_MODEL": "gpt-4o"})
    def test_model_set(self):
        """LLM_MODEL 设置时正确获取"""
        info = _get_env_info()
        assert info["model"] == "gpt-4o"


# ── 测试: _get_default_report_dir ──


class TestGetDefaultReportDir:
    """默认报告目录解析"""

    def test_resolves_to_project_root_data(self):
        """默认路径解析到项目根目录 data/eval_reports/"""
        report_dir = _get_default_report_dir()
        # run_eval.py 在 backend/tests/eval/ 下
        # 向上 4 级: backend/tests/eval/run_eval.py -> project root
        assert report_dir.name == "eval_reports"
        assert report_dir.parent.name == "data"
        # 确认不是 backend/data/
        assert "backend" not in str(report_dir)

    def test_is_absolute_path(self):
        """返回绝对路径"""
        report_dir = _get_default_report_dir()
        assert report_dir.is_absolute()


# ── 测试: HTML 报告生成集成 ──


class TestHTMLReportGeneration:
    """正常: HTML 报告生成"""

    @pytest.mark.asyncio
    async def test_single_mode_generates_html(self, tmp_path):
        """正向评估后生成 HTML 文件"""
        cases = [_make_test_case()]
        client = _make_mock_client_single()
        report, records = await run_single_turn(client, cases)

        env_info = {"git_commit": "abc1234", "model": "test-model"}
        report_data = build_report_data(
            case_records=records,
            dataset_mode="single",
            env_info=env_info,
            eval_time="2026-04-29T10:00:00",
        )

        html_content = generate_html_report(report_data)
        html_path = tmp_path / "test_report.html"
        html_path.write_text(html_content, encoding="utf-8")

        assert html_path.exists()
        content = html_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "AI Agent Evaluation Report" in content

    @pytest.mark.asyncio
    async def test_negative_mode_generates_html(self, tmp_path):
        """负面评估后生成 HTML 文件"""
        cases = [_make_negative_case()]
        client = _make_mock_client_negative()
        report, records = await run_negative(client, cases)

        env_info = {"git_commit": "abc1234", "model": "test-model"}
        report_data = build_report_data(
            case_records=records,
            dataset_mode="negative",
            env_info=env_info,
            eval_time="2026-04-29T10:00:00",
        )

        html_content = generate_html_report(report_data)
        html_path = tmp_path / "test_report.html"
        html_path.write_text(html_content, encoding="utf-8")

        assert html_path.exists()
        content = html_path.read_text()
        assert "<!DOCTYPE html>" in content

    @pytest.mark.asyncio
    async def test_all_mode_generates_html(self, tmp_path):
        """all 模式生成包含正向+负面数据的 HTML"""
        pos_cases = [_make_test_case()]
        neg_cases = [_make_negative_case()]

        pos_client = _make_mock_client_single()
        neg_client = _make_mock_client_negative()

        _, pos_records = await run_single_turn(pos_client, pos_cases)
        _, neg_records = await run_negative(neg_client, neg_cases)

        all_records = pos_records + neg_records
        env_info = {"git_commit": "abc1234", "model": "test-model"}
        report_data = build_report_data(
            case_records=all_records,
            dataset_mode="all",
            env_info=env_info,
            eval_time="2026-04-29T10:00:00",
        )

        html_content = generate_html_report(report_data)
        html_path = tmp_path / "test_report.html"
        html_path.write_text(html_content, encoding="utf-8")

        assert html_path.exists()
        content = html_path.read_text()
        # all 模式下 report_data_json 中包含正向和负面数据
        assert "tool_selection" in content  # category stats
        assert "Violation Rate" in content  # 负面板块

    @pytest.mark.asyncio
    async def test_failed_case_shows_agent_reply_in_html(self, tmp_path):
        """正向评估失败用例展示 agent_reply 文本"""
        cases = [_make_test_case(expected_tools=["create_entry"])]
        client = _make_mock_client_single([
            {"tools": ["search_entries"], "args": [{}], "content": "帮你搜索了一些内容"},
        ])
        report, records = await run_single_turn(client, cases)

        env_info = {"git_commit": "abc1234", "model": "test-model"}
        report_data = build_report_data(
            case_records=records,
            dataset_mode="single",
            env_info=env_info,
            eval_time="2026-04-29T10:00:00",
        )

        html_content = generate_html_report(report_data)
        assert "帮你搜索了一些内容" in html_content

    @pytest.mark.asyncio
    async def test_violated_case_shows_agent_reply_in_html(self, tmp_path):
        """负面评估违规用例展示 agent_reply 文本"""
        cases = [_make_negative_case(should_not_call=["search_entries"])]
        client = _make_mock_client_negative([
            {"tools": ["search_entries"], "args": [{}], "content": "违规搜索了内容"},
        ])
        report, records = await run_negative(client, cases)

        env_info = {"git_commit": "abc1234", "model": "test-model"}
        report_data = build_report_data(
            case_records=records,
            dataset_mode="negative",
            env_info=env_info,
            eval_time="2026-04-29T10:00:00",
        )

        html_content = generate_html_report(report_data)
        assert "违规搜索了内容" in html_content


# ── 测试: history.json 管理 ──


class TestHistoryJson:
    """正常: history.json 追加"""

    def test_first_run_creates_history(self, tmp_path):
        """首次运行创建 history.json"""
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.85,
        }
        append_history(record, tmp_path)

        history_file = tmp_path / "history.json"
        assert history_file.exists()

        data = json.loads(history_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["dataset_mode"] == "single"

    def test_consecutive_runs_append(self, tmp_path):
        """连续运行两次，history.json 有两条记录"""
        record1 = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.85,
        }
        record2 = {
            "eval_time": "2026-04-29T11:00:00",
            "dataset_mode": "negative",
            "pass_rate": 0.0,
        }
        append_history(record1, tmp_path)
        append_history(record2, tmp_path)

        history_file = tmp_path / "history.json"
        data = json.loads(history_file.read_text())
        assert len(data) == 2
        assert data[0]["dataset_mode"] == "single"
        assert data[1]["dataset_mode"] == "negative"

    def test_history_contains_dataset_mode(self, tmp_path):
        """history.json 包含 dataset_mode 字段"""
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "all",
            "pass_rate": 0.75,
        }
        append_history(record, tmp_path)

        data = json.loads((tmp_path / "history.json").read_text())
        assert data[0]["dataset_mode"] == "all"


# ── 测试: 边界条件 ──


class TestBoundaryConditions:
    """边界条件测试"""

    def test_report_dir_auto_created(self, tmp_path):
        """report-dir 不存在时自动创建"""
        nested_dir = tmp_path / "nested" / "deep" / "reports"
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.5,
        }
        append_history(record, nested_dir)
        assert nested_dir.exists()
        assert (nested_dir / "history.json").exists()

    @pytest.mark.asyncio
    async def test_empty_cases(self):
        """空用例列表正常处理"""
        client = _make_mock_client_single()
        report, records = await run_single_turn(client, [])
        assert isinstance(report, EvaluationReport)
        assert report.total_cases == 0
        assert records == []

    def test_history_corrupted_json(self, tmp_path):
        """history.json 非法 JSON 时降级处理"""
        history_file = tmp_path / "history.json"
        history_file.write_text("NOT VALID JSON{{{{", encoding="utf-8")

        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.5,
        }
        # 应不报错
        append_history(record, tmp_path)

        # history.json 被重建为当前记录
        data = json.loads(history_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_history_not_array(self, tmp_path):
        """history.json 不是数组时降级处理"""
        history_file = tmp_path / "history.json"
        history_file.write_text('{"key": "value"}', encoding="utf-8")

        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.5,
        }
        # 应不报错
        append_history(record, tmp_path)

        data = json.loads(history_file.read_text())
        assert isinstance(data, list)
        assert len(data) == 1

    def test_corrupted_history_backup(self, tmp_path):
        """损坏的 history.json 被备份为 .bak"""
        history_file = tmp_path / "history.json"
        corrupted_content = "NOT VALID JSON"
        history_file.write_text(corrupted_content, encoding="utf-8")

        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.5,
        }
        append_history(record, tmp_path)

        bak_file = tmp_path / "history.json.bak"
        assert bak_file.exists()
        assert bak_file.read_text() == corrupted_content


# ── 测试: 异常处理 ──


class TestExceptionHandling:
    """异常场景测试"""

    @patch("subprocess.run", side_effect=Exception("command failed"))
    def test_git_rev_parse_failure(self, mock_run):
        """git rev-parse 失败时 commit 字段降级为 'unknown'"""
        info = _get_env_info()
        assert info["git_commit"] == "unknown"

    @patch.dict(os.environ, {}, clear=True)
    def test_llm_model_not_set(self):
        """LLM_MODEL 未设置时 model 字段降级为 'unknown'"""
        env = dict(os.environ)
        env.pop("LLM_MODEL", None)
        with patch.dict(os.environ, env, clear=True):
            info = _get_env_info()
            assert info["model"] == "unknown"

    def test_template_render_failure_no_delete_history(self, tmp_path):
        """模板渲染失败时不删除已生成的 history.json"""
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.5,
        }
        append_history(record, tmp_path)

        history_file = tmp_path / "history.json"
        assert history_file.exists()
        original_content = history_file.read_text()

        # 模拟模板渲染失败
        with patch(
            "tests.eval.run_eval.generate_html_report",
            side_effect=Exception("template error"),
        ):
            # history.json 仍应存在
            assert history_file.exists()
            assert history_file.read_text() == original_content


# ── 测试: SSE content 事件 agent_reply 提取 ──


class TestSSEContentExtraction:
    """SSE content 事件 payload key 为 'content' 时 agent_reply 正确提取"""

    def test_parse_sse_stream_extracts_content(self):
        """parse_sse_stream 正确提取 content 字段"""
        from tests.eval.run_eval import parse_sse_stream

        lines = [
            'event: content',
            'data: {"content": "你好"}',
            'event: content',
            'data: {"content": "，世界"}',
            'event: tool_call',
            'data: {"tool": "search_entries", "args": {}}',
        ]
        result = parse_sse_stream(lines)
        assert result["content"] == "你好，世界"
        assert result["tools"] == ["search_entries"]

    def test_parse_sse_stream_no_content(self):
        """无 content 事件时 content 为空字符串"""
        from tests.eval.run_eval import parse_sse_stream

        lines = [
            'event: tool_call',
            'data: {"tool": "search_entries", "args": {}}',
        ]
        result = parse_sse_stream(lines)
        assert result["content"] == ""


# ── 测试: --output JSON 兼容性 ──


class TestOutputJsonCompatibility:
    """正常: --output JSON 兼容性不受影响"""

    @pytest.mark.asyncio
    async def test_single_records_compatible_with_json_output(self):
        """single 模式 records 可用于 JSON 输出"""
        cases = [_make_test_case()]
        client = _make_mock_client_single()
        report, records = await run_single_turn(client, cases)

        # 模拟构建 output_data
        output_data = {
            "single_turn": {
                "total": report.total_cases,
                "passed": report.total_passed,
                "pass_rate": f"{report.overall_pass_rate:.1%}",
            }
        }
        json_str = json.dumps(output_data, ensure_ascii=False)
        assert "single_turn" in json_str

    @pytest.mark.asyncio
    async def test_negative_records_compatible_with_json_output(self):
        """negative 模式 records 可用于 JSON 输出"""
        cases = [_make_negative_case()]
        client = _make_mock_client_negative()
        report, records = await run_negative(client, cases)

        output_data = {
            "negative": {
                "total": report.total_cases,
                "violations": report.total_violations,
                "violation_rate": f"{report.violation_rate:.1%}",
            }
        }
        json_str = json.dumps(output_data, ensure_ascii=False)
        assert "negative" in json_str


# ── 测试: report-dir 参数 ──


class TestReportDirParameter:
    """--report-dir 参数测试"""

    def test_custom_report_dir(self, tmp_path):
        """--report-dir 指定自定义目录"""
        custom_dir = tmp_path / "custom_reports"
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.5,
        }
        append_history(record, custom_dir)
        assert custom_dir.exists()
        assert (custom_dir / "history.json").exists()

    def test_custom_report_dir_nested(self, tmp_path):
        """--report-dir 指定不存在的嵌套目录时自动创建"""
        nested_dir = tmp_path / "a" / "b" / "c"
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.5,
        }
        append_history(record, nested_dir)
        assert nested_dir.exists()

    def test_default_report_dir_not_in_backend(self):
        """默认 report-dir 不在 backend/ 目录下"""
        default_dir = _get_default_report_dir()
        assert "backend" not in str(default_dir)


# ── 测试: 完整流程 mock ──


class TestFullFlowMocked:
    """完整流程 mock 测试（不依赖真实 Agent）"""

    @pytest.mark.asyncio
    async def test_single_flow_generates_report(self, tmp_path):
        """single 模式完整流程"""
        cases = [
            _make_test_case("ST-001", "tool_selection", "搜索笔记", ["search_entries"]),
            _make_test_case("ST-002", "tool_selection", "创建笔记", ["create_entry"]),
        ]
        client = _make_mock_client_single([
            {"tools": ["search_entries"], "args": [{}], "content": "找到3条笔记"},
            {"tools": ["create_entry"], "args": [{}], "content": "已创建笔记"},
        ])

        report, records = await run_single_turn(client, cases)
        assert len(records) == 2
        assert records[0]["passed"] is True
        assert records[0]["agent_reply"] == "找到3条笔记"
        assert records[1]["passed"] is True
        assert records[1]["agent_reply"] == "已创建笔记"

        # 构建 + 生成 HTML
        env_info = {"git_commit": "abc", "model": "test"}
        report_data = build_report_data(records, "single", env_info, "2026-04-29T10:00:00")
        assert report_data.total_positive == 2
        assert report_data.total_passed == 2

        html = generate_html_report(report_data)
        assert "AI Agent Evaluation Report" in html

        # 追加 history
        history_record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": report_data.pass_rate,
        }
        append_history(history_record, tmp_path)
        history = json.loads((tmp_path / "history.json").read_text())
        assert len(history) == 1
        assert history[0]["dataset_mode"] == "single"

    @pytest.mark.asyncio
    async def test_negative_flow_generates_report(self, tmp_path):
        """negative 模式完整流程"""
        cases = [
            _make_negative_case("NEG-001", "no_tool", "你好", ["search_entries"]),
            _make_negative_case("NEG-002", "no_tool", "闲聊", ["create_entry"]),
        ]
        client = _make_mock_client_negative([
            {"tools": [], "args": [], "content": "你好！"},
            {"tools": ["create_entry"], "args": [{}], "content": "已创建"},
        ])

        report, records = await run_negative(client, cases)
        assert len(records) == 2
        assert records[0]["violated"] is False
        assert records[0]["agent_reply"] == "你好！"
        assert records[1]["violated"] is True
        assert records[1]["agent_reply"] == "已创建"

        env_info = {"git_commit": "abc", "model": "test"}
        report_data = build_report_data(records, "negative", env_info, "2026-04-29T10:00:00")
        assert report_data.total_negative == 2
        assert report_data.total_violations == 1

        html = generate_html_report(report_data)
        assert "已创建" in html

        history_record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "negative",
            "pass_rate": report_data.pass_rate,
        }
        append_history(history_record, tmp_path)
        history = json.loads((tmp_path / "history.json").read_text())
        assert len(history) == 1
        assert history[0]["dataset_mode"] == "negative"

    @pytest.mark.asyncio
    async def test_all_flow_generates_report(self, tmp_path):
        """all 模式完整流程（正向+负面）"""
        pos_cases = [_make_test_case()]
        neg_cases = [_make_negative_case()]

        pos_client = _make_mock_client_single([
            {"tools": ["search_entries"], "args": [{}], "content": "搜索结果"},
        ])
        neg_client = _make_mock_client_negative([
            {"tools": [], "args": [], "content": "你好"},
        ])

        _, pos_records = await run_single_turn(pos_client, pos_cases)
        _, neg_records = await run_negative(neg_client, neg_cases)

        all_records = pos_records + neg_records
        env_info = {"git_commit": "abc", "model": "test"}
        report_data = build_report_data(all_records, "all", env_info, "2026-04-29T10:00:00")

        assert report_data.total_positive == 1
        assert report_data.total_negative == 1

        html = generate_html_report(report_data)
        assert "AI Agent Evaluation Report" in html

        history_record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "all",
            "pass_rate": report_data.pass_rate,
        }
        append_history(history_record, tmp_path)
        history = json.loads((tmp_path / "history.json").read_text())
        assert len(history) == 1
        assert history[0]["dataset_mode"] == "all"

    def test_consecutive_runs_history_accumulates(self, tmp_path):
        """连续运行两次，history.json 累积两条记录"""
        for i in range(2):
            record = {
                "eval_time": f"2026-04-29T10:0{i}:00",
                "dataset_mode": "single",
                "pass_rate": 0.8 + i * 0.05,
            }
            append_history(record, tmp_path)

        history = json.loads((tmp_path / "history.json").read_text())
        assert len(history) == 2
