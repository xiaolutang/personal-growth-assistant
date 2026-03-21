"""聊天服务 - 处理意图识别和操作执行"""
import json
from typing import AsyncGenerator, Optional

from app.api.schemas import EntryCreate, EntryUpdate
from app.graphs.task_parser_graph import TaskParserGraph
from app.routers import intent as intent_module
from app.routers.deps import get_entry_service
from app.services.entry_service import EntryService
from app.services.intent_service import IntentService


def sse_event(event: str, data: dict) -> str:
    """格式化 SSE 事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ChatService:
    """
    聊天服务 - 统一处理意图识别和操作执行

    职责：
    - 意图检测（create/update/delete/read/review/knowledge/help）
    - 根据意图执行对应操作
    - 流式返回 SSE 事件
    """

    def __init__(
        self,
        graph: TaskParserGraph,
        intent_service: Optional[IntentService] = None,
        entry_service: Optional[EntryService] = None,
    ):
        self.graph = graph
        self._intent_service = intent_service
        self._entry_service = entry_service

    @property
    def intent_service(self) -> IntentService:
        if self._intent_service is None:
            self._intent_service = intent_module.get_intent_service()
        return self._intent_service

    @property
    def entry_service(self) -> EntryService:
        if self._entry_service is None:
            self._entry_service = get_entry_service()
        return self._entry_service

    async def detect_intent(self, text: str) -> dict:
        """检测用户意图"""
        resp = await self.intent_service.detect(text)
        return {
            "intent": resp.intent,
            "confidence": resp.confidence,
            "query": resp.query or text,
            "entities": resp.entities,
        }

    async def process_intent(
        self,
        intent: str,
        query: str,
        entities: dict,
        text: str,
        session_id: str,
        confirm: Optional[dict] = None,
    ) -> AsyncGenerator[str, None]:
        """
        根据意图执行操作，返回 SSE 事件流

        Args:
            intent: 意图类型
            query: 查询内容
            entities: 提取的实体
            text: 原始用户输入
            session_id: 会话 ID
            confirm: 确认操作（多选场景）
        """
        if intent == "create":
            async for event in self._handle_create(text, session_id):
                yield event
        elif intent == "update":
            async for event in self._handle_update(query, entities, confirm):
                yield event
        elif intent == "delete":
            async for event in self._handle_delete(query, confirm):
                yield event
        elif intent == "read":
            async for event in self._handle_read(query):
                yield event
        elif intent == "review":
            yield sse_event("done", {"intent": "review", "need_client_action": True, "entities": entities})
        elif intent == "knowledge":
            yield sse_event("done", {"intent": "knowledge", "need_client_action": True, "query": query})
        elif intent == "help":
            yield sse_event("done", {"intent": "help", "need_client_action": True})
        else:
            yield sse_event("done", {"intent": intent, "need_client_action": True})

    async def _handle_create(
        self, text: str, session_id: str
    ) -> AsyncGenerator[str, None]:
        """处理创建意图"""
        full_json = ""
        async for chunk in self.graph.stream_parse(text, session_id):
            if chunk.startswith("data: "):
                yield f"event: content\n{chunk}\n"
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
                    entry = await self.entry_service.create_entry(
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
                    first_title = tasks[0].get("title", "") if tasks else ""
                    if len(created_ids) == 1 and first_title:
                        yield sse_event("done", {"message": f"已记录「{first_title[:20]}」"})
                    else:
                        yield sse_event("done", {"message": f"已创建 {len(created_ids)} 个条目"})

            except json.JSONDecodeError as e:
                yield sse_event("error", {"message": f"解析失败: {str(e)}"})

    async def _handle_update(
        self, query: str, entities: dict, confirm: Optional[dict]
    ) -> AsyncGenerator[str, None]:
        """处理更新意图"""
        if confirm:
            entry_id = confirm.get("item_id")
            field = entities.get("field", "status")
            value = entities.get("value")

            if field and value:
                update_data = {field: value}
                success, msg = await self.entry_service.update_entry(entry_id, EntryUpdate(**update_data))
                if success:
                    yield sse_event("updated", {"id": entry_id, "changes": update_data})
                    yield sse_event("done", {"message": "已更新"})
                else:
                    yield sse_event("error", {"message": msg})
            return

        # 搜索条目
        results = await self.entry_service.search_entries(query, limit=10)
        items = [{"id": r.id, "title": r.title} for r in results.entries]

        if len(items) == 0:
            yield sse_event("done", {"message": f"未找到「{query}」相关内容"})
        elif len(items) == 1:
            entry_id = items[0]["id"]
            field = entities.get("field", "status")
            value = entities.get("value")

            if field and value:
                update_data = {field: value}
                success, msg = await self.entry_service.update_entry(entry_id, EntryUpdate(**update_data))
                if success:
                    item_title = items[0]["title"]
                    yield sse_event("updated", {"id": entry_id, "title": item_title, "changes": update_data})
                    yield sse_event("done", {"message": f"已更新「{item_title}」"})
                else:
                    yield sse_event("error", {"message": msg})
        else:
            yield sse_event("confirm", {"action": "update", "items": items, "entities": entities})

    async def _handle_delete(
        self, query: str, confirm: Optional[dict]
    ) -> AsyncGenerator[str, None]:
        """处理删除意图"""
        if confirm:
            entry_id = confirm.get("item_id")
            success = await self.entry_service.delete_entry(entry_id)
            if success:
                yield sse_event("deleted", {"id": entry_id})
                yield sse_event("done", {"message": "已删除"})
            else:
                yield sse_event("error", {"message": "删除失败"})
            return

        # 搜索条目
        results = await self.entry_service.search_entries(query, limit=10)
        items = [{"id": r.id, "title": r.title} for r in results.entries]

        if len(items) == 0:
            yield sse_event("done", {"message": f"未找到「{query}」相关内容"})
        else:
            yield sse_event("confirm", {"action": "delete", "items": items})

    async def _handle_read(self, query: str) -> AsyncGenerator[str, None]:
        """处理读取意图"""
        results = await self.entry_service.search_entries(query, limit=10)
        items = [
            {"id": r.id, "title": r.title, "status": r.status, "category": r.category}
            for r in results.entries
        ]

        yield sse_event("results", {"items": items, "count": len(items)})
        yield sse_event("done", {"message": f"找到 {len(items)} 个结果"})
