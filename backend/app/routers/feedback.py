"""用户反馈 API 路由"""
import asyncio
from typing import Any, Literal
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints

from app.core.config import get_settings
from app.routers.deps import get_current_user
from app.models.user import User
from log_service_sdk import report_issue

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
    issue: dict[str, Any]


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(payload: FeedbackRequest, user: User = Depends(get_current_user)) -> FeedbackResponse:
    """代理用户反馈到 log-service issue API"""
    settings = get_settings()

    try:
        issue = await asyncio.to_thread(
            report_issue,
            settings.LOG_SERVICE_URL,
            payload.title,
            "personal-growth-assistant",
            description=payload.description,
            severity=payload.severity,
            component="frontend",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="反馈服务暂时不可用，请稍后重试") from exc

    return FeedbackResponse(success=True, issue=issue)
