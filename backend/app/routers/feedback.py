"""用户反馈 API 路由"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Literal
from typing_extensions import Annotated

import httpx
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

# 远程状态 → 本地状态映射
_REMOTE_STATUS_MAP: dict[str, str] = {
    "pending": "reported",
    "in_progress": "in_progress",
    "resolved": "resolved",
}


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
    updated_at: str | None = None


class FeedbackListResponse(BaseModel):
    """反馈列表响应"""

    items: list[FeedbackItem]
    total: int


class FeedbackSyncResponse(BaseModel):
    """反馈同步响应"""

    synced_count: int
    updated_count: int
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


@router.post("/feedback/sync", response_model=FeedbackSyncResponse)
async def sync_feedbacks(
    user: User = Depends(get_current_user),
) -> FeedbackSyncResponse:
    """同步反馈状态：从 log-service 拉取远程 issue 状态并更新本地"""
    storage = get_storage()
    if not storage or not storage.sqlite:
        raise HTTPException(status_code=503, detail="存储服务未初始化")

    # 获取有远程 issue_id 的反馈
    feedbacks = storage.sqlite.list_feedbacks_with_issue_id(user.id)
    if not feedbacks:
        # 无需同步，返回完整列表
        all_items = storage.sqlite.list_feedbacks_by_user(user.id)
        return FeedbackSyncResponse(
            synced_count=0,
            updated_count=0,
            items=[FeedbackItem(**item) for item in all_items],
            total=len(all_items),
        )

    settings = get_settings()
    synced_count = 0
    updated_count = 0

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        for fb in feedbacks:
            remote_id = fb["log_service_issue_id"]
            try:
                resp = await http_client.get(
                    f"{settings.LOG_SERVICE_URL}/api/issues/{remote_id}"
                )
                if resp.status_code != 200:
                    # 404/超时/其他错误：该条 status 和 updated_at 均不变
                    continue

                remote_data = resp.json()
                remote_status = remote_data.get("status", "")
                local_status = _REMOTE_STATUS_MAP.get(remote_status)

                if local_status is None:
                    # 未知 status：保持原状态不更新
                    continue

                synced_count += 1

                if fb["status"] != local_status:
                    # 状态实际变更 → 更新 status + updated_at
                    updated_at = datetime.now(timezone.utc).isoformat()
                    storage.sqlite.sync_feedback_status(fb["id"], local_status, updated_at)
                    updated_count += 1
                elif fb.get("updated_at") is None:
                    # 首次同步（updated_at 为 null）→ 写入 updated_at
                    updated_at = datetime.now(timezone.utc).isoformat()
                    storage.sqlite.sync_feedback_status(fb["id"], local_status, updated_at)
                # else: 状态未变更且非首次 → 不更新
            except (httpx.TimeoutException, httpx.HTTPError):
                # 单条超时/网络错误：跳过，其他继续
                continue
            except Exception:
                logger.warning("同步反馈 %d 远程 issue %d 异常", fb["id"], remote_id, exc_info=True)
                continue

    # 返回同步后的完整列表
    all_items = storage.sqlite.list_feedbacks_by_user(user.id)
    return FeedbackSyncResponse(
        synced_count=synced_count,
        updated_count=updated_count,
        items=[FeedbackItem(**item) for item in all_items],
        total=len(all_items),
    )
