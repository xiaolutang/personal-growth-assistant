"""成长回顾统计服务"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field


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

    def get_daily_report(self, target_date: Optional[date] = None) -> DailyReport:
        """
        获取日报

        Args:
            target_date: 目标日期，默认今天

        Returns:
            DailyReport: 日报数据
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()
        next_day = (target_date + timedelta(days=1)).isoformat()

        # 获取当天任务
        tasks = self._sqlite.list_entries(
            type="task",
            start_date=date_str,
            end_date=next_day,
            limit=1000,
        )

        # 获取当天笔记
        notes = self._sqlite.list_entries(
            type="note",
            start_date=date_str,
            end_date=next_day,
            limit=1000,
        )

        # 统计
        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)

        # 获取完成的任务
        completed_tasks = [t for t in tasks if t.get("status") == "complete"]

        return DailyReport(
            date=date_str,
            task_stats=task_stats,
            note_stats=note_stats,
            completed_tasks=completed_tasks,
        )

    def get_weekly_report(self, week_start: Optional[date] = None) -> WeeklyReport:
        """
        获取周报

        Args:
            week_start: 周开始日期，默认本周一

        Returns:
            WeeklyReport: 周报数据
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        start_str = week_start.isoformat()
        end_str = (week_end + timedelta(days=1)).isoformat()

        # 获取本周任务和笔记
        tasks = self._sqlite.list_entries(
            type="task",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
        )

        # 统计
        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)

        # 每日分解
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

    def get_monthly_report(self, month_start: Optional[date] = None) -> MonthlyReport:
        """
        获取月报

        Args:
            month_start: 月开始日期，默认本月第一天

        Returns:
            MonthlyReport: 月报数据
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if month_start is None:
            today = date.today()
            month_start = date(today.year, today.month, 1)

        # 计算月末
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        start_str = month_start.isoformat()
        end_str = (month_end + timedelta(days=1)).isoformat()

        # 获取本月任务和笔记
        tasks = self._sqlite.list_entries(
            type="task",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
        )

        # 统计
        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)

        # 周分解
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
