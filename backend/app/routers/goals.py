"""目标管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.goal import (
    GoalCreate,
    GoalUpdate,
    GoalResponse,
    GoalListResponse,
    GoalDetailResponse,
)
from app.routers.deps import get_current_user, get_goal_service
from app.models.user import User

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=201)
async def create_goal(
    request: GoalCreate,
    user: User = Depends(get_current_user),
):
    """创建目标"""
    service = get_goal_service()
    result, status_code, message = await service.create_goal(request, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status_code, detail=message)
    return result


@router.get("", response_model=GoalListResponse)
async def list_goals(
    status: str = Query(None, description="按状态过滤: active/completed/abandoned"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    user: User = Depends(get_current_user),
):
    """列出目标"""
    service = get_goal_service()
    results, status_code, message = await service.list_goals(user.id, status=status, limit=limit)
    return GoalListResponse(goals=results)


@router.get("/{goal_id}", response_model=GoalDetailResponse)
async def get_goal(
    goal_id: str,
    user: User = Depends(get_current_user),
):
    """获取目标详情"""
    service = get_goal_service()
    result, status_code, message = await service.get_goal(goal_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status_code, detail=message)
    return result


@router.put("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    request: GoalUpdate,
    user: User = Depends(get_current_user),
):
    """更新目标"""
    service = get_goal_service()
    result, status_code, message = await service.update_goal(goal_id, request, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status_code, detail=message)
    return result


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: str,
    user: User = Depends(get_current_user),
):
    """删除目标（仅 abandoned 状态可删除）"""
    service = get_goal_service()
    result, status_code, message = await service.delete_goal(goal_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=status_code, detail=message)
    return {"message": message}
