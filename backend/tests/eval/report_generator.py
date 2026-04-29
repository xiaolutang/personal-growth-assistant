"""B193 报告数据模型 + 生成器

核心组件:
- EvalReportData: 评估报告数据模型 (dataclass)
- build_report_data(): 聚合 case records 为 EvalReportData
- escape_for_html(): HTML 特殊字符转义
- escape_for_js(): JSON 安全序列化（处理 </script> 等）
- load_history(): 读取历次运行摘要
- append_history(): 追加运行记录到 history.json
- generate_html_report(): 渲染 HTML 报告
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Set


# ── Schema 定义 ──

POSITIVE_CASE_REQUIRED_KEYS: Set[str] = {
    "input", "expected_tools", "actual_tools", "agent_reply",
    "passed", "category", "elapsed_seconds",
}

NEGATIVE_CASE_REQUIRED_KEYS: Set[str] = {
    "input", "should_not_call", "actual_tools", "agent_reply",
    "violated", "violated_tools", "category", "elapsed_seconds",
}

HISTORY_ROW_REQUIRED_KEYS: Set[str] = {
    "eval_time", "dataset_mode", "pass_rate",
}


# ── 转义辅助函数 ──


def escape_for_html(text: str) -> str:
    """转义 HTML 特殊字符

    转义: < > & " '

    Args:
        text: 原始字符串

    Returns:
        转义后的字符串
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def escape_for_js(value: str) -> str:
    """序列化为 JS 安全字符串

    使用 json.dumps 确保引号、反斜杠、换行等字符被正确转义。
    额外将 </script 替换为 <\\/script 防止浏览器误解析 script 闭合标签。
    浏览器的 HTML 解析器在 <script> 块内遇到 </script 就会关闭标签，
    即使它出现在 JS 字符串内部。

    Args:
        value: 原始字符串

    Returns:
        JSON 字符串字面量（含引号），可直接嵌入 <script> 标签
    """
    serialized = json.dumps(value, ensure_ascii=False)
    # 防止 </script> 在 <script> 块中被浏览器解析为标签闭合
    serialized = serialized.replace("</script", "<\\/script")
    return serialized


# ── 数据模型 ──


@dataclass
class EvalReportData:
    """评估报告数据模型

    同时支持正向、负面和混合模式评估。

    Attributes:
        eval_time: 评估时间 (ISO 格式)
        dataset_mode: 数据集模式 (single / negative / all)
        pass_rate: 正向通过率 (0.0 - 1.0)，无正向用例时为 0.0
        total_positive: 正向用例总数
        total_passed: 正向通过数
        category_stats: 分类统计 {category: {total, passed, pass_rate}}
        failed_cases: 失败用例列表
        total_negative: 负面用例总数
        total_violations: 负面违规数
        violation_rate: 负面违规率 (0.0 - 1.0)，无负面用例时为 0.0
        negative_violations: 负面违规用例列表
        efficiency: 效率指标 {total_elapsed, avg_elapsed, median_elapsed, total_cases}
        env_info: 环境信息 {python_version, os, model, ...}
    """

    eval_time: str = ""
    dataset_mode: str = ""
    pass_rate: float = 0.0
    total_positive: int = 0
    total_passed: int = 0
    category_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    failed_cases: List[Dict[str, Any]] = field(default_factory=list)
    total_negative: int = 0
    total_violations: int = 0
    violation_rate: float = 0.0
    negative_violations: List[Dict[str, Any]] = field(default_factory=list)
    efficiency: Dict[str, Any] = field(default_factory=dict)
    env_info: Dict[str, Any] = field(default_factory=dict)


# ── Schema 验证 ──


def _validate_positive_case(rec: Dict[str, Any], index: int) -> None:
    """验证正向用例 schema，缺少必填字段时抛出 ValueError"""
    missing = POSITIVE_CASE_REQUIRED_KEYS - set(rec.keys())
    if missing:
        raise ValueError(
            f"Positive case record at index {index} missing required keys: "
            f"{sorted(missing)}. Got keys: {sorted(rec.keys())}"
        )


def _validate_negative_case(rec: Dict[str, Any], index: int) -> None:
    """验证负面用例 schema，缺少必填字段时抛出 ValueError"""
    missing = NEGATIVE_CASE_REQUIRED_KEYS - set(rec.keys())
    if missing:
        raise ValueError(
            f"Negative case record at index {index} missing required keys: "
            f"{sorted(missing)}. Got keys: {sorted(rec.keys())}"
        )


def validate_history_record(record: Dict[str, Any]) -> None:
    """验证 history 记录 schema，缺少必填字段时抛出 ValueError"""
    missing = HISTORY_ROW_REQUIRED_KEYS - set(record.keys())
    if missing:
        raise ValueError(
            f"History record missing required keys: {sorted(missing)}. "
            f"Got keys: {sorted(record.keys())}"
        )


# ── build_report_data ──


def build_report_data(
    case_records: List[Dict[str, Any]],
    dataset_mode: str,
    env_info: Dict[str, Any],
    eval_time: Optional[str] = None,
) -> EvalReportData:
    """聚合 case records 为 EvalReportData

    根据每条 record 中是否含有 'violated' 字段判断正向/负面用例:
    - 正向用例: 含 input / expected_tools / actual_tools / agent_reply / passed / category / elapsed_seconds
    - 负面用例: 含 input / should_not_call / actual_tools / agent_reply / violated / violated_tools / category / elapsed_seconds

    dataset_mode 控制板块填充:
    - 'single': 正向板块填充，负面板块空态
    - 'negative': 负面板块填充，正向板块空态
    - 'all': 全板块填充

    Args:
        case_records: 用例记录列表（每条为 dict）
        dataset_mode: 数据集模式
        env_info: 环境信息
        eval_time: 可选评估时间 (ISO 格式)，不传则使用当前时间

    Returns:
        EvalReportData

    Raises:
        ValueError: 用例记录缺少必填字段
    """
    positive_records: List[Dict[str, Any]] = []
    negative_records: List[Dict[str, Any]] = []

    for i, rec in enumerate(case_records):
        if "violated" in rec:
            _validate_negative_case(rec, i)
            negative_records.append(rec)
        else:
            _validate_positive_case(rec, i)
            positive_records.append(rec)

    # ── 正向指标 ──
    total_positive = len(positive_records) if dataset_mode in ("single", "all") else 0
    total_passed = 0
    pass_rate = 0.0
    category_stats: Dict[str, Dict[str, Any]] = {}
    failed_cases: List[Dict[str, Any]] = []

    if dataset_mode in ("single", "all") and positive_records:
        total_passed = sum(1 for r in positive_records if r["passed"])
        pass_rate = round(total_passed / total_positive, 4) if total_positive > 0 else 0.0

        # 分类统计
        cat_map: Dict[str, List[Dict[str, Any]]] = {}
        for rec in positive_records:
            cat_map.setdefault(rec["category"], []).append(rec)

        for cat, recs in cat_map.items():
            total = len(recs)
            passed = sum(1 for r in recs if r["passed"])
            category_stats[cat] = {
                "total": total,
                "passed": passed,
                "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
            }

        failed_cases = [rec for rec in positive_records if not rec["passed"]]

    # ── 负面指标 ──
    total_negative = len(negative_records) if dataset_mode in ("negative", "all") else 0
    total_violations = 0
    violation_rate = 0.0
    negative_violations: List[Dict[str, Any]] = []

    if dataset_mode in ("negative", "all") and negative_records:
        negative_violations = [rec for rec in negative_records if rec["violated"]]
        total_violations = len(negative_violations)
        violation_rate = round(total_violations / total_negative, 4) if total_negative > 0 else 0.0

    # ── 效率指标 ──
    all_records = positive_records + negative_records
    elapsed_list = [r["elapsed_seconds"] for r in all_records]
    total_elapsed = sum(elapsed_list)
    sorted_elapsed = sorted(elapsed_list)
    if sorted_elapsed:
        mid = len(sorted_elapsed) // 2
        median_elapsed = (
            sorted_elapsed[mid] if len(sorted_elapsed) % 2 == 1
            else (sorted_elapsed[mid - 1] + sorted_elapsed[mid]) / 2
        )
    else:
        median_elapsed = 0.0

    avg_elapsed = round(total_elapsed / len(elapsed_list), 4) if elapsed_list else 0.0

    efficiency = {
        "total_elapsed": round(total_elapsed, 4),
        "avg_elapsed": avg_elapsed,
        "median_elapsed": round(median_elapsed, 4),
        "total_cases": len(all_records),
    }

    return EvalReportData(
        eval_time=eval_time or datetime.now().isoformat(),
        dataset_mode=dataset_mode,
        pass_rate=pass_rate,
        total_positive=total_positive,
        total_passed=total_passed,
        category_stats=category_stats,
        failed_cases=failed_cases,
        total_negative=total_negative,
        total_violations=total_violations,
        violation_rate=violation_rate,
        negative_violations=negative_violations,
        efficiency=efficiency,
        env_info=env_info,
    )


# ── history.json 管理 ──


def load_history(reports_dir: Path) -> List[Dict[str, Any]]:
    """读取历次运行摘要列表

    history.json 格式: 数组，每项含 eval_time / dataset_mode / pass_rate 等。

    恢复策略:
    - 文件不存在 → 返回空列表
    - 非法 JSON → 返回空列表 + 打印 warning
    - 非数组 → 返回空列表 + 打印 warning

    Args:
        reports_dir: 报告目录 (包含 history.json)

    Returns:
        历史记录列表
    """
    reports_dir = Path(reports_dir)
    history_file = reports_dir / "history.json"

    if not history_file.exists():
        return []

    try:
        content = history_file.read_text(encoding="utf-8")
    except OSError:
        warnings.warn(f"Cannot read history file: {history_file}")
        return []

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        warnings.warn(f"Invalid JSON in history file: {history_file}, returning empty list")
        return []

    if not isinstance(data, list):
        warnings.warn(
            f"history.json is not an array (got {type(data).__name__}), "
            f"returning empty list"
        )
        return []

    return data


def append_history(
    record: Dict[str, Any],
    reports_dir: Path,
) -> None:
    """追加运行记录到 history.json

    - 不覆盖已有数据
    - 首次运行时自动创建目录和文件
    - 损坏时备份旧文件为 history.json.bak 并重建
    - 验证记录 schema（必须含 eval_time, dataset_mode, pass_rate）

    Args:
        record: 运行记录
        reports_dir: 报告目录

    Raises:
        ValueError: 记录缺少必填字段
    """
    validate_history_record(record)

    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    history_file = reports_dir / "history.json"
    history_bak = reports_dir / "history.json.bak"

    # 判断文件是否损坏（区分合法空数组和损坏文件）
    is_corrupted = False
    existing: List[Dict[str, Any]] = []

    if history_file.exists():
        try:
            content = history_file.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, list):
                existing = data
            else:
                # 非数组 → 损坏
                is_corrupted = True
        except (json.JSONDecodeError, OSError):
            # 非法 JSON 或读取失败 → 损坏
            is_corrupted = True
    # 文件不存在 → existing 保持空列表，不是损坏

    if is_corrupted:
        # 备份旧文件
        try:
            history_bak.write_text(
                history_file.read_text(encoding="utf-8"), encoding="utf-8"
            )
        except OSError:
            pass
        # 以当前记录重建
        new_data = [record]
    else:
        # 正常追加（包括合法空数组场景）
        new_data = existing + [record]

    history_file.write_text(
        json.dumps(new_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ── HTML 报告生成 ──


_DEFAULT_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Eval Report - $eval_time</title>
<style>
body { font-family: -apple-system, sans-serif; margin: 2rem; color: #333; }
h1 { color: #6366F1; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background: #f5f5f5; }
.pass { color: green; }
.fail { color: red; }
.stats { margin: 1rem 0; }
.metric { display: inline-block; margin-right: 2rem; }
.metric-value { font-size: 1.5rem; font-weight: bold; }
</style>
</head>
<body>
<h1>Evaluation Report</h1>
<div class="stats">
<p>Time: $eval_time</p>
<p>Dataset Mode: $dataset_mode</p>
<div class="metric">
<span>Pass Rate:</span>
<span class="metric-value $pass_rate_class">$pass_rate_display</span>
<span>($total_passed / $total_positive cases)</span>
</div>
<div class="metric">
<span>Violation Rate:</span>
<span class="metric-value $violation_rate_class">$violation_rate_display</span>
<span>($total_violations / $total_negative cases)</span>
</div>
</div>

<h2>Category Stats</h2>
$category_stats_html

<h2>Failed Cases</h2>
$failed_cases_html

<h2>Negative Violations</h2>
$negative_violations_html

<h2>Efficiency</h2>
$efficiency_html

<h2>Environment</h2>
$env_info_html

<script>
const reportData = $report_data_json;
</script>
</body>
</html>""")


def _render_category_stats(stats: Dict[str, Dict[str, Any]]) -> str:
    """渲染分类统计表格"""
    if not stats:
        return "<p>No data</p>"

    rows = []
    for cat, s in sorted(stats.items()):
        rate = s.get("pass_rate", 0.0)
        rate_str = f"{rate:.1%}"
        cls = "pass" if rate >= 0.8 else "fail"
        rows.append(
            f"<tr><td>{escape_for_html(cat)}</td>"
            f"<td>{s.get('total', 0)}</td>"
            f"<td>{s.get('passed', 0)}</td>"
            f'<td class="{cls}">{rate_str}</td></tr>'
        )

    return (
        "<table><tr><th>Category</th><th>Total</th><th>Passed</th>"
        f"<th>Pass Rate</th></tr>{''.join(rows)}</table>"
    )


def _render_cases(cases: List[Dict[str, Any]], case_type: str) -> str:
    """渲染用例表格"""
    if not cases:
        return "<p>None</p>"

    if case_type == "failed":
        rows = []
        for c in cases:
            status = "FAIL"
            reply = str(c.get("agent_reply", ""))
            # 截断过长的回复以保持表格可读性
            if len(reply) > 200:
                reply = reply[:200] + "..."
            rows.append(
                f"<tr>"
                f"<td>{escape_for_html(str(c.get('input', '')))}</td>"
                f"<td>{escape_for_html(str(c.get('expected_tools', [])))}</td>"
                f"<td>{escape_for_html(str(c.get('actual_tools', [])))}</td>"
                f"<td>{escape_for_html(reply)}</td>"
                f'<td class="fail">{status}</td></tr>'
            )
        return (
            "<table><tr><th>Input</th><th>Expected</th><th>Actual</th>"
            f"<th>Agent Reply</th><th>Status</th></tr>{''.join(rows)}</table>"
        )
    else:  # negative
        rows = []
        for c in cases:
            reply = str(c.get("agent_reply", ""))
            if len(reply) > 200:
                reply = reply[:200] + "..."
            rows.append(
                f"<tr>"
                f"<td>{escape_for_html(str(c.get('input', '')))}</td>"
                f"<td>{escape_for_html(str(c.get('should_not_call', [])))}</td>"
                f"<td>{escape_for_html(str(c.get('violated_tools', [])))}</td>"
                f"<td>{escape_for_html(reply)}</td>"
                f'<td class="fail">VIOLATED</td></tr>'
            )
        return (
            "<table><tr><th>Input</th><th>Should Not Call</th>"
            f"<th>Violated Tools</th><th>Agent Reply</th><th>Status</th></tr>"
            f"{''.join(rows)}</table>"
        )


def _render_dict(data: Dict[str, Any]) -> str:
    """渲染字典为简单列表"""
    if not data:
        return "<p>N/A</p>"
    items = []
    for k, v in data.items():
        items.append(f"<li><strong>{escape_for_html(str(k))}</strong>: "
                     f"{escape_for_html(str(v))}</li>")
    return f"<ul>{''.join(items)}</ul>"


def generate_html_report(
    report_data: EvalReportData,
    template_path: Optional[str] = None,
    history_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """生成 HTML 报告

    使用 string.Template 渲染。暂用简单默认模板，
    完整模板由 B194 实现。

    函数签名接受 EvalReportData、可选模板路径和可选历史数据，
    返回完整 HTML 字符串。

    Args:
        report_data: 评估报告数据
        template_path: 可选模板文件路径
        history_data: 可选历史记录列表（供 B194 趋势图使用）

    Returns:
        完整 HTML 字符串
    """
    if template_path:
        template_str = Path(template_path).read_text(encoding="utf-8")
        tmpl = Template(template_str)
    else:
        tmpl = _DEFAULT_TEMPLATE

    # 序列化 report data 为 JSON（嵌入 script 标签供前端使用）
    report_dict = {
        "eval_time": report_data.eval_time,
        "dataset_mode": report_data.dataset_mode,
        "pass_rate": report_data.pass_rate,
        "total_positive": report_data.total_positive,
        "total_passed": report_data.total_passed,
        "category_stats": report_data.category_stats,
        "failed_cases": [
            {
                "input": c.get("input", ""),
                "expected_tools": c.get("expected_tools", []),
                "actual_tools": c.get("actual_tools", []),
                "agent_reply": c.get("agent_reply", ""),
                "passed": c.get("passed", False),
                "category": c.get("category", ""),
                "elapsed_seconds": c.get("elapsed_seconds", 0.0),
            }
            for c in report_data.failed_cases
        ],
        "total_negative": report_data.total_negative,
        "total_violations": report_data.total_violations,
        "violation_rate": report_data.violation_rate,
        "negative_violations": [
            {
                "input": c.get("input", ""),
                "should_not_call": c.get("should_not_call", []),
                "actual_tools": c.get("actual_tools", []),
                "agent_reply": c.get("agent_reply", ""),
                "violated": c.get("violated", False),
                "violated_tools": c.get("violated_tools", []),
                "category": c.get("category", ""),
                "elapsed_seconds": c.get("elapsed_seconds", 0.0),
            }
            for c in report_data.negative_violations
        ],
        "efficiency": report_data.efficiency,
        "env_info": report_data.env_info,
        "history": history_data or [],
    }
    report_data_json = json.dumps(report_dict, ensure_ascii=False, indent=2)
    # 防止 JSON 内的 </script> 被浏览器解析为 script 标签闭合
    report_data_json = report_data_json.replace("</script", "<\\/script")

    html = tmpl.safe_substitute(
        eval_time=escape_for_html(report_data.eval_time),
        dataset_mode=escape_for_html(report_data.dataset_mode),
        pass_rate_display=f"{report_data.pass_rate:.1%}",
        pass_rate_class="pass" if report_data.pass_rate >= 0.8 else "fail",
        total_passed=str(report_data.total_passed),
        total_positive=str(report_data.total_positive),
        violation_rate_display=f"{report_data.violation_rate:.1%}",
        violation_rate_class="pass" if report_data.violation_rate <= 0.1 else "fail",
        total_violations=str(report_data.total_violations),
        total_negative=str(report_data.total_negative),
        category_stats_html=_render_category_stats(report_data.category_stats),
        failed_cases_html=_render_cases(report_data.failed_cases, "failed"),
        negative_violations_html=_render_cases(report_data.negative_violations, "negative"),
        efficiency_html=_render_dict(report_data.efficiency),
        env_info_html=_render_dict(report_data.env_info),
        report_data_json=report_data_json,
    )

    return html
