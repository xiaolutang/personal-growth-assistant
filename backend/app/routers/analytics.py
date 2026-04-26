"""Analytics 埋点 API 路由"""

from fastapi import APIRouter, Depends

from app.api.schemas.analytics import AnalyticsEventCreate, AnalyticsEventResponse
from app.models.user import User
from app.routers.deps import get_current_user, get_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/event", response_model=AnalyticsEventResponse)
async def record_event(
    event: AnalyticsEventCreate,
    current_user: User = Depends(get_current_user),
):
    """记录前端埋点事件（best-effort）"""
    try:
        service = get_analytics_service()
        if service:
            service.record_event(current_user.id, event.event_type, event.metadata)
    except Exception:
        pass  # best-effort: 写入失败不影响业务
    return {"ok": True}
