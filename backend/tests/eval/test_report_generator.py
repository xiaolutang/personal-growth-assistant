"""B193 报告数据模型 + 生成器 测试

覆盖:
- escape_for_html / escape_for_js 转义辅助
- EvalReportData 数据模型
- build_report_data 聚合正向/负面用例 + dataset_mode 分支 + schema 验证
- load_history / append_history history.json 管理
- generate_html_report HTML 渲染
- 边界：HTML 标签注入、</script> 注入、history 损坏恢复
"""

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.eval.report_generator import (
    POSITIVE_CASE_REQUIRED_KEYS,
    NEGATIVE_CASE_REQUIRED_KEYS,
    HISTORY_ROW_REQUIRED_KEYS,
    EvalReportData,
    append_history,
    build_report_data,
    escape_for_html,
    escape_for_js,
    generate_html_report,
    load_history,
    validate_history_record,
)


# ── Fixtures ──


@pytest.fixture
def history_dir(tmp_path: Path) -> Path:
    """提供临时目录作为 data/eval_reports/"""
    d = tmp_path / "eval_reports"
    d.mkdir()
    return d


def _make_positive_records() -> List[Dict[str, Any]]:
    """构造正向用例记录列表"""
    return [
        {
            "input": "帮我记录一条灵感",
            "expected_tools": ["create_entry"],
            "actual_tools": ["create_entry"],
            "agent_reply": "已为你记录灵感",
            "passed": True,
            "category": "tool_selection",
            "elapsed_seconds": 1.2,
        },
        {
            "input": "今天的学习心得",
            "expected_tools": ["create_entry"],
            "actual_tools": [],
            "agent_reply": "好的",
            "passed": False,
            "category": "tool_selection",
            "elapsed_seconds": 0.8,
        },
    ]


def _make_negative_records() -> List[Dict[str, Any]]:
    """构造负面用例记录列表"""
    return [
        {
            "input": "你好呀",
            "should_not_call": ["create_entry", "search_entries"],
            "actual_tools": ["create_entry"],
            "agent_reply": "已记录",
            "violated": True,
            "violated_tools": ["create_entry"],
            "category": "no_tool",
            "elapsed_seconds": 0.5,
        },
        {
            "input": "今天天气不错",
            "should_not_call": ["create_entry"],
            "actual_tools": [],
            "agent_reply": "是的，天气很好",
            "violated": False,
            "violated_tools": [],
            "category": "no_tool",
            "elapsed_seconds": 0.3,
        },
    ]


def _default_env_info() -> Dict[str, Any]:
    return {
        "python_version": "3.12.0",
        "os": "darwin",
        "model": "gpt-4o-mini",
    }


# ── escape_for_html ──


class TestEscapeForHtml:
    def test_escapes_angle_brackets(self):
        assert escape_for_html("<div>") == "&lt;div&gt;"

    def test_escapes_ampersand(self):
        assert escape_for_html("a & b") == "a &amp; b"

    def test_escapes_double_quote(self):
        assert escape_for_html('a "b" c') == "a &quot;b&quot; c"

    def test_escapes_single_quote(self):
        result = escape_for_html("it's")
        assert "'" not in result
        assert "&" in result

    def test_combined(self):
        result = escape_for_html("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result
        assert "script" in result  # 文本保留


# ── escape_for_js ──


class TestEscapeForJs:
    def test_quotes_serialized(self):
        result = escape_for_js('he said "hello"')
        parsed = json.loads(result)
        assert parsed == 'he said "hello"'

    def test_closing_script_tag(self):
        result = escape_for_js("</script><script>alert(1)</script>")
        # 结果应该是合法 JSON 字符串
        parsed = json.loads(result)
        assert "</script>" in parsed
        # 原始序列化结果中不应包含裸露的 </script>（会被转义为 <\/script>）
        assert "</script>" not in result
        assert "<\\/script>" in result

    def test_normal_string(self):
        result = escape_for_js("hello world")
        parsed = json.loads(result)
        assert parsed == "hello world"

    def test_newlines_and_backslash(self):
        result = escape_for_js("line1\nline2\\path")
        parsed = json.loads(result)
        assert "line1" in parsed
        assert "line2" in parsed


# ── EvalReportData 数据模型 ──


class TestEvalReportData:
    def test_dataclass_fields(self):
        data = EvalReportData(
            eval_time="2026-04-29T10:00:00",
            dataset_mode="all",
            pass_rate=0.85,
            total_positive=10,
            total_passed=8,
            total_negative=5,
            total_violations=1,
            violation_rate=0.2,
        )
        assert data.dataset_mode == "all"
        assert data.pass_rate == 0.85
        assert data.total_positive == 10
        assert data.total_negative == 5
        assert data.violation_rate == 0.2

    def test_all_required_fields(self):
        """确保数据模型包含所有必要字段"""
        import dataclasses
        fields = {f.name for f in dataclasses.fields(EvalReportData)}
        expected = {
            "eval_time", "dataset_mode", "pass_rate", "total_positive",
            "total_passed", "category_stats", "failed_cases",
            "total_negative", "total_violations", "violation_rate",
            "negative_violations", "efficiency", "env_info",
        }
        assert expected.issubset(fields)

    def test_schema_constants_defined(self):
        """Schema 常量包含正确的必填键"""
        assert "input" in POSITIVE_CASE_REQUIRED_KEYS
        assert "expected_tools" in POSITIVE_CASE_REQUIRED_KEYS
        assert "passed" in POSITIVE_CASE_REQUIRED_KEYS
        assert "should_not_call" in NEGATIVE_CASE_REQUIRED_KEYS
        assert "violated" in NEGATIVE_CASE_REQUIRED_KEYS
        assert "violated_tools" in NEGATIVE_CASE_REQUIRED_KEYS
        assert "eval_time" in HISTORY_ROW_REQUIRED_KEYS
        assert "dataset_mode" in HISTORY_ROW_REQUIRED_KEYS


# ── build_report_data ──


class TestBuildReportData:
    def test_positive_cases_schema(self):
        """正向用例聚合：schema 含 expected_tools/passed"""
        records = _make_positive_records()
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())

        assert report.dataset_mode == "single"
        assert report.pass_rate == 0.5  # 1 passed / 2 total
        assert report.total_positive == 2
        assert report.total_passed == 1
        assert len(report.failed_cases) == 1
        fc = report.failed_cases[0]
        assert "expected_tools" in fc
        assert "passed" in fc
        assert fc["passed"] is False

    def test_negative_cases_schema(self):
        """负面用例聚合：schema 含 should_not_call/violated/violated_tools"""
        records = _make_negative_records()
        report = build_report_data(records, dataset_mode="negative", env_info=_default_env_info())

        assert report.dataset_mode == "negative"
        assert report.total_negative == 2
        assert report.total_violations == 1
        assert report.violation_rate == 0.5  # 1 violated / 2 total
        assert len(report.negative_violations) == 1
        nv = report.negative_violations[0]
        assert "should_not_call" in nv
        assert "violated" in nv
        assert "violated_tools" in nv

    def test_dataset_mode_single_positive_filled_negative_empty(self):
        """dataset_mode='single': 正向板块填充，负面板块空态"""
        records = _make_positive_records()
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())

        assert report.total_positive == 2
        assert report.total_negative == 0
        assert report.total_violations == 0
        assert report.violation_rate == 0.0
        assert report.negative_violations == []
        assert report.dataset_mode == "single"

    def test_dataset_mode_negative_negative_filled_positive_empty(self):
        """dataset_mode='negative': 负面板块填充，正向板块空态"""
        records = _make_negative_records()
        report = build_report_data(records, dataset_mode="negative", env_info=_default_env_info())

        assert report.total_negative == 2
        assert report.total_violations == 1
        assert report.violation_rate == 0.5
        assert report.negative_violations  # 负面有数据
        assert report.total_positive == 0
        assert report.pass_rate == 0.0
        assert report.failed_cases == []

    def test_dataset_mode_all_both_filled(self):
        """dataset_mode='all': 全板块填充"""
        records = _make_positive_records() + _make_negative_records()
        report = build_report_data(records, dataset_mode="all", env_info=_default_env_info())

        assert report.dataset_mode == "all"
        assert report.total_positive == 2
        assert report.total_negative == 2
        assert report.category_stats
        assert report.negative_violations

    def test_efficiency_metrics(self):
        """效率指标包含在报告中"""
        records = _make_positive_records()
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())
        assert "total_elapsed" in report.efficiency
        assert "avg_elapsed" in report.efficiency
        assert "median_elapsed" in report.efficiency
        assert "total_cases" in report.efficiency
        assert report.efficiency["total_cases"] == 2

    def test_median_elapsed_correct(self):
        """中位数延迟计算正确"""
        records = [
            {
                "input": "a",
                "expected_tools": ["x"],
                "actual_tools": ["x"],
                "agent_reply": "ok",
                "passed": True,
                "category": "test",
                "elapsed_seconds": 1.0,
            },
            {
                "input": "b",
                "expected_tools": ["x"],
                "actual_tools": [],
                "agent_reply": "ok",
                "passed": False,
                "category": "test",
                "elapsed_seconds": 3.0,
            },
            {
                "input": "c",
                "expected_tools": ["x"],
                "actual_tools": ["x"],
                "agent_reply": "ok",
                "passed": True,
                "category": "test",
                "elapsed_seconds": 5.0,
            },
        ]
        report = build_report_data(records, dataset_mode="single", env_info={})
        assert report.efficiency["median_elapsed"] == 3.0

    def test_env_info_preserved(self):
        records = _make_positive_records()
        env = _default_env_info()
        report = build_report_data(records, dataset_mode="single", env_info=env)
        assert report.env_info == env

    def test_eval_time_injectable(self):
        """eval_time 可由调用方注入，不强制使用当前时间"""
        records = _make_positive_records()
        report = build_report_data(
            records, dataset_mode="single",
            env_info={}, eval_time="2026-01-15T08:30:00",
        )
        assert report.eval_time == "2026-01-15T08:30:00"

    def test_eval_time_default_is_now(self):
        """不传 eval_time 时使用当前时间"""
        records = _make_positive_records()
        report = build_report_data(records, dataset_mode="single", env_info={})
        assert report.eval_time  # 非空
        assert "202" in report.eval_time  # 大致时间格式检查

    def test_missing_positive_keys_raises(self):
        """正向用例缺少必填字段时抛出 ValueError"""
        bad_record = {
            "input": "test",
            "expected_tools": ["x"],
            # 缺少 actual_tools, agent_reply, passed, category, elapsed_seconds
        }
        with pytest.raises(ValueError, match="missing required keys"):
            build_report_data([bad_record], dataset_mode="single", env_info={})

    def test_missing_negative_keys_raises(self):
        """负面用例缺少必填字段时抛出 ValueError"""
        bad_record = {
            "input": "test",
            "violated": True,
            # 缺少 should_not_call, actual_tools, agent_reply, violated_tools, category, elapsed_seconds
        }
        with pytest.raises(ValueError, match="missing required keys"):
            build_report_data([bad_record], dataset_mode="negative", env_info={})


# ── generate_html_report ──


class TestGenerateHtmlReport:
    def test_returns_non_empty_html(self):
        """接收合法数据返回非空 HTML 字符串"""
        records = _make_positive_records()
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())
        html = generate_html_report(report)
        assert isinstance(html, str)
        assert len(html) > 0
        assert "<html" in html.lower() or "<!doctype" in html.lower()

    def test_with_template_path(self, tmp_path: Path):
        """函数签名接受模板路径"""
        template = tmp_path / "report_template.html"
        template.write_text("<html><body>$eval_time</body></html>")

        records = _make_positive_records()
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())
        html = generate_html_report(report, template_path=str(template))
        assert isinstance(html, str)
        assert len(html) > 0

    def test_html_injection_escaped(self):
        """input 含 HTML 标签时渲染结果中标签被转义不破坏 DOM"""
        records = [
            {
                "input": "<img src=x onerror=alert(1)>",
                "expected_tools": ["create_entry"],
                "actual_tools": ["create_entry"],
                "agent_reply": "ok",
                "passed": True,
                "category": "boundary",
                "elapsed_seconds": 0.1,
            }
        ]
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())
        html = generate_html_report(report)
        # HTML 标签应被转义
        assert "<img" not in html or "&lt;img" in html

    def test_script_tag_injection_escaped(self):
        """agent_reply 含 </script> 时渲染结果不提前关闭 script 标签"""
        records = [
            {
                "input": "test",
                "expected_tools": ["create_entry"],
                "actual_tools": ["create_entry"],
                "agent_reply": "</script><script>alert(1)</script>",
                "passed": False,  # 让它出现在 failed_cases 中
                "category": "boundary",
                "elapsed_seconds": 0.1,
            }
        ]
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())
        html = generate_html_report(report)
        assert isinstance(html, str)
        assert len(html) > 0
        # 关键断言：HTML 中 <script> 块内不应包含裸露的 </script>
        # （那会导致 script 块提前关闭，引发 XSS）
        script_blocks = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
        for block in script_blocks:
            assert "</script>" not in block, (
                "Found raw </script> inside <script> block - XSS vulnerability"
            )

    def test_negative_mode_shows_violation_rate(self):
        """负面模式报告显示违规率而非通过率"""
        records = _make_negative_records()
        report = build_report_data(records, dataset_mode="negative", env_info=_default_env_info())
        html = generate_html_report(report)
        assert "50.0%" in html  # violation_rate = 1/2 = 50%
        assert "Violation Rate" in html

    def test_report_data_json_contains_negative_fields(self):
        """嵌入的 JSON 数据包含负面指标字段"""
        records = _make_negative_records()
        report = build_report_data(records, dataset_mode="negative", env_info=_default_env_info())
        html = generate_html_report(report)
        # 从 script 块中提取 JSON
        script_blocks = re.findall(r"<script>\s*const reportData = (.*?);\s*</script>", html, re.DOTALL)
        assert len(script_blocks) == 1
        # 解析时需要将转义还原
        json_str = script_blocks[0].replace("<\\/script", "</script")
        data = json.loads(json_str)
        assert "total_negative" in data
        assert data["total_negative"] == 2
        assert "violation_rate" in data
        assert data["violation_rate"] == 0.5


# ── load_history / append_history ──


class TestLoadHistory:
    def test_load_multiple_records(self, history_dir: Path):
        """读取多条历史记录"""
        history = [
            {"eval_time": "2026-04-28T10:00:00", "dataset_mode": "single", "pass_rate": 0.8},
            {"eval_time": "2026-04-29T10:00:00", "dataset_mode": "all", "pass_rate": 0.9},
        ]
        history_file = history_dir / "history.json"
        history_file.write_text(json.dumps(history), encoding="utf-8")

        result = load_history(history_dir)
        assert len(result) == 2
        assert result[0]["dataset_mode"] == "single"
        assert result[1]["dataset_mode"] == "all"

    def test_empty_array_returns_empty_list(self, history_dir: Path):
        """history.json 为空数组时返回空列表"""
        history_file = history_dir / "history.json"
        history_file.write_text("[]", encoding="utf-8")

        result = load_history(history_dir)
        assert result == []

    def test_invalid_json_returns_empty_list_with_warning(self, history_dir: Path):
        """非法 JSON 时返回空列表 + warning"""
        history_file = history_dir / "history.json"
        history_file.write_text("{invalid json", encoding="utf-8")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = load_history(history_dir)
            assert result == []
            assert len(w) >= 1

    def test_non_array_returns_empty_list_with_warning(self, history_dir: Path):
        """非数组时返回空列表 + warning"""
        history_file = history_dir / "history.json"
        history_file.write_text('{"key": "value"}', encoding="utf-8")

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = load_history(history_dir)
            assert result == []
            assert len(w) >= 1

    def test_nonexistent_returns_empty_list(self, history_dir: Path):
        """history.json 不存在时返回空列表"""
        result = load_history(history_dir)
        assert result == []


class TestAppendHistory:
    def test_append_to_empty_history(self, history_dir: Path):
        """追加记录到空 history.json"""
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.85,
        }
        append_history(record, history_dir)

        result = load_history(history_dir)
        assert len(result) == 1
        assert result[0]["pass_rate"] == 0.85

    def test_append_to_existing_history(self, history_dir: Path):
        """追加到已有 history.json（多条记录）"""
        existing = [
            {"eval_time": "2026-04-28T10:00:00", "dataset_mode": "single", "pass_rate": 0.8},
        ]
        history_file = history_dir / "history.json"
        history_file.write_text(json.dumps(existing), encoding="utf-8")

        new_record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "all",
            "pass_rate": 0.9,
        }
        append_history(new_record, history_dir)

        result = load_history(history_dir)
        assert len(result) == 2
        assert result[0]["pass_rate"] == 0.8
        assert result[1]["pass_rate"] == 0.9

    def test_creates_directory_if_not_exists(self, tmp_path: Path):
        """首次运行时自动创建 data/eval_reports/ 目录"""
        new_dir = tmp_path / "new_eval_reports"
        assert not new_dir.exists()

        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.85,
        }
        append_history(record, new_dir)

        assert new_dir.exists()
        result = load_history(new_dir)
        assert len(result) == 1

    def test_history_json_not_exists_auto_creates(self, tmp_path: Path):
        """history.json 不存在时 append_history 自动创建"""
        d = tmp_path / "eval_reports"
        d.mkdir()
        assert not (d / "history.json").exists()

        record = {"eval_time": "2026-04-29", "dataset_mode": "single", "pass_rate": 0.5}
        append_history(record, d)

        assert (d / "history.json").exists()
        data = json.loads((d / "history.json").read_text(encoding="utf-8"))
        assert len(data) == 1

    def test_corrupted_json_backup_and_rebuild(self, history_dir: Path):
        """损坏 history.json 恢复策略：备份旧文件并重建"""
        history_file = history_dir / "history.json"
        history_file.write_text("{bad content", encoding="utf-8")

        new_record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.85,
        }
        append_history(new_record, history_dir)

        # 旧文件应被备份
        assert (history_dir / "history.json.bak").exists()
        # 新 history.json 只包含当前记录
        result = load_history(history_dir)
        assert len(result) == 1
        assert result[0]["pass_rate"] == 0.85

    def test_non_array_json_backup_and_rebuild(self, history_dir: Path):
        """history.json 不是数组时备份并重建"""
        history_file = history_dir / "history.json"
        history_file.write_text('{"key": "value"}', encoding="utf-8")

        new_record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "negative",
            "pass_rate": 0.0,
        }
        append_history(new_record, history_dir)

        assert (history_dir / "history.json.bak").exists()
        result = load_history(history_dir)
        assert len(result) == 1

    def test_does_not_overwrite_valid_history(self, history_dir: Path):
        """追加时不覆盖已有数据"""
        existing = [
            {"eval_time": "2026-04-27", "dataset_mode": "single", "pass_rate": 0.7},
            {"eval_time": "2026-04-28", "dataset_mode": "single", "pass_rate": 0.8},
        ]
        history_file = history_dir / "history.json"
        history_file.write_text(json.dumps(existing), encoding="utf-8")

        append_history(
            {"eval_time": "2026-04-29", "dataset_mode": "all", "pass_rate": 0.9},
            history_dir,
        )

        result = load_history(history_dir)
        assert len(result) == 3

    def test_append_to_valid_empty_array_no_backup(self, history_dir: Path):
        """追加到合法空数组 history.json 不应创建备份"""
        history_file = history_dir / "history.json"
        history_file.write_text("[]", encoding="utf-8")

        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "single",
            "pass_rate": 0.85,
        }
        append_history(record, history_dir)

        # 不应创建备份文件（合法空数组不是损坏）
        assert not (history_dir / "history.json.bak").exists()
        # 新记录应正常追加
        result = load_history(history_dir)
        assert len(result) == 1
        assert result[0]["pass_rate"] == 0.85

    def test_append_invalid_record_raises(self, history_dir: Path):
        """缺少必填字段的记录应抛出 ValueError"""
        bad_record = {"eval_time": "2026-04-29"}  # 缺少 dataset_mode 和 pass_rate
        with pytest.raises(ValueError, match="missing required keys"):
            append_history(bad_record, history_dir)

    def test_history_full_schema_roundtrip(self, history_dir: Path):
        """完整 history 记录 schema 往返测试"""
        record = {
            "eval_time": "2026-04-29T10:00:00",
            "dataset_mode": "all",
            "pass_rate": 0.85,
            "total_positive": 68,
            "total_passed": 58,
            "total_negative": 24,
            "total_violations": 2,
            "violation_rate": 0.083,
        }
        append_history(record, history_dir)

        result = load_history(history_dir)
        assert len(result) == 1
        assert result[0]["dataset_mode"] == "all"
        assert result[0]["total_positive"] == 68
        assert result[0]["total_negative"] == 24
        assert result[0]["violation_rate"] == 0.083
