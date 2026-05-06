"""评估趋势对比脚本 eval_trend.py

读取 history.json，输出最近 N 次评估的趋势对比：
通过率变化、分类维度 delta、失败用例回归/新增。
支持 --diff 参数对比任意两次评估的详细差异。

用法:
    cd backend
    uv run python -m tests.eval.eval_trend --last 10
    uv run python -m tests.eval.eval_trend --diff 2 3
    uv run python -m tests.eval.eval_trend --history /path/to/history.json

参数:
    --history   history.json 路径 (默认 data/eval_reports/history.json)
    --last N    显示最近 N 次趋势 (默认 10)
    --diff N M  对比第 N 次和第 M 次的详细差异 (1-indexed)
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── 路径解析 ──


def _get_default_history_path() -> Path:
    """获取默认 history.json 路径: 项目根目录/data/eval_reports/history.json"""
    return Path(__file__).resolve().parent.parent.parent.parent / "data" / "eval_reports" / "history.json"


# ── 数据加载 ──


def load_history(path: str | Path) -> List[Dict[str, Any]]:
    """加载 history.json

    Args:
        path: history.json 文件路径

    Returns:
        历史记录列表

    Raises:
        SystemExit: JSON 解析失败时打印警告并退出
    """
    path = Path(path)

    if not path.exists():
        return []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"WARNING: 无法读取 {path}: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"WARNING: JSON 解析失败 {path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print(f"WARNING: history.json 不是数组 (类型: {type(data).__name__})", file=sys.stderr)
        sys.exit(1)

    return data


# ── 趋势输出 ──


def _fmt_pct(value: float) -> str:
    """格式化百分比率值"""
    return f"{value:.2%}"


def _delta_arrow(current: float, previous: float) -> str:
    """计算 delta 并返回带箭头的字符串"""
    delta = current - previous
    if delta > 0.005:
        return f"+{delta:.2%} ^"
    elif delta < -0.005:
        return f"{delta:.2%} v"
    else:
        return f"{delta:+.2%} ="


def print_trend(records: List[Dict[str, Any]], last_n: int = 10) -> str:
    """输出最近 N 次评估趋势 (Markdown 格式)

    Args:
        records: history.json 记录列表
        last_n: 显示最近 N 次 (默认 10)

    Returns:
        Markdown 格式字符串
    """
    if not records:
        return "无历史数据"

    # 取最近 last_n 条
    subset = records[-last_n:]
    lines: List[str] = []

    lines.append(f"## 评估趋势 (最近 {len(subset)} 次)")
    lines.append("")

    # 趋势表格
    lines.append("| # | 时间 | 通过率 | Delta | 正向通过 | 违规数 | Commit |")
    lines.append("|---|------|--------|-------|---------|--------|--------|")

    for i, rec in enumerate(subset):
        idx = len(records) - len(subset) + i + 1
        eval_time = rec.get("eval_time", "N/A")
        # 截断时间显示
        if len(eval_time) > 19:
            eval_time = eval_time[:19]

        pass_rate = rec.get("pass_rate", 0.0)
        total_passed = rec.get("total_passed", "-")
        total_violations = rec.get("total_violations", "-")
        env_info = rec.get("env_info", {})
        commit = env_info.get("git_commit", "-") if isinstance(env_info, dict) else "-"

        # 计算 delta (与前一次比较)
        if i > 0:
            prev_rate = subset[i - 1].get("pass_rate", 0.0)
            delta_str = _delta_arrow(pass_rate, prev_rate)
        else:
            delta_str = "-"

        lines.append(
            f"| {idx} | {eval_time} | {_fmt_pct(pass_rate)} | {delta_str} | "
            f"{total_passed} | {total_violations} | {commit} |"
        )

    lines.append("")

    # 摘要
    if len(subset) >= 2:
        first_rate = subset[0].get("pass_rate", 0.0)
        last_rate = subset[-1].get("pass_rate", 0.0)
        overall_delta = last_rate - first_rate
        lines.append(f"**趋势摘要**: {len(subset)} 次评估，通过率从 {_fmt_pct(first_rate)} 变化到 {_fmt_pct(last_rate)} ({overall_delta:+.2%})")
    elif len(subset) == 1:
        rec = subset[0]
        pass_rate = rec.get("pass_rate", 0.0)
        lines.append(f"**当前状态**: 通过率 {_fmt_pct(pass_rate)}，正向通过 {rec.get('total_passed', '-')}，违规 {rec.get('total_violations', '-')}")

    return "\n".join(lines)


# ── 差异对比 ──


def print_diff(records: List[Dict[str, Any]], n: int, m: int) -> str:
    """对比第 N 次和第 M 次评估的详细差异

    Args:
        records: history.json 记录列表
        n: 第 N 次 (1-indexed)
        m: 第 M 次 (1-indexed)

    Returns:
        Markdown 格式字符串
    """
    if not records:
        return "无历史数据"

    total = len(records)
    if n < 1 or n > total:
        return f"ERROR: 第 {n} 次评估不存在 (共 {total} 次)"
    if m < 1 or m > total:
        return f"ERROR: 第 {m} 次评估不存在 (共 {total} 次)"

    rec_n = records[n - 1]
    rec_m = records[m - 1]

    lines: List[str] = []
    lines.append(f"## 评估对比: 第 {n} 次 vs 第 {m} 次")
    lines.append("")
    lines.append("> **注意**: 当前仅对比聚合指标（通过率/通过数/违规数）。")
    lines.append("> case-level 差异（新增失败/回归修复/分类维度 delta）待 history 扩展后支持。")
    lines.append("")

    time_n = rec_n.get("eval_time", "N/A")[:19]
    time_m = rec_m.get("eval_time", "N/A")[:19]
    lines.append(f"| 指标 | 第 {n} 次 ({time_n}) | 第 {m} 次 ({time_m}) | Delta |")
    lines.append("|------|---------------------|---------------------|-------|")

    # 通过率
    rate_n = rec_n.get("pass_rate", 0.0)
    rate_m = rec_m.get("pass_rate", 0.0)
    lines.append(
        f"| 通过率 | {_fmt_pct(rate_n)} | {_fmt_pct(rate_m)} | {_delta_arrow(rate_m, rate_n)} |"
    )

    # 正向通过
    passed_n = rec_n.get("total_passed", 0)
    passed_m = rec_m.get("total_passed", 0)
    lines.append(
        f"| 正向通过数 | {passed_n} | {passed_m} | {passed_m - passed_n:+d} |"
    )

    # 正向总数
    pos_n = rec_n.get("total_positive", 0)
    pos_m = rec_m.get("total_positive", 0)
    lines.append(
        f"| 正向总数 | {pos_n} | {pos_m} | {pos_m - pos_n:+d} |"
    )

    # 违规数
    viol_n = rec_n.get("total_violations", 0)
    viol_m = rec_m.get("total_violations", 0)
    lines.append(
        f"| 违规数 | {viol_n} | {viol_m} | {viol_m - viol_n:+d} |"
    )

    # 违规率
    vrate_n = rec_n.get("violation_rate", 0.0)
    vrate_m = rec_m.get("violation_rate", 0.0)
    lines.append(
        f"| 违规率 | {_fmt_pct(vrate_n)} | {_fmt_pct(vrate_m)} | {_delta_arrow(vrate_m, vrate_n)} |"
    )

    lines.append("")

    # 环境信息对比
    env_n = rec_n.get("env_info", {})
    env_m = rec_m.get("env_info", {})
    if isinstance(env_n, dict) and isinstance(env_m, dict):
        commit_n = env_n.get("git_commit", "-")
        commit_m = env_m.get("git_commit", "-")
        model_n = env_n.get("model", "-")
        model_m = env_m.get("model", "-")

        if commit_n != commit_m or model_n != model_m:
            lines.append("### 环境变化")
            lines.append("")
            if commit_n != commit_m:
                lines.append(f"- Commit: {commit_n} -> {commit_m}")
            if model_n != model_m:
                lines.append(f"- Model: {model_n} -> {model_m}")
            lines.append("")

    return "\n".join(lines)


# ── 主入口 ──


def main() -> None:
    parser = argparse.ArgumentParser(
        description="评估趋势对比工具 — 读取 history.json，输出趋势和差异",
    )
    parser.add_argument(
        "--history",
        default=str(_get_default_history_path()),
        help="history.json 路径 (默认 data/eval_reports/history.json)",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=10,
        metavar="N",
        help="显示最近 N 次趋势 (默认 10)",
    )
    parser.add_argument(
        "--diff",
        nargs=2,
        type=int,
        metavar=("N", "M"),
        help="对比第 N 次和第 M 次的详细差异 (1-indexed)",
    )

    args = parser.parse_args()

    records = load_history(args.history)

    if args.diff:
        output = print_diff(records, args.diff[0], args.diff[1])
    else:
        output = print_trend(records, last_n=args.last)

    print(output)


if __name__ == "__main__":
    main()
