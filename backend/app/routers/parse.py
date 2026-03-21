"""解析 API 路由"""
from typing import Optional, List
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.graphs.task_parser_graph import TaskParserGraph
from app.routers import intent as intent_module
from app.routers.deps import get_entry_service
from app.api.schemas import EntryCreate, EntryUpdate

router = APIRouter(tags=["parse"])


def sse_event(event: str, data: dict) -> str:
    """格式化 SSE 事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

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


class ConfirmAction(BaseModel):
    """确认操作"""
    action: str = Field(..., description="操作类型: update/delete")
    item_id: str = Field(..., description="用户选择的条目 ID")


class ChatRequest(BaseModel):
    """统一聊天请求"""
    text: str = Field(..., min_length=1, description="用户输入文本")
    session_id: str = Field(default="default", description="会话 ID")
    skip_intent: bool = Field(default=False, description="跳过意图检测（前端已确认为 create）")
    confirm: Optional[ConfirmAction] = Field(default=None, description="确认操作（多选场景）")


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


async def _stream_chat_with_intent(text: str, session_id: str, skip_intent: bool = False, confirm: Optional[ConfirmAction] = None):
    """流式响应生成器：一站式处理意图识别和操作执行"""

    # === Step 1: 意图识别 ===
    if skip_intent:
        intent_result = {"intent": "create", "confidence": 1.0, "query": text, "entities": {}}
    else:
        intent_resp = await intent_module.detect_intent_service(text)
        intent_result = {
            "intent": intent_resp.intent,
            "confidence": intent_resp.confidence,
            "query": intent_resp.query or text,
            "entities": intent_resp.entities,
        }

    intent = intent_result["intent"]
    query = intent_result["query"]
    entities = intent_result["entities"]

    # 发送意图事件
    yield sse_event("intent", intent_result)

    # === Step 2: 根据意图执行操作 ===
    entry_service = get_entry_service()

    if intent == "create":
        # 流式解析并直接创建
        if not _graph:
            yield sse_event("error", {"message": "服务未初始化"})
            return

        full_json = ""
        async for chunk in _graph.stream_parse(text, session_id):
            if chunk.startswith("data: "):
                yield f"event: content\n{chunk}\n"
                # 提取 JSON 内容
                try:
                    data_str = chunk[6:].strip()
                    if data_str and data_str != "[DONE]":
                        data = json.loads(data_str)
                        if data.get("content"):
                            full_json += data["content"]
                except json.JSONDecodeError:
                    pass
            else:
                yield chunk
                if chunk.startswith("data: ") and not chunk.startswith("data: [DONE]"):
                    try:
                        data = json.loads(chunk[6:].strip())
                        if data.get("content"):
                            full_json += data["content"]
                    except json.JSONDecodeError:
                        pass

        # 解析并创建条目
        if full_json:
            try:
                parsed = json.loads(full_json)
                tasks = parsed.get("tasks", [])
                created_ids = []

                for task in tasks:
                    entry = await entry_service.create_entry(
                        EntryCreate(
                            type=task.get("category", "task"),
                            title=task.get("title", ""),
                            content=task.get("content"),
                            status=task.get("status"),
                            tags=task.get("tags"),
                            planned_date=task.get("planned_date"),
                        )
                    )
                    created_ids.append(entry.id)

                if created_ids:
                    yield sse_event("created", {"ids": created_ids, "count": len(created_ids)})
                    # 获取第一个任务的标题用于更友好的提示
                    first_title = tasks[0].get("title", "") if tasks else ""
                    if len(created_ids) == 1 and first_title:
                        yield sse_event("done", {"message": f"已记录「{first_title[:20]}」"})
                    else:
                        yield sse_event("done", {"message": f"已创建 {len(created_ids)} 个条目"})

            except json.JSONDecodeError as e:
                yield sse_event("error", {"message": f"解析失败: {str(e)}"})

    elif intent == "update":
        # 处理确认操作
        if confirm:
            entry_id = confirm.item_id
            field = entities.get("field", "status")
            value = entities.get("value")

            if field and value:
                update_data = {field: value}
                success, msg = await entry_service.update_entry(entry_id, EntryUpdate(**update_data))
                if success:
                    yield sse_event("updated", {"id": entry_id, "changes": update_data})
                    yield sse_event("done", {"message": "已更新"})
                else:
                    yield sse_event("error", {"message": msg})
            return

        # 搜索条目
        results = await entry_service.search_entries(query, limit=10)
        items = [{"id": r.id, "title": r.title} for r in results.entries]

        if len(items) == 0:
            yield sse_event("done", {"message": f"未找到「{query}」相关内容"})
        elif len(items) == 1:
            # 单个结果，直接更新
            entry_id = items[0]["id"]
            field = entities.get("field", "status")
            value = entities.get("value")

            if field and value:
                update_data = {field: value}
                success, msg = await entry_service.update_entry(entry_id, EntryUpdate(**update_data))
                if success:
                    item_title = items[0]["title"]
                    yield sse_event("updated", {"id": entry_id, "title": item_title, "changes": update_data})
                    yield sse_event("done", {"message": f"已更新「{item_title}」"})
                else:
                    yield sse_event("error", {"message": msg})
        else:
            # 多个结果，返回确认列表
            yield sse_event("confirm", {"action": "update", "items": items, "entities": entities})

    elif intent == "delete":
        # 处理确认操作
        if confirm:
            entry_id = confirm.item_id
            success = await entry_service.delete_entry(entry_id)
            if success:
                yield sse_event("deleted", {"id": entry_id})
                yield sse_event("done", {"message": "已删除"})
            else:
                yield sse_event("error", {"message": "删除失败"})
            return

        # 搜索条目
        results = await entry_service.search_entries(query, limit=10)
        items = [{"id": r.id, "title": r.title} for r in results.entries]

        if len(items) == 0:
            yield sse_event("done", {"message": f"未找到「{query}」相关内容"})
        else:
            # 删除必须确认，返回确认列表
            yield sse_event("confirm", {"action": "delete", "items": items})

    elif intent == "read":
        # 搜索条目
        results = await entry_service.search_entries(query, limit=10)
        items = [{"id": r.id, "title": r.title, "status": r.status, "category": r.category} for r in results.entries]

        yield sse_event("results", {"items": items, "count": len(items)})
        yield sse_event("done", {"message": f"找到 {len(items)} 个结果"})

    elif intent == "review":
        # 返回需要前端处理的标记
        yield sse_event("done", {"intent": "review", "need_client_action": True, "entities": entities})

    elif intent == "knowledge":
        # 返回需要前端处理的标记
        yield sse_event("done", {"intent": "knowledge", "need_client_action": True, "query": query})

    elif intent == "help":
        # 返回需要前端处理的标记
        yield sse_event("done", {"intent": "help", "need_client_action": True})

    else:
        # 未知意图，fallback 到 create
        yield sse_event("done", {"intent": intent, "need_client_action": True})


@router.post("/chat")
async def chat(request: ChatRequest):
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
    if not _graph:
        raise HTTPException(status_code=503, detail="服务未初始化")

    return StreamingResponse(
        _stream_chat_with_intent(
            request.text,
            request.session_id,
            request.skip_intent,
            request.confirm
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
