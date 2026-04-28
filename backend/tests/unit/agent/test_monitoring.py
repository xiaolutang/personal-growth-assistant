"""Agent 监控指标与告警系统 单元测试

覆盖:
- AgentMetrics 各指标计算
- AlertRule 规则触发
- AlertEngine 内置规则 + 自定义规则
- MetricsReport 日报/周报格式
- 边界: 空数据、单次调用、大量数据
"""

from datetime import date

import pytest

from app.agent.monitoring import (
    AgentMetrics,
    Alert,
    AlertEngine,
    AlertRule,
    MetricsReport,
)


# ── AgentMetrics 测试 ──


class TestAgentMetrics:
    """AgentMetrics 指标计算测试"""

    def test_empty_metrics(self):
        """空数据时所有指标返回 0"""
        metrics = AgentMetrics()
        assert metrics.get_tool_selection_accuracy() == 0.0
        assert metrics.get_param_extraction_accuracy() == 0.0
        assert metrics.get_average_latency() == 0.0
        assert metrics.get_total_tokens() == 0
        assert metrics.get_ask_user_accuracy() == 0.0
        assert metrics.get_tool_call_count() == 0
        assert metrics.get_ask_user_count() == 0

    def test_single_tool_call(self):
        """单次调用各指标正确"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "create_entry", correct=True, latency_ms=200.0, tokens_used=150
        )

        assert metrics.get_tool_selection_accuracy() == 1.0
        assert metrics.get_param_extraction_accuracy() == 1.0
        assert metrics.get_average_latency() == 200.0
        assert metrics.get_total_tokens() == 150
        assert metrics.get_tool_call_count() == 1

    def test_tool_selection_accuracy(self):
        """工具选择准确率计算"""
        metrics = AgentMetrics()
        metrics.record_tool_call("create_entry", correct=True, latency_ms=100.0)
        metrics.record_tool_call("delete_entry", correct=True, latency_ms=100.0)
        metrics.record_tool_call("search_entries", correct=False, latency_ms=100.0)
        metrics.record_tool_call("update_entry", correct=True, latency_ms=100.0)

        accuracy = metrics.get_tool_selection_accuracy()
        assert accuracy == pytest.approx(0.75)

    def test_param_extraction_accuracy(self):
        """参数提取准确率计算"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "create_entry", correct=True, latency_ms=100.0, params_correct=True
        )
        metrics.record_tool_call(
            "update_entry", correct=True, latency_ms=100.0, params_correct=False
        )
        metrics.record_tool_call(
            "search_entries", correct=True, latency_ms=100.0, params_correct=True
        )

        accuracy = metrics.get_param_extraction_accuracy()
        assert accuracy == pytest.approx(2 / 3)

    def test_average_latency(self):
        """平均延迟计算"""
        metrics = AgentMetrics()
        metrics.record_tool_call("t1", correct=True, latency_ms=100.0)
        metrics.record_tool_call("t2", correct=True, latency_ms=300.0)
        metrics.record_tool_call("t3", correct=True, latency_ms=500.0)

        avg = metrics.get_average_latency()
        assert avg == pytest.approx(300.0)

    def test_total_tokens(self):
        """Token 消耗累加"""
        metrics = AgentMetrics()
        metrics.record_tool_call("t1", correct=True, latency_ms=100.0, tokens_used=100)
        metrics.record_tool_call("t2", correct=True, latency_ms=100.0, tokens_used=200)
        metrics.record_tool_call("t3", correct=True, latency_ms=100.0, tokens_used=300)

        assert metrics.get_total_tokens() == 600

    def test_ask_user_accuracy(self):
        """追问准确率"""
        metrics = AgentMetrics()
        metrics.record_ask_user(was_necessary=True)
        metrics.record_ask_user(was_necessary=True)
        metrics.record_ask_user(was_necessary=False)
        metrics.record_ask_user(was_necessary=True)

        assert metrics.get_ask_user_accuracy() == pytest.approx(0.75)

    def test_ask_user_empty(self):
        """无追问记录时准确率为 0"""
        metrics = AgentMetrics()
        assert metrics.get_ask_user_accuracy() == 0.0

    def test_tool_breakdown(self):
        """按工具名分组统计"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "create_entry", correct=True, latency_ms=100.0, tokens_used=50
        )
        metrics.record_tool_call(
            "create_entry", correct=False, latency_ms=200.0, tokens_used=80
        )
        metrics.record_tool_call(
            "search_entries", correct=True, latency_ms=150.0, tokens_used=100
        )

        breakdown = metrics.get_tool_breakdown()
        assert "create_entry" in breakdown
        assert "search_entries" in breakdown

        create_stats = breakdown["create_entry"]
        assert create_stats["count"] == 2
        assert create_stats["correct"] == 1
        assert create_stats["accuracy"] == pytest.approx(0.5)
        assert create_stats["avg_latency"] == pytest.approx(150.0)
        assert create_stats["total_tokens"] == 130

        search_stats = breakdown["search_entries"]
        assert search_stats["count"] == 1
        assert search_stats["correct"] == 1
        assert search_stats["accuracy"] == 1.0

    def test_get_summary(self):
        """汇总包含所有指标"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "create_entry", correct=True, latency_ms=100.0, tokens_used=50
        )
        metrics.record_ask_user(was_necessary=True)

        summary = metrics.get_summary()
        assert "tool_selection_accuracy" in summary
        assert "param_extraction_accuracy" in summary
        assert "average_latency_ms" in summary
        assert "total_tokens" in summary
        assert "ask_user_accuracy" in summary
        assert "tool_call_count" in summary
        assert "ask_user_count" in summary
        assert "tool_breakdown" in summary

        assert summary["tool_call_count"] == 1
        assert summary["ask_user_count"] == 1

    def test_large_data(self):
        """大量数据性能测试"""
        metrics = AgentMetrics()
        for i in range(1000):
            correct = i % 10 != 0  # 90% 准确率
            metrics.record_tool_call(
                f"tool_{i % 5}",
                correct=correct,
                latency_ms=float(100 + i),
                tokens_used=50 + i,
            )

        assert metrics.get_tool_call_count() == 1000
        accuracy = metrics.get_tool_selection_accuracy()
        assert accuracy == pytest.approx(0.9)

    def test_previous_week_tokens(self):
        """上周 token 对比"""
        metrics = AgentMetrics()
        metrics.set_weekly_tokens("2026-W16", 5000)
        metrics.set_weekly_tokens("2026-W17", 10000)

        # 查询 W17 的上周（W16）
        prev = metrics.get_previous_week_tokens("2026-W17")
        assert prev == 5000

    def test_previous_week_tokens_no_data(self):
        """无历史周数据时返回 0"""
        metrics = AgentMetrics()
        assert metrics.get_previous_week_tokens("2026-W17") == 0

    def test_previous_week_tokens_invalid_key(self):
        """无效的 week_key 返回 0"""
        metrics = AgentMetrics()
        assert metrics.get_previous_week_tokens("invalid") == 0


# ── AlertRule 测试 ──


class TestAlertRule:
    """告警规则触发测试"""

    def test_rule_triggered(self):
        """规则条件满足时触发"""
        rule = AlertRule(
            name="test_rule",
            condition=lambda m: m.get("value", 0) < 10,
            message="Value is too low",
            severity="medium",
        )
        assert rule.condition({"value": 5}) is True
        assert rule.condition({"value": 15}) is False

    def test_rule_default_severity(self):
        """默认严重程度为 medium"""
        rule = AlertRule(
            name="test",
            condition=lambda m: False,
            message="test",
        )
        assert rule.severity == "medium"


# ── AlertEngine 测试 ──


class TestAlertEngine:
    """告警引擎测试"""

    def test_builtin_rules_count(self):
        """内置 4 条规则"""
        engine = AlertEngine()
        assert len(engine.get_rules()) == 4

    def test_no_alerts_when_healthy(self):
        """指标健康时无告警"""
        metrics = AgentMetrics()
        for _ in range(10):
            metrics.record_tool_call(
                "create_entry", correct=True, latency_ms=500.0, tokens_used=100
            )

        engine = AlertEngine()
        alerts = engine.check_rules(metrics)
        assert len(alerts) == 0

    def test_tool_selection_low_alert(self):
        """工具选择准确率 < 85% 触发告警"""
        metrics = AgentMetrics()
        for i in range(10):
            correct = i < 7  # 70% 准确率
            metrics.record_tool_call("tool", correct=correct, latency_ms=100.0)

        engine = AlertEngine()
        alerts = engine.check_rules(metrics)
        alert_names = [a.rule_name for a in alerts]
        assert "tool_selection_low" in alert_names

        tool_alert = next(a for a in alerts if a.rule_name == "tool_selection_low")
        assert tool_alert.severity == "medium"

    def test_param_extraction_low_alert(self):
        """参数提取准确率 < 85% 触发告警"""
        metrics = AgentMetrics()
        for i in range(10):
            params_correct = i < 8  # 80% 准确率
            metrics.record_tool_call(
                "tool", correct=True, latency_ms=100.0, params_correct=params_correct
            )

        engine = AlertEngine()
        alerts = engine.check_rules(metrics)
        alert_names = [a.rule_name for a in alerts]
        assert "param_extraction_low" in alert_names

    def test_high_latency_alert(self):
        """平均延迟 > 3000ms 触发告警"""
        metrics = AgentMetrics()
        metrics.record_tool_call("tool", correct=True, latency_ms=5000.0)

        engine = AlertEngine()
        alerts = engine.check_rules(metrics)
        alert_names = [a.rule_name for a in alerts]
        assert "high_latency" in alert_names

        latency_alert = next(a for a in alerts if a.rule_name == "high_latency")
        assert latency_alert.severity == "high"

    def test_token_spike_alert(self):
        """Token 突增 > 2x 触发告警"""
        metrics = AgentMetrics()
        # 上周 100 tokens
        metrics.set_weekly_tokens("2026-W16", 100)
        # 本周消费 300 tokens（3x 突增）
        metrics.record_tool_call("tool", correct=True, latency_ms=100.0, tokens_used=300)

        engine = AlertEngine()
        # 手动注入当前周信息以触发检测
        # AlertEngine 使用 date.today()，这里通过 set_weekly_tokens 设置上周数据
        # 由于 date.today() 可能不是 W17，直接设置一个足够远的上周
        # 更好的方式是直接验证 condition 逻辑
        import datetime

        today = date.today()
        iso = today.isocalendar()
        current_week_key = f"{iso[0]}-W{iso[1]:02d}"

        # 设置上周数据
        metrics_prev = AgentMetrics()
        metrics_prev.set_weekly_tokens(
            current_week_key, 0
        )  # 确保 get_previous_week_tokens 可工作

        # 使用另一个 metrics 设置上周历史
        metrics2 = AgentMetrics()
        # 设置上周 token 为 100
        monday = today - datetime.timedelta(days=today.weekday())
        last_monday = monday - datetime.timedelta(days=7)
        last_iso = last_monday.isocalendar()
        last_week_key = f"{last_iso[0]}-W{last_iso[1]:02d}"
        metrics2.set_weekly_tokens(last_week_key, 100)

        # 本周消费 300
        metrics2.record_tool_call(
            "tool", correct=True, latency_ms=100.0, tokens_used=300
        )

        alerts = engine.check_rules(metrics2)
        alert_names = [a.rule_name for a in alerts]
        assert "token_spike" in alert_names

    def test_no_token_spike_when_no_previous(self):
        """无上周数据时不触发 token 突增告警"""
        metrics = AgentMetrics()
        metrics.record_tool_call("tool", correct=True, latency_ms=100.0, tokens_used=300)

        engine = AlertEngine()
        alerts = engine.check_rules(metrics)
        alert_names = [a.rule_name for a in alerts]
        assert "token_spike" not in alert_names

    def test_custom_rule(self):
        """自定义规则注册和触发"""
        engine = AlertEngine()
        custom_rule = AlertRule(
            name="custom_check",
            condition=lambda m: m.get("tool_call_count", 0) > 100,
            message="Tool call count exceeds 100",
            severity="critical",
        )
        engine.add_rule(custom_rule)
        assert len(engine.get_rules()) == 5

        metrics = AgentMetrics()
        for i in range(110):
            metrics.record_tool_call("tool", correct=True, latency_ms=100.0)

        alerts = engine.check_rules(metrics)
        alert_names = [a.rule_name for a in alerts]
        assert "custom_check" in alert_names

    def test_custom_rule_not_triggered(self):
        """自定义规则不满足时不触发"""
        engine = AlertEngine()
        custom_rule = AlertRule(
            name="custom_check",
            condition=lambda m: m.get("tool_call_count", 0) > 100,
            message="Tool call count exceeds 100",
            severity="critical",
        )
        engine.add_rule(custom_rule)

        metrics = AgentMetrics()
        metrics.record_tool_call("tool", correct=True, latency_ms=100.0)

        alerts = engine.check_rules(metrics)
        alert_names = [a.rule_name for a in alerts]
        assert "custom_check" not in alert_names

    def test_multiple_alerts(self):
        """多个规则同时触发"""
        metrics = AgentMetrics()
        # 低准确率 + 高延迟
        for i in range(10):
            correct = i < 5  # 50% 准确率
            metrics.record_tool_call("tool", correct=correct, latency_ms=5000.0)

        engine = AlertEngine()
        alerts = engine.check_rules(metrics)
        alert_names = [a.rule_name for a in alerts]
        assert "tool_selection_low" in alert_names
        assert "high_latency" in alert_names
        assert len(alerts) >= 2

    def test_alert_has_correct_structure(self):
        """告警结构包含必要字段"""
        metrics = AgentMetrics()
        metrics.record_tool_call("tool", correct=False, latency_ms=100.0)

        engine = AlertEngine()
        alerts = engine.check_rules(metrics)
        if alerts:
            alert = alerts[0]
            assert hasattr(alert, "rule_name")
            assert hasattr(alert, "severity")
            assert hasattr(alert, "message")
            assert hasattr(alert, "details")
            assert alert.severity in ("low", "medium", "high", "critical")


# ── MetricsReport 测试 ──


class TestMetricsReport:
    """报告生成测试"""

    def test_daily_report_format(self):
        """日报格式正确"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "create_entry", correct=True, latency_ms=200.0, tokens_used=100
        )
        metrics.record_ask_user(was_necessary=True)

        report = MetricsReport()
        result = report.daily_report(metrics, date(2026, 4, 28))

        assert result["report_type"] == "daily"
        assert result["date"] == "2026-04-28"
        assert "metrics" in result
        assert "alerts" in result
        assert "alert_count" in result
        assert "suggestions" in result
        assert isinstance(result["alerts"], list)
        assert isinstance(result["suggestions"], list)

    def test_daily_report_default_date(self):
        """日报默认使用今天"""
        metrics = AgentMetrics()
        report = MetricsReport()
        result = report.daily_report(metrics)

        assert result["date"] == date.today().isoformat()

    def test_weekly_report_format(self):
        """周报格式正确"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "search_entries", correct=True, latency_ms=300.0, tokens_used=200
        )

        report = MetricsReport()
        result = report.weekly_report(metrics, date(2026, 4, 27))

        assert result["report_type"] == "weekly"
        assert "week" in result
        assert "date_range" in result
        assert "metrics" in result
        assert "alerts" in result
        assert "alert_count" in result
        assert "suggestions" in result

    def test_weekly_report_default_week(self):
        """周报默认使用本周"""
        metrics = AgentMetrics()
        report = MetricsReport()
        result = report.weekly_report(metrics)

        today = date.today()
        week_start = today - __import__("datetime").timedelta(days=today.weekday())
        assert result["date_range"].startswith(week_start.isoformat())

    def test_daily_report_with_alerts(self):
        """日报包含告警"""
        metrics = AgentMetrics()
        for i in range(10):
            correct = i < 5  # 50% 准确率
            metrics.record_tool_call("tool", correct=correct, latency_ms=5000.0)

        report = MetricsReport()
        result = report.daily_report(metrics, date(2026, 4, 28))

        assert result["alert_count"] > 0
        assert len(result["alerts"]) > 0

        # 检查告警结构
        alert = result["alerts"][0]
        assert "rule_name" in alert
        assert "severity" in alert
        assert "message" in alert

    def test_daily_report_serializable(self):
        """日报可序列化（纯 dict 结构）"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "tool", correct=True, latency_ms=100.0, tokens_used=50
        )

        report = MetricsReport()
        result = report.daily_report(metrics)

        # 确保可 JSON 序列化
        import json

        serialized = json.dumps(result, ensure_ascii=False)
        assert isinstance(serialized, str)
        deserialized = json.loads(serialized)
        assert deserialized["report_type"] == "daily"

    def test_weekly_report_serializable(self):
        """周报可序列化"""
        metrics = AgentMetrics()
        metrics.record_tool_call(
            "tool", correct=True, latency_ms=100.0, tokens_used=50
        )

        report = MetricsReport()
        result = report.weekly_report(metrics)

        import json

        serialized = json.dumps(result, ensure_ascii=False)
        assert isinstance(serialized, str)

    def test_suggestions_healthy(self):
        """健康状态下建议正常"""
        metrics = AgentMetrics()
        for _ in range(10):
            metrics.record_tool_call(
                "tool", correct=True, latency_ms=500.0, tokens_used=100
            )

        report = MetricsReport()
        result = report.daily_report(metrics)

        assert any("正常" in s or "良好" in s for s in result["suggestions"])

    def test_suggestions_empty_data(self):
        """空数据时有提示建议"""
        metrics = AgentMetrics()
        report = MetricsReport()
        result = report.daily_report(metrics)

        assert len(result["suggestions"]) > 0
        assert any("暂无" in s or "检查" in s for s in result["suggestions"])

    def test_suggestions_low_accuracy(self):
        """低准确率时有优化建议"""
        metrics = AgentMetrics()
        for i in range(10):
            correct = i < 5
            metrics.record_tool_call("tool", correct=correct, latency_ms=100.0)

        report = MetricsReport()
        result = report.daily_report(metrics)

        assert any("准确率" in s for s in result["suggestions"])

    def test_suggestions_high_latency(self):
        """高延迟时有优化建议"""
        metrics = AgentMetrics()
        metrics.record_tool_call("tool", correct=True, latency_ms=5000.0)

        report = MetricsReport()
        result = report.daily_report(metrics)

        assert any("延迟" in s for s in result["suggestions"])

    def test_custom_alert_engine(self):
        """报告使用自定义告警引擎"""
        engine = AlertEngine()
        engine.add_rule(
            AlertRule(
                name="always_fire",
                condition=lambda m: True,
                message="Always fires",
                severity="low",
            )
        )

        metrics = AgentMetrics()
        metrics.record_tool_call("tool", correct=True, latency_ms=100.0)

        report = MetricsReport(alert_engine=engine)
        result = report.daily_report(metrics)

        assert result["alert_count"] >= 1
        alert_names = [a["rule_name"] for a in result["alerts"]]
        assert "always_fire" in alert_names
