"""通知/提醒 API 路由"""

from fastapi import APIRouter, Depends, HTTPException

from app.routers.deps import get_current_user, get_notification_service
from app.models.user import User
from app.services.notification_service import NotificationPreferences

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
async def get_notifications(
    user: User = Depends(get_current_user),
):
    """获取当前用户通知列表（按需生成）"""
    svc = get_notification_service()
    return svc.get_notifications(user.id)


@router.post("/notifications/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: str,
    user: User = Depends(get_current_user),
):
    """标记通知已读"""
    svc = get_notification_service()
    svc.dismiss_notification(notification_id, user.id)
    return {"success": True}


@router.get("/notification-preferences", response_model=NotificationPreferences)
async def get_preferences(
    user: User = Depends(get_current_user),
):
    """获取提醒偏好"""
    svc = get_notification_service()
    return svc.get_preferences(user.id)


@router.put("/notification-preferences", response_model=NotificationPreferences)
async def update_preferences(
    prefs: NotificationPreferences,
    user: User = Depends(get_current_user),
):
    """更新提醒偏好"""
    svc = get_notification_service()
    return svc.update_preferences(user.id, prefs)
