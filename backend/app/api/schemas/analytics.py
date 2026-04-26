"""Analytics 埋点 Schema (DTO)"""

from typing import Literal, Optional

from pydantic import BaseModel


class AnalyticsEventCreate(BaseModel):
    """埋点事件创建请求"""
    event_type: Literal[
        "entry_created",
        "entry_viewed",
        "chat_message_sent",
        "search_performed",
        "page_viewed",
        "onboarding_completed",
    ]
    metadata: Optional[dict] = None


class AnalyticsEventResponse(BaseModel):
    """埋点事件响应"""
    ok: bool = True
