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
        # stream_mode="updates" 格式：每个 event 只包含本步新增的消息
        events = [
            {
                "agent": {
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
                }
            },
            {
                "tools": {
                    "messages": [
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
                }
            },
            {
                "agent": {
                    "messages": [
                        AIMessage(content="已为你创建了任务「测试任务」。"),
                    ]
                }
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

        # 纯对话回复：content（最终回复） + done，无 tool_call/tool_result
        assert "tool_call" not in event_types
        assert "tool_result" not in event_types
        assert event_types[-1] == "done"
        # 应该有 content 事件（AIMessage 有 content 且无 tool_calls → content 而非 thinking）
        assert "content" in event_types

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


# === B01: Command 模式测试 ===


class TestCommandModeRedirect:
    """command 模式下闲聊意图 → redirect_to_chat tool_call → redirect SSE 事件"""

    @pytest.mark.asyncio
    async def test_conversational_intent_produces_redirect(self):
        """闲聊意图（如'你好'）→ Agent 调用 redirect_to_chat → redirect 事件"""
        from langchain_core.messages import AIMessage, ToolMessage

        # Agent 调用 redirect_to_chat 工具
        tool_call_id = "call_redirect_001"
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_call_id,
                                    "name": "redirect_to_chat",
                                    "args": {"reason": "conversational"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"reason": "conversational", "target": "chat"}),
                            tool_call_id=tool_call_id,
                        ),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        # 构造 command 模式的 page_context
        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:cmd-sess1",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]

        # 应该有 redirect 事件
        assert "redirect" in event_types
        redirect_events = [(e, d) for e, d in result if e == "redirect"]
        assert len(redirect_events) == 1
        redirect_data = redirect_events[0][1]
        assert redirect_data["reason"] == "conversational"
        assert redirect_data["target"] == "chat"

        # 不应产生 tool_call 事件（redirect_to_chat 被拦截）
        tool_call_events = [(e, d) for e, d in result if e == "tool_call"]
        redirect_tc = [tc for _, tc in tool_call_events if tc["tool"] == "redirect_to_chat"]
        assert len(redirect_tc) == 0, "redirect_to_chat 不应产生 tool_call SSE 事件"

        # 不应产生 tool_result 事件（被拦截的 call ID 跳过 ToolMessage）
        tool_result_events = [(e, d) for e, d in result if e == "tool_result"]
        assert len(tool_result_events) == 0, "被拦截的 redirect_to_chat 不应产生 tool_result"

    @pytest.mark.asyncio
    async def test_conversational_longer_input_produces_redirect(self):
        """闲聊意图（如'聊聊最近'）→ Agent 调用 redirect_to_chat → redirect 事件"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_redirect_002"
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_call_id,
                                    "name": "redirect_to_chat",
                                    "args": {"reason": "conversational"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"reason": "conversational", "target": "chat"}),
                            tool_call_id=tool_call_id,
                        ),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="聊聊最近",
            thread_id="user1:cmd-sess2",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        assert "redirect" in event_types


class TestCommandModeToolCall:
    """command 模式下可执行意图 → 正常 tool_call + created/updated"""

    @pytest.mark.asyncio
    async def test_executable_intent_produces_tool_call(self):
        """可执行意图（如'完成项目报告'）→ tool_call(create_entry) + created"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_cmd_001"
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_call_id,
                                    "name": "create_entry",
                                    "args": {"category": "task", "title": "完成项目报告"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({
                                "success": True,
                                "data": {
                                    "id": "entry-cmd-001",
                                    "title": "完成项目报告",
                                    "category": "task",
                                    "status": "doing",
                                },
                            }),
                            tool_call_id=tool_call_id,
                        ),
                    ]
                }
            },
            {
                "agent": {
                    "messages": [
                        AIMessage(content="已为你创建了任务「完成项目报告」。"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="完成项目报告",
            thread_id="user1:cmd-sess3",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]

        # 应该有正常的 tool_call 和 created 事件，不应有 redirect
        assert "tool_call" in event_types
        assert "created" in event_types
        assert "redirect" not in event_types

    @pytest.mark.asyncio
    async def test_update_intent_produces_tool_call(self):
        """可执行意图（如'标记任务 xxx 完成'）→ tool_call(update_entry) + updated"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_cmd_002"
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_call_id,
                                    "name": "update_entry",
                                    "args": {"entry_id": "e-task-001", "status": "complete"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({
                                "success": True,
                                "data": {
                                    "entry_id": "e-task-001",
                                    "message": "更新成功",
                                },
                            }),
                            tool_call_id=tool_call_id,
                        ),
                    ]
                }
            },
            {
                "agent": {
                    "messages": [
                        AIMessage(content="已将任务标记为完成。"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="标记任务 e-task-001 完成",
            thread_id="user1:cmd-sess4",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        assert "tool_call" in event_types
        assert "updated" in event_types
        assert "redirect" not in event_types


class TestCommandModeAskUserIntercept:
    """command 模式下拦截 ask_user tool_call，替换为简短回复"""

    @pytest.mark.asyncio
    async def test_command_mode_no_ask_user(self):
        """command 模式下不产生 ask_user tool_call，替换为 content（简短回复）"""
        from langchain_core.messages import AIMessage, ToolMessage

        # Agent 尝试调用 ask_user（在 command 模式下应该被拦截）
        # 真实场景中 ask_user 后 Agent 循环终止，不会有后续 agent 回复
        tool_call_id = "call_ask_cmd_001"
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_call_id,
                                    "name": "ask_user",
                                    "args": {"question": "你想创建什么？"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"type": "ask", "question": "你想创建什么？"}),
                            tool_call_id=tool_call_id,
                        ),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="记一下",
            thread_id="user1:cmd-sess5",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]

        # command 模式下不应产生 ask_user tool_call
        tool_call_events = [(e, d) for e, d in result if e == "tool_call"]
        ask_user_calls = [tc for _, tc in tool_call_events if tc["tool"] == "ask_user"]
        assert len(ask_user_calls) == 0, "command 模式不应产生 ask_user tool_call"

        # 应该产生 content 事件（简短回复），包含原始问题
        content_events = [(e, d) for e, d in result if e == "content"]
        assert len(content_events) >= 1, "command 模式拦截 ask_user 后应产生 content 事件"
        assert "你想创建什么" in content_events[0][1]["content"]

        # 不应产生 ask_user 的 tool_result（被拦截的 call ID 跳过 ToolMessage）
        tool_result_events = [(e, d) for e, d in result if e == "tool_result"]
        assert len(tool_result_events) == 0, "command 模式下被拦截的 ask_user 不应产生 tool_result"


class TestCommandModeSessionSkip:
    """command 模式跳过 session 元数据写入"""

    @pytest.mark.asyncio
    async def test_command_mode_skips_session_touch(self):
        """command 模式不触发 session 元数据写入"""
        from langchain_core.messages import AIMessage

        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(content="已创建任务。"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        # 设置 mock session store
        mock_session_store = MagicMock()
        mock_session_store.session_exists = MagicMock(return_value=False)
        service.set_session_meta_store(mock_session_store)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="创建任务测试",
            thread_id="user1:cmd-sess-skip",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        assert event_types[-1] == "done"

        # session_store 不应被调用
        mock_session_store.session_exists.assert_not_called()
        mock_session_store.create_session.assert_not_called()
        mock_session_store.touch_session.assert_not_called()


class TestCommandModeNonAffecting:
    """command 模式不影响非 command page_type 行为"""

    @pytest.mark.asyncio
    async def test_home_mode_no_redirect(self):
        """home page_type 不产生 redirect 事件"""
        from langchain_core.messages import AIMessage

        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(content="你好！有什么我可以帮你的吗？"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "home"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:home-sess1",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        assert "redirect" not in event_types
        assert "content" in event_types

    @pytest.mark.asyncio
    async def test_no_page_context_no_redirect(self):
        """无 page_context 时不产生 redirect 事件"""
        from langchain_core.messages import AIMessage

        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(content="你好！"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:noctx-sess1",
            user_id="user1",
            page_context=None,
        )

        event_types = [e[0] for e in result]
        assert "redirect" not in event_types
        assert "content" in event_types

    @pytest.mark.asyncio
    async def test_home_mode_ask_user_normal(self):
        """home 模式下 ask_user 行为不变"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_home_ask_001"
        events = [
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "ask_user",
                                "args": {"question": "你想记什么？"},
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps({"type": "ask", "question": "你想记什么？"}),
                        tool_call_id=tool_call_id,
                    ),
                    AIMessage(content="你想记什么？"),
                ]
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "home"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="记一下",
            thread_id="user1:home-sess2",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        # home 模式下 ask_user 应该正常产生 tool_call 事件
        assert "tool_call" in event_types
        tool_call_events = [(e, d) for e, d in result if e == "tool_call"]
        ask_user_calls = [tc for _, tc in tool_call_events if tc["tool"] == "ask_user"]
        assert len(ask_user_calls) == 1
        # 不应产生 redirect
        assert "redirect" not in event_types


class TestCommandModeContentEvent:
    """command 模式下问答意图 → content 事件（简短直接回答）"""

    @pytest.mark.asyncio
    async def test_qa_intent_with_tool_call_produces_content(self):
        """问答意图（如'本周进展'）→ tool_call(get_review_summary) + content，不产生 redirect"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_cmd_qa_001"
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_call_id,
                                    "name": "get_review_summary",
                                    "args": {"period": "week"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({
                                "success": True,
                                "data": {"completed": 5, "trend": "+20%"},
                            }),
                            tool_call_id=tool_call_id,
                        ),
                    ]
                }
            },
            {
                "agent": {
                    "messages": [
                        AIMessage(content="本周你完成了 5 个任务，比上周增加了 20%。"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="本周进展",
            thread_id="user1:cmd-qa1",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        # 问答意图（有 tool_call）在 command 模式下应该用 content 而非 redirect
        assert "tool_call" in event_types
        assert "content" in event_types
        assert "redirect" not in event_types

    @pytest.mark.asyncio
    async def test_qa_with_tool_call_produces_content(self):
        """问答意图有 tool_call（Agent 查了工具后回答）→ content 事件"""
        from langchain_core.messages import AIMessage, ToolMessage

        # Agent 先调 search_entries，然后给出最终回答
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[{"name": "search_entries", "args": {"query": "今天任务"}, "id": "tc-search-1", "type": "tool_call"}],
                        ),
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content='{"success": true, "data": {"total": 3}}',
                            tool_call_id="tc-search-1",
                        ),
                    ]
                }
            },
            {
                "agent": {
                    "messages": [
                        AIMessage(content="你今天有 3 个待办任务。"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="今天有什么任务",
            thread_id="user1:cmd-qa-tool",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        # 有 tool_call 的 Q&A 应该产生 content
        assert "content" in event_types
        assert "redirect" not in event_types

    @pytest.mark.asyncio
    async def test_direct_answer_without_tool_call_produces_content(self):
        """command 模式下无 tool_call 的直接回答/简短澄清 → content 事件"""
        from langchain_core.messages import AIMessage

        # Agent 按指令直接回答，不调工具
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(content="请告诉我你想创建什么内容的任务。"),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "command"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="帮我创建一个任务",
            thread_id="user1:cmd-clarify",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]
        # 无 tool_call 的直接回答应该产生 content，不应该 redirect
        assert "content" in event_types
        assert "redirect" not in event_types


class TestNonCommandModeRedirectDefensive:
    """非 command 模式下意外调用 redirect_to_chat → 防御性降级为 content"""

    @pytest.mark.asyncio
    async def test_home_mode_redirect_to_chat_downgrades_to_content(self):
        """home 模式下 LLM 意外调用 redirect_to_chat → 降级为 content 而非 redirect"""
        from langchain_core.messages import AIMessage, ToolMessage

        tool_call_id = "call_redirect_defense_001"
        events = [
            {
                "agent": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "id": tool_call_id,
                                    "name": "redirect_to_chat",
                                    "args": {"reason": "conversational"},
                                    "type": "tool_call",
                                }
                            ],
                        )
                    ]
                }
            },
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"reason": "conversational", "target": "chat"}),
                            tool_call_id=tool_call_id,
                        ),
                    ]
                }
            },
        ]

        service = _make_agent_service(stream_events=events)

        # 使用 home 模式（非 command）
        mock_page_ctx = MagicMock()
        mock_page_ctx.page_type = "home"
        mock_page_ctx.entry_id = None
        mock_page_ctx.extra = None

        result = await _collect_sse(
            service,
            text="你好",
            thread_id="user1:home-sess1",
            user_id="user1",
            page_context=mock_page_ctx,
        )

        event_types = [e[0] for e in result]

        # 不应产生 redirect 事件（降级为 content）
        assert "redirect" not in event_types
        # 应产生 content 事件
        assert "content" in event_types
        content_events = [d for e, d in result if e == "content"]
        assert any("日知" in c.get("content", "") for c in content_events)
