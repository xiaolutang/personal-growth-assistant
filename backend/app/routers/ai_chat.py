"""AI 对话 API 路由"""
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.routers.deps import get_current_user
from app.models.user import User
from app.services.ai_chat_service import AIChatService, ChatMessage

router = APIRouter(prefix="/ai", tags=["ai"])

# Service singleton
_ai_chat_service: AIChatService = None


def get_ai_chat_service() -> AIChatService:
    global _ai_chat_service
    if _ai_chat_service is None:
        from app.routers.deps import storage
        _ai_chat_service = AIChatService()
        if storage and hasattr(storage, "llm_caller") and storage.llm_caller:
            _ai_chat_service.set_llm_caller(storage.llm_caller)
    return _ai_chat_service


@router.post("/chat")
async def ai_chat(
    request: ChatMessage,
    user: User = Depends(get_current_user),
):
    """AI 对话端点 — SSE 流式返回"""
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="消息不能为空")

    service = get_ai_chat_service()

    async def generate():
        async for token in service.chat_stream(
            message=request.message,
            context=request.context,
            user_id=user.id,
        ):
            # SSE format: data: {json}\n\n
            data = json.dumps({"token": token}, ensure_ascii=False)
            yield f"data: {data}\n\n"
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
