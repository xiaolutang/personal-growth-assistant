"""解析 API 路由"""
import logging
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.graphs.task_parser_graph import TaskParserGraph
from app.services.chat_service import ChatService
from app.services.session_meta_store import SessionMetaStore, SessionMeta
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


# 全局 Graph 实例（由 main.py 注入）
_graph: Optional[TaskParserGraph] = None
_chat_service: Optional[ChatService] = None
_session_meta_store: Optional[SessionMetaStore] = None


def set_graph(graph: TaskParserGraph):
    """设置 TaskParserGraph 实例"""
    global _graph, _chat_service, _session_meta_store
    _graph = graph
    _chat_service = ChatService(graph=graph)
    # 初始化会话元数据存储
    settings = get_settings()
    _session_meta_store = SessionMetaStore(settings.sqlite_checkpoints_path.replace('.db', '_meta.db'))


# === 响应模型 ===

class ParseRequest(BaseModel):
    """解析请求"""
    text: str = Field(..., min_length=1, description="自然语言文本")
    session_id: str = Field(default="default", description="会话 ID（对应 LangGraph thread_id）")


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


class SessionResponse(BaseModel):
    """会话操作响应"""
    status: str
    message: str = ""


# === 会话管理响应模型 ===

class SessionInfo(BaseModel):
    """会话信息"""
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionUpdate(BaseModel):
    """会话更新请求"""
    title: str = Field(..., min_length=1, max_length=100, description="会话标题")


class MessageInfo(BaseModel):
    """消息信息"""
    id: str
    role: str
    content: str
    timestamp: str


# SSE 响应头配置
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# === 路由 ===

@router.post("/parse")
async def parse(request: ParseRequest, user: User = Depends(get_current_user)):
    """
    解析自然语言文本，流式返回结果（SSE）

    使用 LangGraph Checkpointer 管理对话历史，
    通过 thread_id（{user_id}:{session_id}）实现多轮对话隔离。
    """
    if not _graph:
        raise HTTPException(status_code=503, detail="服务未初始化")

    thread_id = _namespaced_thread_id(user.id, request.session_id)

    return StreamingResponse(
        _graph.stream_parse(request.text, thread_id),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.delete("/session/{session_id}", response_model=SessionResponse)
async def clear_session(session_id: str, user: User = Depends(get_current_user)):
    """
    清空指定会话的对话历史

    Args:
        session_id: 会话 ID（对应 LangGraph thread_id）
    """
    if not _graph:
        raise HTTPException(status_code=503, detail="服务未初始化")
    thread_id = _namespaced_thread_id(user.id, session_id)
    await _graph.clear_thread(thread_id)
    return {"status": "ok", "message": f"会话 {session_id} 已清空"}


@router.post("/chat")
async def chat(request: ChatRequest, user: User = Depends(get_current_user)):
    """
    统一聊天接口（一站式处理意图识别和操作执行）

    一次请求完成：
    1. 意图检测（可跳过）
    2. 根据意图执行操作（create/update/delete/read 等）
    3. 多选场景返回 confirm 事件，前端确认后携带 confirm 参数再次调用

    SSE 事件：
    - event: intent  - 意图检测结果
    - event: content - 流式内容（create 意图）
    - event: created - 创建成功
    - event: updated - 更新成功
    - event: deleted - 删除成功
    - event: confirm - 需要用户确认（多选场景）
    - event: results - 搜索结果（read 意图）
    - event: done    - 完成
    - event: error   - 错误
    """
    if not _chat_service:
        raise HTTPException(status_code=503, detail="服务未初始化")

    thread_id = _namespaced_thread_id(user.id, request.session_id)

    async def generate():
        # Step 1: 意图识别
        from app.services.chat_service import sse_event
        from app.core.config import get_settings
        page_ctx = request.page_context
        if request.force_intent:
            # 测试用：仅 DEBUG 模式允许，生产环境拒绝
            if not get_settings().DEBUG:
                yield sse_event("error", {"message": "force_intent 仅在 DEBUG 模式下可用"})
                return
            intent_result = {
                "intent": request.force_intent,
                "confidence": 1.0,
                "query": request.text,
                "entities": {},
            }
        elif request.skip_intent:
            intent_result = {
                "intent": "create",
                "confidence": 1.0,
                "query": request.text,
                "entities": {},
            }
        else:
            intent_result = await _chat_service.detect_intent(
                request.text, page_context=page_ctx
            )

        intent = intent_result["intent"]
        query = intent_result["query"]
        entities = intent_result["entities"]

        # 发送意图事件
        yield sse_event("intent", intent_result)

        # Step 2: 执行操作
        confirm_dict = request.confirm.model_dump() if request.confirm else None
        async for event in _chat_service.process_intent(
            intent=intent,
            query=query,
            entities=entities,
            text=request.text,
            session_id=thread_id,
            user_id=user.id,
            confirm=confirm_dict,
            page_context=page_ctx,
        ):
            yield event

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


# === 会话管理 API ===

@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(user: User = Depends(get_current_user)):
    """
    获取当前用户的所有会话列表

    返回会话 ID、标题、创建时间、更新时间
    """
    if not _session_meta_store:
        raise HTTPException(status_code=503, detail="服务未初始化")

    sessions = _session_meta_store.get_all_sessions(user_id=user.id)
    return [
        SessionInfo(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageInfo])
async def get_session_messages(session_id: str, user: User = Depends(get_current_user)):
    """
    获取指定会话的消息历史

    从 LangGraph checkpointer 读取消息
    """
    from langchain_core.messages import HumanMessage as LCHumanMessage, AIMessage as LCAIMessage

    if not _graph:
        raise HTTPException(status_code=503, detail="服务未初始化")

    thread_id = _namespaced_thread_id(user.id, session_id)
    messages = []
    try:
        # 从 checkpointer 获取会话状态
        config = {"configurable": {"thread_id": thread_id}}
        state = await _graph.checkpointer.aget_tuple(config)

        if state and state.checkpoint:
            # 解析消息
            channel_values = state.checkpoint.get("channel_values", {})
            msgs = channel_values.get("messages", [])

            for i, msg in enumerate(msgs):
                # 处理 LangChain 消息对象
                if isinstance(msg, LCHumanMessage):
                    role = "user"
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                elif isinstance(msg, LCAIMessage):
                    role = "assistant"
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                else:
                    # 兼容字典格式
                    role = "user" if isinstance(msg, dict) and msg.get("type") == "human" else "assistant"
                    content = msg.get("content", "") if isinstance(msg, dict) else str(msg)

                messages.append(MessageInfo(
                    id=f"{session_id}-{i}",
                    role=role,
                    content=content,
                    timestamp=state.checkpoint.get("ts", datetime.now().isoformat()),
                ))
    except Exception as e:
        # 会话不存在或读取失败时返回空列表
        logger.debug(f"Failed to get session messages for {thread_id}: {e}")

    return messages


@router.patch("/sessions/{session_id}", response_model=SessionInfo)
async def update_session(session_id: str, data: SessionUpdate, user: User = Depends(get_current_user)):
    """
    更新会话元数据（如标题）
    """
    if not _session_meta_store:
        raise HTTPException(status_code=503, detail="服务未初始化")

    # 检查会话是否存在，不存在则创建
    if not _session_meta_store.session_exists(session_id, user_id=user.id):
        _session_meta_store.create_session(session_id, data.title, user_id=user.id)
    else:
        _session_meta_store.update_title(session_id, data.title, user_id=user.id)

    updated = _session_meta_store.get_session(session_id, user_id=user.id)
    if not updated:
        raise HTTPException(status_code=500, detail="更新失败")

    return SessionInfo(
        id=updated.id,
        title=updated.title,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/sessions/{session_id}", response_model=SessionResponse)
async def delete_session(session_id: str, user: User = Depends(get_current_user)):
    """
    删除会话（包括元数据和对话历史）
    """
    if not _graph or not _session_meta_store:
        raise HTTPException(status_code=503, detail="服务未初始化")

    thread_id = _namespaced_thread_id(user.id, session_id)

    # 删除对话历史
    await _graph.clear_thread(thread_id)

    # 删除元数据
    _session_meta_store.delete_session(session_id, user_id=user.id)

    return {"status": "ok", "message": f"会话 {session_id} 已删除"}
