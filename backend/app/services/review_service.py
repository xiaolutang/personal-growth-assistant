"""成长回顾统计服务"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field


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


class ReviewService:
    """成长回顾统计服务"""

    def __init__(self, sqlite_storage=None):
        """
        初始化服务

        Args:
            sqlite_storage: SQLite 存储实例
        """
        self._sqlite = sqlite_storage

    def set_sqlite_storage(self, storage):
        """设置 SQLite 存储"""
        self._sqlite = storage

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

        return DailyReport(
            date=date_str,
            task_stats=task_stats,
            note_stats=note_stats,
            completed_tasks=completed_tasks,
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

        return WeeklyReport(
            start_date=start_str,
            end_date=week_end.isoformat(),
            task_stats=task_stats,
            note_stats=note_stats,
            daily_breakdown=daily_breakdown,
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

        return MonthlyReport(
            month=month_start.strftime("%Y-%m"),
            task_stats=task_stats,
            note_stats=note_stats,
            weekly_breakdown=weekly_breakdown,
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
