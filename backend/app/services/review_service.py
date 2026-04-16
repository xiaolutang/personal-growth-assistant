"""成长回顾统计服务"""
import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.callers import APICaller

logger = logging.getLogger(__name__)


def _run_async(coro):
    """安全地在同步方法中运行异步协程"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # 已经在事件循环中（FastAPI async 路由），使用 nest_asyncio 或创建新线程
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class TrendPeriod(BaseModel):
    """趋势统计周期"""
    date: str = Field(..., description="日期（YYYY-MM-DD 或 YYYY-WXX）")
    total: int = Field(0, description="总任务数")
    completed: int = Field(0, description="已完成数")
    completion_rate: float = Field(0.0, description="完成率（百分比）")
    notes_count: int = Field(0, description="笔记数")


class TrendResponse(BaseModel):
    """趋势数据响应"""
    periods: List[TrendPeriod] = Field(default_factory=list, description="统计周期数组")


class HeatmapItem(BaseModel):
    """热力图项"""
    concept: str
    mastery: str = "new"
    entry_count: int = 0
    category: Optional[str] = None


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


class WeeklyReport(BaseModel):
    """周报响应"""
    start_date: str
    end_date: str
    task_stats: TaskStats
    note_stats: NoteStats
    daily_breakdown: List[dict] = Field(default_factory=list)
    ai_summary: Optional[str] = None


class MonthlyReport(BaseModel):
    """月报响应"""
    month: str
    task_stats: TaskStats
    note_stats: NoteStats
    weekly_breakdown: List[dict] = Field(default_factory=list)
    ai_summary: Optional[str] = None


class ActivityHeatmapItem(BaseModel):
    date: str
    count: int = 0


class ActivityHeatmapResponse(BaseModel):
    year: int
    items: List[ActivityHeatmapItem] = []


class ReviewService:
    """成长回顾统计服务"""

    def __init__(self, sqlite_storage=None):
        """
        初始化服务

        Args:
            sqlite_storage: SQLite 存储实例
        """
        self._sqlite = sqlite_storage
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

    def get_daily_report(self, target_date: Optional[date] = None, user_id: Optional[str] = None) -> DailyReport:
        """获取日报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()
        next_day = (target_date + timedelta(days=1)).isoformat()

        tasks = self._sqlite.list_entries(
            type="task",
            start_date=date_str,
            end_date=next_day,
            limit=1000,
            user_id=user_id,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=date_str,
            end_date=next_day,
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
            ai_summary = _run_async(
                self._generate_ai_summary("daily", stats_data, user_id=user_id or "_default")
            )

        return DailyReport(
            date=date_str,
            task_stats=task_stats,
            note_stats=note_stats,
            completed_tasks=completed_tasks,
            ai_summary=ai_summary,
        )

    def get_weekly_report(self, week_start: Optional[date] = None, user_id: Optional[str] = None) -> WeeklyReport:
        """获取周报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        start_str = week_start.isoformat()
        end_str = (week_end + timedelta(days=1)).isoformat()

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
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_str = day.isoformat()
            next_day_str = (day + timedelta(days=1)).isoformat()

            day_tasks = self._sqlite.list_entries(
                type="task",
                start_date=day_str,
                end_date=next_day_str,
                limit=1000,
                user_id=user_id,
            )

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
            ai_summary = _run_async(
                self._generate_ai_summary("weekly", stats_data, user_id=user_id or "_default")
            )

        return WeeklyReport(
            start_date=start_str,
            end_date=week_end.isoformat(),
            task_stats=task_stats,
            note_stats=note_stats,
            daily_breakdown=daily_breakdown,
            ai_summary=ai_summary,
        )

    def get_monthly_report(self, month_start: Optional[date] = None, user_id: Optional[str] = None) -> MonthlyReport:
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
        end_str = (month_end + timedelta(days=1)).isoformat()

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

        while current_week_start <= month_end:
            week_end = min(current_week_start + timedelta(days=6), month_end)

            week_tasks = self._sqlite.list_entries(
                type="task",
                start_date=current_week_start.isoformat(),
                end_date=(week_end + timedelta(days=1)).isoformat(),
                limit=1000,
                user_id=user_id,
            )

            completed = sum(1 for t in week_tasks if t.get("status") == "complete")
            weekly_breakdown.append({
                "week": f"第{week_num}周",
                "start_date": current_week_start.isoformat(),
                "end_date": week_end.isoformat(),
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
            ai_summary = _run_async(
                self._generate_ai_summary("monthly", stats_data, user_id=user_id or "_default")
            )

        return MonthlyReport(
            month=month_start.strftime("%Y-%m"),
            task_stats=task_stats,
            note_stats=note_stats,
            weekly_breakdown=weekly_breakdown,
            ai_summary=ai_summary,
        )

    def get_trend_data(
        self,
        period: str = "daily",
        days: int = 7,
        weeks: int = 8,
        user_id: Optional[str] = None,
    ) -> TrendResponse:
        """获取趋势数据"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if period not in ("daily", "weekly"):
            raise ValueError("period 参数必须是 daily 或 weekly")

        periods: List[TrendPeriod] = []

        if period == "daily":
            count = max(1, min(days, 365))
            today = date.today()
            for i in range(count):
                target_date = today - timedelta(days=i)
                next_day = target_date + timedelta(days=1)

                tasks = self._sqlite.list_entries(
                    type="task",
                    start_date=target_date.isoformat(),
                    end_date=next_day.isoformat(),
                    limit=1000,
                    user_id=user_id,
                )
                notes = self._sqlite.list_entries(
                    type="note",
                    start_date=target_date.isoformat(),
                    end_date=next_day.isoformat(),
                    limit=1000,
                    user_id=user_id,
                )

                total = len(tasks)
                completed = sum(1 for t in tasks if t.get("status") == "complete")
                completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

                periods.append(TrendPeriod(
                    date=target_date.isoformat(),
                    total=total,
                    completed=completed,
                    completion_rate=completion_rate,
                    notes_count=len(notes),
                ))
        else:  # weekly
            count = max(1, min(weeks, 52))
            today = date.today()
            current_week_start = today - timedelta(days=today.weekday())

            for i in range(count):
                week_start = current_week_start - timedelta(weeks=i)
                week_end = week_start + timedelta(days=6)
                next_day_after_week = week_end + timedelta(days=1)

                tasks = self._sqlite.list_entries(
                    type="task",
                    start_date=week_start.isoformat(),
                    end_date=next_day_after_week.isoformat(),
                    limit=1000,
                    user_id=user_id,
                )
                notes = self._sqlite.list_entries(
                    type="note",
                    start_date=week_start.isoformat(),
                    end_date=next_day_after_week.isoformat(),
                    limit=1000,
                    user_id=user_id,
                )

                total = len(tasks)
                completed = sum(1 for t in tasks if t.get("status") == "complete")
                completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

                periods.append(TrendPeriod(
                    date=week_start.isoformat(),
                    total=total,
                    completed=completed,
                    completion_rate=completion_rate,
                    notes_count=len(notes),
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

    def get_knowledge_heatmap(self, user_id: str = "_default") -> HeatmapResponse:
        """
        获取知识热力图

        Args:
            user_id: 用户 ID

        Returns:
            HeatmapResponse: 知识热力图数据
        """
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

        # 按 entry_count 降序排序
        items.sort(key=lambda x: x.entry_count, reverse=True)

        return HeatmapResponse(items=items)

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

        points: List[GrowthCurvePoint] = []

        for i in range(count):
            week_start = current_week_start - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            next_day_after_week = week_end + timedelta(days=1)

            # 获取该周的条目
            week_entries = self._sqlite.list_entries(
                start_date=week_start.isoformat(),
                end_date=next_day_after_week.isoformat(),
                limit=1000,
                user_id=user_id,
            )

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

        使用聚合 SQL 获取最近 90 天内有条目的日期列表，
        然后在内存中从今天开始往前计算连续天数。

        Args:
            user_id: 用户 ID

        Returns:
            连续天数，无条目时返回 0
        """
        if not self._sqlite:
            return 0

        conn = self._sqlite._get_conn()
        try:
            rows = conn.execute(
                """SELECT DISTINCT DATE(created_at) AS d
                   FROM entries
                   WHERE user_id = ? AND created_at >= date('now', '-90 days')
                   ORDER BY d DESC""",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            return 0

        # 从今天开始往前数连续天数
        date_set = {row["d"] for row in rows}
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
            end_date=(today + timedelta(days=1)).isoformat(),
            limit=1000,
            user_id=user_id,
        )

        if not recent_entries:
            return []

        insights: List[str] = []

        # 1. 分类分布分析
        category_counts: Dict[str, int] = {}
        for entry in recent_entries:
            entry_type = entry.get("type", "task")
            category_counts[entry_type] = category_counts.get(entry_type, 0) + 1

        total_count = len(recent_entries)
        if total_count > 0:
            # 找到最多的类别
            top_category = max(category_counts, key=category_counts.get)
            top_ratio = category_counts[top_category] / total_count

            category_labels = {
                "task": "任务",
                "note": "笔记",
                "inbox": "灵感",
                "project": "项目",
            }
            top_label = category_labels.get(top_category, top_category)

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

    def _generate_daily_focus(
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
                result = _run_async(
                    asyncio.wait_for(self._llm_caller.call(messages), timeout=10.0)
                )
                if result:
                    # 尝试解析 JSON
                    try:
                        # 提取 JSON 部分（可能包含在 markdown 代码块中）
                        text = result.strip()
                        if "```json" in text:
                            text = text.split("```json")[1].split("```")[0].strip()
                        elif "```" in text:
                            text = text.split("```")[1].split("```")[0].strip()
                        parsed = json.loads(text)
                        if isinstance(parsed, dict) and "title" in parsed:
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

    def get_morning_digest(self, user_id: str) -> MorningDigestResponse:
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

        # 1. 今日待办（状态非 complete，优先级排序）
        all_tasks = self._sqlite.list_entries(
            type="task",
            limit=1000,
            user_id=user_id,
        )

        def _parse_date_str(val):
            """解析 planned_date 字段为 date 对象"""
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

        today_todos = [
            t for t in all_tasks
            if t.get("status") in ("waitStart", "doing")
            and _parse_date_str(t.get("planned_date")) == today
        ]
        priority_order = {"high": 0, "medium": 1, "low": 2}
        today_todos.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

        # 2. 拖延任务（planned_date 已过，状态非 complete）
        overdue = [
            t for t in all_tasks
            if t.get("status") in ("waitStart", "doing")
            and t.get("planned_date")
            and _parse_date_str(t.get("planned_date")) is not None
            and _parse_date_str(t.get("planned_date")) < today
        ]
        overdue.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

        # 3. 未跟进灵感（>3天未转化的 inbox 条目）
        three_days_ago = today - timedelta(days=3)
        all_inbox = self._sqlite.list_entries(
            type="inbox",
            limit=1000,
            user_id=user_id,
        )
        stale_inbox = [
            i for i in all_inbox
            if _parse_date_str(i.get("created_at")) is not None
            and _parse_date_str(i.get("created_at")) <= three_days_ago
            and i.get("status") in ("waitStart", "pending")
        ]

        # 4. 本周学习摘要
        week_start = today - timedelta(days=today.weekday())
        week_end_str = (week_start + timedelta(days=7)).isoformat()
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
        ai_suggestion = self._generate_morning_suggestion(
            today_todos=today_todos,
            overdue=overdue,
            stale_inbox=stale_inbox,
            weekly_summary=weekly_summary,
            user_id=user_id,
        )

        # 6. 新增增强字段
        learning_streak = self._calculate_learning_streak(user_id)
        pattern_insights = self._generate_pattern_insights(user_id)
        daily_focus = self._generate_daily_focus(
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

    def _generate_morning_suggestion(
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
                suggestion = _run_async(
                    self._generate_ai_summary("morning_digest", stats_data, user_id=user_id)
                )
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
        entry_count: int, recent_count: int, note_count: int
    ) -> str:
        """
        根据统计数据计算掌握度

        规则：
        - 0 条目 → new
        - 1-2 条目 → beginner
        - 3+ 条目且有近期活动 → intermediate
        - 6+ 条目且笔记占比 > 30% → advanced
        """
        if entry_count == 0:
            return "new"

        note_ratio = note_count / entry_count if entry_count > 0 else 0

        if entry_count >= 6 and note_ratio > 0.3:
            return "advanced"
        elif entry_count >= 3 and recent_count > 0:
            return "intermediate"
        elif entry_count >= 1:
            return "beginner"
        return "new"

    def get_activity_heatmap(self, year: int, user_id: str) -> ActivityHeatmapResponse:
        """获取年度每日活动热力图数据（基于 created_at）"""
        from datetime import date as date_type

        start = date_type(year, 1, 1)
        end = date_type(year, 12, 31)
        start_str = start.isoformat()
        end_str = end.isoformat() + "T23:59:59"

        conn = self._sqlite._get_conn()
        try:
            rows = conn.execute(
                """SELECT DATE(created_at) as d, COUNT(*) as cnt
                   FROM entries
                   WHERE user_id = ? AND created_at >= ? AND created_at <= ?
                   GROUP BY DATE(created_at)""",
                (user_id, start_str, end_str),
            ).fetchall()
            counts = {row["d"]: row["cnt"] for row in rows}
        finally:
            conn.close()

        items = []
        current = start
        while current <= end:
            items.append(ActivityHeatmapItem(
                date=current.isoformat(),
                count=counts.get(current.isoformat(), 0),
            ))
            current += timedelta(days=1)

        return ActivityHeatmapResponse(year=year, items=items)
