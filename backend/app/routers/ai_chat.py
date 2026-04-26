"""AI 对话 API 路由"""
import json
import re
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.routers.deps import get_current_user
from app.models.user import User
from app.services.ai_chat_service import AIChatService, ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# thread_id 合法字符：仅允许 page:前缀 + 字母数字连字符下划线
_THREAD_ID_RE = re.compile(r"^[a-zA-Z0-9_:\-]+$")

# Service singleton
_ai_chat_service: AIChatService = None


def get_ai_chat_service() -> AIChatService:
    global _ai_chat_service
    if _ai_chat_service is None:
        from app.routers.deps import storage
        _ai_chat_service = AIChatService()
        if storage and hasattr(storage, "llm_caller") and storage.llm_caller:
            _ai_chat_service.set_llm_caller(storage.llm_caller)
        # 注入 LangGraph checkpointer（从 parse 模块的 graph 实例获取）
        try:
            from app.routers.parse import _graph
            if _graph and _graph.checkpointer:
                _ai_chat_service.set_checkpointer(_graph.checkpointer)
        except Exception:
            pass
    return _ai_chat_service


def _page_thread_id(page_name: str, user_id: str) -> str:
    """生成页面级 thread_id，格式 page:{page_name}:{user_id}"""
    thread_id = f"page:{page_name}:{user_id}"
    return thread_id


class ChatHistoryMessage(BaseModel):
    """历史消息响应"""
    role: str
    content: str


@router.post("/chat")
async def ai_chat(
    request: ChatMessage,
    user: User = Depends(get_current_user),
):
    """AI 对话端点 — SSE 流式返回

    支持持久化：
    - 当 context 中包含 page 字段时，使用 thread_id=page:{page}:{user_id} 格式
    - 通过 LangGraph checkpointer 自动保存对话历史
    """
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="消息不能为空")

    service = get_ai_chat_service()

    # 构建持久化 thread_id
    thread_id = None
    page = request.context.get("page", "") if request.context else ""
    if page:
        thread_id = _page_thread_id(page, user.id)

    async def generate():
        full_response = ""
        async for token in service.chat_stream(
            message=request.message,
            context=request.context,
            user_id=user.id,
            thread_id=thread_id,
        ):
            data = json.dumps({"token": token}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            full_response += token
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/history", response_model=list[ChatHistoryMessage])
async def get_chat_history(
    page: str = Query(..., description="页面名称，用于构建 thread_id"),
    limit: int = Query(default=20, ge=1, le=100, description="最多返回的消息条数"),
    user: User = Depends(get_current_user),
):
    """获取页面级对话历史

    使用 thread_id=page:{page}:{user_id} 从 LangGraph checkpointer 加载历史消息。
    页面刷新后调用此接口恢复对话。
    """
    service = get_ai_chat_service()
    thread_id = _page_thread_id(page, user.id)

    history = await service.load_history(thread_id, limit=limit)
    return [ChatHistoryMessage(role=m.role, content=m.content) for m in history]
