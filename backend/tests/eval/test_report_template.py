"""B194 HTML 报告模板测试

覆盖:
- 模板渲染正常数据不抛异常
- 生成的 HTML 包含所有 7 个板块标题
- 失败用例区域展示期望 vs 实际对比
- Chart.js 数据正确嵌入 script 标签 (JSON 格式验证)
- 离线时 HTML 可浏览器打开 (文字内容完整)
- 边界: 全部通过 / 无历史数据 / 无负面违规 / single 模式 / negative 模式
- 异常: 模板文件不存在时 generate_html_report 抛出明确错误
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.eval.report_generator import (
    EvalReportData,
    build_report_data,
    generate_html_report,
)


# ── Fixtures & Helpers ──


def _make_positive_records() -> List[Dict[str, Any]]:
    """构造正向用例记录列表 (1 pass + 1 fail)"""
    return [
        {
            "input": "help me record an idea",
            "expected_tools": ["create_entry"],
            "actual_tools": ["create_entry"],
            "agent_reply": "Idea recorded successfully",
            "passed": True,
            "category": "tool_selection",
            "elapsed_seconds": 1.2,
        },
        {
            "input": "today's learning notes",
            "expected_tools": ["create_entry"],
            "actual_tools": [],
            "agent_reply": "OK, noted",
            "passed": False,
            "category": "tool_selection",
            "elapsed_seconds": 0.8,
        },
        {
            "input": "search my notes",
            "expected_tools": ["search_entries"],
            "actual_tools": ["search_entries"],
            "agent_reply": "Here are the results",
            "passed": True,
            "category": "tool_selection",
            "elapsed_seconds": 1.5,
        },
    ]


def _make_all_pass_positive_records() -> List[Dict[str, Any]]:
    """全部通过的正向用例"""
    return [
        {
            "input": "record idea",
            "expected_tools": ["create_entry"],
            "actual_tools": ["create_entry"],
            "agent_reply": "Done",
            "passed": True,
            "category": "tool_selection",
            "elapsed_seconds": 0.9,
        },
    ]


def _make_negative_records() -> List[Dict[str, Any]]:
    """构造负面用例记录列表"""
    return [
        {
            "input": "Hello there",
            "should_not_call": ["create_entry", "search_entries"],
            "actual_tools": ["create_entry"],
            "agent_reply": "Recorded",
            "violated": True,
            "violated_tools": ["create_entry"],
            "category": "no_tool",
            "elapsed_seconds": 0.5,
        },
        {
            "input": "Nice weather today",
            "should_not_call": ["create_entry"],
            "actual_tools": [],
            "agent_reply": "Yes, great weather",
            "violated": False,
            "violated_tools": [],
            "category": "no_tool",
            "elapsed_seconds": 0.3,
        },
    ]


def _make_no_violation_negative_records() -> List[Dict[str, Any]]:
    """全部通过的负面用例（无违规）"""
    return [
        {
            "input": "Hello",
            "should_not_call": ["create_entry"],
            "actual_tools": [],
            "agent_reply": "Hi there!",
            "violated": False,
            "violated_tools": [],
            "category": "no_tool",
            "elapsed_seconds": 0.2,
        },
    ]


def _default_env_info() -> Dict[str, Any]:
    return {
        "python_version": "3.12.0",
        "os": "darwin",
        "model": "gpt-4o-mini",
        "commit": "abc123def",
    }


def _make_history() -> List[Dict[str, Any]]:
    """构造历史记录"""
    return [
        {"eval_time": "2026-04-27T10:00:00", "dataset_mode": "single", "pass_rate": 0.70},
        {"eval_time": "2026-04-28T10:00:00", "dataset_mode": "single", "pass_rate": 0.80},
    ]


def _render_report(
    records: List[Dict[str, Any]],
    dataset_mode: str = "single",
    env_info: Optional[Dict[str, Any]] = None,
    history_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """辅助函数: 从 records 构建数据并渲染 HTML"""
    report = build_report_data(
        records,
        dataset_mode=dataset_mode,
        env_info=env_info or _default_env_info(),
    )
    return generate_html_report(report, history_data=history_data)


# ── Normal Tests ──


class TestTemplateRenderingNormal:
    """正常: 模板渲染合法数据不抛异常"""

    def test_renders_without_exception(self):
        """混合用例 (positive + negative) 渲染不抛异常"""
        records = _make_positive_records() + _make_negative_records()
        html = _render_report(records, dataset_mode="all")
        assert isinstance(html, str)
        assert len(html) > 0

    def test_renders_single_mode(self):
        """single 模式渲染不抛异常"""
        html = _render_report(_make_positive_records(), dataset_mode="single")
        assert isinstance(html, str)
        assert len(html) > 0

    def test_renders_negative_mode(self):
        """negative 模式渲染不抛异常"""
        html = _render_report(_make_negative_records(), dataset_mode="negative")
        assert isinstance(html, str)
        assert len(html) > 0

    def test_with_history_data(self):
        """带历史数据渲染不抛异常"""
        html = _render_report(
            _make_positive_records(),
            history_data=_make_history(),
        )
        assert isinstance(html, str)
        assert len(html) > 0


class TestAllSevenSections:
    """正常: 生成的 HTML 包含所有 7 个板块的标题"""

    def test_contains_all_section_titles(self):
        """HTML 包含 7 个板块标题"""
        records = _make_positive_records() + _make_negative_records()
        html = _render_report(records, dataset_mode="all", history_data=_make_history())

        expected_titles = [
            "Assessment Methodology",     # Section 1
            "Overview Dashboard",          # Section 2
            "Category Statistics",         # Section 3
            "Failed Cases Detail",         # Section 4
            "Negative Violations",         # Section 5
            "History Trend",               # Section 6
            "Efficiency Metrics",          # Section 7
        ]
        for title in expected_titles:
            assert title in html, f"Missing section title: {title}"

    def test_section_ids_present(self):
        """每个板块有对应 id 属性"""
        records = _make_positive_records()
        html = _render_report(records)

        expected_ids = [
            "section-methodology",
            "section-overview",
            "section-categories",
            "section-failed-cases",
            "section-negative-violations",
            "section-history-trend",
            "section-efficiency",
        ]
        for sid in expected_ids:
            assert sid in html, f"Missing section id: {sid}"


class TestFailedCasesComparison:
    """正常: 失败用例区域展示期望 vs 实际对比"""

    def test_shows_expected_vs_actual(self):
        """失败用例 details 包含 Expected Tools 和 Actual Tools 字段"""
        records = _make_positive_records()  # 1 fail
        html = _render_report(records)

        # 失败用例应展示 Expected 和 Actual 对比
        assert "\u671F\u671B\u5DE5\u5177" in html
        assert "\u5B9E\u9645\u5DE5\u5177" in html
        # 失败的输入应出现
        assert "today's learning notes" in html

    def test_failed_case_collapsible(self):
        """失败用例使用 details/summary 可展开收起"""
        records = _make_positive_records()
        html = _render_report(records)

        assert "<details>" in html
        assert "<summary>" in html
        assert "\u5931\u8D25" in html


class TestChartJsDataEmbedding:
    """正常: Chart.js 数据正确嵌入 script 标签"""

    def test_report_data_json_valid(self):
        """嵌入的 JSON 数据格式合法"""
        records = _make_positive_records()
        html = _render_report(records, history_data=_make_history())

        # 提取 var RD = ... 中的 JSON
        match = re.search(r"var RD = (.*?);\s*\n", html, re.DOTALL)
        assert match is not None, "Could not find 'var RD = ...' in HTML"

        # 还原转义后解析 JSON
        json_str = match.group(1).replace("<\\/script", "</script")
        data = json.loads(json_str)

        assert "eval_time" in data
        assert "dataset_mode" in data
        assert "pass_rate" in data
        assert "category_stats" in data
        assert "failed_cases" in data
        assert "efficiency" in data
        assert "history" in data
        assert data["total_positive"] == 3
        assert data["total_passed"] == 2
        assert len(data["history"]) == 2

    def test_chart_js_cdn_present(self):
        """HTML 包含 Chart.js CDN 引用"""
        html = _render_report(_make_positive_records())
        assert "chart.js" in html
        assert "cdn.jsdelivr.net" in html

    def test_chart_canvas_elements_present(self):
        """HTML 包含 Chart.js 所需的 canvas 元素"""
        html = _render_report(_make_positive_records(), history_data=_make_history())
        assert 'id="overviewChart"' in html
        assert 'id="categoryChart"' in html
        assert 'id="trendChart"' in html

    def test_no_raw_script_close_in_json(self):
        """JSON 数据中不含裸露的 </script>"""
        records = [
            {
                "input": "test",
                "expected_tools": ["x"],
                "actual_tools": ["x"],
                "agent_reply": "</script><script>alert(1)</script>",
                "passed": True,
                "category": "test",
                "elapsed_seconds": 0.1,
            },
        ]
        html = _render_report(records)

        # script 块内不应含裸露的 </script>
        script_blocks = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
        for block in script_blocks:
            assert "</script>" not in block


class TestOfflineViewable:
    """正常: 离线时 HTML 文件仍可浏览器打开，文字内容完整"""

    def test_text_content_complete_offline(self):
        """移除 script 标签后文字内容仍完整"""
        records = _make_positive_records()
        html = _render_report(records, history_data=_make_history())

        # 模拟离线：移除所有 script 标签
        no_script = re.sub(r"<script[\s\S]*?</script>", "", html)

        # 关键文字内容仍在
        assert "Assessment Methodology" in no_script
        assert "Overview Dashboard" in no_script
        assert "Category Statistics" in no_script
        assert "Failed Cases Detail" in no_script
        assert "Efficiency Metrics" in no_script

    def test_fallback_elements_present(self):
        """Chart.js 未加载时的 fallback 元素存在"""
        html = _render_report(_make_positive_records(), history_data=_make_history())
        assert "overviewChartFallback" in html
        assert "categoryChartFallback" in html
        assert "trendChartFallback" in html

    def test_inline_css_self_contained(self):
        """HTML 自包含（内联 CSS），无外部样式依赖"""
        html = _render_report(_make_positive_records())
        # 有内联 style 标签
        assert "<style>" in html
        # 无外部 CSS link
        assert '<link rel="stylesheet"' not in html


# ── Boundary Tests ──


class TestAllPassedBoundary:
    """边界: 全部通过时失败用例区域显示 'All cases passed'"""

    def test_all_passed_shows_message(self):
        records = _make_all_pass_positive_records()
        html = _render_report(records)
        assert "\u5168\u90E8\u901A\u8FC7" in html

    def test_all_passed_no_fail_details(self):
        records = _make_all_pass_positive_records()
        html = _render_report(records)
        # 不应出现 <details> 折叠面板（失败用例详情）
        assert "<details>" not in html


class TestNoHistoryBoundary:
    """边界: 无历史数据时趋势图显示 'First run'"""

    def test_no_history_shows_first_run(self):
        html = _render_report(_make_positive_records(), history_data=None)
        assert "\u9996\u6B21\u8FD0\u884C" in html

    def test_empty_history_shows_first_run(self):
        html = _render_report(_make_positive_records(), history_data=[])
        assert "\u9996\u6B21\u8FD0\u884C" in html


class TestNoViolationsBoundary:
    """边界: 无负面违规时显示 '无违规'"""

    def test_no_violations_shows_message(self):
        records = _make_no_violation_negative_records()
        html = _render_report(records, dataset_mode="negative")
        assert "\u65E0\u8FDD\u89C4" in html


class TestSingleModeNegativeSection:
    """边界: single 模式负面板块显示 '未运行负面评估'"""

    def test_single_mode_negative_not_run(self):
        html = _render_report(_make_positive_records(), dataset_mode="single")
        assert "\u672A\u8FD0\u884C\u8D1F\u9762\u8BC4\u4F30" in html


class TestNegativeModePositiveSection:
    """边界: negative 模式正向统计显示 '未运行正向评估'"""

    def test_negative_mode_positive_not_run(self):
        html = _render_report(_make_negative_records(), dataset_mode="negative")
        assert "\u672A\u8FD0\u884C\u6B63\u5411\u8BC4\u4F30" in html

    def test_negative_mode_no_misleading_pass_rate(self):
        """negative 模式不应在正向板块显示误导的通过率 0.0%"""
        html = _render_report(_make_negative_records(), dataset_mode="negative")
        # Section 2 概览仪表盘不应显示正向通过率数据
        # positive_empty_notice 应出现
        assert "\u672A\u8FD0\u884C\u6B63\u5411\u8BC4\u4F30" in html
        # Section 3 分类统计应为空态
        # 确保分类统计区域出现空态提示
        cat_section = html[html.index("section-categories"):]
        cat_section = cat_section[:cat_section.index("</div>")]
        assert "\u672A\u8FD0\u884C\u6B63\u5411\u8BC4\u4F30" in cat_section

    def test_negative_mode_failed_cases_not_all_passed(self):
        """negative 模式下失败用例区域不应显示 '全部通过'"""
        html = _render_report(_make_negative_records(), dataset_mode="negative")
        failed_section = html[html.index("section-failed-cases"):]
        failed_section = failed_section[:failed_section.index("section-negative-violations")]
        assert "\u5168\u90E8\u901A\u8FC7" not in failed_section
        assert "\u672A\u8FD0\u884C\u6B63\u5411\u8BC4\u4F30" in failed_section


# ── Error Tests ──


class TestTemplateNotFoundError:
    """异常: 模板文件不存在时 generate_html_report 抛出明确错误"""

    def test_missing_template_raises_file_not_found(self, tmp_path: Path):
        """指定不存在的模板路径抛出 FileNotFoundError"""
        records = _make_positive_records()
        report = build_report_data(records, dataset_mode="single", env_info=_default_env_info())

        with pytest.raises(FileNotFoundError, match="Report template not found"):
            generate_html_report(report, template_path=str(tmp_path / "nonexistent.html"))


# ── Integration: Full Report Structure ──


class TestFullReportIntegration:
    """集成测试: 完整报告结构验证"""

    def test_html_valid_structure(self):
        """HTML 包含完整的 DOCTYPE / html / head / body 结构"""
        records = _make_positive_records()
        html = _render_report(records)
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html

    def test_charset_utf8(self):
        """HTML 使用 UTF-8 编码"""
        html = _render_report(_make_positive_records())
        assert 'charset="UTF-8"' in html or "charset=UTF-8" in html

    def test_env_info_displayed(self):
        """环境信息在报告方法板块中展示"""
        html = _render_report(_make_positive_records())
        assert "gpt-4o-mini" in html
        assert "3.12.0" in html
        assert "darwin" in html

    def test_pass_rate_in_overview(self):
        """概览仪表盘展示正确通过率"""
        records = _make_positive_records()  # 2/3 passed
        html = _render_report(records)
        # pass_rate = 2/3 ≈ 66.7%
        assert "66.7%" in html

    def test_category_stats_table(self):
        """分类统计表格包含数据"""
        html = _render_report(_make_positive_records())
        assert "tool_selection" in html
        assert "\u901A\u8FC7\u7387" in html

    def test_history_trend_with_data(self):
        """有历史数据时趋势图显示历史运行数量"""
        html = _render_report(
            _make_positive_records(),
            history_data=_make_history(),
        )
        assert "2 \u6B21\u5386\u53F2\u8FD0\u884C" in html

    def test_efficiency_table_values(self):
        """效率指标表格展示正确数值"""
        records = _make_positive_records()
        html = _render_report(records)
        assert "3.50s" in html  # total_elapsed = 1.2 + 0.8 + 1.5 = 3.5

    def test_negative_mode_violation_rate(self):
        """负面模式展示违规率"""
        records = _make_negative_records()
        html = _render_report(records, dataset_mode="negative")
        assert "50.0%" in html  # 1/2 = 50%

    def test_negative_mode_trend_uses_violation_rate(self):
        """negative 模式趋势图应使用 violation_rate 而非 pass_rate"""
        records = _make_negative_records()
        history = [
            {"eval_time": "2026-04-27", "dataset_mode": "negative", "pass_rate": 0.0, "violation_rate": 0.3},
            {"eval_time": "2026-04-28", "dataset_mode": "negative", "pass_rate": 0.0, "violation_rate": 0.1},
        ]
        html = _render_report(records, dataset_mode="negative", history_data=history)
        # JS 代码中应根据 dataset_mode 选择 violation_rate
        assert "violation_rate" in html
        assert "\\u8FDD\\u89C4\\u7387\\u8D8B\\u52BF" in html  # JS 中 unicode 转义的"违规率趋势"
