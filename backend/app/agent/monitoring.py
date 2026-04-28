"""Agent 监控指标与告警系统

提供 Agent 运行时的关键指标采集、告警规则检查和报告生成功能。

核心组件:
    - AgentMetrics: 指标采集器，记录工具调用、追问行为等
    - AlertRule: 告警规则定义
    - AlertEngine: 告警引擎，检查规则并产生告警
    - MetricsReport: 报告生成器，支持日报/周报

采集指标:
    - 工具选择准确率
    - 参数提取准确率
    - 平均延迟 (ms)
    - Token 消耗总量
    - 追问准确率
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ── 数据记录 ──


class ToolCallRecord(BaseModel):
    """单次工具调用记录"""

    tool_name: str = Field(..., description="工具名称")
    correct: bool = Field(..., description="工具选择是否正确")
    params_correct: bool = Field(default=True, description="参数提取是否正确")
    latency_ms: float = Field(..., description="延迟（毫秒）")
    tokens_used: int = Field(default=0, description="消耗的 token 数")
    timestamp: datetime = Field(default_factory=datetime.now, description="调用时间")


class AskUserRecord(BaseModel):
    """追问行为记录"""

    was_necessary: bool = Field(..., description="追问是否必要")
    timestamp: datetime = Field(default_factory=datetime.now, description="追问时间")


# ── AgentMetrics ── 指标采集器


class AgentMetrics:
    """Agent 指标采集器

    记录工具调用和追问行为，计算各项准确率和性能指标。

    Usage:
        metrics = AgentMetrics()
        metrics.record_tool_call("create_entry", correct=True, latency_ms=150.0, tokens_used=200)
        metrics.record_ask_user(was_necessary=True)

        accuracy = metrics.get_tool_selection_accuracy()
        summary = metrics.get_summary()
    """

    def __init__(self) -> None:
        self._tool_calls: List[ToolCallRecord] = []
        self._ask_user_records: List[AskUserRecord] = []
        # 历史周 token 消耗，用于对比突增检测
        self._weekly_tokens: Dict[str, int] = {}

    def record_tool_call(
        self,
        tool_name: str,
        correct: bool,
        latency_ms: float,
        tokens_used: int = 0,
        params_correct: bool = True,
    ) -> None:
        """记录单次工具调用

        Args:
            tool_name: 工具名称
            correct: 工具选择是否正确
            latency_ms: 延迟毫秒数
            tokens_used: 消耗的 token 数
            params_correct: 参数提取是否正确
        """
        record = ToolCallRecord(
            tool_name=tool_name,
            correct=correct,
            params_correct=params_correct,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        self._tool_calls.append(record)

    def record_ask_user(self, was_necessary: bool) -> None:
        """记录追问行为

        Args:
            was_necessary: 追问是否必要
        """
        record = AskUserRecord(was_necessary=was_necessary)
        self._ask_user_records.append(record)

    def set_weekly_tokens(self, week_key: str, total_tokens: int) -> None:
        """设置历史周的 token 消耗（用于突增检测）

        Args:
            week_key: 周标识，如 "2026-W17"
            total_tokens: 该周总 token 消耗
        """
        self._weekly_tokens[week_key] = total_tokens

    def get_tool_selection_accuracy(self) -> float:
        """工具选择准确率

        Returns:
            准确率 0.0~1.0，无数据时返回 0.0
        """
        if not self._tool_calls:
            return 0.0
        correct_count = sum(1 for r in self._tool_calls if r.correct)
        return correct_count / len(self._tool_calls)

    def get_param_extraction_accuracy(self) -> float:
        """参数提取准确率

        Returns:
            准确率 0.0~1.0，无数据时返回 0.0
        """
        if not self._tool_calls:
            return 0.0
        correct_count = sum(1 for r in self._tool_calls if r.params_correct)
        return correct_count / len(self._tool_calls)

    def get_average_latency(self) -> float:
        """平均延迟（ms）

        Returns:
            平均延迟毫秒数，无数据时返回 0.0
        """
        if not self._tool_calls:
            return 0.0
        total = sum(r.latency_ms for r in self._tool_calls)
        return total / len(self._tool_calls)

    def get_total_tokens(self) -> int:
        """Token 消耗总量

        Returns:
            总 token 数
        """
        return sum(r.tokens_used for r in self._tool_calls)

    def get_ask_user_accuracy(self) -> float:
        """追问准确率（必要追问占比）

        Returns:
            准确率 0.0~1.0，无数据时返回 0.0
        """
        if not self._ask_user_records:
            return 0.0
        necessary_count = sum(1 for r in self._ask_user_records if r.was_necessary)
        return necessary_count / len(self._ask_user_records)

    def get_tool_call_count(self) -> int:
        """工具调用总次数"""
        return len(self._tool_calls)

    def get_ask_user_count(self) -> int:
        """追问总次数"""
        return len(self._ask_user_records)

    def get_tool_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """按工具名称分组的统计

        Returns:
            {tool_name: {count, correct, accuracy, avg_latency, tokens}}
        """
        breakdown: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "correct": 0,
                "total_latency": 0.0,
                "total_tokens": 0,
            }
        )
        for r in self._tool_calls:
            entry = breakdown[r.tool_name]
            entry["count"] += 1
            if r.correct:
                entry["correct"] += 1
            entry["total_latency"] += r.latency_ms
            entry["total_tokens"] += r.tokens_used

        result = {}
        for name, entry in breakdown.items():
            result[name] = {
                "count": entry["count"],
                "correct": entry["correct"],
                "accuracy": entry["correct"] / entry["count"]
                if entry["count"] > 0
                else 0.0,
                "avg_latency": entry["total_latency"] / entry["count"]
                if entry["count"] > 0
                else 0.0,
                "total_tokens": entry["total_tokens"],
            }
        return result

    def get_previous_week_tokens(self, current_week_key: str) -> int:
        """获取上一周的 token 消耗

        Args:
            current_week_key: 当前周标识，如 "2026-W17"

        Returns:
            上一周 token 消耗，无数据时返回 0
        """
        # 从 week_key 解析出周一日期，减 7 天得到上周
        try:
            parts = current_week_key.split("-W")
            year = int(parts[0])
            week = int(parts[1])
            monday = date.fromisocalendar(year, week, 1)
            last_monday = monday - timedelta(days=7)
            last_week_key = f"{last_monday.isocalendar()[0]}-W{last_monday.isocalendar()[1]:02d}"
            return self._weekly_tokens.get(last_week_key, 0)
        except (ValueError, IndexError):
            return 0

    def get_summary(self) -> Dict[str, Any]:
        """所有指标汇总

        Returns:
            包含所有核心指标的字典
        """
        return {
            "tool_selection_accuracy": self.get_tool_selection_accuracy(),
            "param_extraction_accuracy": self.get_param_extraction_accuracy(),
            "average_latency_ms": self.get_average_latency(),
            "total_tokens": self.get_total_tokens(),
            "ask_user_accuracy": self.get_ask_user_accuracy(),
            "tool_call_count": self.get_tool_call_count(),
            "ask_user_count": self.get_ask_user_count(),
            "tool_breakdown": self.get_tool_breakdown(),
        }


# ── AlertRule ── 告警规则定义


@dataclass
class AlertRule:
    """告警规则

    Attributes:
        name: 规则名称
        condition: 判断函数，接收 metrics dict，返回 True 表示触发告警
        message: 告警消息模板
        severity: 告警严重程度 low/medium/high/critical
    """

    name: str
    condition: Callable[[Dict[str, Any]], bool]
    message: str
    severity: str = "medium"


# ── AlertEngine ── 告警引擎


@dataclass
class Alert:
    """告警实例"""

    rule_name: str
    severity: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class AlertEngine:
    """告警引擎

    内置 4 条核心告警规则，支持自定义规则注册。

    内置规则:
        - tool_selection_low: 工具选择准确率 < 85% → medium
        - param_extraction_low: 参数提取准确率 < 85% → medium
        - high_latency: 平均延迟 > 3000ms → high
        - token_spike: token 突增 > 2x（与上周比较）→ medium
    """

    def __init__(self) -> None:
        self._rules: List[AlertRule] = []
        self._register_builtin_rules()

    def _register_builtin_rules(self) -> None:
        """注册内置告警规则"""
        self._rules.extend(
            [
                AlertRule(
                    name="tool_selection_low",
                    condition=lambda m: m.get("tool_selection_accuracy", 1.0) < 0.85,
                    message="工具选择准确率低于 85%（当前: {accuracy:.1%}）",
                    severity="medium",
                ),
                AlertRule(
                    name="param_extraction_low",
                    condition=lambda m: m.get("param_extraction_accuracy", 1.0) < 0.85,
                    message="参数提取准确率低于 85%（当前: {accuracy:.1%}）",
                    severity="medium",
                ),
                AlertRule(
                    name="high_latency",
                    condition=lambda m: m.get("average_latency_ms", 0.0) > 3000,
                    message="平均延迟超过 3000ms（当前: {latency:.0f}ms）",
                    severity="high",
                ),
                AlertRule(
                    name="token_spike",
                    condition=lambda m: m.get("token_spike_ratio", 0.0) > 2.0,
                    message="Token 消耗突增超过 2 倍（当前: {ratio:.1f}x）",
                    severity="medium",
                ),
            ]
        )

    def add_rule(self, rule: AlertRule) -> None:
        """注册自定义告警规则

        Args:
            rule: 告警规则实例
        """
        self._rules.append(rule)

    def check_rules(self, metrics: AgentMetrics) -> List[Alert]:
        """检查所有告警规则

        Args:
            metrics: 指标采集器实例

        Returns:
            触发的告警列表
        """
        summary = metrics.get_summary()
        alerts: List[Alert] = []

        # 计算 token 突增比例
        current_date = date.today()
        iso = current_date.isocalendar()
        current_week_key = f"{iso[0]}-W{iso[1]:02d}"
        prev_tokens = metrics.get_previous_week_tokens(current_week_key)
        current_tokens = summary["total_tokens"]
        if prev_tokens > 0:
            spike_ratio = current_tokens / prev_tokens
        else:
            spike_ratio = 0.0

        # 构建检查上下文
        context = {
            **summary,
            "token_spike_ratio": spike_ratio,
        }

        for rule in self._rules:
            try:
                if rule.condition(context):
                    # 格式化消息
                    try:
                        message = rule.message.format(
                            accuracy=summary.get("tool_selection_accuracy", 0),
                            latency=summary.get("average_latency_ms", 0),
                            ratio=spike_ratio,
                        )
                    except (KeyError, IndexError):
                        message = rule.message

                    alerts.append(
                        Alert(
                            rule_name=rule.name,
                            severity=rule.severity,
                            message=message,
                            details=context,
                        )
                    )
            except Exception as e:
                logger.warning("告警规则 '%s' 检查异常: %s", rule.name, e)

        return alerts

    def get_rules(self) -> List[AlertRule]:
        """获取所有已注册的规则列表"""
        return list(self._rules)


# ── MetricsReport ── 报告生成


class MetricsReport:
    """指标报告生成器

    支持生成日报和周报，包含指标趋势、告警列表和建议动作。
    """

    def __init__(self, alert_engine: Optional[AlertEngine] = None) -> None:
        self._alert_engine = alert_engine or AlertEngine()

    def daily_report(
        self, metrics: AgentMetrics, report_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """生成日报

        Args:
            metrics: 指标采集器实例
            report_date: 报告日期，默认今天

        Returns:
            可序列化的日报字典
        """
        if report_date is None:
            report_date = date.today()

        summary = metrics.get_summary()
        alerts = self._alert_engine.check_rules(metrics)

        return {
            "report_type": "daily",
            "date": report_date.isoformat(),
            "metrics": summary,
            "alerts": [
                {
                    "rule_name": a.rule_name,
                    "severity": a.severity,
                    "message": a.message,
                }
                for a in alerts
            ],
            "alert_count": len(alerts),
            "suggestions": self._generate_suggestions(summary, alerts),
        }

    def weekly_report(
        self, metrics: AgentMetrics, week_start: Optional[date] = None
    ) -> Dict[str, Any]:
        """生成周报

        Args:
            metrics: 指标采集器实例
            week_start: 周开始日期，默认本周一

        Returns:
            可序列化的周报字典
        """
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        summary = metrics.get_summary()
        alerts = self._alert_engine.check_rules(metrics)

        iso = week_start.isocalendar()
        week_key = f"{iso[0]}-W{iso[1]:02d}"

        return {
            "report_type": "weekly",
            "week": week_key,
            "date_range": f"{week_start.isoformat()} ~ {week_end.isoformat()}",
            "metrics": summary,
            "alerts": [
                {
                    "rule_name": a.rule_name,
                    "severity": a.severity,
                    "message": a.message,
                }
                for a in alerts
            ],
            "alert_count": len(alerts),
            "suggestions": self._generate_suggestions(summary, alerts),
        }

    def _generate_suggestions(
        self, summary: Dict[str, Any], alerts: List[Alert]
    ) -> List[str]:
        """根据指标和告警生成建议动作

        Args:
            summary: 指标汇总
            alerts: 告警列表

        Returns:
            建议动作列表
        """
        suggestions: List[str] = []

        if not summary.get("tool_call_count", 0):
            suggestions.append("今日暂无工具调用数据，建议检查 Agent 是否正常运行。")
            return suggestions

        # 工具选择准确率低
        tool_acc = summary.get("tool_selection_accuracy", 1.0)
        if tool_acc < 0.85:
            suggestions.append(
                "工具选择准确率偏低，建议优化 system prompt 中的工具描述，"
                "或增加更多 few-shot 示例。"
            )

        # 参数提取准确率低
        param_acc = summary.get("param_extraction_accuracy", 1.0)
        if param_acc < 0.85:
            suggestions.append(
                "参数提取准确率偏低，建议检查工具的参数 schema 定义，"
                "确保参数描述清晰且类型约束合理。"
            )

        # 延迟高
        avg_latency = summary.get("average_latency_ms", 0.0)
        if avg_latency > 3000:
            suggestions.append(
                "平均延迟较高，建议排查 LLM API 响应时间和工具执行耗时，"
                "考虑使用更快的模型或优化工具实现。"
            )

        # 追问准确率低
        ask_acc = summary.get("ask_user_accuracy", 0.0)
        if summary.get("ask_user_count", 0) > 0 and ask_acc < 0.5:
            suggestions.append(
                "追问准确率偏低，Agent 可能在不需要追问时过多询问用户，"
                "建议优化判断逻辑减少不必要的追问。"
            )

        # 无告警
        if not alerts:
            suggestions.append("所有指标正常，Agent 运行状态良好。")

        return suggestions
