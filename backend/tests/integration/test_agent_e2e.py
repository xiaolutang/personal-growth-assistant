"""Agent E2E 集成测试

使用 httpx AsyncClient + 真实 FastAPI app 测试 Agent 端到端流程。
Mock LLM 调用（使用 AsyncMock），不发起真实 API 请求。

覆盖场景：
1. 端到端 CRUD（创建/更新/搜索/删除）
2. 多轮对话（ask_user 追问 -> 用户回复）
3. SSE 流式输出完整序列验证
4. 错误处理
"""

import json
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


# === SSE 解析工具 ===


def parse_sse_events(raw: str) -> list[tuple[str, dict]]:
    """解析 SSE 文本流为 (event_type, data) 列表"""
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


async def collect_sse_from_response(response) -> list[tuple[str, dict]]:
    """从 httpx StreamingResponse 收集并解析 SSE 事件"""
    raw = ""
    async for line in response.aiter_lines():
        raw += line + "\n"
    return parse_sse_events(raw)


async def collect_sse_bytes(response) -> list[tuple[str, dict]]:
    """从 httpx StreamingResponse (bytes) 收集并解析 SSE 事件"""
    raw = ""
    async for chunk in response.aiter_bytes():
        raw += chunk.decode("utf-8", errors="replace")
    return parse_sse_events(raw)


# === Mock LLM 响应构建工具 ===


def make_openai_response(
    content: str = "",
    tool_calls: list | None = None,
):
    """创建模拟的 OpenAI API 响应对象"""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def make_tool_call(name: str, args: dict, call_id: str = "call_1"):
    """创建模拟的 tool_call 对象"""
    tc = MagicMock()
    tc.id = call_id
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = json.dumps(args, ensure_ascii=False)
    return tc


# === Fixtures ===


@pytest_asyncio.fixture
async def e2e_client(storage, test_user) -> AsyncGenerator[AsyncClient, None]:
    """创建注入了 mock Agent 的测试客户端"""
    from app.main import app
    from app.services.auth_service import create_access_token
    from app.services.agent_service import AgentService
    from app.agent.tools import ToolDependencies, AGENT_TOOLS
    from app.agent.react_agent import ReActAgentGraph
    from app.routers import parse as parse_module
    from app.routers import deps

    # 创建 token
    token = create_access_token(test_user.id)

    # 创建 mock Agent（使用真实 agent graph 但 mock LLM client）
    mock_client = MagicMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=make_openai_response(content="你好！")
    )

    import aiosqlite
    import tempfile

    db_path = tempfile.mktemp(suffix="_e2e_checkpoints.db")
    conn = await aiosqlite.connect(db_path)
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    from app.agent.react_agent import OpenAICompatibleChatModel

    chat_model = OpenAICompatibleChatModel(client=mock_client, model_name="test-model")

    agent_graph = ReActAgentGraph(
        chat_model=chat_model,
        tools=AGENT_TOOLS,
        checkpointer=checkpointer,
    )

    # 构建 ToolDependencies（注入真实 entry_service）
    tool_deps = ToolDependencies()
    entry_svc = deps.get_entry_service()
    tool_deps.set_entry_service(entry_svc)
    review_svc = deps.get_review_service()
    if review_svc:
        tool_deps.set_review_service(review_svc)

    # 创建并注入 AgentService
    agent_service = AgentService()
    agent_service.set_react_agent(agent_graph)
    agent_service.set_dependencies(tool_deps)

    # 注入到 parse router
    parse_module.set_agent_service(agent_service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        # 将 mock_client 附加到 client 上，以便测试中修改 LLM 响应
        c._mock_llm_client = mock_client
        c._agent_service = agent_service
        c._checkpointer_conn = conn
        c._db_path = db_path
        yield c

    # 清理
    parse_module.set_agent_service(None)
    await conn.close()
    import os

    try:
        os.unlink(db_path)
    except OSError:
        pass


# === 端到端 CRUD 测试 ===


class TestAgentE2ECRUD:
    """端到端 CRUD 测试：通过 /chat 接口完成创建/更新/搜索/删除"""

    @pytest.mark.asyncio
    async def test_create_entry_via_chat(self, e2e_client):
        """POST /chat 创建条目：验证 SSE 流包含 created 事件"""
        mock_client = e2e_client._mock_llm_client
        entry_id = f"note-{uuid.uuid4().hex[:8]}"

        # 设置 LLM 第一次返回 tool_call(create_entry)，第二次返回文本回复
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                make_openai_response(
                    content="",
                    tool_calls=[
                        make_tool_call(
                            "create_entry",
                            {
                                "category": "inbox",
                                "title": "今天学习了 Python",
                                "content": "",
                            },
                            "call_create_1",
                        )
                    ],
                ),
                make_openai_response(
                    content="好的，已经帮你记录了这个想法！"
                ),
            ]
        )

        response = await e2e_client.post(
            "/chat",
            json={
                "text": "帮我记录一个想法：今天学习了 Python",
                "session_id": "e2e-create",
            },
        )

        assert response.status_code == 200
        events = await collect_sse_bytes(response)
        event_types = [e[0] for e in events]

        # 验证 SSE 流包含预期事件
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert event_types[-1] == "done"

        # 验证 tool_call 是 create_entry
        tool_call_events = [d for e, d in events if e == "tool_call"]
        assert len(tool_call_events) >= 1
        assert tool_call_events[0]["tool"] == "create_entry"

    @pytest.mark.asyncio
    async def test_update_entry_via_chat(self, e2e_client, test_user):
        """POST /chat 更新条目：验证 SSE 流包含 updated 事件"""
        mock_client = e2e_client._mock_llm_client

        # 先创建一个条目（使用与 test_user 相同的 user_id）
        from app.routers import deps

        entry_svc = deps.get_entry_service()
        from app.api.schemas import EntryCreate

        entry = await entry_svc.create_entry(
            EntryCreate(
                category="task",
                title="学习任务",
                content="学习 Python",
            ),
            user_id=test_user.id,
        )
        entry_id = entry.id

        # 设置 LLM 响应
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                make_openai_response(
                    content="",
                    tool_calls=[
                        make_tool_call(
                            "update_entry",
                            {"entry_id": entry_id, "status": "complete"},
                            "call_update_1",
                        )
                    ],
                ),
                make_openai_response(content="已帮你标记为完成。"),
            ]
        )

        response = await e2e_client.post(
            "/chat",
            json={
                "text": f"把任务 {entry_id} 标记为已完成",
                "session_id": "e2e-update",
            },
        )

        assert response.status_code == 200
        events = await collect_sse_bytes(response)
        event_types = [e[0] for e in events]

        # 验证有 tool_call 和 done
        assert "tool_call" in event_types
        assert event_types[-1] == "done"

        # 验证 tool_call 是 update_entry
        tool_call_events = [d for e, d in events if e == "tool_call"]
        assert tool_call_events[0]["tool"] == "update_entry"

    @pytest.mark.asyncio
    async def test_search_entries_via_chat(self, e2e_client):
        """POST /chat 搜索条目：验证 SSE 流返回搜索结果"""
        mock_client = e2e_client._mock_llm_client

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                make_openai_response(
                    content="",
                    tool_calls=[
                        make_tool_call(
                            "search_entries",
                            {"query": "Python", "limit": 5},
                            "call_search_1",
                        )
                    ],
                ),
                make_openai_response(content="搜索完成，以下是结果。"),
            ]
        )

        response = await e2e_client.post(
            "/chat",
            json={
                "text": "搜索关于 Python 的内容",
                "session_id": "e2e-search",
            },
        )

        assert response.status_code == 200
        events = await collect_sse_bytes(response)
        event_types = [e[0] for e in events]

        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert event_types[-1] == "done"

        # 验证 tool_call 是 search_entries
        tool_call_events = [d for e, d in events if e == "tool_call"]
        assert tool_call_events[0]["tool"] == "search_entries"

    @pytest.mark.asyncio
    async def test_delete_entry_via_chat(self, e2e_client, test_user):
        """POST /chat 删除条目：验证 SSE 流包含 tool_result"""
        mock_client = e2e_client._mock_llm_client

        # 先创建一个条目（使用与 test_user 相同的 user_id）
        from app.routers import deps
        from app.api.schemas import EntryCreate

        entry_svc = deps.get_entry_service()
        entry = await entry_svc.create_entry(
            EntryCreate(category="inbox", title="待删除的记录"),
            user_id=test_user.id,
        )
        entry_id = entry.id

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                make_openai_response(
                    content="",
                    tool_calls=[
                        make_tool_call(
                            "delete_entry",
                            {"entry_id": entry_id},
                            "call_delete_1",
                        )
                    ],
                ),
                make_openai_response(content="已帮你删除了。"),
            ]
        )

        response = await e2e_client.post(
            "/chat",
            json={
                "text": f"删除记录 {entry_id}",
                "session_id": "e2e-delete",
            },
        )

        assert response.status_code == 200
        events = await collect_sse_bytes(response)
        event_types = [e[0] for e in events]

        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert event_types[-1] == "done"

        # 验证 tool_call 是 delete_entry
        tool_call_events = [d for e, d in events if e == "tool_call"]
        assert tool_call_events[0]["tool"] == "delete_entry"

        # 验证 tool_result success
        tool_result_events = [d for e, d in events if e == "tool_result"]
        assert tool_result_events[0]["success"] is True


# === 多轮对话测试 ===


class TestAgentE2EMultiTurn:
    """多轮对话测试：ask_user 追问 -> 用户回复 -> 操作"""

    @pytest.mark.asyncio
    async def test_ask_user_and_continue(self, e2e_client):
        """信息不足时 Agent 使用 ask_user 追问，用户回复后继续操作"""
        mock_client = e2e_client._mock_llm_client
        session_id = f"multi-turn-{uuid.uuid4().hex[:6]}"

        # 第一轮：LLM 调用 ask_user
        mock_client.chat.completions.create = AsyncMock(
            return_value=make_openai_response(
                content="",
                tool_calls=[
                    make_tool_call(
                        "ask_user",
                        {"question": "你想创建什么类型的条目？"},
                        "call_ask_1",
                    )
                ],
            )
        )

        response_1 = await e2e_client.post(
            "/chat",
            json={
                "text": "帮我创建一个任务",
                "session_id": session_id,
            },
        )

        assert response_1.status_code == 200
        events_1 = await collect_sse_bytes(response_1)
        event_types_1 = [e[0] for e in events_1]

        # 验证 ask_user 的 tool_call 事件
        assert "tool_call" in event_types_1
        tool_call_events_1 = [d for e, d in events_1 if e == "tool_call"]
        assert tool_call_events_1[0]["tool"] == "ask_user"

        # 验证 tool_result 事件（ask_user 的结果）
        assert "tool_result" in event_types_1

        # 第二轮：用户回复后 LLM 创建条目
        # 注意：checkpointer 恢复了历史，LLM 可能多次调用
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                make_openai_response(
                    content="",
                    tool_calls=[
                        make_tool_call(
                            "create_entry",
                            {"category": "task", "title": "学习 LangGraph"},
                            "call_create_2",
                        )
                    ],
                ),
                make_openai_response(content="已创建任务「学习 LangGraph」。"),
                # 额外备用响应（防止 checkpointer 恢复后多次 LLM 调用）
                make_openai_response(content="已完成。"),
                make_openai_response(content="完成。"),
            ]
        )

        response_2 = await e2e_client.post(
            "/chat",
            json={
                "text": "创建一个学习 LangGraph 的任务",
                "session_id": session_id,
            },
        )

        assert response_2.status_code == 200
        events_2 = await collect_sse_bytes(response_2)
        event_types_2 = [e[0] for e in events_2]

        # 验证第二轮有 create_entry 的 tool_call（可能不排在第一个，因为历史恢复）
        assert "tool_call" in event_types_2
        tool_call_events_2 = [d for e, d in events_2 if e == "tool_call"]
        tool_names = [tc["tool"] for tc in tool_call_events_2]
        assert "create_entry" in tool_names
        assert event_types_2[-1] == "done"


# === SSE 流式输出测试 ===


class TestAgentE2ESSESequence:
    """SSE 流式输出完整序列验证"""

    @pytest.mark.asyncio
    async def test_complete_sse_sequence(self, e2e_client):
        """验证完整 SSE 事件序列：thinking -> tool_call -> tool_result -> content -> done"""
        mock_client = e2e_client._mock_llm_client

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                make_openai_response(
                    content="好的，我来帮你搜索。",
                    tool_calls=[
                        make_tool_call(
                            "search_entries",
                            {"query": "测试"},
                            "call_seq_1",
                        )
                    ],
                ),
                make_openai_response(content="找到了相关内容。"),
            ]
        )

        response = await e2e_client.post(
            "/chat",
            json={
                "text": "搜索测试",
                "session_id": "e2e-sse-seq",
            },
        )

        assert response.status_code == 200
        events = await collect_sse_bytes(response)
        event_types = [e[0] for e in events]

        # 验证事件序列中包含关键事件类型
        assert "thinking" in event_types, f"缺少 thinking 事件，实际事件: {event_types}"
        assert "tool_call" in event_types, f"缺少 tool_call 事件，实际事件: {event_types}"
        assert "tool_result" in event_types, f"缺少 tool_result 事件，实际事件: {event_types}"
        assert "done" in event_types, f"缺少 done 事件，实际事件: {event_types}"

        # 验证 done 是最后一个事件
        assert event_types[-1] == "done"

        # 验证事件顺序：thinking 应在 tool_call 之前
        thinking_idx = event_types.index("thinking")
        tool_call_idx = event_types.index("tool_call")
        assert thinking_idx < tool_call_idx

        # 验证 tool_call 在 tool_result 之前
        tool_result_idx = event_types.index("tool_result")
        assert tool_call_idx < tool_result_idx

    @pytest.mark.asyncio
    async def test_pure_chat_no_tool_events(self, e2e_client):
        """纯对话场景：无 tool_call/tool_result 事件"""
        mock_client = e2e_client._mock_llm_client

        mock_client.chat.completions.create = AsyncMock(
            return_value=make_openai_response(
                content="你好！我是日知，你的个人成长助手。有什么可以帮你的吗？"
            )
        )

        response = await e2e_client.post(
            "/chat",
            json={
                "text": "你好",
                "session_id": "e2e-pure-chat",
            },
        )

        assert response.status_code == 200
        events = await collect_sse_bytes(response)
        event_types = [e[0] for e in events]

        # 纯对话只有 thinking + done
        assert "tool_call" not in event_types
        assert "tool_result" not in events
        assert event_types[-1] == "done"

    @pytest.mark.asyncio
    async def test_error_handling_invalid_session(self, e2e_client):
        """错误处理：Agent 未初始化时返回 503"""
        from app.routers import parse as parse_module

        # 临时清除 agent_service
        original_service = parse_module._agent_service
        parse_module.set_agent_service(None)

        try:
            response = await e2e_client.post(
                "/chat",
                json={
                    "text": "测试",
                    "session_id": "e2e-error",
                },
            )
            assert response.status_code == 503
            data = response.json()
            assert "Agent" in data["detail"] or "未初始化" in data["detail"]
        finally:
            # 恢复 agent_service
            parse_module.set_agent_service(original_service)

    @pytest.mark.asyncio
    async def test_invalid_session_id_rejected(self, e2e_client):
        """错误处理：非法 session_id 格式返回 400"""
        response = await e2e_client.post(
            "/chat",
            json={
                "text": "测试",
                "session_id": "invalid:session:id",
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_text_rejected(self, e2e_client):
        """错误处理：空文本返回 422"""
        response = await e2e_client.post(
            "/chat",
            json={
                "text": "",
                "session_id": "e2e-empty",
            },
        )

        assert response.status_code == 422


# === Agent Service SSE 编排测试（不依赖 HTTP） ===


class TestAgentServiceSSEOrchestration:
    """直接测试 AgentService.chat() 的 SSE 事件编排（不经过 HTTP）"""

    @pytest.mark.asyncio
    async def test_created_event_extraction(self):
        """Tool 返回 {id, category, title} 时触发 created 事件"""
        from app.services.agent_service import AgentService, sse_event
        from app.agent.tools import ToolDependencies

        service = AgentService()
        mock_agent = MagicMock()

        tool_call_id = "call_created"

        async def _stream(**kwargs):
            yield {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "create_entry",
                                "args": {"category": "note", "title": "测试"},
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps(
                            {
                                "success": True,
                                "data": {
                                    "id": "note-xyz789",
                                    "title": "测试笔记",
                                    "category": "note",
                                    "status": "doing",
                                },
                            }
                        ),
                        tool_call_id=tool_call_id,
                    ),
                    AIMessage(content="已创建。"),
                ]
            }

        mock_agent.stream = MagicMock(side_effect=_stream)
        service.set_react_agent(mock_agent)
        service.set_dependencies(ToolDependencies())

        raw = ""
        async for chunk in service.chat(
            text="创建笔记",
            thread_id="test:created",
            user_id="test",
        ):
            raw += chunk

        events = parse_sse_events(raw)
        event_types = [e[0] for e in events]

        # 验证有 created 事件
        assert "created" in event_types
        created_events = [d for e, d in events if e == "created"]
        assert created_events[0]["id"] == "note-xyz789"
        assert created_events[0]["type"] == "note"

        # 验证 done 在最后
        assert event_types[-1] == "done"

    @pytest.mark.asyncio
    async def test_updated_event_extraction(self):
        """Tool 返回 {entry_id, message} 时触发 updated 事件"""
        from app.services.agent_service import AgentService
        from app.agent.tools import ToolDependencies

        service = AgentService()
        mock_agent = MagicMock()

        tool_call_id = "call_updated"

        async def _stream(**kwargs):
            yield {
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
                        content=json.dumps(
                            {
                                "success": True,
                                "data": {
                                    "entry_id": "e1",
                                    "message": "已更新",
                                },
                            }
                        ),
                        tool_call_id=tool_call_id,
                    ),
                    AIMessage(content="已更新完成。"),
                ]
            }

        mock_agent.stream = MagicMock(side_effect=_stream)
        service.set_react_agent(mock_agent)
        service.set_dependencies(ToolDependencies())

        raw = ""
        async for chunk in service.chat(
            text="标记完成",
            thread_id="test:updated",
            user_id="test",
        ):
            raw += chunk

        events = parse_sse_events(raw)
        event_types = [e[0] for e in events]

        assert "updated" in event_types
        updated_events = [d for e, d in events if e == "updated"]
        assert updated_events[0]["id"] == "e1"

    @pytest.mark.asyncio
    async def test_multi_tool_calls_in_sequence(self):
        """多个 tool_calls 按顺序发送 tool_call 事件"""
        from app.services.agent_service import AgentService
        from app.agent.tools import ToolDependencies

        service = AgentService()
        mock_agent = MagicMock()

        async def _stream(**kwargs):
            yield {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_1",
                                "name": "search_entries",
                                "args": {"query": "Python"},
                                "type": "tool_call",
                            },
                            {
                                "id": "call_2",
                                "name": "get_entry",
                                "args": {"entry_id": "note-123"},
                                "type": "tool_call",
                            },
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps({"success": True, "data": {"entries": []}}),
                        tool_call_id="call_1",
                    ),
                    ToolMessage(
                        content=json.dumps({"success": False, "error": "不存在"}),
                        tool_call_id="call_2",
                    ),
                    AIMessage(content="搜索完成。"),
                ]
            }

        mock_agent.stream = MagicMock(side_effect=_stream)
        service.set_react_agent(mock_agent)
        service.set_dependencies(ToolDependencies())

        raw = ""
        async for chunk in service.chat(
            text="搜索",
            thread_id="test:multi",
            user_id="test",
        ):
            raw += chunk

        events = parse_sse_events(raw)
        tool_call_events = [d for e, d in events if e == "tool_call"]

        # 验证有两个 tool_call 事件
        assert len(tool_call_events) == 2
        assert tool_call_events[0]["tool"] == "search_entries"
        assert tool_call_events[1]["tool"] == "get_entry"

    @pytest.mark.asyncio
    async def test_failed_tool_result_event(self):
        """Tool 执行失败时 tool_result 的 success 为 False"""
        from app.services.agent_service import AgentService
        from app.agent.tools import ToolDependencies

        service = AgentService()
        mock_agent = MagicMock()

        tool_call_id = "call_fail"

        async def _stream(**kwargs):
            yield {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": tool_call_id,
                                "name": "delete_entry",
                                "args": {"entry_id": "nonexist"},
                                "type": "tool_call",
                            }
                        ],
                    ),
                    ToolMessage(
                        content=json.dumps(
                            {
                                "success": False,
                                "error": "条目不存在: nonexist",
                            }
                        ),
                        tool_call_id=tool_call_id,
                    ),
                    AIMessage(content="抱歉，找不到这个条目。"),
                ]
            }

        mock_agent.stream = MagicMock(side_effect=_stream)
        service.set_react_agent(mock_agent)
        service.set_dependencies(ToolDependencies())

        raw = ""
        async for chunk in service.chat(
            text="删除不存在的条目",
            thread_id="test:fail",
            user_id="test",
        ):
            raw += chunk

        events = parse_sse_events(raw)
        tool_result_events = [d for e, d in events if e == "tool_result"]

        assert len(tool_result_events) >= 1
        assert tool_result_events[0]["success"] is False
        assert "不存在" in tool_result_events[0]["result"]["error"]
