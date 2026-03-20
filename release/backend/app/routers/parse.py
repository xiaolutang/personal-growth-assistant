"""解析 API 路由"""
from typing import Optional
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.graphs.task_parser_graph import TaskParserGraph
from app.routers import intent as intent_module

router = APIRouter(tags=["parse"])

# 全局 Graph 实例（由 main.py 注入）
_graph: Optional[TaskParserGraph] = None


def set_graph(graph: TaskParserGraph):
    """设置 TaskParserGraph 实例"""
    global _graph
    _graph = graph


# === 响应模型 ===

class ParseRequest(BaseModel):
    """解析请求"""
    text: str = Field(..., min_length=1, description="自然语言文本")
    session_id: str = Field(default="default", description="会话 ID（对应 LangGraph thread_id）")


class ChatRequest(BaseModel):
    """统一聊天请求"""
    text: str = Field(..., min_length=1, description="用户输入文本")
    session_id: str = Field(default="default", description="会话 ID")
    skip_intent: bool = Field(default=False, description="跳过意图检测（前端已确认为 create）")


class SessionResponse(BaseModel):
    """会话操作响应"""
    status: str
    message: str = ""


# SSE 响应头配置
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# === 路由 ===

@router.post("/parse")
async def parse(request: ParseRequest):
    """
    解析自然语言文本，流式返回结果（SSE）

    使用 LangGraph Checkpointer 管理对话历史，
    通过 thread_id（session_id）实现多轮对话。
    """
    if not _graph:
        raise HTTPException(status_code=503, detail="服务未初始化")

    return StreamingResponse(
        _graph.stream_parse(request.text, request.session_id),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.delete("/session/{session_id}", response_model=SessionResponse)
async def clear_session(session_id: str):
    """
    清空指定会话的对话历史

    Args:
        session_id: 会话 ID（对应 LangGraph thread_id）
    """
    if not _graph:
        raise HTTPException(status_code=503, detail="服务未初始化")
    _graph.clear_thread(session_id)
    return {"status": "ok", "message": f"会话 {session_id} 已清空"}


async def _stream_chat_with_intent(text: str, session_id: str, skip_intent: bool = False):
    """流式响应生成器：先发送意图，再流式发送内容"""
    if skip_intent:
        # 前端已确认为 create，跳过意图检测
        intent_result = {"intent": "create", "confidence": 1.0, "query": text, "entities": {}}
    else:
        # 复用 intent 模块的检测服务
        intent_resp = await intent_module.detect_intent_service(text)
        intent_result = {
            "intent": intent_resp.intent,
            "confidence": intent_resp.confidence,
            "query": intent_resp.query or text,
            "entities": intent_resp.entities,
        }

    intent = intent_result["intent"]

    # 发送意图事件
    yield f"event: intent\ndata: {json.dumps(intent_result, ensure_ascii=False)}\n\n"

    if intent == "create":
        # 流式解析
        if not _graph:
            yield f"event: error\ndata: {json.dumps({'message': '服务未初始化'}, ensure_ascii=False)}\n\n"
            return
        async for chunk in _graph.stream_parse(text, session_id):
            # 包装为统一的 event: content 格式
            if chunk.startswith("data: "):
                yield f"event: content\n{chunk}\n"
            else:
                yield chunk
    else:
        # 其他意图，返回意图信息让前端处理
        yield f"event: done\ndata: {json.dumps({'intent': intent, 'need_client_action': True}, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    统一聊天接口（合并意图检测和处理）

    一次请求完成：
    1. 意图检测（可跳过）
    2. 根据意图分发处理

    返回 SSE 流式响应：
    - event: intent  - 意图检测结果
    - event: content - 流式内容（create 意图）
    - event: done    - 完成，包含 need_client_action 表示是否需要前端额外处理
    """
    if not _graph:
        raise HTTPException(status_code=503, detail="服务未初始化")

    return StreamingResponse(
        _stream_chat_with_intent(request.text, request.session_id, request.skip_intent),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
