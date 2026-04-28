"""评估转录记录系统

完整记录每次评估的 Agent trace（LLM 调用、工具调用、延迟、token 消耗），
支持存储管理、审查流程、饱和度监控。

核心组件:
- EvalTranscript: 单次评估转录记录（含完整 Agent 执行轨迹）
- TranscriptStore: 转录存储管理（data/eval_transcripts/YYYY-MM-DD/eval-NNN.json）
- TranscriptReviewer: 审查流程工具（筛选失败/低分评估、人工判定标签）
- SaturationMonitor: 饱和度监控（各维度通过率趋势、难度建议）
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# ── Agent Trace 数据结构 ──


@dataclass
class ToolCallRecord:
    """单次工具调用记录

    Attributes:
        tool: 工具名称
        args: 调用参数
        result: 返回结果
        latency_ms: 调用延迟（毫秒）
    """

    tool: str
    args: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool,
            "args": self.args,
            "result": self.result,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCallRecord":
        return cls(
            tool=data["tool"],
            args=data.get("args", {}),
            result=data.get("result"),
            latency_ms=data.get("latency_ms", 0.0),
        )


@dataclass
class LLMCallRecord:
    """单次 LLM 调用记录

    Attributes:
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
        latency_ms: 调用延迟（毫秒）
        model: 模型名称（可选）
    """

    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMCallRecord":
        return cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            latency_ms=data.get("latency_ms", 0.0),
            model=data.get("model", ""),
        )


@dataclass
class AgentTrace:
    """Agent 完整执行轨迹

    Attributes:
        input: 用户输入
        output: Agent 最终回复
        tool_calls: 工具调用记录列表
        llm_calls: LLM 调用记录列表
        total_latency_ms: 总延迟（毫秒）
        iteration_count: Agent 循环轮数
    """

    input: str = ""
    output: str = ""
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    llm_calls: List[LLMCallRecord] = field(default_factory=list)
    total_latency_ms: float = 0.0
    iteration_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input": self.input,
            "output": self.output,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "llm_calls": [lc.to_dict() for lc in self.llm_calls],
            "total_latency_ms": self.total_latency_ms,
            "iteration_count": self.iteration_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTrace":
        return cls(
            input=data.get("input", ""),
            output=data.get("output", ""),
            tool_calls=[
                ToolCallRecord.from_dict(tc) for tc in data.get("tool_calls", [])
            ],
            llm_calls=[
                LLMCallRecord.from_dict(lc) for lc in data.get("llm_calls", [])
            ],
            total_latency_ms=data.get("total_latency_ms", 0.0),
            iteration_count=data.get("iteration_count", 0),
        )

    @property
    def total_input_tokens(self) -> int:
        """总输入 token 数"""
        return sum(lc.input_tokens for lc in self.llm_calls)

    @property
    def total_output_tokens(self) -> int:
        """总输出 token 数"""
        return sum(lc.output_tokens for lc in self.llm_calls)

    @property
    def total_tokens(self) -> int:
        """总 token 数"""
        return self.total_input_tokens + self.total_output_tokens


# ── 人工判定标签 ──


class HumanLabel(str):
    """人工判定标签

    可选值:
    - pass: 评估结果正确
    - agent_error: Agent 行为有误
    - judge_error: 评分器判定有误
    - ambiguous: 模棱两可，难以判定
    """

    PASS = "pass"
    AGENT_ERROR = "agent_error"
    JUDGE_ERROR = "judge_error"
    AMBIGUOUS = "ambiguous"

    @classmethod
    def valid_labels(cls) -> List[str]:
        return [cls.PASS, cls.AGENT_ERROR, cls.JUDGE_ERROR, cls.AMBIGUOUS]


# ── EvalTranscript ──


@dataclass
class EvalTranscript:
    """单次评估转录记录

    记录一次评估的完整信息：测试用例、Agent 执行轨迹、
    Judge 评分、Outcome 评级、人工判定等。

    Attributes:
        transcript_id: 唯一 ID（eval-NNN 格式）
        timestamp: 评估时间（ISO 格式字符串）
        test_case_id: 关联的测试用例 ID
        test_case_category: 测试分类
        agent_trace: 完整 Agent 执行轨迹
        judge_result: JudgeResult 序列化数据（来自 B190）或 None
        outcome_grade: OutcomeGrade 序列化数据（来自 B190）或 None
        human_label: 人工判定标签（pass/agent_error/judge_error/ambiguous）
        human_notes: 人工备注
        metadata: 额外元数据
    """

    transcript_id: str = ""
    timestamp: str = ""
    test_case_id: str = ""
    test_case_category: str = ""
    agent_trace: AgentTrace = field(default_factory=AgentTrace)
    judge_result: Optional[Dict[str, Any]] = None
    outcome_grade: Optional[Dict[str, Any]] = None
    human_label: Optional[str] = None
    human_notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.transcript_id:
            self.transcript_id = _generate_transcript_id()
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "transcript_id": self.transcript_id,
            "timestamp": self.timestamp,
            "test_case_id": self.test_case_id,
            "test_case_category": self.test_case_category,
            "agent_trace": self.agent_trace.to_dict(),
            "judge_result": self.judge_result,
            "outcome_grade": self.outcome_grade,
            "human_label": self.human_label,
            "human_notes": self.human_notes,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvalTranscript":
        """从字典反序列化"""
        agent_trace_data = data.get("agent_trace", {})
        if isinstance(agent_trace_data, dict):
            agent_trace = AgentTrace.from_dict(agent_trace_data)
        else:
            agent_trace = AgentTrace()

        return cls(
            transcript_id=data.get("transcript_id", ""),
            timestamp=data.get("timestamp", ""),
            test_case_id=data.get("test_case_id", ""),
            test_case_category=data.get("test_case_category", ""),
            agent_trace=agent_trace,
            judge_result=data.get("judge_result"),
            outcome_grade=data.get("outcome_grade"),
            human_label=data.get("human_label"),
            human_notes=data.get("human_notes", ""),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "EvalTranscript":
        """从 JSON 字符串反序列化"""
        return cls.from_dict(json.loads(json_str))

    @property
    def judge_average_score(self) -> Optional[float]:
        """从 judge_result 中提取平均分，无则返回 None"""
        if self.judge_result is None:
            return None
        return self.judge_result.get("average_score")

    @property
    def judge_total_score(self) -> Optional[int]:
        """从 judge_result 中提取总分，无则返回 None"""
        if self.judge_result is None:
            return None
        return self.judge_result.get("total_score")

    @property
    def is_passed(self) -> bool:
        """判断评估是否通过（基于 outcome_grade）"""
        if self.outcome_grade is not None:
            return self.outcome_grade.get("passed", False)
        if self.judge_result is not None:
            avg = self.judge_average_score
            return avg is not None and avg >= 3.0
        return False

    @property
    def date_str(self) -> str:
        """提取日期字符串 YYYY-MM-DD"""
        if self.timestamp:
            return self.timestamp[:10]
        return date.today().isoformat()


# ── 序号生成 ──


def _generate_transcript_id(seq: Optional[int] = None) -> str:
    """生成 transcript ID

    Args:
        seq: 可选序号，不传则用 0

    Returns:
        eval-NNN 格式 ID
    """
    if seq is not None:
        return f"eval-{seq:03d}"
    return "eval-000"


# ── TranscriptStore ──


class TranscriptStore:
    """转录存储管理

    存储路径格式: data/eval_transcripts/YYYY-MM-DD/eval-NNN.json
    NNN 为当日自增序号。

    用法:
        store = TranscriptStore(base_dir=Path("data/eval_transcripts"))
        store.save(transcript)
        loaded = store.load("eval-001", "2026-04-28")
        all_today = store.list("2026-04-28")
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """初始化

        Args:
            base_dir: 存储根目录，默认为 data/eval_transcripts
        """
        if base_dir is None:
            # 默认路径：项目根目录/data/eval_transcripts
            project_root = Path(__file__).resolve().parents[3]
            base_dir = project_root / "data" / "eval_transcripts"
        self.base_dir = Path(base_dir)

    def _date_dir(self, date_str: str) -> Path:
        """获取日期目录路径"""
        return self.base_dir / date_str

    def _next_seq(self, date_str: str) -> int:
        """获取指定日期的下一个序号"""
        date_dir = self._date_dir(date_str)
        if not date_dir.exists():
            return 1

        existing_files = list(date_dir.glob("eval-*.json"))
        if not existing_files:
            return 1

        # 从文件名中提取最大序号
        max_seq = 0
        for f in existing_files:
            name = f.stem  # eval-NNN
            try:
                seq = int(name.split("-")[1])
                max_seq = max(max_seq, seq)
            except (IndexError, ValueError):
                continue

        return max_seq + 1

    def save(self, transcript: EvalTranscript) -> str:
        """保存转录记录

        自动分配序号并创建目录。

        Args:
            transcript: 评估转录记录

        Returns:
            保存的文件路径
        """
        date_str = transcript.date_str
        date_dir = self._date_dir(date_str)

        # 如果 transcript_id 还是默认的（eval-000），分配新序号
        if transcript.transcript_id in ("", "eval-000"):
            seq = self._next_seq(date_str)
            transcript.transcript_id = f"eval-{seq:03d}"

        # 更新 timestamp 中的日期部分确保一致
        date_dir.mkdir(parents=True, exist_ok=True)

        filepath = date_dir / f"{transcript.transcript_id}.json"
        filepath.write_text(transcript.to_json(), encoding="utf-8")

        return str(filepath)

    def load(self, transcript_id: str, date_str: str) -> EvalTranscript:
        """加载指定转录

        Args:
            transcript_id: 转录 ID（如 eval-001）
            date_str: 日期字符串（如 2026-04-28）

        Returns:
            EvalTranscript

        Raises:
            FileNotFoundError: 文件不存在
        """
        filepath = self._date_dir(date_str) / f"{transcript_id}.json"
        if not filepath.exists():
            raise FileNotFoundError(
                f"Transcript not found: {filepath}"
            )

        data = json.loads(filepath.read_text(encoding="utf-8"))
        return EvalTranscript.from_dict(data)

    def list(self, date_str: str) -> List[EvalTranscript]:
        """列出指定日期的所有转录

        Args:
            date_str: 日期字符串（如 2026-04-28）

        Returns:
            EvalTranscript 列表，按序号排序
        """
        date_dir = self._date_dir(date_str)
        if not date_dir.exists():
            return []

        transcripts = []
        for filepath in sorted(date_dir.glob("eval-*.json")):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                transcripts.append(EvalTranscript.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue

        return transcripts

    def delete(self, transcript_id: str, date_str: str) -> bool:
        """删除转录

        Args:
            transcript_id: 转录 ID
            date_str: 日期字符串

        Returns:
            是否删除成功
        """
        filepath = self._date_dir(date_str) / f"{transcript_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def list_dates(self) -> List[str]:
        """列出所有有转录记录的日期

        Returns:
            日期字符串列表，按时间排序
        """
        if not self.base_dir.exists():
            return []

        dates = []
        for d in self.base_dir.iterdir():
            if d.is_dir() and len(d.name) == 10 and d.name[4] == "-":
                dates.append(d.name)

        return sorted(dates)


# ── TranscriptReviewer ──


class TranscriptReviewer:
    """审查流程工具

    提供筛选、标签管理、统计功能，支持人工审查评估结果。

    用法:
        reviewer = TranscriptReviewer()
        failed = reviewer.filter_failed(transcripts)
        unlabeled = reviewer.filter_unlabeled(transcripts)
        reviewer.add_human_label(store, "eval-001", "2026-04-28",
                                  "agent_error", "工具选择错误")
        summary = reviewer.review_summary(transcripts)
    """

    # 通过阈值：平均分低于此值视为失败
    FAIL_THRESHOLD = 3.0

    def filter_failed(self, transcripts: List[EvalTranscript]) -> List[EvalTranscript]:
        """筛选失败的评估

        判定条件：judge_result 总平均分 < 3.0，或 outcome_grade.passed 为 False。

        Args:
            transcripts: 转录列表

        Returns:
            失败的转录列表
        """
        failed = []
        for t in transcripts:
            # 优先用 outcome_grade
            if t.outcome_grade is not None:
                if not t.outcome_grade.get("passed", False):
                    failed.append(t)
                    continue

            # 用 judge_result 平均分
            avg = t.judge_average_score
            if avg is not None and avg < self.FAIL_THRESHOLD:
                failed.append(t)
                continue

            # 两者都没有，如果 outcome_grade 未通过也算失败
            if t.judge_result is None and t.outcome_grade is None:
                continue

        return failed

    def filter_unlabeled(
        self, transcripts: List[EvalTranscript]
    ) -> List[EvalTranscript]:
        """筛选未人工判定的转录

        Args:
            transcripts: 转录列表

        Returns:
            未人工判定的转录列表
        """
        return [t for t in transcripts if t.human_label is None]

    def filter_by_label(
        self,
        transcripts: List[EvalTranscript],
        label: str,
    ) -> List[EvalTranscript]:
        """按标签筛选

        Args:
            transcripts: 转录列表
            label: 人工判定标签（pass/agent_error/judge_error/ambiguous）

        Returns:
            匹配的转录列表
        """
        return [t for t in transcripts if t.human_label == label]

    def add_human_label(
        self,
        store: TranscriptStore,
        transcript_id: str,
        date_str: str,
        label: str,
        notes: str = "",
    ) -> EvalTranscript:
        """添加人工判定标签

        加载转录 → 设置标签 → 保存。

        Args:
            store: 存储管理器
            transcript_id: 转录 ID
            date_str: 日期字符串
            label: 判定标签
            notes: 人工备注

        Returns:
            更新后的转录记录

        Raises:
            ValueError: 标签不合法
        """
        valid = HumanLabel.valid_labels()
        if label not in valid:
            raise ValueError(
                f"Invalid label '{label}'. Must be one of: {valid}"
            )

        transcript = store.load(transcript_id, date_str)
        transcript.human_label = label
        if notes:
            transcript.human_notes = notes

        store.save(transcript)
        return transcript

    def review_summary(
        self, transcripts: List[EvalTranscript]
    ) -> Dict[str, Any]:
        """审查统计摘要

        Args:
            transcripts: 转录列表

        Returns:
            统计信息字典，包含各标签数量、待审查数等
        """
        total = len(transcripts)
        if total == 0:
            return {
                "total": 0,
                "labeled": 0,
                "unlabeled": 0,
                "failed": 0,
                "label_counts": {},
            }

        label_counts: Dict[str, int] = {}
        labeled = 0
        unlabeled = 0
        failed_count = 0

        for t in transcripts:
            if t.human_label is not None:
                labeled += 1
                label_counts[t.human_label] = label_counts.get(t.human_label, 0) + 1
            else:
                unlabeled += 1

            # 检查是否失败
            if t.outcome_grade is not None:
                if not t.outcome_grade.get("passed", False):
                    failed_count += 1
            elif t.judge_average_score is not None:
                if t.judge_average_score < self.FAIL_THRESHOLD:
                    failed_count += 1

        return {
            "total": total,
            "labeled": labeled,
            "unlabeled": unlabeled,
            "failed": failed_count,
            "label_counts": label_counts,
        }


# ── SaturationMonitor ──


@dataclass
class TrendPoint:
    """趋势数据点

    Attributes:
        date: 日期字符串
        pass_rate: 通过率（0.0 - 1.0）
        count: 样本数
    """

    date: str
    pass_rate: float
    count: int


@dataclass
class DimensionTrend:
    """单维度趋势

    Attributes:
        dimension: 维度名称
        points: 趋势数据点列表
        current_rate: 最新通过率
        trend_direction: 趋势方向（up/down/stable）
    """

    dimension: str
    points: List[TrendPoint] = field(default_factory=list)
    current_rate: float = 0.0
    trend_direction: str = "stable"


class SaturationMonitor:
    """饱和度监控

    跟踪各维度通过率趋势，当通过率 >90% 时建议增加难度。

    用法:
        monitor = SaturationMonitor()
        trend = monitor.compute_trend(transcripts, "tool_selection")
        overall = monitor.overall_trend(transcripts)
        report = monitor.trend_report(transcripts)
    """

    # 建议增加难度的阈值
    DIFFICULTY_INCREASE_THRESHOLD = 0.90

    def _extract_dimension_score(
        self, transcript: EvalTranscript, dimension: str
    ) -> Optional[float]:
        """从转录中提取指定维度的分数

        Args:
            transcript: 评估转录
            dimension: 维度名称

        Returns:
            分数（1-5），如果无数据返回 None
        """
        if transcript.judge_result is None:
            return None

        dim_scores = transcript.judge_result.get("dimension_scores", {})
        dim_data = dim_scores.get(dimension, {})
        if isinstance(dim_data, dict):
            return dim_data.get("score")
        return None

    def _is_dimension_pass(
        self, transcript: EvalTranscript, dimension: str
    ) -> bool:
        """判断某维度是否通过（score >= 4）"""
        score = self._extract_dimension_score(transcript, dimension)
        return score is not None and score >= 4.0

    def compute_trend(
        self,
        transcripts: List[EvalTranscript],
        dimension: str,
    ) -> DimensionTrend:
        """计算指定维度的通过率趋势

        按日期分组计算通过率。维度通过标准：score >= 4。

        Args:
            transcripts: 转录列表
            dimension: 维度名称

        Returns:
            DimensionTrend 趋势数据
        """
        if not transcripts:
            return DimensionTrend(dimension=dimension)

        # 按日期分组
        by_date: Dict[str, List[EvalTranscript]] = {}
        for t in transcripts:
            d = t.date_str
            by_date.setdefault(d, []).append(t)

        points: List[TrendPoint] = []
        for d in sorted(by_date.keys()):
            day_transcripts = by_date[d]
            passed = sum(
                1 for t in day_transcripts
                if self._is_dimension_pass(t, dimension)
            )
            total = len(day_transcripts)
            pass_rate = passed / total if total > 0 else 0.0
            points.append(TrendPoint(date=d, pass_rate=pass_rate, count=total))

        # 计算趋势方向
        current_rate = points[-1].pass_rate if points else 0.0
        trend_direction = "stable"
        if len(points) >= 2:
            recent_rate = points[-1].pass_rate
            prev_rate = points[-2].pass_rate
            diff = recent_rate - prev_rate
            if diff > 0.05:
                trend_direction = "up"
            elif diff < -0.05:
                trend_direction = "down"

        return DimensionTrend(
            dimension=dimension,
            points=points,
            current_rate=current_rate,
            trend_direction=trend_direction,
        )

    def overall_trend(
        self, transcripts: List[EvalTranscript]
    ) -> Dict[str, DimensionTrend]:
        """所有维度通过率趋势

        从所有转录中提取出现的维度，分别计算趋势。

        Args:
            transcripts: 转录列表

        Returns:
            维度名 -> DimensionTrend 的字典
        """
        # 收集所有出现的维度
        dimensions = set()
        for t in transcripts:
            if t.judge_result is not None:
                dim_scores = t.judge_result.get("dimension_scores", {})
                dimensions.update(dim_scores.keys())

        result: Dict[str, DimensionTrend] = {}
        for dim in sorted(dimensions):
            result[dim] = self.compute_trend(transcripts, dim)

        return result

    def suggest_difficulty_increase(
        self, trend_data: Dict[str, DimensionTrend]
    ) -> List[Dict[str, Any]]:
        """生成难度增加建议

        通过率 >90% 的维度建议增加难度。

        Args:
            trend_data: 维度趋势数据

        Returns:
            建议列表，每项包含维度、当前通过率、建议内容
        """
        suggestions = []
        for dim, trend in trend_data.items():
            if trend.current_rate > self.DIFFICULTY_INCREASE_THRESHOLD:
                suggestions.append({
                    "dimension": dim,
                    "current_pass_rate": round(trend.current_rate, 3),
                    "threshold": self.DIFFICULTY_INCREASE_THRESHOLD,
                    "suggestion": (
                        f"维度 '{dim}' 通过率 {trend.current_rate:.1%} "
                        f"超过阈值 {self.DIFFICULTY_INCREASE_THRESHOLD:.0%}，"
                        f"建议增加测试难度或引入更复杂的场景"
                    ),
                })
        return suggestions

    def trend_report(
        self, transcripts: List[EvalTranscript]
    ) -> Dict[str, Any]:
        """生成趋势报告

        包含各维度通过率趋势和难度建议。

        Args:
            transcripts: 转录列表

        Returns:
            趋势报告字典
        """
        overall = self.overall_trend(transcripts)
        suggestions = self.suggest_difficulty_increase(overall)

        # 各维度摘要
        dimension_summary = {}
        for dim, trend in overall.items():
            dimension_summary[dim] = {
                "current_pass_rate": round(trend.current_rate, 3),
                "trend_direction": trend.trend_direction,
                "data_points": len(trend.points),
                "total_samples": sum(p.count for p in trend.points),
            }

        return {
            "total_transcripts": len(transcripts),
            "dimensions": dimension_summary,
            "difficulty_suggestions": suggestions,
            "saturated_dimensions": len(suggestions),
        }
