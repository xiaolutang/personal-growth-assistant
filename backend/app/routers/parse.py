"""解析 API 路由"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.agent_service import AgentService, sse_event
from app.routers.deps import get_current_user, namespaced_thread_id
from app.models.user import User

logger = logging.getLogger(__name__)

# greeting 特殊消息常量
GREETING_MESSAGE = "__greeting__"

router = APIRouter(tags=["parse"])


# 全局 Agent 实例（由 main.py 注入）
_agent_service: Optional[AgentService] = None


def set_agent_service(agent_service: AgentService) -> None:
    """设置 AgentService 实例（由 main.py 在 Agent 初始化完成后调用）"""
    global _agent_service
    _agent_service = agent_service


# === 响应模型 ===

class PageContext(BaseModel):
    """页面级上下文，标识用户当前所在的页面"""
    page_type: str = Field(
        ...,
        description="页面类型: home/explore/entry/review/graph",
    )
    entry_id: Optional[str] = Field(default=None, description="当前查看的条目 ID（entry 页面时使用）")
    extra: Optional[dict] = Field(default=None, description="附加上下文信息")


class ChatRequest(BaseModel):
    """统一聊天请求"""
    model_config = {"populate_by_name": True, "extra": "ignore"}

    text: str = Field(..., min_length=1, description="用户输入文本")
    session_id: str = Field(default="default", description="会话 ID")
    page_context: Optional[PageContext] = Field(default=None, description="页面级上下文")


# SSE 响应头配置
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# === 路由 ===

@router.post("/chat")
async def chat(request: ChatRequest, user: User = Depends(get_current_user)):
    """
    统一聊天接口（ReAct Agent 路径）

    SSE 事件：
    - event: thinking   - Agent 思考内容
    - event: tool_call  - Agent 调用工具
    - event: tool_result - 工具执行结果
    - event: content    - 流式内容
    - event: created    - 创建成功
    - event: updated    - 更新成功
    - event: done       - 完成
    - event: error      - 错误
    """
    if not _agent_service or _agent_service.agent is None:
        raise HTTPException(status_code=503, detail="Agent 服务未初始化")

    thread_id = namespaced_thread_id(user.id, request.session_id)

    # __greeting__ 特殊消息：查询用户会话数，设置 is_new_user，
    # 跳过 touch_session 和 HumanMessage 持久化
    is_greeting = request.text == GREETING_MESSAGE

    if is_greeting:
        return StreamingResponse(
            _greeting_generate(user.id, thread_id, request.page_context),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    async def agent_generate():
        async for event in _agent_service.chat(
            text=request.text,
            thread_id=thread_id,
            user_id=user.id,
            page_context=request.page_context,
        ):
            yield event

    return StreamingResponse(
        agent_generate(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


async def _greeting_generate(user_id: str, thread_id: str, page_context: Optional[PageContext] = None):
    """处理 __greeting__ 消息：查询会话数，判断 is_new_user，直接调用 Agent 生成回复。

    关键行为：
    - 通过 AgentService.is_new_user() 判断是否新用户
    - 跳过 touch_session（不创建会话记录）
    - 使用临时 thread_id，完成后清理 checkpoint，避免孤儿状态
    - 通过 AgentService.chat(is_new_user=...) 透传 is_new_user
    - 透传 page_context，与正常聊天路径保持一致
    """
    # 查询用户是否为新用户
    is_new_user = False
    if _agent_service:
        try:
            is_new_user = _agent_service.is_new_user(user_id)
        except Exception:
            logger.debug("查询会话数失败，降级为非新用户", exc_info=True)
            is_new_user = False

    # 使用临时 thread_id，避免 __greeting__ 消息存入用户真实对话历史
    greeting_thread_id = f"__greeting__:{thread_id}"

    try:
        async for event in _agent_service.chat(
            text=GREETING_MESSAGE,
            thread_id=greeting_thread_id,
            user_id=user_id,
            page_context=page_context,
            is_new_user=is_new_user,
            skip_touch_session=True,
        ):
            yield event
    except Exception as e:
        logger.error("__greeting__ 处理异常", exc_info=True)
        yield sse_event("error", {"message": "Agent 服务暂时不可用"})
        yield sse_event("done", {})
    finally:
        # 清理 greeting checkpoint，避免孤儿线程
        if _agent_service and _agent_service.agent is not None:
            try:
                await _agent_service.agent.clear_thread(greeting_thread_id)
            except Exception:
                logger.debug("清理 greeting checkpoint 失败", exc_info=True)
