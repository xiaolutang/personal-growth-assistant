"""成长回顾统计 - Pydantic 模型定义"""
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class TrendPeriod(BaseModel):
    """趋势统计周期"""
    date: str = Field(..., description="日期（YYYY-MM-DD 或 YYYY-WXX）")
    total: int = Field(0, description="总任务数")
    completed: int = Field(0, description="已完成数")
    completion_rate: float = Field(0.0, description="完成率（百分比）")
    notes_count: int = Field(0, description="笔记数")
    task_count: int = Field(0, description="任务数")
    inbox_count: int = Field(0, description="灵感数")


class TrendResponse(BaseModel):
    """趋势数据响应"""
    periods: List[TrendPeriod] = Field(default_factory=list, description="统计周期数组")


class HeatmapItem(BaseModel):
    """热力图项"""
    concept: str
    mastery: str = "new"
    entry_count: int = 0
    category: Optional[str] = None
    mention_count: int = 0


class HeatmapResponse(BaseModel):
    """知识热力图响应"""
    items: List[HeatmapItem] = []


class GrowthCurvePoint(BaseModel):
    """成长曲线点"""
    week: str  # e.g. "2026-W15"
    total_concepts: int = 0
    advanced_count: int = 0
    intermediate_count: int = 0
    beginner_count: int = 0


class GrowthCurveResponse(BaseModel):
    """成长曲线响应"""
    points: List[GrowthCurvePoint] = []


class MorningDigestTodo(BaseModel):
    """晨报待办项"""
    id: str
    title: str
    priority: str = "medium"
    planned_date: Optional[str] = None


class MorningDigestOverdue(BaseModel):
    """晨报拖延项"""
    id: str
    title: str
    priority: str = "medium"
    planned_date: Optional[str] = None


class MorningDigestStaleInbox(BaseModel):
    """晨报未跟进灵感"""
    id: str
    title: str
    created_at: str


class MorningDigestWeeklySummary(BaseModel):
    """晨报本周学习摘要"""
    new_concepts: List[str] = []
    entries_count: int = 0


class DailyFocus(BaseModel):
    """每日聚焦"""
    title: str
    description: str
    target_entry_id: Optional[str] = None


class MorningDigestResponse(BaseModel):
    """AI 晨报响应"""
    date: str
    ai_suggestion: str
    todos: List[MorningDigestTodo] = []
    overdue: List[MorningDigestOverdue] = []
    stale_inbox: List[MorningDigestStaleInbox] = []
    weekly_summary: MorningDigestWeeklySummary = Field(default_factory=MorningDigestWeeklySummary)
    learning_streak: int = 0
    daily_focus: Optional[DailyFocus] = None
    pattern_insights: List[str] = []
    cached_at: Optional[str] = None


class TaskStats(BaseModel):
    """任务统计"""
    total: int = Field(..., description="总任务数")
    completed: int = Field(..., description="已完成数")
    doing: int = Field(..., description="进行中数")
    wait_start: int = Field(..., description="待开始数")
    completion_rate: float = Field(..., description="完成率")


class NoteStats(BaseModel):
    """笔记统计"""
    total: int = Field(..., description="笔记总数")
    recent_titles: List[str] = Field(default_factory=list, description="最近笔记标题")


class DailyReport(BaseModel):
    """日报响应"""
    date: str
    task_stats: TaskStats
    note_stats: NoteStats
    completed_tasks: List[dict] = Field(default_factory=list)
    ai_summary: Optional[str] = None


class VsLastPeriod(BaseModel):
    """环比差值"""
    delta_completion_rate: Optional[float] = Field(None, description="完成率差值（百分比）")
    delta_total: Optional[int] = Field(None, description="总任务数差值")


class WeeklyReport(BaseModel):
    """周报响应"""
    start_date: str
    end_date: str
    task_stats: TaskStats
    note_stats: NoteStats
    daily_breakdown: List[dict] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    vs_last_week: Optional[VsLastPeriod] = Field(None, description="环比上周")


class MonthlyReport(BaseModel):
    """月报响应"""
    month: str
    task_stats: TaskStats
    note_stats: NoteStats
    weekly_breakdown: List[dict] = Field(default_factory=list)
    ai_summary: Optional[str] = None
    vs_last_month: Optional[VsLastPeriod] = Field(None, description="环比上月")


class ActivityHeatmapItem(BaseModel):
    date: str
    count: int = 0


class ActivityHeatmapResponse(BaseModel):
    year: int
    items: List[ActivityHeatmapItem] = []


class BehaviorPattern(BaseModel):
    """行为模式"""
    pattern: str = Field(..., description="模式描述")
    frequency: int = Field(0, description="出现频率")
    trend: Literal["improving", "stable", "declining"] = Field("stable", description="趋势")


class GrowthSuggestion(BaseModel):
    """成长建议"""
    suggestion: str = Field(..., description="建议内容")
    priority: Literal["high", "medium", "low"] = Field("medium", description="优先级")
    related_area: str = Field("", description="相关领域")


class CapabilityChange(BaseModel):
    """能力变化"""
    capability: str = Field(..., description="能力名称")
    previous_level: float = Field(0.0, ge=0.0, le=1.0, description="前水平 (0-1)")
    current_level: float = Field(0.0, ge=0.0, le=1.0, description="当前水平 (0-1)")
    change: float = Field(0.0, description="变化值")


class DeepInsights(BaseModel):
    """深度洞察内容"""
    behavior_patterns: List[BehaviorPattern] = Field(default_factory=list, max_length=3, description="行为模式")
    growth_suggestions: List[GrowthSuggestion] = Field(default_factory=list, max_length=3, description="成长建议")
    capability_changes: List[CapabilityChange] = Field(default_factory=list, max_length=3, description="能力变化")


class InsightsResponse(BaseModel):
    """深度洞察响应"""
    period: Literal["weekly", "monthly"] = Field(..., description="周期")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    insights: DeepInsights = Field(default_factory=DeepInsights, description="洞察内容")
    source: Literal["llm", "rule_based"] = Field("rule_based", description="来源")
