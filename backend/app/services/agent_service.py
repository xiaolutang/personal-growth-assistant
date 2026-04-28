"""AgentService — 管理 Agent 会话、注入页面上下文、编排 SSE 事件

职责：
- 持有 ReActAgentGraph 实例
- 持有 ToolDependencies 并注入 services
- 将 Agent 的 stream 输出转换为 SSE 事件流
- 管理 thread_id（{user_id}:{session_id} 格式）
- 注入页面上下文到 Agent 的 system prompt

分层：Router → AgentService → Agent → Tools → Services → Infrastructure
"""

import json
import logging
import time
from datetime import date
from typing import Any, AsyncGenerator, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.react_agent import ReActAgentGraph
from app.agent.tools import AGENT_TOOLS, AGENT_TOOL_NAMES, ToolDependencies
from app.agent.monitoring import AgentMetrics
from app.services.session_meta_store import SessionMetaStore

logger = logging.getLogger(__name__)


# ── 页面类型 → Agent page 参数映射 ──

_PAGE_TYPE_TO_AGENT_PAGE: dict[str, str] = {
    "home": "home",
    "explore": "explore",
    "review": "review",
    "entry": "entry_detail",
    "entry_detail": "entry_detail",
    "tasks": "home",
    "notes": "home",
    "inbox": "home",
    "projects": "home",
    "graph": "explore",
}


def sse_event(event: str, data: dict) -> str:
    """格式化 SSE 事件

    格式: "event: {event}\\ndata: {json}\\n\\n"
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class AgentService:
    """Agent 服务 — 管理 ReActAgentGraph 会话和 SSE 事件编排

    使用方式：
        service = AgentService()
        service.set_react_agent(agent)
        service.set_dependencies(deps)

        async for sse in service.chat(text, thread_id, user_id, page_context):
            print(sse)
    """

    def __init__(self):
        self._agent: Optional[ReActAgentGraph] = None
        self._dependencies: Optional[ToolDependencies] = None
        self._session_meta_store: Optional[SessionMetaStore] = None
        self.metrics = AgentMetrics()

    def set_react_agent(self, agent: ReActAgentGraph) -> None:
        """注入 ReActAgentGraph 实例"""
        self._agent = agent

    def set_dependencies(self, deps: ToolDependencies) -> None:
        """注入 ToolDependencies 实例"""
        self._dependencies = deps

    def set_session_meta_store(self, store: SessionMetaStore) -> None:
        """注入 SessionMetaStore 实例"""
        self._session_meta_store = store

    @property
    def agent(self) -> Optional[ReActAgentGraph]:
        return self._agent

    @property
    def dependencies(self) -> Optional[ToolDependencies]:
        return self._dependencies

    async def chat(
        self,
        text: str,
        thread_id: str,
        user_id: str,
        page_context: Optional[Any] = None,
        is_new_user: bool = False,
    ) -> AsyncGenerator[str, None]:
        """调用 ReActAgentGraph 并将 stream 输出转换为 SSE 事件流。

        SSE 事件编排：
        - Agent LLM thinking → event: thinking
        - Agent tool_calls → event: tool_call（逐个）
        - Agent tool 结果 → event: tool_result（逐个）
        - Agent 文本输出 → event: content
        - 条目创建/更新 → event: created / event: updated（从 tool_result 提取）
        - Agent 循环结束 → event: done
        - 异常 → event: error

        Args:
            text: 用户输入文本
            thread_id: 会话线程 ID（{user_id}:{session_id} 格式）
            user_id: 用户 ID
            page_context: 页面上下文（PageContext 模型实例或 None）
            is_new_user: 是否新用户

        Yields:
            SSE 格式的事件字符串
        """
        if self._agent is None:
            yield sse_event("error", {"message": "Agent 服务未初始化"})
            return

        if self._dependencies is None:
            yield sse_event("error", {"message": "Agent 依赖未初始化"})
            return

        # 构建页面上下文
        page, page_context_str = await self._build_agent_context(page_context, user_id)

        # Touch session 元数据，确保活跃对话出现在会话列表中
        if self._session_meta_store is not None:
            try:
                # thread_id 格式: {user_id}:{session_id}
                session_id = thread_id.split(":", 1)[-1] if ":" in thread_id else thread_id
                if not self._session_meta_store.session_exists(session_id, user_id=user_id):
                    # 截取用户输入前 20 字符作为默认标题
                    title = text[:20] + ("..." if len(text) > 20 else "")
                    self._session_meta_store.create_session(session_id, title, user_id=user_id)
                else:
                    self._session_meta_store.touch_session(session_id, user_id=user_id)
            except Exception:
                logger.debug("Touch session 元数据失败", exc_info=True)

        try:
            # 跟踪已发送的 message 数量，用于检测新增消息
            prev_message_count = 0
            has_content = False
            has_error = False
            # 跟踪工具调用时间，用于计算延迟
            tool_call_timestamps: dict[str, float] = {}

            async for state in self._agent.stream(
                message=text,
                thread_id=thread_id,
                user_id=user_id,
                dependencies=self._dependencies,
                page=page,
                page_context=page_context_str,
                is_new_user=is_new_user,
            ):
                # state 是 ReActAgentState（MessagesState 的子类）
                messages = state.get("messages", [])
                new_messages = messages[prev_message_count:]
                prev_message_count = len(messages)

                for msg in new_messages:
                    async for event in self._process_message(msg, tool_call_timestamps):
                        # 检测是否有实际内容事件
                        event_type = self._extract_event_type(event)
                        if event_type == "content":
                            has_content = True
                        elif event_type == "error":
                            has_error = True
                        elif event_type == "created" or event_type == "updated":
                            has_content = True
                        yield event

            # 发送 done 事件
            if not has_error:
                yield sse_event("done", {})
            else:
                # 已经发了 error 事件，但仍然发 done 以关闭流
                yield sse_event("done", {})

        except Exception as e:
            logger.error("AgentService.chat 异常: %s", e, exc_info=True)
            yield sse_event("error", {"message": f"处理失败: {str(e)}"})
            yield sse_event("done", {})

    async def _process_message(self, msg: Any, tool_call_timestamps: dict[str, float]) -> AsyncGenerator[str, None]:
        """将单条 LangChain message 转换为 SSE 事件。

        处理规则：
        - AIMessage with tool_calls → thinking (如有 content) + tool_call 事件
        - AIMessage without tool_calls → content 事件（如有 content）
        - ToolMessage → tool_result 事件 + 可能的 created/updated 事件
        - HumanMessage → 忽略（我们自己发送的）
        """
        if isinstance(msg, AIMessage):
            # 如果有 tool_calls，中间过程用 thinking 事件
            if msg.tool_calls:
                if msg.content:
                    yield sse_event("thinking", {"content": msg.content})
                # 逐个发送 tool_call 事件
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "")
                    tc_id = tc.get("id", "")
                    # 记录 tool_call 开始时间
                    tool_call_timestamps[tc_id] = time.monotonic()
                    if tool_name == "ask_user":
                        self.metrics.record_ask_user(was_necessary=True)
                    yield sse_event("tool_call", {
                        "id": tc.get("id", ""),
                        "tool": tc.get("name", ""),
                        "args": tc.get("args", {}),
                    })
            else:
                # 无 tool_calls = 最终回复，用 content 事件
                if msg.content:
                    yield sse_event("content", {"content": msg.content})

        elif isinstance(msg, ToolMessage):
            # 解析 tool 结果
            tool_name = ""
            success = True
            result_data = msg.content

            # 计算工具执行延迟
            latency_ms = 0.0
            call_start = tool_call_timestamps.pop(msg.tool_call_id, None)
            if call_start is not None:
                latency_ms = (time.monotonic() - call_start) * 1000

            # 尝试解析 JSON 结果
            try:
                if isinstance(msg.content, str):
                    parsed = json.loads(msg.content)
                    # ToolResult 结构: {success, data, error}
                    success = parsed.get("success", True)
                    result_data = parsed.get("data", parsed)
                    if not success:
                        result_data = {"error": parsed.get("error", "未知错误")}

                    # 检测 created/updated 事件
                    # create_entry 返回 {id, title, category, status}
                    if success and isinstance(result_data, dict):
                        if "id" in result_data and "category" in result_data:
                            yield sse_event("created", {
                                "id": result_data["id"],
                                "type": result_data.get("category", ""),
                                "title": result_data.get("title", ""),
                            })
                        elif "entry_id" in result_data:
                            yield sse_event("updated", {
                                "id": result_data["entry_id"],
                                "changes": result_data.get("message", ""),
                            })
            except (json.JSONDecodeError, TypeError):
                # 非 JSON 格式的 tool 结果
                pass

            yield sse_event("tool_result", {
                "tool_call_id": msg.tool_call_id,
                "result": result_data if isinstance(result_data, (dict, list)) else {"raw": str(result_data)},
                "success": success,
            })

            # 记录工具调用指标（使用真实延迟和成功状态）
            self.metrics.record_tool_call(
                tool_name=tool_name or msg.name or "unknown",
                correct=success,
                latency_ms=latency_ms,
            )

        elif isinstance(msg, HumanMessage):
            # 忽略用户消息（是我们自己注入的）
            pass

    @staticmethod
    def _extract_event_type(event_str: str) -> str:
        """从 SSE 事件字符串中提取事件类型"""
        if event_str.startswith("event: "):
            return event_str.split("\n")[0][7:].strip()
        return ""

    async def _build_agent_context(
        self,
        page_context: Optional[Any],
        user_id: str,
    ) -> tuple[str, str]:
        """根据页面上下文构建 Agent 的 page 和 page_context 参数。

        Returns:
            (page, page_context_str) 元组
        """
        if page_context is None:
            return "", ""

        page_type = getattr(page_context, "page_type", "")
        page = _PAGE_TYPE_TO_AGENT_PAGE.get(page_type, page_type)

        parts: list[str] = []

        # Entry 页面：注入条目详情
        entry_id = getattr(page_context, "entry_id", None)
        if page_type == "entry" and entry_id and self._dependencies:
            entry_service = self._dependencies.entry_service
            if entry_service:
                try:
                    entry = await entry_service.get_entry(entry_id, user_id)
                    if entry:
                        parts.append(f"条目标题: {entry.title}")
                        parts.append(f"分类: {entry.category}")
                        if entry.tags:
                            parts.append(f"标签: {', '.join(entry.tags)}")
                        if entry.content:
                            parts.append(f"内容摘要: {entry.content[:300]}")
                    else:
                        parts.append(f"正在查看条目 ID: {entry_id}")
                except Exception:
                    logger.debug("获取条目详情失败，降级", exc_info=True)
                    parts.append(f"正在查看条目 ID: {entry_id}")

        # Home 页面：注入今日统计
        if page_type == "home" and self._dependencies:
            entry_service = self._dependencies.entry_service
            if entry_service:
                try:
                    today = date.today().isoformat()
                    result = await entry_service.list_entries(
                        start_date=today, end_date=today, limit=1, user_id=user_id
                    )
                    parts.append(f"今日条目数: {result.total}")
                    doing_result = await entry_service.list_entries(
                        status="doing", limit=1, user_id=user_id
                    )
                    parts.append(f"进行中条目数: {doing_result.total}")
                except Exception:
                    logger.debug("获取今日统计失败", exc_info=True)

        # extra 字段透传
        extra = getattr(page_context, "extra", None)
        if extra:
            for key, value in extra.items():
                parts.append(f"{key}: {value}")

        return page, "\n".join(parts)
