"""聊天服务 - 处理意图识别和操作执行"""
import json
import logging
from datetime import date
from typing import AsyncGenerator, Optional, TYPE_CHECKING

from app.api.schemas import EntryCreate, EntryUpdate
from app.graphs.task_parser_graph import TaskParserGraph
from app.routers import intent as intent_module
from app.routers.deps import get_entry_service
from app.services.entry_service import EntryService
from app.services.intent_service import IntentService

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.routers.parse import PageContext


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

    async def detect_intent(
        self,
        text: str,
        page_context: Optional["PageContext"] = None,
        user_id: str = "_default",
    ) -> dict:
        """检测用户意图"""
        context_hint = await self._build_page_context_hint(page_context, user_id)
        resp = await self.intent_service.detect(text, extra_system_hint=context_hint)
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
        user_id: str,
        confirm: Optional[dict] = None,
        page_context: Optional["PageContext"] = None,
    ) -> AsyncGenerator[str, None]:
        """
        根据意图执行操作，返回 SSE 事件流

        Args:
            intent: 意图类型
            query: 查询内容
            entities: 提取的实体
            text: 原始用户输入
            session_id: 会话 ID
            user_id: 认证用户 ID
            confirm: 确认操作（多选场景）
        """
        if intent == "create":
            async for event in self._handle_create(text, session_id, user_id, page_context=page_context):
                yield event
        elif intent == "update":
            async for event in self._handle_update(query, entities, confirm, user_id, page_context=page_context):
                yield event
        elif intent == "delete":
            async for event in self._handle_delete(query, confirm, user_id):
                yield event
        elif intent == "read":
            async for event in self._handle_read(query, user_id):
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
        self, text: str, session_id: str, user_id: str, page_context: Optional["PageContext"] = None
    ) -> AsyncGenerator[str, None]:
        """处理创建意图"""
        full_json = ""
        # 构建页面上下文提示，通过参数注入到 graph 系统提示词
        context_hint = await self._build_page_context_hint(page_context, user_id)
        async for chunk in self.graph.stream_parse(text, session_id, page_context_hint=context_hint):
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
                        ),
                        user_id=user_id,
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
        self, query: str, entities: dict, confirm: Optional[dict], user_id: str,
        page_context: Optional["PageContext"] = None,
    ) -> AsyncGenerator[str, None]:
        """处理更新意图

        当 page_context.page_type == "entry" 且 entry_id 存在时，
        搜索优先，未命中则 fallback 到 entry_id 作为目标。
        """
        if confirm:
            entry_id = confirm.get("item_id")
            field = entities.get("field", "status")
            value = entities.get("value")

            if field and value:
                update_data = {field: value}
                success, msg = await self.entry_service.update_entry(entry_id, EntryUpdate(**update_data), user_id=user_id)
                if success:
                    yield sse_event("updated", {"id": entry_id, "changes": update_data})
                    yield sse_event("done", {"message": "已更新"})
                else:
                    yield sse_event("error", {"message": msg})
            return

        # 搜索条目
        results = await self.entry_service.search_entries(query, limit=10, user_id=user_id)
        items = [{"id": r.id, "title": r.title} for r in results.entries]

        # 判断是否在条目页且有 entry_id，用于 fallback
        ctx_entry_id = (
            page_context.entry_id
            if page_context and page_context.page_type == "entry" and page_context.entry_id
            else None
        )

        if len(items) == 0:
            # 搜索无结果：如果有上下文 entry_id，直接更新该条目
            if ctx_entry_id:
                field = entities.get("field", "status")
                value = entities.get("value")
                if field and value:
                    update_data = {field: value}
                    success, msg = await self.entry_service.update_entry(
                        ctx_entry_id, EntryUpdate(**update_data), user_id=user_id
                    )
                    if success:
                        yield sse_event("updated", {"id": ctx_entry_id, "changes": update_data})
                        yield sse_event("done", {"message": "已更新"})
                    else:
                        yield sse_event("error", {"message": msg})
                else:
                    yield sse_event("done", {"message": f"未找到「{query}」相关内容"})
            else:
                yield sse_event("done", {"message": f"未找到「{query}」相关内容"})
        elif len(items) == 1:
            entry_id = items[0]["id"]
            field = entities.get("field", "status")
            value = entities.get("value")

            if field and value:
                update_data = {field: value}
                success, msg = await self.entry_service.update_entry(entry_id, EntryUpdate(**update_data), user_id=user_id)
                if success:
                    item_title = items[0]["title"]
                    yield sse_event("updated", {"id": entry_id, "title": item_title, "changes": update_data})
                    yield sse_event("done", {"message": f"已更新「{item_title}」"})
                else:
                    yield sse_event("error", {"message": msg})
        else:
            # 搜索有多个结果：检查是否有精确匹配（query 与标题完全一致）
            exact_match = None
            for item in items:
                if item["title"].strip() == query.strip():
                    exact_match = item
                    break

            if exact_match:
                # 精确匹配优先
                entry_id = exact_match["id"]
                field = entities.get("field", "status")
                value = entities.get("value")
                if field and value:
                    update_data = {field: value}
                    success, msg = await self.entry_service.update_entry(
                        entry_id, EntryUpdate(**update_data), user_id=user_id
                    )
                    if success:
                        yield sse_event("updated", {"id": entry_id, "title": exact_match["title"], "changes": update_data})
                        yield sse_event("done", {"message": f"已更新「{exact_match['title']}」"})
                    else:
                        yield sse_event("error", {"message": msg})
                else:
                    yield sse_event("confirm", {"action": "update", "items": items, "entities": entities})
            elif ctx_entry_id:
                # 无精确匹配，fallback 到当前页面条目
                field = entities.get("field", "status")
                value = entities.get("value")
                if field and value:
                    update_data = {field: value}
                    success, msg = await self.entry_service.update_entry(
                        ctx_entry_id, EntryUpdate(**update_data), user_id=user_id
                    )
                    if success:
                        yield sse_event("updated", {"id": ctx_entry_id, "changes": update_data})
                        yield sse_event("done", {"message": "已更新"})
                    else:
                        yield sse_event("error", {"message": msg})
                else:
                    yield sse_event("confirm", {"action": "update", "items": items, "entities": entities})
            else:
                yield sse_event("confirm", {"action": "update", "items": items, "entities": entities})

    async def _handle_delete(
        self, query: str, confirm: Optional[dict], user_id: str
    ) -> AsyncGenerator[str, None]:
        """处理删除意图"""
        if confirm:
            entry_id = confirm.get("item_id")
            success, _ = await self.entry_service.delete_entry(entry_id, user_id=user_id)
            if success:
                yield sse_event("deleted", {"id": entry_id})
                yield sse_event("done", {"message": "已删除"})
            else:
                yield sse_event("error", {"message": "删除失败"})
            return

        # 搜索条目
        results = await self.entry_service.search_entries(query, limit=10, user_id=user_id)
        items = [{"id": r.id, "title": r.title} for r in results.entries]

        if len(items) == 0:
            yield sse_event("done", {"message": f"未找到「{query}」相关内容"})
        else:
            yield sse_event("confirm", {"action": "delete", "items": items})

    async def _handle_read(self, query: str, user_id: str) -> AsyncGenerator[str, None]:
        """处理读取意图"""
        results = await self.entry_service.search_entries(query, limit=10, user_id=user_id)
        items = [
            {"id": r.id, "title": r.title, "status": r.status, "category": r.category}
            for r in results.entries
        ]

        yield sse_event("results", {"items": items, "count": len(items)})
        yield sse_event("done", {"message": f"找到 {len(items)} 个结果"})

    async def _build_page_context_hint(
        self, page_context: Optional["PageContext"], user_id: str = "_default"
    ) -> str:
        """根据页面上下文构建追加到 LLM prompt 的指令文本

        当 page_type == "entry" 且 entry_id 存在时，注入条目详情数据。
        当 page_type == "home" 时，注入今日统计。
        所有数据获取失败时优雅降级，只保留基本页面标识。
        """
        if page_context is None:
            return ""

        PAGE_TYPE_LABELS: dict[str, str] = {
            "home": "首页",
            "explore": "探索页",
            "entry": "条目详情页",
            "review": "回顾页",
            "graph": "知识图谱页",
        }

        page_label = PAGE_TYPE_LABELS.get(page_context.page_type, page_context.page_type)
        parts = [f"[页面上下文] 用户当前在「{page_label}」"]

        # Entry page：注入条目详情数据
        if page_context.page_type == "entry" and page_context.entry_id:
            try:
                entry = await self.entry_service.get_entry(page_context.entry_id, user_id)
                if entry:
                    parts.append(f"条目标题: {entry.title}")
                    parts.append(f"分类: {entry.category}")
                    if entry.tags:
                        parts.append(f"标签: {', '.join(entry.tags)}")
                    if entry.content:
                        summary = entry.content[:300]
                        parts.append(f"内容摘要: {summary}")
                else:
                    # get_entry 返回 None（不存在或属于其他用户）
                    parts.append(f"正在查看条目 ID: {page_context.entry_id}")
            except Exception:
                logger.debug("获取条目详情失败，降级为基础信息", exc_info=True)
                parts.append(f"正在查看条目 ID: {page_context.entry_id}")

        # Home page：注入今日统计
        if page_context.page_type == "home":
            try:
                today = date.today().isoformat()
                result = await self.entry_service.list_entries(
                    start_date=today, end_date=today, limit=1, user_id=user_id
                )
                parts.append(f"今日条目数: {result.total}")
                # 获取进行中的条目数
                doing_result = await self.entry_service.list_entries(
                    status="doing", limit=1, user_id=user_id
                )
                parts.append(f"进行中条目数: {doing_result.total}")
            except Exception:
                logger.debug("获取今日统计失败，跳过", exc_info=True)

        # extra 字段透传
        if page_context.extra:
            for key, value in page_context.extra.items():
                parts.append(f"{key}: {value}")

        return "\n".join(parts)
