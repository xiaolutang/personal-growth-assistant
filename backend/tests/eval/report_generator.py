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


def _safe_json_for_script(obj: Any) -> str:
    """将 Python 对象序列化为可安全嵌入 <script> 标签的 JSON 字符串

    统一使用此函数替代手写 json.dumps + replace，确保 </script> 转义不遗漏。

    Args:
        obj: 可 JSON 序列化的 Python 对象

    Returns:
        安全的 JSON 字符串
    """
    serialized = json.dumps(obj, ensure_ascii=False, indent=2)
    return serialized.replace("</script", "<\\/script")


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
    judge_summary: Dict[str, Any] = field(default_factory=dict)
    judge_by_category: Dict[str, Dict[str, Any]] = field(default_factory=dict)


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

    # ── Judge 评分聚合 ──
    judge_records = [r for r in all_records if r.get("judge_result") is not None]
    judge_successful = [r for r in judge_records if not r["judge_result"].get("error", False)]

    judge_summary: Dict[str, Any] = {}
    judge_by_category: Dict[str, Dict[str, Any]] = {}

    if judge_successful:
        # 计算加权平均分
        weighted_avgs = [r["judge_result"].get("weighted_average", 0.0) for r in judge_successful]
        avg_weighted = sum(weighted_avgs) / len(weighted_avgs) if weighted_avgs else 0.0

        # 计算各维度平均分
        dim_sums: Dict[str, float] = {}
        dim_counts: Dict[str, int] = {}
        for r in judge_successful:
            dim_scores = r["judge_result"].get("dimension_scores", {})
            for dim, data in dim_scores.items():
                if isinstance(data, dict) and "score" in data:
                    dim_sums[dim] = dim_sums.get(dim, 0.0) + data["score"]
                    dim_counts[dim] = dim_counts.get(dim, 0) + 1

        dim_avgs = {
            dim: round(dim_sums[dim] / dim_counts[dim], 2)
            for dim in dim_sums
            if dim_counts.get(dim, 0) > 0
        }

        judge_summary = {
            "total_judged": len(judge_successful),
            "total_error": len(judge_records) - len(judge_successful),
            "avg_weighted_score": round(avg_weighted, 2),
            "dimension_averages": dim_avgs,
        }

        # 按分类聚合
        for r in judge_successful:
            cat = r.get("category", "unknown")
            if cat not in judge_by_category:
                judge_by_category[cat] = {
                    "count": 0,
                    "weighted_avgs": [],
                    "dim_sums": {},
                    "dim_counts": {},
                }
            entry = judge_by_category[cat]
            entry["count"] += 1
            entry["weighted_avgs"].append(r["judge_result"].get("weighted_average", 0.0))
            dim_scores = r["judge_result"].get("dimension_scores", {})
            for dim, data in dim_scores.items():
                if isinstance(data, dict) and "score" in data:
                    entry["dim_sums"][dim] = entry["dim_sums"].get(dim, 0.0) + data["score"]
                    entry["dim_counts"][dim] = entry["dim_counts"].get(dim, 0) + 1

        # 计算每个分类的汇总
        for cat, entry in judge_by_category.items():
            wavs = entry.pop("weighted_avgs")
            avg_w = sum(wavs) / len(wavs) if wavs else 0.0
            dim_avgs_cat = {
                dim: round(entry["dim_sums"][dim] / entry["dim_counts"][dim], 2)
                for dim in entry["dim_sums"]
                if entry["dim_counts"].get(dim, 0) > 0
            }
            entry["avg_weighted_score"] = round(avg_w, 2)
            entry["dimension_averages"] = dim_avgs_cat
            # 清理中间数据
            entry.pop("dim_sums", None)
            entry.pop("dim_counts", None)

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
        judge_summary=judge_summary,
        judge_by_category=judge_by_category,
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


# B194 模板文件名，与 report_generator.py 同目录
_TEMPLATE_FILENAME = "report_template.html"


def _render_category_stats_table(
    stats: Dict[str, Dict[str, Any]], dataset_mode: str,
) -> str:
    """渲染分类统计表格（用于新模板 Section 3）"""
    if dataset_mode == "negative":
        return '<div class="empty-state">未运行正向评估（负面模式）。</div>'
    if not stats:
        return '<div class="empty-state">无分类数据。</div>'

    rows = []
    for cat, s in sorted(stats.items()):
        rate = s.get("pass_rate", 0.0)
        rate_str = f"{rate:.1%}"
        cls = "pass-text" if rate >= 0.8 else "fail-text"
        rows.append(
            f"<tr><td>{escape_for_html(cat)}</td>"
            f"<td>{s.get('total', 0)}</td>"
            f"<td>{s.get('passed', 0)}</td>"
            f'<td class="{cls}">{rate_str}</td></tr>'
        )

    return (
        "<table><tr><th>分类</th><th>总数</th><th>通过</th>"
        f"<th>通过率</th></tr>{''.join(rows)}</table>"
    )


def _render_failed_cases(
    cases: List[Dict[str, Any]], dataset_mode: str,
) -> str:
    """渲染失败用例为可展开的 details 元素（用于新模板 Section 4）"""
    if dataset_mode == "negative":
        return '<div class="empty-state">未运行正向评估（负面模式）。</div>'
    if not cases:
        return '<div class="empty-state">全部通过！</div>'

    items = []
    for i, c in enumerate(cases, 1):
        inp = escape_for_html(str(c.get("input", "")))
        expected = escape_for_html(str(c.get("expected_tools", [])))
        actual = escape_for_html(str(c.get("actual_tools", [])))
        reply = str(c.get("agent_reply", ""))
        if len(reply) > 500:
            reply = reply[:500] + "..."
        reply_escaped = escape_for_html(reply)
        items.append(
            f"<details>"
            f"<summary><span>#{i} {inp}</span> "
            f'<span class="badge badge-fail">\u5931\u8D25</span></summary>'
            f'<div class="detail-body">'
            f'<div class="field"><div class="field-label">\u7528\u6237\u8F93\u5165</div>'
            f'<div class="field-value">{inp}</div></div>'
            f'<div class="field"><div class="field-label">\u671F\u671B\u5DE5\u5177</div>'
            f'<div class="field-value">{expected}</div></div>'
            f'<div class="field"><div class="field-label">\u5B9E\u9645\u5DE5\u5177</div>'
            f'<div class="field-value">{actual}</div></div>'
            f'<div class="field"><div class="field-label">\u667A\u80FD\u4F53\u56DE\u590D</div>'
            f'<div class="field-value">{reply_escaped}</div></div>'
            f"</div></details>"
        )
    return "".join(items)


def _render_negative_violations(
    violations: List[Dict[str, Any]],
    total_negative: int,
    violation_rate: float,
    dataset_mode: str,
) -> str:
    """渲染负面违规板块（用于新模板 Section 5）"""
    # 条件渲染：single 模式未运行负面评估
    if dataset_mode == "single":
        return '<div class="empty-state">未运行负面评估（单轮模式）。</div>'

    parts = []
    parts.append(
        f'<p>\u8FDD\u89C4\u7387\uFF1A<strong>{violation_rate:.1%}</strong> '
        f"({len(violations)} / {total_negative} \u6761\u8D1F\u9762\u7528\u4F8B)</p>"
    )

    if not violations:
        parts.append('<div class="empty-state">\u65E0\u8FDD\u89C4\u3002</div>')
        return "".join(parts)

    rows = []
    for c in violations:
        inp = escape_for_html(str(c.get("input", "")))
        should_not = escape_for_html(str(c.get("should_not_call", [])))
        violated_tools = escape_for_html(str(c.get("violated_tools", [])))
        reply = str(c.get("agent_reply", ""))
        if len(reply) > 200:
            reply = reply[:200] + "..."
        reply_escaped = escape_for_html(reply)
        rows.append(
            f"<tr>"
            f"<td>{inp}</td>"
            f"<td>{should_not}</td>"
            f"<td>{violated_tools}</td>"
            f"<td>{reply_escaped}</td>"
            f'<td class="fail-text">\u8FDD\u89C4</td></tr>'
        )
    parts.append(
        "<table><tr><th>\u8F93\u5165</th><th>\u4E0D\u5E94\u8C03\u7528</th>"
        "<th>\u8FDD\u89C4\u5DE5\u5177</th><th>\u667A\u80FD\u4F53\u56DE\u590D</th><th>\u72B6\u6001</th></tr>"
        f"{''.join(rows)}</table>"
    )
    return "".join(parts)


def _render_history_trend(
    history_data: Optional[List[Dict[str, Any]]],
) -> str:
    """渲染历史趋势板块（用于新模板 Section 6）"""
    if not history_data:
        return '<div class="empty-state">\u9996\u6B21\u8FD0\u884C\u2014\u2014\u5C1A\u65E0\u5386\u53F2\u6570\u636E\u3002</div>'
    count = len(history_data)
    return f"<p>\u663E\u793A {count} \u6B21\u5386\u53F2\u8FD0\u884C\u7684\u8D8B\u52BF\u3002</p>"


def _render_env_info(env_info: Dict[str, Any]) -> str:
    """渲染环境信息为列表项（用于新模板 Section 1）"""
    if not env_info:
        return '      <li><span class="env-key">N/A</span></li>'
    items = []
    for k, v in env_info.items():
        items.append(
            f'      <li><span class="env-key">{escape_for_html(str(k))}</span>: '
            f"{escape_for_html(str(v))}</li>"
        )
    return "\n".join(items)


def _render_tool_call_distribution(
    failed_cases: List[Dict[str, Any]],
    negative_violations: List[Dict[str, Any]],
) -> str:
    """渲染工具调用次数分布表（用于新模板 Section 7）

    基于 failed_cases + negative_violations 统计工具调用分布。
    注意：通过的用例不在 EvalReportData 中，因此分布仅覆盖异常用例。
    """
    all_visible = failed_cases + negative_violations
    if not all_visible:
        return '<h3>\u5DE5\u5177\u8C03\u7528\u6B21\u6570\u5206\u5E03</h3><div class="empty-state">\u65E0\u5DE5\u5177\u8C03\u7528\u6570\u636E\u3002</div>'
    # 收集每个用例的工具调用次数
    tool_counts: Dict[int, int] = {}
    for c in all_visible:
        actual = c.get("actual_tools", [])
        count = len(actual) if isinstance(actual, list) else 0
        tool_counts[count] = tool_counts.get(count, 0) + 1

    rows = []
    for n_calls in sorted(tool_counts.keys()):
        rows.append(
            f"<tr><td>{n_calls} \u6B21\u5DE5\u5177\u8C03\u7528</td>"
            f"<td>{tool_counts[n_calls]}</td></tr>"
        )
    return (
        '<h3>\u5DE5\u5177\u8C03\u7528\u6B21\u6570\u5206\u5E03\uFF08\u5931\u8D25/\u8FDD\u89C4\u7528\u4F8B\uFF09</h3>'
        "<table><tr><th>\u5DE5\u5177\u8C03\u7528</th><th>\u6570\u91CF</th></tr>"
        f"{''.join(rows)}</table>"
    )


def _render_positive_empty_notice(dataset_mode: str) -> str:
    """渲染正向板块空态提示"""
    if dataset_mode == "negative":
        return '<div class="empty-state">未运行正向评估（负面模式）。</div>'
    return ""


def _render_judge_section(
    judge_summary: Dict[str, Any],
    judge_by_category: Dict[str, Dict[str, Any]],
    dataset_mode: str,
) -> str:
    """渲染 LLM-as-Judge 评分区块（用于新模板 Section 8）

    顶部展示加权平均分，各分类下展示 7 维度条形图（内联 CSS）。
    """
    if dataset_mode == "negative":
        return '<div class="empty-state">\u672A\u8FD0\u884C\u6B63\u5411\u8BC4\u4F30\uFF0C\u65E0 Judge \u8BC4\u5206\u6570\u636E\u3002</div>'

    if not judge_summary:
        return '<div class="empty-state">\u672A\u542F\u7528 LLM-as-Judge \u8BC4\u5206\u6216\u65E0\u6709\u6548\u6570\u636E\u3002</div>'

    parts = []

    # 顶部概览
    avg_w = judge_summary.get("avg_weighted_score", 0.0)
    total_judged = judge_summary.get("total_judged", 0)
    total_error = judge_summary.get("total_error", 0)
    dim_avgs = judge_summary.get("dimension_averages", {})

    parts.append(
        f'<div class="judge-overview">'
        f'<div class="stat-card neutral">'
        f'<div class="label">Judge \u52A0\u6743\u5E73\u5747\u5206</div>'
        f'<div class="value">{avg_w:.2f}</div>'
        f'</div>'
        f'<div class="stat-card neutral">'
        f'<div class="label">\u8BC4\u5206\u7528\u4F8B\u6570</div>'
        f'<div class="value">{total_judged}</div>'
        f'</div>'
    )
    if total_error > 0:
        parts.append(
            f'<div class="stat-card fail">'
            f'<div class="label">\u8BC4\u5206\u5931\u8D25\u6570</div>'
            f'<div class="value">{total_error}</div>'
            f'</div>'
        )
    parts.append('</div>')

    # 总体维度条形图
    if dim_avgs:
        parts.append('<h3>\u603B\u4F53\u7EF4\u5EA6\u5E73\u5747\u5206</h3>')
        parts.append('<div class="judge-bar-chart">')
        for dim, avg in sorted(dim_avgs.items()):
            pct = (avg / 5.0) * 100
            color = "#059669" if avg >= 4.0 else ("#f59e0b" if avg >= 3.0 else "#dc2626")
            parts.append(
                f'<div class="judge-bar-row">'
                f'<div class="judge-bar-label">{escape_for_html(dim)}</div>'
                f'<div class="judge-bar-track">'
                f'<div class="judge-bar-fill" style="width:{pct:.1f}%;background:{color};"></div>'
                f'</div>'
                f'<div class="judge-bar-score">{avg:.2f}</div>'
                f'</div>'
            )
        parts.append('</div>')

    # 各分类维度条形图
    if judge_by_category:
        parts.append('<h3>\u5404\u5206\u7C7B\u7EF4\u5EA6\u5E73\u5747\u5206</h3>')
        for cat, cat_data in sorted(judge_by_category.items()):
            cat_avg = cat_data.get("avg_weighted_score", 0.0)
            cat_dim_avgs = cat_data.get("dimension_averages", {})
            cat_count = cat_data.get("count", 0)
            parts.append(
                f'<details>'
                f'<summary><span>{escape_for_html(cat)} '
                f'(\u52A0\u6743\u5747\u5206: {cat_avg:.2f}, {cat_count} \u6761)</span></summary>'
                f'<div class="detail-body">'
                f'<div class="judge-bar-chart">'
            )
            for dim, avg in sorted(cat_dim_avgs.items()):
                pct = (avg / 5.0) * 100
                color = "#059669" if avg >= 4.0 else ("#f59e0b" if avg >= 3.0 else "#dc2626")
                parts.append(
                    f'<div class="judge-bar-row">'
                    f'<div class="judge-bar-label">{escape_for_html(dim)}</div>'
                    f'<div class="judge-bar-track">'
                    f'<div class="judge-bar-fill" style="width:{pct:.1f}%;background:{color};"></div>'
                    f'</div>'
                    f'<div class="judge-bar-score">{avg:.2f}</div>'
                    f'</div>'
                )
            parts.append('</div></div></details>')

    return "".join(parts)


def generate_html_report(
    report_data: EvalReportData,
    template_path: Optional[str] = None,
    history_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """生成 HTML 报告

    使用 string.Template 渲染 report_template.html。
    支持自定义模板路径，默认使用同目录下的 report_template.html。

    Args:
        report_data: 评估报告数据
        template_path: 可选模板文件路径（默认使用同目录 report_template.html）
        history_data: 可选历史记录列表（用于趋势图）

    Returns:
        完整 HTML 字符串

    Raises:
        FileNotFoundError: 模板文件不存在
    """
    # 确定模板路径
    if template_path:
        tpl_path = Path(template_path)
    else:
        tpl_path = Path(__file__).parent / _TEMPLATE_FILENAME

    if not tpl_path.exists():
        raise FileNotFoundError(
            f"Report template not found: {tpl_path}. "
            f"Ensure report_template.html exists in the same directory as report_generator.py."
        )

    template_str = tpl_path.read_text(encoding="utf-8")
    tmpl = Template(template_str)

    # 序列化 report data 为 JSON（嵌入 script 标签供 Chart.js 使用）
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
    report_data_json = _safe_json_for_script(report_dict)

    # 计算派生值
    total_failed = report_data.total_positive - report_data.total_passed
    efficiency = report_data.efficiency

    html = tmpl.safe_substitute(
        # Header
        eval_time=escape_for_html(report_data.eval_time),
        dataset_mode=escape_for_html(report_data.dataset_mode),
        # Section 1: Assessment Methodology
        env_info_items=_render_env_info(report_data.env_info),
        # Section 2: Overview Dashboard
        pass_rate_display=f"{report_data.pass_rate:.1%}",
        pass_rate_card_class="pass" if report_data.pass_rate >= 0.8 else "fail",
        total_passed=str(report_data.total_passed),
        total_failed=str(total_failed),
        total_positive=str(report_data.total_positive),
        positive_empty_notice=_render_positive_empty_notice(report_data.dataset_mode),
        # Section 3: Category Statistics
        category_stats_content=_render_category_stats_table(
            report_data.category_stats, report_data.dataset_mode,
        ),
        # Section 4: Failed Cases
        failed_cases_content=_render_failed_cases(
            report_data.failed_cases, report_data.dataset_mode,
        ),
        # Section 5: Negative Violations
        negative_violations_content=_render_negative_violations(
            report_data.negative_violations,
            report_data.total_negative,
            report_data.violation_rate,
            report_data.dataset_mode,
        ),
        # Section 6: History Trend
        history_trend_content=_render_history_trend(history_data),
        # Section 7: Efficiency Metrics
        efficiency_total_cases=str(efficiency.get("total_cases", 0)),
        efficiency_total_elapsed=f"{efficiency.get('total_elapsed', 0.0):.2f}",
        efficiency_avg_elapsed=f"{efficiency.get('avg_elapsed', 0.0):.2f}",
        efficiency_median_elapsed=f"{efficiency.get('median_elapsed', 0.0):.2f}",
        tool_call_distribution=_render_tool_call_distribution(
            report_data.failed_cases, report_data.negative_violations,
        ),
        # Section 8: LLM-as-Judge Scores
        judge_section_content=_render_judge_section(
            report_data.judge_summary,
            report_data.judge_by_category,
            report_data.dataset_mode,
        ),
        # Negative stats (for Section 1)
        total_negative=str(report_data.total_negative),
        total_violations=str(report_data.total_violations),
        # Chart.js data
        report_data_json=report_data_json,
    )

    return html
