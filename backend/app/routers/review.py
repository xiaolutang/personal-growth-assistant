"""成长回顾 API 路由"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.routers.deps import get_storage

router = APIRouter(prefix="/review", tags=["review"])


# === 请求/响应模型 ===

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


# === API 端点 ===

@router.get("/daily", response_model=DailyReport)
async def get_daily_report(
    date_param: Optional[str] = Query(None, alias="date", description="日期 (YYYY-MM-DD)，默认今天")
):
    """获取日报"""
    storage = get_storage()

    # 解析日期
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    else:
        target_date = date.today()

    date_str = target_date.isoformat()
    next_day = (target_date + timedelta(days=1)).isoformat()

    if not storage.sqlite:
        raise HTTPException(status_code=503, detail="SQLite 索引不可用")

    # 获取当天任务
    tasks = storage.sqlite.list_entries(
        type="task",
        start_date=date_str,
        end_date=next_day,
        limit=1000,
    )

    # 获取当天笔记
    notes = storage.sqlite.list_entries(
        type="note",
        start_date=date_str,
        end_date=next_day,
        limit=1000,
    )

    # 统计任务
    task_stats = _calculate_task_stats(tasks)

    # 统计笔记
    note_stats = NoteStats(
        total=len(notes),
        recent_titles=[n.get("title", "")[:50] for n in notes[:5]],
    )

    # 获取完成的任务
    completed_tasks = [t for t in tasks if t.get("status") == "complete"]

    return DailyReport(
        date=date_str,
        task_stats=task_stats,
        note_stats=note_stats,
        completed_tasks=completed_tasks,
    )


@router.get("/weekly", response_model=WeeklyReport)
async def get_weekly_report(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)，默认本周一")
):
    """获取周报"""
    storage = get_storage()

    # 计算本周日期范围
    if start_date:
        try:
            week_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    else:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    week_end = week_start + timedelta(days=6)

    start_str = week_start.isoformat()
    end_str = (week_end + timedelta(days=1)).isoformat()  # 包含最后一天

    if not storage.sqlite:
        raise HTTPException(status_code=503, detail="SQLite 索引不可用")

    # 获取本周任务和笔记
    tasks = storage.sqlite.list_entries(
        type="task",
        start_date=start_str,
        end_date=end_str,
        limit=1000,
    )

    notes = storage.sqlite.list_entries(
        type="note",
        start_date=start_str,
        end_date=end_str,
        limit=1000,
    )

    # 统计
    task_stats = _calculate_task_stats(tasks)
    note_stats = NoteStats(
        total=len(notes),
        recent_titles=[n.get("title", "")[:50] for n in notes[:5]],
    )

    # 每日分解
    daily_breakdown = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.isoformat()
        next_day_str = (day + timedelta(days=1)).isoformat()

        day_tasks = storage.sqlite.list_entries(
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


@router.get("/monthly", response_model=MonthlyReport)
async def get_monthly_report(
    month: Optional[str] = Query(None, description="月份 (YYYY-MM)，默认本月")
):
    """获取月报"""
    storage = get_storage()

    # 计算月份范围
    if month:
        try:
            month_start = datetime.strptime(month, "%Y-%m").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="月份格式错误，应为 YYYY-MM")
    else:
        today = date.today()
        month_start = date(today.year, today.month, 1)

    # 计算月末
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

    start_str = month_start.isoformat()
    end_str = (month_end + timedelta(days=1)).isoformat()

    if not storage.sqlite:
        raise HTTPException(status_code=503, detail="SQLite 索引不可用")

    # 获取本月任务和笔记
    tasks = storage.sqlite.list_entries(
        type="task",
        start_date=start_str,
        end_date=end_str,
        limit=1000,
    )

    notes = storage.sqlite.list_entries(
        type="note",
        start_date=start_str,
        end_date=end_str,
        limit=1000,
    )

    # 统计
    task_stats = _calculate_task_stats(tasks)
    note_stats = NoteStats(
        total=len(notes),
        recent_titles=[n.get("title", "")[:50] for n in notes[:5]],
    )

    # 周分解
    weekly_breakdown = []
    current_week_start = month_start
    week_num = 1

    while current_week_start <= month_end:
        week_end = min(current_week_start + timedelta(days=6), month_end)

        week_tasks = storage.sqlite.list_entries(
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


# === 辅助函数 ===

def _calculate_task_stats(tasks: List[dict]) -> TaskStats:
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
