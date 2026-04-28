"""会话管理 API 路由"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, Field

from app.services.session_meta_store import SessionMetaStore
from app.routers.deps import get_current_user, namespaced_thread_id
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sessions"])


# 全局实例（由 main.py 注入）
_checkpointer: Optional[AsyncSqliteSaver] = None
_session_meta_store: Optional[SessionMetaStore] = None


def set_checkpointer(checkpointer: AsyncSqliteSaver) -> None:
    """设置 AsyncSqliteSaver 实例"""
    global _checkpointer
    _checkpointer = checkpointer


def set_session_meta_store(store: SessionMetaStore) -> None:
    """设置 SessionMetaStore 实例"""
    global _session_meta_store
    _session_meta_store = store


# === 响应模型 ===

class SessionResponse(BaseModel):
    """会话操作响应"""
    status: str
    message: str = ""


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


# === 路由 ===

@router.delete("/session/{session_id}", response_model=SessionResponse)
async def clear_session(session_id: str, user: User = Depends(get_current_user)):
    """
    清空指定会话的对话历史

    Args:
        session_id: 会话 ID（对应 LangGraph thread_id）
    """
    if not _checkpointer:
        raise HTTPException(status_code=503, detail="服务未初始化")
    thread_id = namespaced_thread_id(user.id, session_id)
    await _checkpointer.adelete_thread(thread_id)
    return {"status": "ok", "message": f"会话 {session_id} 已清空"}


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

    if not _checkpointer:
        raise HTTPException(status_code=503, detail="服务未初始化")

    thread_id = namespaced_thread_id(user.id, session_id)
    messages = []
    try:
        # 从 checkpointer 获取会话状态
        config = {"configurable": {"thread_id": thread_id}}
        state = await _checkpointer.aget_tuple(config)

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
    if not _checkpointer or not _session_meta_store:
        raise HTTPException(status_code=503, detail="服务未初始化")

    thread_id = namespaced_thread_id(user.id, session_id)

    # 删除对话历史
    await _checkpointer.adelete_thread(thread_id)

    # 删除元数据
    _session_meta_store.delete_session(session_id, user_id=user.id)

    return {"status": "ok", "message": f"会话 {session_id} 已删除"}
