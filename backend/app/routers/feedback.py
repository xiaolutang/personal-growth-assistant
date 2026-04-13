"""用户反馈 API 路由"""
import asyncio
import logging
from typing import Any, Literal
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints

from app.core.config import get_settings
from app.routers.deps import get_current_user, get_storage
from app.models.user import User
from log_service_sdk import report_issue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

Severity = Literal["low", "medium", "high", "critical"]
NonEmptyTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FeedbackRequest(BaseModel):
    """前端反馈请求"""

    title: NonEmptyTitle
    description: str | None = None
    severity: Severity = "medium"


class FeedbackResponse(BaseModel):
    """反馈提交响应"""

    success: bool
    feedback: dict[str, Any]


class FeedbackItem(BaseModel):
    """单条反馈记录"""

    id: int
    user_id: str
    title: str
    description: str | None = None
    severity: str = "medium"
    log_service_issue_id: int | None = None
    status: str = "pending"
    created_at: str


class FeedbackListResponse(BaseModel):
    """反馈列表响应"""

    items: list[FeedbackItem]
    total: int


async def _report_to_log_service(
    feedback_id: int,
    title: str,
    description: str | None,
    severity: str,
) -> None:
    """后台任务：异步上报到 log-service"""
    settings = get_settings()
    storage = get_storage()

    try:
        issue = await asyncio.to_thread(
            report_issue,
            settings.LOG_SERVICE_URL,
            title,
            "personal-growth-assistant",
            description=description,
            severity=severity,
            component="frontend",
        )
        remote_id = issue.get("id")
        if storage and storage.sqlite:
            storage.sqlite.update_feedback_status(
                feedback_id, "reported", log_service_issue_id=remote_id
            )
        logger.info("反馈 %d 已上报到 log-service，远程 ID: %s", feedback_id, remote_id)
    except Exception:
        logger.warning("反馈 %d 上报 log-service 失败，保留 pending 状态", feedback_id, exc_info=True)


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
) -> FeedbackResponse:
    """提交反馈：本地先写入，后台异步上报 log-service"""
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    # 1. 本地写入
    feedback = storage.sqlite.create_feedback(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
    )

    # 2. 后台异步上报
    asyncio.create_task(
        _report_to_log_service(
            feedback_id=feedback["id"],
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
        )
    )

    return FeedbackResponse(success=True, feedback=feedback)


@router.get("/feedback", response_model=FeedbackListResponse)
async def list_feedbacks(
    user: User = Depends(get_current_user),
) -> FeedbackListResponse:
    """获取当前用户的反馈列表"""
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    items = storage.sqlite.list_feedbacks_by_user(user.id)
    return FeedbackListResponse(
        items=[FeedbackItem(**item) for item in items],
        total=len(items),
    )


@router.get("/feedback/{feedback_id}", response_model=FeedbackItem)
async def get_feedback(
    feedback_id: int,
    user: User = Depends(get_current_user),
) -> FeedbackItem:
    """获取单条反馈详情"""
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    feedback = storage.sqlite.get_feedback_by_id(feedback_id, user.id)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")

    return FeedbackItem(**feedback)
