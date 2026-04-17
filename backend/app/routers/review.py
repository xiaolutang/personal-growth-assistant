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
    TrendResponse,
    HeatmapResponse,
    GrowthCurveResponse,
    MorningDigestResponse,
    ActivityHeatmapResponse,
    VsLastPeriod,
)

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/daily", response_model=DailyReport)
async def get_daily_report(
    date_param: Optional[str] = Query(None, alias="date", description="日期 (YYYY-MM-DD)，默认今天"),
    user: User = Depends(get_current_user),
):
    """获取日报"""
    review_service = get_review_service()

    try:
        target_date = review_service.parse_date(date_param)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return review_service.get_daily_report(target_date, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/weekly", response_model=WeeklyReport)
async def get_weekly_report(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)，默认本周一"),
    user: User = Depends(get_current_user),
):
    """获取周报"""
    review_service = get_review_service()

    try:
        week_start = review_service.parse_date(start_date)
        if start_date is None:
            today = date.today()
            week_start = today - __import__('datetime').timedelta(days=today.weekday())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return review_service.get_weekly_report(week_start, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/monthly", response_model=MonthlyReport)
async def get_monthly_report(
    month: Optional[str] = Query(None, description="月份 (YYYY-MM)，默认本月"),
    user: User = Depends(get_current_user),
):
    """获取月报"""
    review_service = get_review_service()

    try:
        month_start = review_service.parse_month(month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return review_service.get_monthly_report(month_start, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/trend", response_model=TrendResponse)
async def get_trend_data(
    period: str = Query("daily", description="统计周期: daily 或 weekly"),
    days: int = Query(7, description="daily 模式天数", ge=1, le=365),
    weeks: int = Query(8, description="weekly 模式周数", ge=1, le=52),
    user: User = Depends(get_current_user),
):
    """获取趋势数据"""
    review_service = get_review_service()

    if period not in ("daily", "weekly"):
        raise HTTPException(status_code=422, detail="period 参数必须是 daily 或 weekly")

    try:
        return review_service.get_trend_data(
            period=period,
            days=days,
            weeks=weeks,
            user_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/knowledge-heatmap", response_model=HeatmapResponse)
async def get_knowledge_heatmap(
    user: User = Depends(get_current_user),
):
    """获取知识热力图"""
    review_service = get_review_service()

    try:
        return review_service.get_knowledge_heatmap(user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/growth-curve", response_model=GrowthCurveResponse)
async def get_growth_curve(
    weeks: int = Query(8, description="回溯周数", ge=1, le=52),
    user: User = Depends(get_current_user),
):
    """获取成长曲线数据"""
    review_service = get_review_service()

    try:
        return review_service.get_growth_curve(weeks=weeks, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/morning-digest", response_model=MorningDigestResponse)
async def get_morning_digest(
    user: User = Depends(get_current_user),
):
    """获取 AI 晨报 — 每日主动建议"""
    review_service = get_review_service()

    try:
        return review_service.get_morning_digest(user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/activity-heatmap", response_model=ActivityHeatmapResponse)
async def get_activity_heatmap(
    year: int = Query(default=date.today().year, description="年份"),
    user: User = Depends(get_current_user),
):
    """获取年度每日活动热力图"""
    review_service = get_review_service()
    return review_service.get_activity_heatmap(year=year, user_id=user.id)
