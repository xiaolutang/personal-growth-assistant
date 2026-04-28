"""解析 API 路由"""
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.agent_service import AgentService
from app.routers.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["parse"])

# session_id 合法字符约束：仅允许字母数字和连字符（UUID 格式），防止冒号分隔符冲突
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9-]+$")


def _namespaced_thread_id(user_id: str, session_id: str) -> str:
    """将 session_id 命名空间化为 '{user_id}:{session_id}'，实现 LangGraph checkpoint 天然隔离"""
    if not _SESSION_ID_RE.match(session_id):
        raise HTTPException(status_code=400, detail="session_id 仅允许字母数字和连字符")
    return f"{user_id}:{session_id}"


# 全局 Agent 实例（由 main.py 注入）
_agent_service: Optional[AgentService] = None


def set_agent_service(agent_service: AgentService) -> None:
    """设置 AgentService 实例（由 main.py 在 Agent 初始化完成后调用）"""
    global _agent_service
    _agent_service = agent_service


# === 响应模型 ===

class ConfirmAction(BaseModel):
    """确认操作"""
    action: str = Field(..., description="操作类型: update/delete")
    item_id: str = Field(..., description="用户选择的条目 ID")


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
    model_config = {"populate_by_name": True}

    text: str = Field(..., min_length=1, description="用户输入文本")
    session_id: str = Field(default="default", description="会话 ID")
    skip_intent: bool = Field(default=False, description="跳过意图检测（前端已确认为 create）")
    confirm: Optional[ConfirmAction] = Field(default=None, description="确认操作（多选场景）")
    page_context: Optional[PageContext] = Field(default=None, description="页面级上下文")
    force_intent: Optional[str] = Field(default=None, description="测试用：强制指定意图（跳过意图检测）")


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

    thread_id = _namespaced_thread_id(user.id, request.session_id)

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
