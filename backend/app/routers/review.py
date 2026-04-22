"""成长回顾 API 路由"""
import io
import tempfile
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.routers.deps import get_review_service, get_current_user, get_knowledge_service
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
    InsightsResponse,
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
        return await review_service.get_daily_report(target_date, user_id=user.id)
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
        return await review_service.get_weekly_report(week_start, user_id=user.id)
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
        return await review_service.get_monthly_report(month_start, user_id=user.id)
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
        return await review_service.get_knowledge_heatmap(user_id=user.id)
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
        return await review_service.get_morning_digest(user_id=user.id)
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


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    period: str = Query(..., description="统计周期: weekly 或 monthly"),
    user: User = Depends(get_current_user),
):
    """获取 AI 深度洞察"""
    if period not in ("weekly", "monthly"):
        raise HTTPException(status_code=422, detail="period 参数必须是 weekly 或 monthly")

    review_service = get_review_service()

    try:
        return await review_service.get_insights(period=period, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/growth-report")
async def export_growth_report(
    user: User = Depends(get_current_user),
):
    """导出成长报告 Markdown 文件"""
    review_service = get_review_service()
    if not review_service or not review_service._sqlite:
        raise HTTPException(status_code=503, detail="review_service 未初始化")

    user_id = user.id
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # Section 1: 概览 — 逐类调用 sqlite.count_entries
    categories = ["task", "note", "inbox", "project", "decision", "reflection", "question"]
    category_labels = {
        "task": "任务", "note": "笔记", "inbox": "灵感", "project": "项目",
        "decision": "决策", "reflection": "复盘", "question": "待解问题",
    }
    counts = {}
    for cat in categories:
        counts[cat] = review_service._sqlite.count_entries(type=cat, user_id=user_id)
    total = sum(counts.values())

    overview_lines = [
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 总条目数 | {total} |",
    ]
    for cat in categories:
        overview_lines.append(f"| {category_labels[cat]} | {counts[cat]} |")

    # Section 2: 学习趋势 — 近4周周计数
    trend_data = review_service.get_trend_data(period="weekly", weeks=4, user_id=user_id)
    trend_lines = []
    if trend_data and hasattr(trend_data, "daily_data") and trend_data.daily_data:
        # 按周聚合 daily_data
        from collections import defaultdict
        weekly_buckets = defaultdict(int)
        for item in trend_data.daily_data:
            d = item.date if hasattr(item, "date") else str(item.get("date", ""))
            cnt = item.total if hasattr(item, "total") else item.get("total", 0)
            # 取周一开始日期
            try:
                dt = date.fromisoformat(str(d))
                week_start = dt - __import__("datetime").timedelta(days=dt.weekday())
                weekly_buckets[week_start.isoformat()] += cnt
            except (ValueError, TypeError):
                pass
        for week_start in sorted(weekly_buckets.keys()):
            trend_lines.append(f"- {week_start}: {weekly_buckets[week_start]} 条")
    if not trend_lines:
        trend_lines = ["暂无数据"]

    # Section 3: 学习连续天数
    streak = review_service._calculate_learning_streak(user_id)

    # Section 4: 知识图谱概览
    ks = get_knowledge_service()
    knowledge_lines = []
    try:
        stats = ks._stats_from_sqlite(user_id)
        knowledge_lines = [
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 概念数 | {stats.concept_count} |",
            f"| 关联数 | {stats.relation_count} |",
        ]
        # 掌握度分布
        if hasattr(stats, "category_distribution") and stats.category_distribution:
            dist_str = " / ".join(f"{k} {v}" for k, v in stats.category_distribution.items())
            knowledge_lines.append(f"| 掌握度分布 | {dist_str} |")
    except Exception:
        knowledge_lines = ["暂无数据"]

    # 生成 Markdown
    md_content = f"""# 📊 成长报告

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

    # 使用 StreamingResponse 返回
    filename = f"growth_report_{date_str}.md"
    return StreamingResponse(
        iter([md_content.encode("utf-8")]),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
