"""eval_trend.py 测试

覆盖:
- print_trend 趋势输出（5 条记录、单条记录、空数据）
- load_history 损坏 JSON 处理
- print_diff 差异对比
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from tests.eval.eval_trend import load_history, print_diff, print_trend


# ── Fixtures ──


def _make_records(count: int = 5) -> List[Dict[str, Any]]:
    """构造 count 条历史记录，通过率递增"""
    records = []
    base_rate = 0.70
    for i in range(count):
        rate = round(base_rate + i * 0.03, 4)
        passed = int(68 * rate)
        records.append({
            "eval_time": f"2026-04-29T{10 + i:02d}:00:00",
            "dataset_mode": "all",
            "pass_rate": rate,
            "total_positive": 68,
            "total_passed": passed,
            "total_negative": 24,
            "total_violations": i,
            "violation_rate": round(i / 24, 4) if i > 0 else 0.0,
            "html_file": f"2026-04-29_{100000 + i}.html",
            "env_info": {"git_commit": "abc1234", "model": "gpt-4o"},
        })
    return records


@pytest.fixture
def history_dir(tmp_path: Path) -> Path:
    """提供临时目录作为 data/eval_reports/"""
    d = tmp_path / "eval_reports"
    d.mkdir()
    return d


# ── print_trend ──


class TestPrintTrend:
    def test_trend_with_data(self):
        """给定 5 条记录，验证趋势输出包含 Markdown 表格和摘要"""
        records = _make_records(5)
        output = print_trend(records, last_n=10)

        assert "## 评估趋势 (最近 5 次)" in output
        assert "| # | 时间 | 通过率 | Delta |" in output
        assert "70.00%" in output
        assert "82.00%" in output
        assert "趋势摘要" in output
        assert "+12.00%" in output  # 0.82 - 0.70

    def test_trend_shows_delta_arrows(self):
        """趋势表中后续行显示 Delta 变化箭头"""
        records = _make_records(3)
        output = print_trend(records, last_n=10)

        # 第一行 delta 为 "-"（无前一次）
        assert "| - |" in output
        # 后续行有变化箭头
        assert "^" in output  # 通过率上升

    def test_trend_single_record(self):
        """单条记录输出当前状态"""
        records = _make_records(1)
        output = print_trend(records, last_n=10)

        assert "## 评估趋势 (最近 1 次)" in output
        assert "当前状态" in output
        assert "70.00%" in output
        # 单条时不应出现 "趋势摘要"
        assert "趋势摘要" not in output

    def test_trend_empty_history(self):
        """空数据输出'无历史数据'"""
        output = print_trend([], last_n=10)
        assert output == "无历史数据"

    def test_trend_last_n_limits_output(self):
        """--last 参数限制显示条数"""
        records = _make_records(20)
        output = print_trend(records, last_n=5)

        assert "最近 5 次" in output
        # 应显示 #16 到 #20（# 号后紧跟数字+空格+时间）
        assert "| 20 |" in output
        # 不应显示 #1 到 #10（通过率值来区分）
        # 前 10 条的通过率范围 70%~97%，后 5 条是 115%~127%
        assert "70.00%" not in output
        assert "82.00%" not in output

    def test_trend_shows_commit_and_violations(self):
        """趋势表包含 Commit 和违规数列"""
        records = _make_records(3)
        output = print_trend(records, last_n=10)

        assert "abc1234" in output  # git commit
        assert "violations" not in output.lower()  # 表头用中文
        # 违规数在表格中显示
        lines = output.split("\n")
        data_lines = [l for l in lines if l.startswith("|") and "abc1234" in l]
        assert len(data_lines) > 0


# ── load_history ──


class TestLoadHistory:
    def test_corrupt_history_returns_empty(self, history_dir: Path):
        """JSON 解析失败时返回空列表并警告"""
        history_file = history_dir / "history.json"
        history_file.write_text("{invalid json content", encoding="utf-8")

        result = load_history(history_dir)
        assert result == []

    def test_nonexistent_returns_empty(self, history_dir: Path):
        """文件不存在时返回空列表"""
        result = load_history(history_dir / "nonexistent")
        assert result == []

    def test_valid_json_returns_records(self, history_dir: Path):
        """合法 JSON 返回记录列表"""
        records = _make_records(3)
        history_file = history_dir / "history.json"
        history_file.write_text(json.dumps(records), encoding="utf-8")

        result = load_history(history_dir)
        assert len(result) == 3
        assert result[0]["pass_rate"] == 0.70

    def test_non_array_json_returns_empty(self, history_dir: Path):
        """非数组 JSON 返回空列表并警告"""
        history_file = history_dir / "history.json"
        history_file.write_text('{"key": "value"}', encoding="utf-8")

        result = load_history(history_dir)
        assert result == []


# ── print_diff ──


class TestPrintDiff:
    def test_diff_output(self):
        """--diff 2 3 输出正确差异"""
        records = _make_records(5)
        output = print_diff(records, 2, 3)

        assert "## 评估对比: 第 2 次 vs 第 3 次" in output
        assert "通过率" in output
        assert "73.00%" in output  # 第 2 次
        assert "76.00%" in output  # 第 3 次
        assert "正向通过数" in output
        assert "违规数" in output
        assert "违规率" in output

    def test_diff_shows_delta(self):
        """diff 输出包含 Delta 列"""
        records = _make_records(5)
        output = print_diff(records, 1, 5)

        # 通过率从 70% 到 82%, delta = +12%
        assert "+12.00%" in output

    def test_diff_empty_history(self):
        """空数据输出'无历史数据'"""
        output = print_diff([], 1, 2)
        assert output == "无历史数据"

    def test_diff_out_of_range(self):
        """超出范围的索引返回错误信息"""
        records = _make_records(3)
        output = print_diff(records, 1, 10)
        assert "ERROR" in output
        assert "第 10 次评估不存在" in output

    def test_diff_same_env_no_change(self):
        """相同环境信息时不输出环境变化"""
        records = _make_records(3)
        output = print_diff(records, 1, 2)

        # 所有记录 env_info 相同，不应出现环境变化
        assert "环境变化" not in output

    def test_diff_different_env_shows_change(self):
        """不同环境信息时输出环境变化"""
        records = [
            {
                "eval_time": "2026-04-29T10:00:00",
                "dataset_mode": "all",
                "pass_rate": 0.80,
                "total_passed": 54,
                "total_positive": 68,
                "total_negative": 24,
                "total_violations": 0,
                "violation_rate": 0.0,
                "env_info": {"git_commit": "aaa1111", "model": "gpt-4o"},
            },
            {
                "eval_time": "2026-04-30T10:00:00",
                "dataset_mode": "all",
                "pass_rate": 0.85,
                "total_passed": 58,
                "total_positive": 68,
                "total_negative": 24,
                "total_violations": 1,
                "violation_rate": 0.0417,
                "env_info": {"git_commit": "bbb2222", "model": "gpt-4o"},
            },
        ]
        output = print_diff(records, 1, 2)

        assert "环境变化" in output
        assert "aaa1111" in output
        assert "bbb2222" in output

    def test_diff_order_matters(self):
        """diff 第 N 次和第 M 次的顺序影响输出标题"""
        records = _make_records(5)
        output = print_diff(records, 3, 1)

        assert "第 3 次 vs 第 1 次" in output
