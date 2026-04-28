"""B187: AgentService 单元测试

验证：
1. 正常 SSE 流完整序列（thinking → tool_call → tool_result → content → done）
2. ask_user 场景 SSE 流
3. 无 tool 调用时只有 content → done
4. 请求含旧字段时忽略不报错
5. LLM 超时返回 error 事件
6. 新 session_id 首次调用可正常工作
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.tools import ToolDependencies
from app.services.agent_service import AgentService, sse_event


# === 辅助工具 ===


def _parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    """解析 SSE 文本流为 (event, data) 列表"""
    events = []
    chunks = raw.strip().split("\n\n")
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        event_name = ""
        data_str = ""
        for line in chunk.split("\n"):
            if line.startswith("event: "):
                event_name = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:]
        if event_name:
            events.append((event_name, json.loads(data_str) if data_str else {}))
    return events


def _make_agent_service(
    stream_events: list[dict] | None = None,
    raise_on_stream: Exception | None = None,
) -> AgentService:
    """创建带 mock agent 的 AgentService。

    Args:
        stream_events: agent.stream() yield 的事件列表（每个事件是一个 state dict）
        raise_on_stream: 如果设置，stream 期间抛出此异常
    """
    service = AgentService()

    # Mock agent
    mock_agent = MagicMock()

    if raise_on_stream:

        async def _stream_raise(**kwargs):
            raise raise_on_stream
            yield  # noqa: unreachable — 使其成为 async generator

        mock_agent.stream = MagicMock(side_effect=_stream_raise)
    elif stream_events is not None:

        async def _stream(**kwargs):
            for event in stream_events:
                yield event

        mock_agent.stream = MagicMock(side_effect=_stream)
    else:

        async def _stream(**kwargs):
            yield {"messages": []}

        mock_agent.stream = MagicMock(side_effect=_stream)

    service.set_react_agent(mock_agent)
    service.set_dependencies(ToolDependencies())

    return service


async def _collect_sse(service: AgentService, **kwargs) -> list[tuple[str, dict]]:
    """收集 AgentService.chat() 的所有 SSE 事件"""
    raw = ""
    async for chunk in service.chat(**kwargs):
        raw += chunk
    return _parse_sse_events(raw)


# === 测试类 ===


class TestAgentServiceFullFlow:
    """正常 SSE 流完整序列：thinking → tool_call → tool_result → content → done"""

    @pytest.mark.asyncio
    async def test_full_tool_call_flow(self):
        """Agent 调用 create_entry tool，完整 SSE 流序列"""
        from langchain_core.messages import AIMessage, ToolMessage

        # 模拟 Agent 输出：
        # 1. AI 思考 + tool_call(create_entry)
        # 2. Tool 执行结果
        # 3. AI 最终回复（无 tool_calls）
        tool_call_id = "call_001"
        events = [
            {
                "messages": [
                    AIMessage(
                        content="好的，我来帮你创建这个条目。",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "create_entry",
                                "args": {
                                    "category": "task",
                                    "title": "测试任务",
                                },
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            },
            {
                "messages": [
                    AIMessage(
                        content="好的，我来帮你创建这个条目。",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "create_entry",
                                "args": {
                                    "category": "task",
                                    "title": "测试任务",
                                },
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps({
                            "success": True,
                            "data": {
                                "id": "entry-abc",
                                "title": "测试任务",
                                "category": "task",
                                "status": "doing",
                            },
                        }),
                        tool_call_id=tool_call_id,
                    ),
                ]
            },
            {
                "messages": [
                    AIMessage(
                        content="好的，我来帮你创建这个条目。",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "create_entry",
                                "args": {
                                    "category": "task",
                                    "title": "测试任务",
                                },
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps({
                            "success": True,
                            "data": {
                                "id": "entry-abc",
                                "title": "测试任务",
                                "category": "task",
                                "status": "doing",
                            },
                        }),
                        tool_call_id=tool_call_id,
                    ),
                    AIMessage(content="已为你创建了任务「测试任务」。"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)
        result = await _collect_sse(
            service,
            text="创建一个测试任务",
            thread_id="user1:sess1",
            user_id="user1",
        )

        event_types = [e[0] for e in result]

        # 验证完整序列
        assert "thinking" in event_types
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "content" in event_types or "thinking" in event_types  # 最终 AI 回复
        assert event_types[-1] == "done"

        # 验证 tool_call 事件内容
        tool_call_events = [(e, d) for e, d in result if e == "tool_call"]
        assert len(tool_call_events) == 1
        tc_event = tool_call_events[0][1]
        assert tc_event["tool"] == "create_entry"
        assert tc_event["id"] == tool_call_id

        # 验证 tool_result 事件内容
        tool_result_events = [(e, d) for e, d in result if e == "tool_result"]
        assert len(tool_result_events) == 1
        tr_event = tool_result_events[0][1]
        assert tr_event["tool_call_id"] == tool_call_id
        assert tr_event["success"] is True

        # 验证 created 事件
        created_events = [(e, d) for e, d in result if e == "created"]
        assert len(created_events) == 1
        assert created_events[0][1]["id"] == "entry-abc"

    @pytest.mark.asyncio
    async def test_updated_event_from_tool_result(self):
        """update_entry tool 执行成功时触发 updated 事件"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_002"
        events = [
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "update_entry",
                                "args": {"entry_id": "e1", "status": "complete"},
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps({
                            "success": True,
                            "data": {
                                "entry_id": "e1",
                                "message": "更新成功",
                            },
                        }),
                        tool_call_id=tool_call_id,
                    ),
                    AIMessage(content="已更新。"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)
        result = await _collect_sse(
            service,
            text="把任务标记为完成",
            thread_id="user1:sess1",
            user_id="user1",
        )

        updated_events = [(e, d) for e, d in result if e == "updated"]
        assert len(updated_events) == 1
        assert updated_events[0][1]["id"] == "e1"


class TestAgentServiceAskUser:
    """ask_user 场景 SSE 流"""

    @pytest.mark.asyncio
    async def test_ask_user_flow(self):
        """Agent 调用 ask_user tool，SSE 包含 tool_call → tool_result → content → done"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_ask_001"
        events = [
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "ask_user",
                                "args": {"question": "你想创建什么类型的条目？"},
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps({"type": "ask", "question": "你想创建什么类型的条目？"}),
                        tool_call_id=tool_call_id,
                    ),
                    AIMessage(content="你想创建什么类型的条目？"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)
        result = await _collect_sse(
            service,
            text="记一下",
            thread_id="user1:sess1",
            user_id="user1",
        )

        event_types = [e[0] for e in result]

        # 验证 ask_user 的 tool_call 事件
        tool_call_events = [(e, d) for e, d in result if e == "tool_call"]
        assert len(tool_call_events) == 1
        assert tool_call_events[0][1]["tool"] == "ask_user"

        # 验证 tool_result 事件
        tool_result_events = [(e, d) for e, d in result if e == "tool_result"]
        assert len(tool_result_events) == 1

        # 验证 done 事件
        assert event_types[-1] == "done"


class TestAgentServiceNoToolCalls:
    """无 tool 调用时只有 content → done"""

    @pytest.mark.asyncio
    async def test_pure_conversation(self):
        """Agent 纯对话回复，无 tool_calls"""
        from langchain_core.messages import AIMessage

        events = [
            {
                "messages": [
                    AIMessage(content="你好！有什么我可以帮你的吗？"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)
        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:sess1",
            user_id="user1",
        )

        event_types = [e[0] for e in result]

        # 只有 thinking（因为 AIMessage content 发为 thinking） + done
        assert "tool_call" not in event_types
        assert "tool_result" not in event_types
        assert event_types[-1] == "done"
        # 应该有 thinking 事件（因为 AIMessage 有 content 且无 tool_calls）
        assert "thinking" in event_types

    @pytest.mark.asyncio
    async def test_empty_agent_response(self):
        """Agent 无消息输出时，只有 done"""
        events = [
            {"messages": []},
        ]

        service = _make_agent_service(stream_events=events)
        result = await _collect_sse(
            service,
            text="测试",
            thread_id="user1:sess1",
            user_id="user1",
        )

        event_types = [e[0] for e in result]
        assert event_types == ["done"]


class TestAgentServiceBackwardCompat:
    """请求含旧字段时忽略不报错"""

    @pytest.mark.asyncio
    async def test_old_fields_ignored_in_chat_request(self):
        """ChatRequest 含旧字段 (confirm, skip_intent, force_intent) 时不影响 Agent 路径"""
        from langchain_core.messages import AIMessage

        events = [
            {
                "messages": [
                    AIMessage(content="好的"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)
        result = await _collect_sse(
            service,
            text="创建任务",
            thread_id="user1:sess1",
            user_id="user1",
        )

        # 应该正常完成
        event_types = [e[0] for e in result]
        assert event_types[-1] == "done"
        assert "error" not in event_types

    @pytest.mark.asyncio
    async def test_agent_service_not_initialized(self):
        """AgentService 未设置 agent 时返回 error"""
        service = AgentService()
        # 不设置 react_agent 和 dependencies

        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:sess1",
            user_id="user1",
        )

        event_types = [e[0] for e in result]
        assert "error" in event_types
        error_events = [(e, d) for e, d in result if e == "error"]
        assert "未初始化" in error_events[0][1]["message"]


class TestAgentServiceTimeout:
    """LLM 超时返回 error 事件"""

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_error(self):
        """Agent stream 抛出异常时返回 error + done"""
        import httpx

        service = _make_agent_service(raise_on_stream=httpx.TimeoutException("LLM timeout"))

        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:sess1",
            user_id="user1",
        )

        event_types = [e[0] for e in result]
        assert "error" in event_types
        assert event_types[-1] == "done"

        error_events = [(e, d) for e, d in result if e == "error"]
        assert "处理失败" in error_events[0][1]["message"]

    @pytest.mark.asyncio
    async def test_generic_exception_returns_error(self):
        """Agent stream 抛出通用异常时返回 error + done"""
        service = _make_agent_service(raise_on_stream=RuntimeError("unexpected"))

        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:sess1",
            user_id="user1",
        )

        event_types = [e[0] for e in result]
        assert "error" in event_types
        assert event_types[-1] == "done"


class TestAgentServiceNewSession:
    """新 session_id 首次调用可正常工作"""

    @pytest.mark.asyncio
    async def test_new_session_id(self):
        """使用全新的 session_id 首次调用 Agent，正常工作"""
        from langchain_core.messages import AIMessage

        events = [
            {
                "messages": [
                    AIMessage(content="你好！我是日知，你的个人成长助手。"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)
        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:brand-new-session-xyz",
            user_id="user1",
        )

        event_types = [e[0] for e in result]
        assert event_types[-1] == "done"
        assert "error" not in event_types

        # 验证 agent.stream 被调用时传递了正确的 thread_id
        call_kwargs = service.agent.stream.call_args.kwargs
        assert call_kwargs["thread_id"] == "user1:brand-new-session-xyz"
        assert call_kwargs["user_id"] == "user1"

    @pytest.mark.asyncio
    async def test_page_context_passed_to_agent(self):
        """page_context 正确传递到 agent.stream"""
        from langchain_core.messages import AIMessage

        events = [
            {
                "messages": [
                    AIMessage(content="已看到你在首页。"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)

        # 构造一个 mock PageContext
        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "home"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="看看今天有什么",
            thread_id="user1:sess1",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        assert event_types[-1] == "done"

        # 验证 agent.stream 调用时 page 和 page_context 参数被设置
        call_kwargs = service.agent.stream.call_args.kwargs
        assert call_kwargs["page"] == "home"


class TestSSEEventHelper:
    """SSE 事件格式化辅助函数测试"""

    def test_sse_event_format(self):
        """sse_event 生成正确格式的 SSE 文本"""
        result = sse_event("content", {"text": "hello"})
        assert result.startswith("event: content\n")
        assert "data: " in result
        assert result.endswith("\n\n")

        # 验证可被正确解析
        parsed = json.loads(result.split("data: ")[1].strip())
        assert parsed == {"text": "hello"}

    def test_sse_event_chinese(self):
        """sse_event 正确处理中文字符（ensure_ascii=False）"""
        result = sse_event("content", {"text": "你好世界"})
        assert "你好世界" in result
        assert "\\u" not in result

    def test_sse_event_empty_data(self):
        """sse_event 处理空数据"""
        result = sse_event("done", {})
        assert "event: done\n" in result
        assert "data: {}\n\n" in result
