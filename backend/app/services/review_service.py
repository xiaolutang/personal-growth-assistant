"""成长回顾统计服务"""
import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.callers import APICaller

logger = logging.getLogger(__name__)


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


class ReviewService:
    """成长回顾统计服务"""

    CATEGORY_LABELS = {"task": "任务", "note": "笔记", "inbox": "灵感", "project": "项目"}

    def __init__(self, sqlite_storage=None, neo4j_client=None):
        """
        初始化服务

        Args:
            sqlite_storage: SQLite 存储实例
            neo4j_client: Neo4j 客户端（可选，用于知识热力图增强）
        """
        self._sqlite = sqlite_storage
        self._neo4j_client = neo4j_client
        self._llm_caller: Optional["APICaller"] = None

    def set_sqlite_storage(self, storage):
        """设置 SQLite 存储"""
        self._sqlite = storage

    def set_llm_caller(self, caller: "APICaller"):
        """设置 LLM 调用器"""
        self._llm_caller = caller

    @staticmethod
    def calculate_task_stats(tasks: List[dict]) -> TaskStats:
        """计算任务统计"""
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("status") == "complete")
        doing = sum(1 for t in tasks if t.get("status") == "doing")
        wait_start = sum(1 for t in tasks if t.get("status") == "waitStart")

        completion_rate = (completed / total * 100) if total > 0 else 0

        return TaskStats(
            total=total,
            completed=completed,
            doing=doing,
            wait_start=wait_start,
            completion_rate=round(completion_rate, 1),
        )

    @staticmethod
    def calculate_note_stats(notes: List[dict]) -> NoteStats:
        """计算笔记统计"""
        return NoteStats(
            total=len(notes),
            recent_titles=[n.get("title", "")[:50] for n in notes[:5]],
        )

    async def get_daily_report(self, target_date: Optional[date] = None, user_id: Optional[str] = None) -> DailyReport:
        """获取日报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()

        tasks = self._sqlite.list_entries(
            type="task",
            start_date=date_str,
            end_date=date_str,
            limit=1000,
            user_id=user_id,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=date_str,
            end_date=date_str,
            limit=1000,
            user_id=user_id,
        )

        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)
        completed_tasks = [t for t in tasks if t.get("status") == "complete"]

        # 生成 AI 总结
        ai_summary = None
        if self._llm_caller:
            stats_data = {
                "task_stats": task_stats.model_dump(),
                "note_stats": note_stats.model_dump(),
                "completed_tasks": [
                    {"id": t.get("id"), "title": t.get("title")}
                    for t in completed_tasks
                ],
                "recent_note_titles": note_stats.recent_titles,
            }
            ai_summary = await self._generate_ai_summary("daily", stats_data, user_id=user_id or "_default")

        return DailyReport(
            date=date_str,
            task_stats=task_stats,
            note_stats=note_stats,
            completed_tasks=completed_tasks,
            ai_summary=ai_summary,
        )

    async def get_weekly_report(self, week_start: Optional[date] = None, user_id: Optional[str] = None) -> WeeklyReport:
        """获取周报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        start_str = week_start.isoformat()
        end_str = week_end.isoformat()

        tasks = self._sqlite.list_entries(
            type="task",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)

        daily_breakdown = []
        # 从已获取的 tasks 中按日聚合，避免 N+1 查询
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_str = day.isoformat()
            day_tasks = [t for t in tasks if t.get("created_at", "")[:10] == day_str or t.get("updated_at", "")[:10] == day_str]
            completed = sum(1 for t in day_tasks if t.get("status") == "complete")
            daily_breakdown.append({
                "date": day_str,
                "total": len(day_tasks),
                "completed": completed,
            })

        # 生成 AI 总结
        ai_summary = None
        if self._llm_caller:
            stats_data = {
                "task_stats": task_stats.model_dump(),
                "note_stats": note_stats.model_dump(),
                "daily_breakdown": daily_breakdown,
                "recent_note_titles": note_stats.recent_titles,
            }
            ai_summary = await self._generate_ai_summary("weekly", stats_data, user_id=user_id or "_default")

        # 计算环比上周
        vs_last_week = self._calculate_weekly_vs_last_week(
            week_start, task_stats, user_id
        )

        return WeeklyReport(
            start_date=start_str,
            end_date=week_end.isoformat(),
            task_stats=task_stats,
            note_stats=note_stats,
            daily_breakdown=daily_breakdown,
            ai_summary=ai_summary,
            vs_last_week=vs_last_week,
        )

    def _calculate_weekly_vs_last_week(
        self, week_start: date, current_task_stats: TaskStats, user_id: Optional[str]
    ) -> Optional[VsLastPeriod]:
        """计算周环比差值"""
        last_week_start = week_start - timedelta(weeks=1)
        last_week_end = last_week_start + timedelta(days=6)

        last_tasks = self._sqlite.list_entries(
            type="task",
            start_date=last_week_start.isoformat(),
            end_date=last_week_end.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        last_total = len(last_tasks)
        last_completed = sum(1 for t in last_tasks if t.get("status") == "complete")
        last_completion_rate = (last_completed / last_total * 100) if last_total > 0 else 0.0

        if last_total == 0 and current_task_stats.total == 0:
            return VsLastPeriod(delta_completion_rate=None, delta_total=None)

        return VsLastPeriod(
            delta_completion_rate=round(current_task_stats.completion_rate - last_completion_rate, 1),
            delta_total=current_task_stats.total - last_total,
        )

    def _calculate_monthly_vs_last_month(
        self, month_start: date, current_task_stats: TaskStats, user_id: Optional[str]
    ) -> Optional[VsLastPeriod]:
        """计算月环比差值"""
        if month_start.month == 1:
            last_month_start = date(month_start.year - 1, 12, 1)
        else:
            last_month_start = date(month_start.year, month_start.month - 1, 1)

        if last_month_start.month == 12:
            last_month_end = date(last_month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_month_end = date(last_month_start.year, last_month_start.month + 1, 1) - timedelta(days=1)

        last_tasks = self._sqlite.list_entries(
            type="task",
            start_date=last_month_start.isoformat(),
            end_date=last_month_end.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        last_total = len(last_tasks)
        last_completed = sum(1 for t in last_tasks if t.get("status") == "complete")
        last_completion_rate = (last_completed / last_total * 100) if last_total > 0 else 0.0

        if last_total == 0 and current_task_stats.total == 0:
            return VsLastPeriod(delta_completion_rate=None, delta_total=None)

        return VsLastPeriod(
            delta_completion_rate=round(current_task_stats.completion_rate - last_completion_rate, 1),
            delta_total=current_task_stats.total - last_total,
        )

    async def get_monthly_report(self, month_start: Optional[date] = None, user_id: Optional[str] = None) -> MonthlyReport:
        """获取月报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if month_start is None:
            today = date.today()
            month_start = date(today.year, today.month, 1)

        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        start_str = month_start.isoformat()
        end_str = month_end.isoformat()

        tasks = self._sqlite.list_entries(
            type="task",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)

        weekly_breakdown = []
        current_week_start = month_start
        week_num = 1

        # 从已获取的 tasks 中按周聚合，避免 N+1 查询
        while current_week_start <= month_end:
            week_end = min(current_week_start + timedelta(days=6), month_end)
            ws_str = current_week_start.isoformat()
            we_str = week_end.isoformat()

            week_tasks = [
                t for t in tasks
                if ws_str <= (t.get("created_at", "")[:10]) <= we_str
                or ws_str <= (t.get("updated_at", "")[:10]) <= we_str
            ]

            completed = sum(1 for t in week_tasks if t.get("status") == "complete")
            weekly_breakdown.append({
                "week": f"第{week_num}周",
                "start_date": ws_str,
                "end_date": we_str,
                "total": len(week_tasks),
                "completed": completed,
            })

            current_week_start = week_end + timedelta(days=1)
            week_num += 1

        # 生成 AI 总结
        ai_summary = None
        if self._llm_caller:
            stats_data = {
                "task_stats": task_stats.model_dump(),
                "note_stats": note_stats.model_dump(),
                "weekly_breakdown": weekly_breakdown,
                "recent_note_titles": note_stats.recent_titles,
            }
            ai_summary = await self._generate_ai_summary("monthly", stats_data, user_id=user_id or "_default")

        # 计算环比上月
        vs_last_month = self._calculate_monthly_vs_last_month(
            month_start, task_stats, user_id
        )

        return MonthlyReport(
            month=month_start.strftime("%Y-%m"),
            task_stats=task_stats,
            note_stats=note_stats,
            weekly_breakdown=weekly_breakdown,
            ai_summary=ai_summary,
            vs_last_month=vs_last_month,
        )

    def get_trend_data(
        self,
        period: str = "daily",
        days: int = 7,
        weeks: int = 8,
        user_id: Optional[str] = None,
    ) -> TrendResponse:
        """获取趋势数据（单次聚合 SQL 替代 N+1 循环查询）"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if period not in ("daily", "weekly"):
            raise ValueError("period 参数必须是 daily 或 weekly")

        if period == "daily":
            count = max(1, min(days, 365))
            today = date.today()
            start = today - timedelta(days=count - 1)
            end = today + timedelta(days=1)
            agg = self._sqlite.get_trend_aggregation(
                user_id=user_id,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
            )
            return self._build_daily_trend(agg, start, count)
        else:  # weekly
            count = max(1, min(weeks, 52))
            today = date.today()
            current_week_start = today - timedelta(days=today.weekday())
            oldest_week_start = current_week_start - timedelta(weeks=count - 1)
            end = current_week_start + timedelta(days=7)
            agg = self._sqlite.get_trend_aggregation(
                user_id=user_id,
                start_date=oldest_week_start.isoformat(),
                end_date=end.isoformat(),
            )
            return self._build_weekly_trend(agg, current_week_start, count)

    def _build_daily_trend(
        self, agg: list[dict], start: date, count: int
    ) -> TrendResponse:
        """从聚合数据构建日趋势（内存 O(N) 分桶）"""
        from collections import defaultdict

        buckets: dict[str, dict] = defaultdict(
            lambda: {"task": 0, "task_complete": 0, "note": 0, "inbox": 0}
        )
        for row in agg:
            d = row["d"]
            cat = row["category"] or "task"
            status = row["status"] or ""
            cnt = row["cnt"]
            b = buckets[d]
            if cat == "task":
                b["task"] += cnt
                if status == "complete":
                    b["task_complete"] += cnt
            elif cat == "note":
                b["note"] += cnt
            elif cat == "inbox":
                b["inbox"] += cnt

        periods: List[TrendPeriod] = []
        for i in range(count):
            target = start + timedelta(days=i)
            ds = target.isoformat()
            b = buckets.get(ds, {"task": 0, "task_complete": 0, "note": 0, "inbox": 0})
            total = b["task"]
            completed = b["task_complete"]
            completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0
            periods.append(TrendPeriod(
                date=ds,
                total=total,
                completed=completed,
                completion_rate=completion_rate,
                notes_count=b["note"],
                task_count=total,
                inbox_count=b["inbox"],
            ))

        return TrendResponse(periods=periods)

    def _build_weekly_trend(
        self, agg: list[dict], current_week_start: date, count: int
    ) -> TrendResponse:
        """从聚合数据构建周趋势"""
        from collections import defaultdict

        def _week_key(d_str: str) -> str:
            """将日期字符串转为所属周的周一日期"""
            dt = datetime.strptime(d_str, "%Y-%m-%d").date()
            return (dt - timedelta(days=dt.weekday())).isoformat()

        buckets: dict[str, dict] = defaultdict(
            lambda: {"task": 0, "task_complete": 0, "note": 0, "inbox": 0}
        )
        for row in agg:
            wk = _week_key(row["d"])
            cat = row["category"] or "task"
            status = row["status"] or ""
            cnt = row["cnt"]
            b = buckets[wk]
            if cat == "task":
                b["task"] += cnt
                if status == "complete":
                    b["task_complete"] += cnt
            elif cat == "note":
                b["note"] += cnt
            elif cat == "inbox":
                b["inbox"] += cnt

        periods: List[TrendPeriod] = []
        for i in range(count):
            week_start = current_week_start - timedelta(weeks=i)
            ws = week_start.isoformat()
            b = buckets.get(ws, {"task": 0, "task_complete": 0, "note": 0, "inbox": 0})
            total = b["task"]
            completed = b["task_complete"]
            completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0
            periods.append(TrendPeriod(
                date=ws,
                total=total,
                completed=completed,
                completion_rate=completion_rate,
                notes_count=b["note"],
                task_count=total,
                inbox_count=b["inbox"],
            ))

        return TrendResponse(periods=periods)

    @staticmethod
    def parse_date(date_str: Optional[str]) -> date:
        """解析日期字符串"""
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("日期格式错误，应为 YYYY-MM-DD")
        return date.today()

    @staticmethod
    def parse_month(month_str: Optional[str]) -> date:
        """解析月份字符串"""
        if month_str:
            try:
                return datetime.strptime(month_str, "%Y-%m").date()
            except ValueError:
                raise ValueError("月份格式错误，应为 YYYY-MM")
        today = date.today()
        return date(today.year, today.month, 1)

    async def _generate_ai_summary(
        self, report_type: str, stats_data: dict, user_id: str = "_default"
    ) -> str:
        """
        使用 LLM 生成 AI 总结

        Args:
            report_type: 报告类型 (daily/weekly/monthly)
            stats_data: 统计数据
            user_id: 用户 ID

        Returns:
            AI 总结文本，失败时返回空字符串
        """
        if not self._llm_caller:
            return ""

        import json

        system_prompt = (
            "你是个人成长助手「日知」，请根据以下数据生成一段简短的中文总结（2-3句话），"
            "包含关键成就和建议。"
        )

        user_message = (
            f"报告类型：{report_type}\n"
            f"统计数据：\n{json.dumps(stats_data, ensure_ascii=False, indent=2)}"
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            result = await asyncio.wait_for(
                self._llm_caller.call(messages),
                timeout=10.0,
            )
            return result.strip() if result else ""
        except asyncio.TimeoutError:
            logger.warning("AI 总结生成超时")
            return ""
        except Exception as e:
            logger.warning(f"AI 总结生成失败: {e}")
            return ""

    async def get_knowledge_heatmap(self, user_id: str = "_default") -> HeatmapResponse:
        """
        获取知识热力图

        优先使用 Neo4j get_all_concepts_with_stats() 获取数据，
        Neo4j 不可用时降级到 SQLite tags 现有逻辑。

        Args:
            user_id: 用户 ID

        Returns:
            HeatmapResponse: 知识热力图数据
        """
        # 尝试 Neo4j 路径
        if self._neo4j_client:
            try:
                concepts = await self._neo4j_client.get_all_concepts_with_stats(user_id)
                if concepts:
                    relationships = await self._neo4j_client.get_all_relationships(user_id)
                    rel_count_map = self._count_relationships_per_concept(relationships)
                    items = [
                        self._neo4j_concept_to_heatmap(c, rel_count_map)
                        for c in concepts
                    ]
                    # 按 mastery 分组排序
                    items.sort(key=lambda x: self._mastery_order(x.mastery))
                    return HeatmapResponse(items=items)
            except Exception:
                logger.warning("Neo4j 查询失败，降级到 SQLite", exc_info=True)

        # SQLite tags 降级路径
        return self._get_heatmap_from_sqlite(user_id)

    def _get_heatmap_from_sqlite(self, user_id: str) -> HeatmapResponse:
        """从 SQLite tags 获取热力图数据（降级路径）"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        all_entries = self._sqlite.list_entries(limit=1000, user_id=user_id)

        # 从所有条目的 tags 中提取概念并统计
        concept_map: Dict[str, Dict] = {}
        for entry in all_entries:
            tags = entry.get("tags", [])
            entry_type = entry.get("type", "task")
            updated_str = entry.get("updated_at", "")

            for tag in tags:
                if tag not in concept_map:
                    concept_map[tag] = {
                        "entry_count": 0,
                        "recent_count": 0,
                        "note_count": 0,
                    }
                concept_map[tag]["entry_count"] += 1

                if entry_type == "note":
                    concept_map[tag]["note_count"] += 1

                # 检查是否在最近 30 天内更新
                try:
                    if updated_str:
                        if isinstance(updated_str, str):
                            updated_at = datetime.fromisoformat(
                                updated_str.replace("Z", "+00:00")
                            )
                        else:
                            updated_at = updated_str
                        if updated_at >= datetime.now() - timedelta(days=30):
                            concept_map[tag]["recent_count"] += 1
                except (ValueError, TypeError):
                    pass

        # 构建热力图项
        items: List[HeatmapItem] = []
        for concept, info in concept_map.items():
            mastery = self._calculate_mastery_from_stats(
                entry_count=info["entry_count"],
                recent_count=info["recent_count"],
                note_count=info["note_count"],
            )
            items.append(HeatmapItem(
                concept=concept,
                mastery=mastery,
                entry_count=info["entry_count"],
                category="tag",
            ))

        # 按 mastery 分组排序
        items.sort(key=lambda x: self._mastery_order(x.mastery))

        return HeatmapResponse(items=items)

    @staticmethod
    def _count_relationships_per_concept(
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """统计每个概念的关系数量"""
        rel_count: Dict[str, int] = {}
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_count[source] = rel_count.get(source, 0) + 1
            rel_count[target] = rel_count.get(target, 0) + 1
        return rel_count

    def _neo4j_concept_to_heatmap(
        self,
        concept: Dict[str, Any],
        rel_count_map: Dict[str, int],
    ) -> HeatmapItem:
        """将 Neo4j 概念统计转换为 HeatmapItem"""
        name = concept.get("name", "")
        entry_count = concept.get("entry_count", 0)
        mention_count = concept.get("mention_count", 0)
        category = concept.get("category")
        relationship_count = rel_count_map.get(name, 0)

        mastery = self._calculate_mastery_from_stats(
            entry_count=entry_count,
            relationship_count=relationship_count,
        )

        return HeatmapItem(
            concept=name,
            mastery=mastery,
            entry_count=entry_count,
            category=category,
            mention_count=mention_count,
        )

    @staticmethod
    def _mastery_order(mastery: str) -> int:
        """掌握度排序权重（值越小掌握度越高）"""
        order = {"advanced": 0, "intermediate": 1, "beginner": 2, "new": 3}
        return order.get(mastery, 99)

    def get_growth_curve(
        self, weeks: int = 8, user_id: str = "_default"
    ) -> GrowthCurveResponse:
        """
        获取成长曲线数据

        Args:
            weeks: 回溯周数 (1-52)
            user_id: 用户 ID

        Returns:
            GrowthCurveResponse: 成长曲线数据
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        count = max(1, min(weeks, 52))
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())

        # 一次查询获取所有周的条目，避免 N+1
        earliest_week_start = current_week_start - timedelta(weeks=count - 1)
        all_entries = self._sqlite.list_entries(
            start_date=earliest_week_start.isoformat(),
            end_date=today.isoformat(),
            limit=10000,
            user_id=user_id,
        )

        points: List[GrowthCurvePoint] = []

        for i in range(count):
            week_start = current_week_start - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            ws_str = week_start.isoformat()
            we_str = week_end.isoformat()

            # 从内存中过滤该周条目
            week_entries = [
                e for e in all_entries
                if ws_str <= (e.get("created_at", "")[:10]) <= we_str
                or ws_str <= (e.get("updated_at", "")[:10]) <= we_str
            ]

            # 提取概念并计算掌握度分布
            concept_map: Dict[str, Dict] = {}
            for entry in week_entries:
                tags = entry.get("tags", [])
                entry_type = entry.get("type", "task")
                updated_str = entry.get("updated_at", "")

                for tag in tags:
                    if tag not in concept_map:
                        concept_map[tag] = {
                            "entry_count": 0,
                            "recent_count": 0,
                            "note_count": 0,
                        }
                    concept_map[tag]["entry_count"] += 1

                    if entry_type == "note":
                        concept_map[tag]["note_count"] += 1

                    try:
                        if updated_str:
                            if isinstance(updated_str, str):
                                updated_at = datetime.fromisoformat(
                                    updated_str.replace("Z", "+00:00")
                                )
                            else:
                                updated_at = updated_str
                            if updated_at >= datetime.now() - timedelta(days=30):
                                concept_map[tag]["recent_count"] += 1
                    except (ValueError, TypeError):
                        pass

            # 统计掌握度分布
            advanced_count = 0
            intermediate_count = 0
            beginner_count = 0

            for concept, info in concept_map.items():
                mastery = self._calculate_mastery_from_stats(
                    entry_count=info["entry_count"],
                    recent_count=info["recent_count"],
                    note_count=info["note_count"],
                )
                if mastery == "advanced":
                    advanced_count += 1
                elif mastery == "intermediate":
                    intermediate_count += 1
                elif mastery == "beginner":
                    beginner_count += 1

            # 计算周编号 (ISO week)
            iso_calendar = week_start.isocalendar()
            week_label = f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"

            points.append(GrowthCurvePoint(
                week=week_label,
                total_concepts=len(concept_map),
                advanced_count=advanced_count,
                intermediate_count=intermediate_count,
                beginner_count=beginner_count,
            ))

        return GrowthCurveResponse(points=points)

    def _calculate_learning_streak(self, user_id: str) -> int:
        """
        计算学习连续天数（从今天开始往前数连续有记录的天数）

        使用 SQLite 公共方法获取最近 90 天内有条目的日期列表，
        然后在内存中从今天开始往前计算连续天数。

        Args:
            user_id: 用户 ID

        Returns:
            连续天数，无条目时返回 0
        """
        if not self._sqlite:
            return 0

        active_dates = self._sqlite.get_active_dates(user_id, days=90)

        if not active_dates:
            return 0

        # 从今天开始往前数连续天数
        date_set = set(active_dates)
        today = date.today()
        streak = 0
        current = today
        while current.isoformat() in date_set:
            streak += 1
            current -= timedelta(days=1)

        return streak

    def _generate_pattern_insights(self, user_id: str) -> List[str]:
        """
        分析最近 30 天的行为模式，生成洞察

        分析内容：
        - 分类分布（任务 vs 笔记 vs 灵感）
        - 任务完成率趋势

        Args:
            user_id: 用户 ID

        Returns:
            最多 3 条洞察字符串
        """
        if not self._sqlite:
            return []

        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        seven_days_ago = today - timedelta(days=7)

        # 最近 30 天条目
        recent_entries = self._sqlite.list_entries(
            start_date=thirty_days_ago.isoformat(),
            end_date=today.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        if not recent_entries:
            return []

        insights: List[str] = []

        # 1. 分类分布分析（复用共享 helper）
        total_count, category_counts, _, _, _ = self._analyze_category_distribution(recent_entries)

        if total_count > 0:
            # 找到最多的类别
            top_category = max(category_counts, key=category_counts.get)
            top_ratio = category_counts[top_category] / total_count

            top_label = self.CATEGORY_LABELS.get(top_category, top_category)

            if top_ratio > 0.6 and total_count >= 5:
                insights.append(
                    f"你最近 30 天更倾向于创建{top_label}，"
                    f"占比 {int(top_ratio * 100)}%"
                )

        # 2. 最近 7 天 vs 之前的完成率对比
        recent_7_entries = [
            e for e in recent_entries
            if e.get("type") == "task"
            and self._parse_entry_date(e.get("created_at")) is not None
            and self._parse_entry_date(e.get("created_at")) >= seven_days_ago
        ]
        older_entries = [
            e for e in recent_entries
            if e.get("type") == "task"
            and self._parse_entry_date(e.get("created_at")) is not None
            and self._parse_entry_date(e.get("created_at")) < seven_days_ago
        ]

        if recent_7_entries and older_entries:
            recent_completed = sum(1 for e in recent_7_entries if e.get("status") == "complete")
            recent_rate = recent_completed / len(recent_7_entries) * 100

            older_completed = sum(1 for e in older_entries if e.get("status") == "complete")
            older_rate = older_completed / len(older_entries) * 100

            diff = recent_rate - older_rate
            if abs(diff) >= 15:
                direction = "提升" if diff > 0 else "下降"
                insights.append(
                    f"你的任务完成率比上周{direction}了 {int(abs(diff))}%"
                )

        # 3. 灵感转化提醒
        inbox_count = category_counts.get("inbox", 0)
        if inbox_count >= 3:
            insights.append(
                f"你有 {inbox_count} 个灵感尚未转化为行动"
            )

        return insights[:3]

    @staticmethod
    def _parse_entry_date(val) -> Optional[date]:
        """解析条目的日期字段"""
        if not val:
            return None
        if isinstance(val, date):
            return val
        try:
            return datetime.fromisoformat(str(val).replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            try:
                return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return None

    @staticmethod
    def _parse_llm_json(text: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON（可能包含在 markdown 代码块中）"""
        import json
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

    async def _generate_daily_focus(
        self,
        user_id: str,
        overdue: list,
        learning_streak: int,
        recent_activity: list,
    ) -> Optional[DailyFocus]:
        """
        生成每日聚焦建议

        优先使用 LLM 生成个性化建议，LLM 不可用时降级为模板：
        - 有逾期任务：使用最紧急的逾期任务
        - 有近期活动：使用最近的活动
        - 无数据：返回 None

        Args:
            user_id: 用户 ID
            overdue: 逾期任务列表
            learning_streak: 学习连续天数
            recent_activity: 近期活动列表

        Returns:
            DailyFocus 或 None
        """
        # 先尝试 LLM 生成
        if self._llm_caller:
            try:
                import json
                system_prompt = (
                    "你是个人成长助手「日知」，请为用户推荐今天最值得关注的一件事。"
                    "返回 JSON 格式：{\"title\": \"标题\", \"description\": \"描述\", \"target_entry_id\": \"id或null\"}"
                )
                context_data = {
                    "overdue_tasks": [
                        {"id": t.get("id"), "title": t.get("title"), "priority": t.get("priority")}
                        for t in overdue[:3]
                    ],
                    "learning_streak": learning_streak,
                    "recent_titles": [e.get("title", "") for e in recent_activity[:5]],
                }
                user_message = (
                    f"用户学习连续天数：{learning_streak}\n"
                    f"逾期任务：{json.dumps(context_data['overdue_tasks'], ensure_ascii=False)}\n"
                    f"近期活动：{json.dumps(context_data['recent_titles'], ensure_ascii=False)}\n\n"
                    f"请推荐今天最应该聚焦的一件事。"
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
                result = await asyncio.wait_for(self._llm_caller.call(messages), timeout=10.0)
                if result:
                    try:
                        parsed = self._parse_llm_json(result)
                        if parsed and isinstance(parsed, dict) and "title" in parsed:
                            return DailyFocus(
                                title=str(parsed["title"]),
                                description=str(parsed.get("description", "")),
                                target_entry_id=parsed.get("target_entry_id"),
                            )
                    except (json.JSONDecodeError, KeyError, TypeError):
                        logger.debug("LLM daily_focus JSON 解析失败，降级为模板")
                        # 使用 LLM 返回的文本作为 title
                        return DailyFocus(
                            title=result[:50].strip(),
                            description=result.strip(),
                        )
            except (asyncio.TimeoutError, Exception) as e:
                logger.debug(f"LLM daily_focus 生成失败: {e}")

        # 降级为模板
        # 优先：最紧急的逾期任务
        if overdue:
            t = overdue[0]
            return DailyFocus(
                title=f"处理逾期任务：{t.get('title', '未命名')}",
                description=f"该任务已逾期，优先级为 {t.get('priority', 'medium')}，建议今天优先完成。",
                target_entry_id=t.get("id"),
            )

        # 次选：最近的未完成任务
        if recent_activity:
            entry = recent_activity[0]
            if entry.get("status") != "complete":
                return DailyFocus(
                    title=f"继续推进：{entry.get('title', '未命名')}",
                    description="这是你最近在做的任务，保持节奏继续前进。",
                    target_entry_id=entry.get("id"),
                )

        return None

    async def get_morning_digest(self, user_id: str) -> MorningDigestResponse:
        """
        获取 AI 晨报数据

        聚合：今日待办 + 拖延任务 + 未跟进灵感 + 本周学习摘要

        Args:
            user_id: 用户 ID

        Returns:
            MorningDigestResponse
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        today = date.today()
        today_str = today.isoformat()
        tomorrow_str = (today + timedelta(days=1)).isoformat()

        # 1. 今日待办（状态非 complete，planned_date=today）
        # 注意：list_entries 按 created_at 过滤，不能完全依赖它来筛选 planned_date
        # 需要查询更宽的时间范围，再按 planned_date 精确过滤
        all_active_tasks = self._sqlite.list_entries(
            type="task",
            status="doing",
            limit=200,
            user_id=user_id,
        )
        all_wait_tasks = self._sqlite.list_entries(
            type="task",
            status="waitStart",
            limit=200,
            user_id=user_id,
        )
        active_tasks = all_active_tasks + all_wait_tasks

        today_todos = [
            t for t in active_tasks
            if self._parse_entry_date(t.get("planned_date")) == today
        ]

        priority_order = {"high": 0, "medium": 1, "low": 2}
        today_todos.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

        # 2. 拖延任务（planned_date 已过，状态非 complete）
        past_tasks = self._sqlite.list_entries(
            type="task",
            end_date=today_str,
            limit=200,
            user_id=user_id,
        )
        overdue = [
            t for t in past_tasks
            if t.get("status") in ("waitStart", "doing")
            and t.get("planned_date")
            and self._parse_entry_date(t.get("planned_date")) is not None
            and self._parse_entry_date(t.get("planned_date")) < today
        ]
        overdue.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

        # 3. 未跟进灵感（>3天未转化的 inbox 条目）
        three_days_ago = today - timedelta(days=3)
        old_inbox = self._sqlite.list_entries(
            type="inbox",
            end_date=three_days_ago.isoformat(),
            limit=200,
            user_id=user_id,
        )
        stale_inbox = [
            i for i in old_inbox
            if i.get("status") in ("waitStart", "pending")
        ]

        # 4. 本周学习摘要
        week_start = today - timedelta(days=today.weekday())
        week_end_str = (week_start + timedelta(days=6)).isoformat()
        week_start_str = week_start.isoformat()

        week_entries = self._sqlite.list_entries(
            start_date=week_start_str,
            end_date=week_end_str,
            limit=1000,
            user_id=user_id,
        )

        # 提取本周新增概念（tags）
        new_concepts_set: set = set()
        for entry in week_entries:
            for tag in entry.get("tags", []):
                new_concepts_set.add(tag)

        weekly_summary = MorningDigestWeeklySummary(
            new_concepts=sorted(new_concepts_set)[:10],
            entries_count=len(week_entries),
        )

        # 5. 构建 AI 建议
        ai_suggestion = await self._generate_morning_suggestion(
            today_todos=today_todos,
            overdue=overdue,
            stale_inbox=stale_inbox,
            weekly_summary=weekly_summary,
            user_id=user_id,
        )

        # 6. 新增增强字段
        learning_streak = self._calculate_learning_streak(user_id)
        pattern_insights = self._generate_pattern_insights(user_id)
        daily_focus = await self._generate_daily_focus(
            user_id=user_id,
            overdue=overdue,
            learning_streak=learning_streak,
            recent_activity=today_todos[:5] + overdue[:5],
        )

        return MorningDigestResponse(
            date=today_str,
            ai_suggestion=ai_suggestion,
            todos=[
                MorningDigestTodo(
                    id=t.get("id", ""),
                    title=t.get("title", ""),
                    priority=t.get("priority", "medium"),
                    planned_date=t.get("planned_date"),
                )
                for t in today_todos[:5]
            ],
            overdue=[
                MorningDigestOverdue(
                    id=t.get("id", ""),
                    title=t.get("title", ""),
                    priority=t.get("priority", "medium"),
                    planned_date=t.get("planned_date"),
                )
                for t in overdue[:5]
            ],
            stale_inbox=[
                MorningDigestStaleInbox(
                    id=i.get("id", ""),
                    title=i.get("title", ""),
                    created_at=i.get("created_at", ""),
                )
                for i in stale_inbox[:5]
            ],
            weekly_summary=weekly_summary,
            learning_streak=learning_streak,
            daily_focus=daily_focus,
            pattern_insights=pattern_insights,
        )

    async def _generate_morning_suggestion(
        self,
        today_todos: list,
        overdue: list,
        stale_inbox: list,
        weekly_summary: MorningDigestWeeklySummary,
        user_id: str,
    ) -> str:
        """生成晨报建议文本，LLM 不可用时降级为模板"""
        todo_count = len(today_todos)
        overdue_count = len(overdue)
        stale_count = len(stale_inbox)
        concepts_count = len(weekly_summary.new_concepts)
        entries_count = weekly_summary.entries_count

        # 先尝试 LLM
        if self._llm_caller:
            try:
                stats_data = {
                    "todo_count": todo_count,
                    "overdue_count": overdue_count,
                    "stale_inbox_count": stale_count,
                    "week_new_concepts": weekly_summary.new_concepts[:5],
                    "week_entries_count": entries_count,
                    "todos": [t.get("title", "") for t in today_todos[:3]],
                    "overdue_titles": [t.get("title", "") for t in overdue[:3]],
                }
                suggestion = await self._generate_ai_summary("morning_digest", stats_data, user_id=user_id)
                if suggestion:
                    return suggestion
            except Exception:
                pass

        # 降级为模板文本
        parts = []
        if todo_count > 0:
            parts.append(f"你有{todo_count}个任务待完成")
            if overdue_count > 0:
                parts[0] += f"，其中{overdue_count}个已逾期"
        elif overdue_count > 0:
            parts.append(f"你有{overdue_count}个逾期任务需要处理")
        else:
            parts.append("今天没有待办任务，适合学习新知识")

        if stale_count > 0:
            parts.append(f"有{stale_count}个灵感超过3天未跟进")

        if concepts_count > 0:
            parts.append(f"本周学习了{concepts_count}个新概念")

        return "，".join(parts) + "。"

    @staticmethod
    def _calculate_mastery_from_stats(
        entry_count: int,
        recent_count: int = 0,
        note_count: int = 0,
        relationship_count: int = 0,
    ) -> str:
        """
        根据统计数据计算掌握度（阈值式，与 knowledge_service 一致）

        规则：
        - relationship_count 折算为等价 entry_count（每 2 个关系 ≈ 1 个条目）
        - effective_count = entry_count + relationship_count // 2
        - effective_count >= 6 且 note_ratio > 0.3 → advanced
        - effective_count >= 3 且 recent_count > 0 → intermediate
        - effective_count >= 1 → beginner
        - 其他 → new
        """
        effective_count = entry_count + max(0, relationship_count // 2)

        if effective_count == 0:
            return "new"

        note_ratio = note_count / effective_count if effective_count > 0 else 0

        if effective_count >= 6 and note_ratio > 0.3:
            return "advanced"
        elif effective_count >= 3 and recent_count > 0:
            return "intermediate"
        elif effective_count >= 1:
            return "beginner"
        return "new"

    def get_activity_heatmap(self, year: int, user_id: str) -> ActivityHeatmapResponse:
        """获取年度每日活动热力图数据（基于 created_at）"""
        from datetime import date as date_type

        start = date_type(year, 1, 1)
        end = date_type(year, 12, 31)
        start_str = start.isoformat()
        end_str = end.isoformat() + "T23:59:59"

        counts = self._sqlite.get_daily_activity_counts(user_id, start_str, end_str)

        items = []
        current = start
        while current <= end:
            items.append(ActivityHeatmapItem(
                date=current.isoformat(),
                count=counts.get(current.isoformat(), 0),
            ))
            current += timedelta(days=1)

        return ActivityHeatmapResponse(year=year, items=items)

    async def export_growth_report(self, user_id: str) -> str:
        """生成成长报告 Markdown 内容"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        # Section 1: 概览
        categories = ["task", "note", "inbox", "project", "decision", "reflection", "question"]
        category_labels = {
            "task": "任务", "note": "笔记", "inbox": "灵感", "project": "项目",
            "decision": "决策", "reflection": "复盘", "question": "待解问题",
        }
        counts = {cat: self._sqlite.count_entries(type=cat, user_id=user_id) for cat in categories}
        total = sum(counts.values())

        overview_lines = [
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 总条目数 | {total} |",
        ]
        for cat in categories:
            overview_lines.append(f"| {category_labels[cat]} | {counts[cat]} |")

        # Section 2: 学习趋势
        trend_data = self.get_trend_data(period="weekly", weeks=4, user_id=user_id)
        trend_lines = []
        if trend_data and hasattr(trend_data, "daily_data") and trend_data.daily_data:
            from collections import defaultdict
            weekly_buckets = defaultdict(int)
            for item in trend_data.daily_data:
                d = item.date if hasattr(item, "date") else str(item.get("date", ""))
                cnt = item.total if hasattr(item, "total") else item.get("total", 0)
                try:
                    dt = date.fromisoformat(str(d))
                    ws = dt - timedelta(days=dt.weekday())
                    weekly_buckets[ws.isoformat()] += cnt
                except (ValueError, TypeError):
                    pass
            for ws in sorted(weekly_buckets.keys()):
                trend_lines.append(f"- {ws}: {weekly_buckets[ws]} 条")
        if not trend_lines:
            trend_lines = ["暂无数据"]

        # Section 3: 学习连续天数
        streak = self._calculate_learning_streak(user_id)

        # Section 4: 知识图谱概览
        knowledge_lines = []
        try:
            from app.routers.deps import get_knowledge_service
            ks = get_knowledge_service()
            stats = ks.get_knowledge_stats(user_id)
            knowledge_lines = [
                f"| 指标 | 数值 |",
                f"|------|------|",
                f"| 概念数 | {stats.concept_count} |",
                f"| 关联数 | {stats.relation_count} |",
            ]
            if hasattr(stats, "category_distribution") and stats.category_distribution:
                dist_str = " / ".join(f"{k} {v}" for k, v in stats.category_distribution.items())
                knowledge_lines.append(f"| 掌握度分布 | {dist_str} |")
        except Exception:
            knowledge_lines = ["暂无数据"]

        return f"""# 📊 成长报告

> 生成时间：{date_str}
> 报告周期：全部数据

## 概览

{chr(10).join(overview_lines)}

## 学习趋势

{chr(10).join(trend_lines)}

## 学习连续天数

{streak} 天

## 知识图谱概览

{chr(10).join(knowledge_lines)}
"""

    async def get_insights(
        self, period: str = "weekly", user_id: Optional[str] = None
    ) -> InsightsResponse:
        """
        获取 AI 深度洞察

        Args:
            period: 统计周期 (weekly|monthly)
            user_id: 用户 ID

        Returns:
            InsightsResponse 结构化洞察
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        today = date.today()

        # 计算时间范围
        if period == "weekly":
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        else:  # monthly
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                next_month = date(today.year, today.month + 1, 1)
                end_date = next_month - timedelta(days=1)

        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # 获取周期内条目
        entries = self._sqlite.list_entries(
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        # 获取前一个周期的条目（用于对比）
        if period == "weekly":
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
        else:
            if today.month == 1:
                prev_start = date(today.year - 1, 12, 1)
            else:
                prev_start = date(today.year, today.month - 1, 1)
            prev_end = start_date - timedelta(days=1)

        prev_entries = self._sqlite.list_entries(
            start_date=prev_start.isoformat(),
            end_date=prev_end.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        # 尝试 LLM 生成深度洞察
        insights, source = await self._generate_deep_insights(
            period=period,
            entries=entries,
            prev_entries=prev_entries,
            start_date=start_str,
            end_date=end_str,
            user_id=user_id or "_default",
        )

        return InsightsResponse(
            period=period,
            start_date=start_str,
            end_date=end_str,
            insights=insights,
            source=source,
        )

    async def _generate_deep_insights(
        self,
        period: str,
        entries: List[dict],
        prev_entries: List[dict],
        start_date: str,
        end_date: str,
        user_id: str,
    ) -> tuple:
        """
        生成深度洞察

        优先使用 LLM 生成结构化洞察，LLM 不可用时降级为规则分析。

        Args:
            period: 周期
            entries: 本周期条目
            prev_entries: 上周期条目
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户 ID

        Returns:
            (DeepInsights, source) 元组
        """
        # 先尝试 LLM
        if self._llm_caller:
            try:
                import json

                # 统计当前周期数据（复用共享 helper）
                _, _, curr_tasks, curr_notes, curr_inbox = self._analyze_category_distribution(entries)
                curr_completed = sum(1 for t in curr_tasks if t.get("status") == "complete")
                curr_completion_rate = (curr_completed / len(curr_tasks) * 100) if curr_tasks else 0

                # 统计上一周期数据
                _, _, prev_tasks, _, _ = self._analyze_category_distribution(prev_entries)
                prev_completed = sum(1 for t in prev_tasks if t.get("status") == "complete")
                prev_completion_rate = (prev_completed / len(prev_tasks) * 100) if prev_tasks else 0

                # 收集标签
                curr_tags = []
                for e in entries:
                    curr_tags.extend(e.get("tags", []))

                stats_data = {
                    "period": period,
                    "start_date": start_date,
                    "end_date": end_date,
                    "current": {
                        "total_entries": len(entries),
                        "tasks": len(curr_tasks),
                        "completed": curr_completed,
                        "completion_rate": round(curr_completion_rate, 1),
                        "notes": len(curr_notes),
                        "inbox": len(curr_inbox),
                        "top_tags": list(set(curr_tags))[:10],
                    },
                    "previous": {
                        "total_entries": len(prev_entries),
                        "tasks": len(prev_tasks),
                        "completed": prev_completed,
                        "completion_rate": round(prev_completion_rate, 1),
                    },
                }

                system_prompt = (
                    "你是个人成长助手「日知」，请根据用户数据生成深度洞察。"
                    "必须返回 JSON 格式，包含三个字段：\n"
                    "1. behavior_patterns: 行为模式数组，每项含 pattern(描述), frequency(次数), trend(improving/stable/declining)\n"
                    "2. growth_suggestions: 成长建议数组，每项含 suggestion(建议), priority(high/medium/low), related_area(领域)\n"
                    "3. capability_changes: 能力变化数组，每项含 capability(能力名), previous_level(0-1), current_level(0-1), change(变化值)\n"
                    "每个数组最多3项。只返回 JSON，不要其他内容。"
                )

                user_message = (
                    f"周期类型：{period}\n"
                    f"统计数据：\n{json.dumps(stats_data, ensure_ascii=False, indent=2)}\n\n"
                    f"请生成深度洞察。"
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
                result = await asyncio.wait_for(
                    self._llm_caller.call(messages),
                    timeout=10.0,
                )

                if result:
                    parsed = self._parse_llm_json(result)
                    if parsed and isinstance(parsed, dict):
                        insights = DeepInsights(
                            behavior_patterns=[
                                BehaviorPattern(**bp)
                                for bp in parsed.get("behavior_patterns", [])[:3]
                            ],
                            growth_suggestions=[
                                GrowthSuggestion(**gs)
                                for gs in parsed.get("growth_suggestions", [])[:3]
                            ],
                            capability_changes=[
                                CapabilityChange(**cc)
                                for cc in parsed.get("capability_changes", [])[:3]
                            ],
                        )
                        return insights, "llm"

            except asyncio.TimeoutError:
                logger.warning("LLM 深度洞察生成超时，降级为规则分析")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"LLM 深度洞察 JSON 解析失败，降级为规则分析: {e}")
            except Exception as e:
                logger.warning(f"LLM 深度洞察生成失败，降级为规则分析: {e}")

        # 降级为规则分析
        insights = self._generate_rule_based_insights(
            period, entries, prev_entries
        )
        return insights, "rule_based"

    def _analyze_category_distribution(
        self, entries: List[dict]
    ) -> tuple:
        """分析条目分类分布，返回 (total, category_counts, curr_tasks, curr_notes, curr_inbox)"""
        curr_tasks = [e for e in entries if e.get("type") == "task"]
        curr_notes = [e for e in entries if e.get("type") == "note"]
        curr_inbox = [e for e in entries if e.get("type") == "inbox"]

        category_counts: Dict[str, int] = {}
        for entry in entries:
            entry_type = entry.get("type", "task")
            category_counts[entry_type] = category_counts.get(entry_type, 0) + 1

        return len(entries), category_counts, curr_tasks, curr_notes, curr_inbox

    def _generate_rule_based_insights(
        self,
        period: str,
        entries: List[dict],
        prev_entries: List[dict],
    ) -> DeepInsights:
        """
        基于规则的洞察生成（LLM 不可用时的降级方案）

        按请求周期生成洞察，与 _generate_pattern_insights 共享分析模式但周期感知。

        Args:
            period: 周期 (weekly|monthly)
            entries: 本周期条目
            prev_entries: 上周期条目

        Returns:
            DeepInsights 结构化洞察
        """
        behavior_patterns: List[BehaviorPattern] = []
        growth_suggestions: List[GrowthSuggestion] = []
        capability_changes: List[CapabilityChange] = []

        total, category_counts, curr_tasks, curr_notes, curr_inbox = (
            self._analyze_category_distribution(entries)
        )

        period_label = "本周" if period == "weekly" else "本月"

        # --- 行为模式：分类分布（与 _generate_pattern_insights 共享模式） ---
        if total > 0:
            for cat_type, count in category_counts.items():
                ratio = count / total
                if ratio > 0.6 and total >= 5:
                    behavior_patterns.append(BehaviorPattern(
                        pattern=f"{period_label}更倾向于创建{self.CATEGORY_LABELS.get(cat_type, cat_type)}，占比{int(ratio * 100)}%",
                        frequency=count,
                        trend="stable",
                    ))

        # --- 行为模式：完成率趋势 ---
        curr_completed = sum(1 for t in curr_tasks if t.get("status") == "complete")
        curr_rate = (curr_completed / len(curr_tasks) * 100) if curr_tasks else 0

        prev_tasks = [e for e in prev_entries if e.get("type") == "task"]
        prev_completed = sum(1 for t in prev_tasks if t.get("status") == "complete")
        prev_rate = (prev_completed / len(prev_tasks) * 100) if prev_tasks else 0

        if curr_tasks and prev_tasks:
            diff = curr_rate - prev_rate
            if abs(diff) >= 15:
                trend = "improving" if diff > 0 else "declining"
                direction = "提升" if diff > 0 else "下降"
                behavior_patterns.append(BehaviorPattern(
                    pattern=f"{period_label}任务完成率比上期{direction}了{int(abs(diff))}%",
                    frequency=len(curr_tasks),
                    trend=trend,
                ))

        # --- 成长建议 ---
        inbox_count = len(curr_inbox)
        if inbox_count >= 3:
            growth_suggestions.append(GrowthSuggestion(
                suggestion=f"有{inbox_count}个灵感尚未转化为行动，建议及时整理",
                priority="medium",
                related_area="灵感管理",
            ))

        if curr_rate < 50 and len(curr_tasks) >= 3:
            growth_suggestions.append(GrowthSuggestion(
                suggestion=f"{period_label}任务完成率较低，建议减少并行任务数量",
                priority="high",
                related_area="任务管理",
            ))

        if len(curr_notes) == 0 and total >= 3:
            growth_suggestions.append(GrowthSuggestion(
                suggestion=f"{period_label}没有记录学习笔记，建议养成记录习惯",
                priority="medium",
                related_area="学习记录",
            ))

        # --- 能力变化（基于标签活跃度） ---
        curr_tags: Dict[str, int] = {}
        for entry in entries:
            for tag in entry.get("tags", []):
                curr_tags[tag] = curr_tags.get(tag, 0) + 1

        prev_tags: Dict[str, int] = {}
        for entry in prev_entries:
            for tag in entry.get("tags", []):
                prev_tags[tag] = prev_tags.get(tag, 0) + 1

        all_tags = set(curr_tags.keys()) | set(prev_tags.keys())
        for tag in sorted(all_tags, key=lambda t: curr_tags.get(t, 0), reverse=True)[:3]:
            curr_count = curr_tags.get(tag, 0)
            prev_count = prev_tags.get(tag, 0)
            curr_level = min(curr_count / 5.0, 1.0)
            prev_level = min(prev_count / 5.0, 1.0)
            if abs(curr_level - prev_level) > 0.01:
                capability_changes.append(CapabilityChange(
                    capability=tag,
                    previous_level=round(prev_level, 2),
                    current_level=round(curr_level, 2),
                    change=round(curr_level - prev_level, 2),
                ))

        return DeepInsights(
            behavior_patterns=behavior_patterns[:3],
            growth_suggestions=growth_suggestions[:3],
            capability_changes=capability_changes[:3],
        )
