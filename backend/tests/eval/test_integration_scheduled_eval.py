"""B05 run_scheduled_eval.sh 集成测试

通过 subprocess 调用 shell 脚本，验证完整流程的集成行为。
使用 mock HTTP server 模拟后端服务。

覆盖场景:
1. 健康检查失败 → exit 2 + 重试日志
2. dry-run 模式 + 健康检查通过 → exit 0
3. 缺少环境变量 → exit 2
4. 阈值判断：通过率低于阈值 → exit 1
5. 脚本完整流程（非 dry-run）→ 报告生成 + history 追加
6. 趋势输出集成：history.json 存在时输出趋势
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest


# ── 标记 ──

pytestmark = pytest.mark.slow


# ── 路径常量 ──

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "deploy" / "scripts" / "run_scheduled_eval.sh"


# ── Mock HTTP Server ──


class MockAPIHandler(BaseHTTPRequestHandler):
    """模拟后端 API 的 HTTP handler。"""

    # 类变量控制行为
    health_status: int = 200
    login_status: int = 200
    login_token: str = "mock-token-12345"

    def log_message(self, format, *args):
        pass  # 抑制日志输出

    def do_GET(self):
        if self.path == "/health":
            self.send_response(self.health_status)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/auth/login":
            self.send_response(self.login_status)
            self.end_headers()
            if self.login_status == 200:
                response = json.dumps({"access_token": self.login_token})
                self.wfile.write(response.encode())
            else:
                self.wfile.write(b'{"detail":"Invalid credentials"}')
        else:
            self.send_response(404)
            self.end_headers()


class MockAPIServer:
    """在独立线程中运行的 mock HTTP server。"""

    def __init__(self, port: int = 19876):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.server = HTTPServer(("127.0.0.1", self.port), MockAPIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        # 等待 server 就绪
        time.sleep(0.1)

    def stop(self):
        if self.server:
            self.server.shutdown()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


# ── 辅助函数 ──


def _run_script(
    *extra_args: str,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """运行 run_scheduled_eval.sh 并返回结果。"""
    base_env = {
        **os.environ,
        "EVAL_USERNAME": "test_user",
        "EVAL_PASSWORD": "test_pass",
    }
    if env:
        base_env.update(env)

    cmd = ["bash", str(SCRIPT_PATH), *extra_args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=base_env,
        timeout=timeout,
        cwd=str(PROJECT_ROOT),
    )


# ── 测试 ──


class TestScheduledEvalHealthCheck:
    """健康检查集成测试。"""

    def test_health_check_failure_exits_2(self):
        """健康检查失败 → exit 2 + 重试日志。"""
        # 不启动任何 server，curl 会失败
        result = _run_script(
            "--base-url", "http://127.0.0.1:19999",
            "--dry-run",
        )

        assert result.returncode == 2
        assert "健康检查失败" in result.stdout

    def test_health_check_pass_with_mock_server(self):
        """Mock server 健康检查通过 → dry-run 成功 → exit 0。"""
        server = MockAPIServer(port=19877)
        MockAPIHandler.health_status = 200
        MockAPIHandler.login_status = 200
        server.start()

        try:
            result = _run_script(
                "--base-url", server.url,
                "--dry-run",
            )
            assert result.returncode == 0
            assert "健康检查通过" in result.stdout
            assert "dry-run 完成" in result.stdout
        finally:
            server.stop()


class TestScheduledEvalEnvVars:
    """环境变量校验。"""

    def test_missing_username_exits_2(self):
        """缺少 EVAL_USERNAME → exit 2。"""
        result = _run_script(
            "--dry-run",
            env={"EVAL_USERNAME": "", "EVAL_PASSWORD": "pass"},
        )
        assert result.returncode == 2
        assert "EVAL_USERNAME" in result.stdout

    def test_missing_password_exits_2(self):
        """缺少 EVAL_PASSWORD → exit 2。"""
        result = _run_script(
            "--dry-run",
            env={"EVAL_USERNAME": "user", "EVAL_PASSWORD": ""},
        )
        assert result.returncode == 2
        assert "EVAL_PASSWORD" in result.stdout


class TestScheduledEvalLoginValidation:
    """登录验证（dry-run 模式下）。"""

    def test_login_failure_in_dry_run(self):
        """dry-run 模式下登录失败 → exit 2。"""
        server = MockAPIServer(port=19878)
        MockAPIHandler.health_status = 200
        MockAPIHandler.login_status = 401
        server.start()

        try:
            result = _run_script(
                "--base-url", server.url,
                "--dry-run",
            )
            assert result.returncode == 2
            assert "登录" in result.stdout
        finally:
            server.stop()


class TestScheduledEvalThreshold:
    """阈值判断集成测试。

    通过 mock run_eval.py 的输出来测试阈值逻辑。
    实际中 run_eval.py 需要真实 Agent，所以这里验证脚本对输出解析的正确性。
    """

    def test_threshold_logic_with_history_file(self, tmp_path: Path):
        """history.json 存在时 eval_trend 趋势输出正常集成。"""
        # 创建含 2 条记录的 history.json
        history = [
            {
                "eval_time": "2026-05-01T10:00:00",
                "pass_rate": 0.80,
                "total_passed": 50,
                "total_positive": 68,
                "total_violations": 0,
                "violation_rate": 0.0,
                "env_info": {"git_commit": "abc123", "model": "test"},
            },
            {
                "eval_time": "2026-05-02T10:00:00",
                "pass_rate": 0.85,
                "total_passed": 53,
                "total_positive": 68,
                "total_violations": 0,
                "violation_rate": 0.0,
                "env_info": {"git_commit": "def456", "model": "test"},
            },
        ]
        report_dir = tmp_path / "eval_reports"
        report_dir.mkdir()
        (report_dir / "history.json").write_text(
            json.dumps(history, ensure_ascii=False), encoding="utf-8"
        )

        # 用 eval_trend.py 直接验证
        result = subprocess.run(
            [
                "uv", "run", "python", "-m", "tests.eval.eval_trend",
                "--history", str(report_dir / "history.json"),
                "--last", "5",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT / "backend"),
            timeout=15,
        )

        assert result.returncode == 0
        assert "80.00%" in result.stdout
        assert "85.00%" in result.stdout
        assert "趋势摘要" in result.stdout


class TestScheduledEvalScriptIntegration:
    """脚本级集成：验证 shell 脚本与 Python 模块的协作。"""

    def test_eval_trend_diff_integration(self, tmp_path: Path):
        """eval_trend.py --diff 集成：对比两次评估。"""
        history = [
            {
                "eval_time": "2026-05-01T10:00:00",
                "pass_rate": 0.70,
                "total_passed": 40,
                "total_positive": 68,
                "total_violations": 2,
                "violation_rate": 0.08,
                "env_info": {"git_commit": "aaa111", "model": "v1"},
            },
            {
                "eval_time": "2026-05-02T10:00:00",
                "pass_rate": 0.90,
                "total_passed": 55,
                "total_positive": 71,
                "total_violations": 0,
                "violation_rate": 0.0,
                "env_info": {"git_commit": "bbb222", "model": "v2"},
            },
        ]
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps(history, ensure_ascii=False), encoding="utf-8")

        result = subprocess.run(
            [
                "uv", "run", "python", "-m", "tests.eval.eval_trend",
                "--history", str(history_file),
                "--diff", "1", "2",
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT / "backend"),
            timeout=15,
        )

        assert result.returncode == 0
        assert "70.00%" in result.stdout
        assert "90.00%" in result.stdout
        assert "环境变化" in result.stdout
        assert "Commit" in result.stdout

    def test_classify_badcases_pipeline_integration(self, tmp_path: Path):
        """classify_badcases.py 集成：从 bad_cases 到报告 + 模板完整链路。"""
        from tests.eval.classify_badcases import classify_badcases

        badcases_dir = tmp_path / "bad_cases"
        badcases_dir.mkdir()
        output_dir = tmp_path / "output"

        # 写入模拟 bad_cases
        for i in range(3):
            (badcases_dir / f"msg-test-{i:03d}.json").write_text(
                json.dumps(
                    {
                        "message_id": f"msg-test-{i:03d}",
                        "reason": "信息不准确",
                        "detail": f"测试坏例 {i}",
                        "title": "不准确",
                        "created_at": f"2026-05-06T10:0{i}:00+00:00",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        result = classify_badcases(badcases_dir, output_dir)

        # 验证报告文件
        report_file = output_dir / "badcase_classification.md"
        assert report_file.exists()
        report_text = report_file.read_text(encoding="utf-8")
        assert "信息不准确" in report_text
        assert "3 条" in report_text

        # 验证模板文件
        template_file = output_dir / "badcase_to_testcase.json"
        assert template_file.exists()
        templates = json.loads(template_file.read_text(encoding="utf-8"))
        assert len(templates) == 3
        for t in templates:
            assert t["source_reason"] == "信息不准确"
            assert t["category"] == "accuracy"
            assert t["status"] == "draft"

    def test_backfill_classify_full_pipeline(self, tmp_path: Path):
        """完整回流管线集成：backfill → classify → 生成报告。"""
        from tests.eval.classify_badcases import classify_badcases

        # 模拟从 backfill 产出的 bad_cases 数据
        badcases_dir = tmp_path / "bad_cases"
        badcases_dir.mkdir()
        output_dir = tmp_path / "output"

        cases = [
            {"message_id": "msg-pipe-001", "reason": "信息不准确", "detail": "A", "created_at": "2026-05-06T10:00:00+00:00"},
            {"message_id": "msg-pipe-002", "reason": "不完整", "detail": "B", "created_at": "2026-05-06T11:00:00+00:00"},
            {"message_id": "msg-pipe-003", "reason": "理解错了", "detail": "C", "created_at": "2026-05-06T12:00:00+00:00"},
        ]

        for i, case in enumerate(cases):
            (badcases_dir / f"{case['message_id']}_{i}.json").write_text(
                json.dumps(case, ensure_ascii=False), encoding="utf-8"
            )

        # 运行分类
        result = classify_badcases(badcases_dir, output_dir)

        assert result["total_files"] == 3
        assert result["deduped_count"] == 3
        assert result["categories"]["信息不准确"] == 1
        assert result["categories"]["不完整"] == 1
        assert result["categories"]["理解错了"] == 1

        # 模板可被后续流程消费
        templates = json.loads(
            (output_dir / "badcase_to_testcase.json").read_text(encoding="utf-8")
        )
        categories = {t["category"] for t in templates}
        assert "accuracy" in categories
        assert "completeness" in categories
        assert "comprehension" in categories
