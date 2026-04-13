"""成长回顾 API 路由"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.deps import get_review_service, get_current_user
from app.models.user import User
from app.services.review_service import (
    TaskStats,
    NoteStats,
    DailyReport,
    WeeklyReport,
    MonthlyReport,
)

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/daily", response_model=DailyReport)
async def get_daily_report(
    date_param: Optional[str] = Query(None, alias="date", description="日期 (YYYY-MM-DD)，默认今天"),
    user: User = Depends(get_current_user),
):
    """获取日报"""
    review_service = get_review_service()

    # 解析日期
    try:
        target_date = review_service.parse_date(date_param)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return review_service.get_daily_report(target_date)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/weekly", response_model=WeeklyReport)
async def get_weekly_report(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)，默认本周一"),
    user: User = Depends(get_current_user),
):
    """获取周报"""
    review_service = get_review_service()

    # 计算本周日期范围
    try:
        week_start = review_service.parse_date(start_date)
        # 如果指定了日期，使用它；否则从周一开始
        if start_date is None:
            today = date.today()
            week_start = today - __import__('datetime').timedelta(days=today.weekday())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return review_service.get_weekly_report(week_start)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/monthly", response_model=MonthlyReport)
async def get_monthly_report(
    month: Optional[str] = Query(None, description="月份 (YYYY-MM)，默认本月"),
    user: User = Depends(get_current_user),
):
    """获取月报"""
    review_service = get_review_service()

    # 计算月份范围
    try:
        month_start = review_service.parse_month(month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return review_service.get_monthly_report(month_start)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
