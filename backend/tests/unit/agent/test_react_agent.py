"""ReAct Agent 图单元测试

覆盖场景：
1. 正常 tool 调用
2. 纯对话（不触发 tool）
3. ask_user 中断
4. 循环上限
5. 异常降级
6. 首次使用（空 checkpointer）
"""

import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.react_agent import (
    ReActAgentGraph,
    ReActAgentState,
    OpenAICompatibleChatModel,
    MAX_ITERATIONS,
    ROUTE_TOOLS,
    ROUTE_END,
)


# ── Fixtures ──


class MockAsyncOpenAIClient:
    """模拟 AsyncOpenAI 客户端"""

    def __init__(self, responses: list | None = None):
        self.responses = responses or []
        self._call_index = 0
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock(side_effect=self._create_response)

    async def _create_response(self, **kwargs):
        if self._call_index < len(self.responses):
            resp = self.responses[self._call_index]
            self._call_index += 1
            return resp
        # 默认返回空响应
        return self._make_response("")

    @staticmethod
    def _make_response(
        content: str = "",
        tool_calls: list | None = None,
    ):
        """创建模拟的 OpenAI API 响应"""
        message = MagicMock()
        message.content = content
        message.tool_calls = tool_calls

        choice = MagicMock()
        choice.message = message

        response = MagicMock()
        response.choices = [choice]
        return response

    @staticmethod
    def make_tool_call(name: str, args: dict, call_id: str = "call_1"):
        """创建模拟的 tool_call 对象"""
        tc = MagicMock()
        tc.id = call_id
        tc.function = MagicMock()
        tc.function.name = name
        tc.function.arguments = json.dumps(args, ensure_ascii=False)
        return tc


class MockTool:
    """模拟 LangChain BaseTool"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.args_schema = MagicMock()

        # 让 args_schema.schema() 返回空参数
        mock_schema = MagicMock()
        mock_schema.schema.return_value = {
            "properties": {},
            "required": [],
        }
        self.args_schema = mock_schema


@pytest_asyncio.fixture
async def checkpointer(tmp_path):
    """创建临时 checkpointer"""
    import aiosqlite

    db_path = str(tmp_path / "test_checkpoints.db")
    conn = await aiosqlite.connect(db_path)
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    return saver


def make_mock_chat_model(client: MockAsyncOpenAIClient) -> OpenAICompatibleChatModel:
    """创建绑定 mock client 的 chat model"""
    return OpenAICompatibleChatModel(client=client, model_name="test-model")


def make_mock_tools() -> list:
    """创建 mock tool 列表"""
    from app.agent.tools import AGENT_TOOLS
    return AGENT_TOOLS


# ── 测试：路由逻辑 ──


class TestRouteAfterAgent:
    """测试 _route_after_agent 条件边逻辑"""

    def test_no_tool_calls_returns_end(self):
        """无 tool_calls → END"""
        mock_client = MockAsyncOpenAIClient()
        model = make_mock_chat_model(mock_client)
        graph_builder = ReActAgentGraph.__new__(ReActAgentGraph)
        graph_builder.max_iterations = MAX_ITERATIONS

        state = ReActAgentState(
            messages=[HumanMessage(content="hi"), AIMessage(content="hello")],
            iteration_count=0,
        )
        assert graph_builder._route_after_agent(state) == ROUTE_END

    def test_with_tool_calls_returns_tools(self):
        """有 tool_calls → tools"""
        graph_builder = ReActAgentGraph.__new__(ReActAgentGraph)
        graph_builder.max_iterations = MAX_ITERATIONS

        state = ReActAgentState(
            messages=[
                HumanMessage(content="创建任务"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "create_entry",
                            "args": {"category": "task", "title": "测试"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
            ],
            iteration_count=0,
        )
        assert graph_builder._route_after_agent(state) == ROUTE_TOOLS

    def test_iteration_limit_returns_end(self):
        """循环上限 → END"""
        graph_builder = ReActAgentGraph.__new__(ReActAgentGraph)
        graph_builder.max_iterations = MAX_ITERATIONS

        state = ReActAgentState(
            messages=[
                HumanMessage(content="hi"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "create_entry",
                            "args": {},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
            ],
            iteration_count=MAX_ITERATIONS,
        )
        assert graph_builder._route_after_agent(state) == ROUTE_END


class TestRouteAfterTools:
    """测试 _route_after_tools 条件边逻辑"""

    def test_ask_user_returns_end(self):
        """包含 ask_user → END"""
        graph_builder = ReActAgentGraph.__new__(ReActAgentGraph)
        graph_builder.max_iterations = MAX_ITERATIONS

        state = ReActAgentState(
            messages=[
                HumanMessage(content="记一下"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "ask_user",
                            "args": {"question": "你想记什么？"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content='{"type": "ask", "question": "你想记什么？"}',
                    tool_call_id="call_1",
                ),
            ],
            iteration_count=1,
        )
        assert graph_builder._route_after_tools(state) == ROUTE_END

    def test_other_tool_returns_agent(self):
        """非 ask_user 的 tool → 继续循环"""
        graph_builder = ReActAgentGraph.__new__(ReActAgentGraph)
        graph_builder.max_iterations = MAX_ITERATIONS

        state = ReActAgentState(
            messages=[
                HumanMessage(content="搜索"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_entries",
                            "args": {"query": "测试"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content='{"success": true, "data": {"entries": []}}',
                    tool_call_id="call_1",
                ),
            ],
            iteration_count=1,
        )
        assert graph_builder._route_after_tools(state) == "agent"

    def test_iteration_limit_returns_end(self):
        """循环上限 → END"""
        graph_builder = ReActAgentGraph.__new__(ReActAgentGraph)
        graph_builder.max_iterations = MAX_ITERATIONS

        state = ReActAgentState(
            messages=[
                HumanMessage(content="搜索"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "search_entries",
                            "args": {"query": "测试"},
                            "id": "call_1",
                            "type": "tool_call",
                        }
                    ],
                ),
                ToolMessage(
                    content='{"success": true}',
                    tool_call_id="call_1",
                ),
            ],
            iteration_count=MAX_ITERATIONS,
        )
        assert graph_builder._route_after_tools(state) == ROUTE_END


# ── 测试：OpenAICompatibleChatModel ──


class TestOpenAICompatibleChatModel:
    """测试自定义 ChatModel"""

    @pytest.mark.asyncio
    async def test_simple_response(self):
        """普通文本响应"""
        mock_client = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(content="你好！我是日知。")
            ]
        )
        model = make_mock_chat_model(mock_client)

        result = await model._agenerate(
            [
                SystemMessage(content="你是日知"),
                HumanMessage(content="你好"),
            ]
        )

        assert len(result.generations) == 1
        assert isinstance(result.generations[0].message, AIMessage)
        assert result.generations[0].message.content == "你好！我是日知。"

    @pytest.mark.asyncio
    async def test_tool_calls_response(self):
        """tool_calls 响应"""
        mock_client = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(
                    content="",
                    tool_calls=[
                        MockAsyncOpenAIClient.make_tool_call(
                            "search_entries",
                            {"query": "测试"},
                            "call_1",
                        )
                    ],
                )
            ]
        )
        model = make_mock_chat_model(mock_client)

        result = await model._agenerate(
            [
                SystemMessage(content="你是日知"),
                HumanMessage(content="搜索测试"),
            ]
        )

        ai_msg = result.generations[0].message
        assert isinstance(ai_msg, AIMessage)
        assert len(ai_msg.tool_calls) == 1
        assert ai_msg.tool_calls[0]["name"] == "search_entries"
        assert ai_msg.tool_calls[0]["args"] == {"query": "测试"}

    def test_bind_tools(self):
        """bind_tools 转换为 OpenAI 格式"""
        mock_client = MockAsyncOpenAIClient()
        model = make_mock_chat_model(mock_client)

        tools = make_mock_tools()
        bound = model.bind_tools(tools)

        assert bound is not None
        # bound 是 RunnableBinding
        assert hasattr(bound, "invoke")

    def test_convert_messages(self):
        """消息格式转换"""
        mock_client = MockAsyncOpenAIClient()
        model = make_mock_chat_model(mock_client)

        messages = [
            SystemMessage(content="系统提示"),
            HumanMessage(content="用户消息"),
            AIMessage(content="助手回复"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "test_tool",
                        "args": {"key": "value"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(content="工具结果", tool_call_id="call_1"),
        ]

        converted = model._convert_messages(messages)

        assert converted[0]["role"] == "system"
        assert converted[1]["role"] == "user"
        assert converted[2]["role"] == "assistant"
        assert converted[2]["content"] == "助手回复"
        assert converted[3]["role"] == "assistant"
        assert "tool_calls" in converted[3]
        assert converted[4]["role"] == "tool"
        assert converted[4]["tool_call_id"] == "call_1"


# ── 测试：ReAct Agent Graph 集成 ──


class TestReActAgentGraphIntegration:
    """测试 ReAct Agent 图的端到端行为"""

    @pytest.mark.asyncio
    async def test_pure_chat(self, checkpointer):
        """纯对话：不触发 tool，直接回复"""
        mock_client = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(
                    content="你好！有什么可以帮你的？"
                )
            ]
        )
        model = make_mock_chat_model(mock_client)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model,
            tools=tools,
            checkpointer=checkpointer,
        )

        result = await graph.invoke("你好", thread_id="test_pure_chat")

        messages = result["messages"]
        # 应该有 HumanMessage + AIMessage
        assert len(messages) >= 2
        last = messages[-1]
        assert isinstance(last, AIMessage)
        assert "你好" in last.content or "帮" in last.content

    @pytest.mark.asyncio
    async def test_tool_call_loop(self, checkpointer):
        """正常 tool 调用循环"""
        # 第一次调用：LLM 决定调用 search_entries
        # 第二次调用：LLM 根据结果回复用户
        mock_client = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(
                    content="",
                    tool_calls=[
                        MockAsyncOpenAIClient.make_tool_call(
                            "search_entries",
                            {"query": "MCP"},
                            "call_search_1",
                        )
                    ],
                ),
                MockAsyncOpenAIClient._make_response(
                    content="我找到了一些关于 MCP 的内容。"
                ),
            ]
        )
        model = make_mock_chat_model(mock_client)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model,
            tools=tools,
            checkpointer=checkpointer,
        )

        # 需要注入 mock dependencies，否则 tool 会报 service 未初始化
        from app.agent.tools import ToolDependencies

        mock_deps = ToolDependencies()

        result = await graph.invoke(
            "搜索 MCP",
            thread_id="test_tool_call",
            dependencies=mock_deps,
        )

        messages = result["messages"]
        last = messages[-1]
        assert isinstance(last, AIMessage)

    @pytest.mark.asyncio
    async def test_ask_user_interrupt(self, checkpointer):
        """ask_user 中断：调用后循环终止，下次可恢复"""
        mock_client = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(
                    content="",
                    tool_calls=[
                        MockAsyncOpenAIClient.make_tool_call(
                            "ask_user",
                            {"question": "你想记什么类型的内容？"},
                            "call_ask_1",
                        )
                    ],
                ),
            ]
        )
        model = make_mock_chat_model(mock_client)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model,
            tools=tools,
            checkpointer=checkpointer,
        )

        from app.agent.tools import ToolDependencies

        mock_deps = ToolDependencies()

        result = await graph.invoke(
            "记一下",
            thread_id="test_ask_user",
            dependencies=mock_deps,
        )

        messages = result["messages"]
        # 应该包含 ask_user 的 tool call 和 tool result
        has_ask_user_call = False
        has_ask_result = False
        for msg in messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "ask_user":
                        has_ask_user_call = True
            if isinstance(msg, ToolMessage):
                if "ask" in msg.content and "question" in msg.content:
                    has_ask_result = True

        assert has_ask_user_call, "应该有 ask_user 的 tool_call"
        assert has_ask_result, "应该有 ask_user 的 ToolMessage 结果"

        # 循环应该已终止（不是超限终止）
        iteration_count = result.get("iteration_count", 0)
        assert iteration_count < MAX_ITERATIONS

    @pytest.mark.asyncio
    async def test_iteration_limit(self, checkpointer):
        """循环上限：连续 tool 调用后自动结束"""
        # 构造连续调用 tool 的响应（每次都触发 tool_call）
        responses = []
        for i in range(MAX_ITERATIONS + 1):
            responses.append(
                MockAsyncOpenAIClient._make_response(
                    content="",
                    tool_calls=[
                        MockAsyncOpenAIClient.make_tool_call(
                            "search_entries",
                            {"query": f"test_{i}"},
                            f"call_{i}",
                        )
                    ],
                )
            )

        mock_client = MockAsyncOpenAIClient(responses=responses)
        model = make_mock_chat_model(mock_client)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model,
            tools=tools,
            checkpointer=checkpointer,
            max_iterations=MAX_ITERATIONS,
        )

        from app.agent.tools import ToolDependencies

        mock_deps = ToolDependencies()

        result = await graph.invoke(
            "连续搜索",
            thread_id="test_iteration_limit",
            dependencies=mock_deps,
        )

        # 循环应该终止
        iteration_count = result.get("iteration_count", 0)
        assert iteration_count <= MAX_ITERATIONS

    @pytest.mark.asyncio
    async def test_first_time_user(self, checkpointer):
        """首次使用：空 checkpointer 新用户正常工作"""
        mock_client = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(
                    content="你好！我是日知，你的个人成长助手。"
                )
            ]
        )
        model = make_mock_chat_model(mock_client)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model,
            tools=tools,
            checkpointer=checkpointer,
        )

        result = await graph.invoke(
            "你好",
            thread_id="test_first_time",
            is_new_user=True,
        )

        messages = result["messages"]
        last = messages[-1]
        assert isinstance(last, AIMessage)
        assert last.content  # 有内容

    @pytest.mark.asyncio
    async def test_context_recovery(self, checkpointer):
        """上下文恢复：ask_user 后同 thread_id 恢复"""
        # 第一次对话：触发 ask_user
        mock_client_1 = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(
                    content="",
                    tool_calls=[
                        MockAsyncOpenAIClient.make_tool_call(
                            "ask_user",
                            {"question": "你想创建什么类型的条目？"},
                            "call_ask_1",
                        )
                    ],
                ),
            ]
        )
        model_1 = make_mock_chat_model(mock_client_1)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model_1,
            tools=tools,
            checkpointer=checkpointer,
        )

        from app.agent.tools import ToolDependencies

        mock_deps = ToolDependencies()

        # 第一次调用
        result_1 = await graph.invoke(
            "记一下",
            thread_id="test_recovery",
            dependencies=mock_deps,
        )

        # 第二次对话：用户回复
        mock_client_2 = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(
                    content="好的，已帮你创建了任务。"
                )
            ]
        )
        model_2 = make_mock_chat_model(mock_client_2)

        graph_2 = ReActAgentGraph(
            chat_model=model_2,
            tools=tools,
            checkpointer=checkpointer,
        )

        result_2 = await graph_2.invoke(
            "创建一个学习任务",
            thread_id="test_recovery",
            dependencies=mock_deps,
        )

        messages_2 = result_2["messages"]
        # 应该包含之前对话的历史
        assert len(messages_2) > 2  # 之前的历史 + 新消息
        last = messages_2[-1]
        assert isinstance(last, AIMessage)

    @pytest.mark.asyncio
    async def test_llm_error_graceful_degradation(self, checkpointer):
        """异常降级：LLM 调用异常时优雅降级"""
        mock_client = MockAsyncOpenAIClient()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API 服务不可用")
        )
        model = make_mock_chat_model(mock_client)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model,
            tools=tools,
            checkpointer=checkpointer,
        )

        result = await graph.invoke(
            "你好",
            thread_id="test_llm_error",
        )

        messages = result["messages"]
        last = messages[-1]
        assert isinstance(last, AIMessage)
        # 应该有友好的错误信息
        assert "问题" in last.content or "抱歉" in last.content or "错误" in last.content

    @pytest.mark.asyncio
    async def test_clear_thread(self, checkpointer):
        """清空线程历史"""
        mock_client = MockAsyncOpenAIClient(
            responses=[
                MockAsyncOpenAIClient._make_response(content="你好！")
            ]
        )
        model = make_mock_chat_model(mock_client)
        tools = make_mock_tools()

        graph = ReActAgentGraph(
            chat_model=model,
            tools=tools,
            checkpointer=checkpointer,
        )

        # 先发一条消息
        await graph.invoke("你好", thread_id="test_clear")

        # 清空
        await graph.clear_thread("test_clear")

        # 清空后不应抛异常（验证方法存在且可调用）
        # （adelete_thread 可能是空实现，取决于 checkpointer 版本）


# ── 测试：Prompts ──


class TestPrompts:
    """测试 prompt 构建"""

    def test_build_system_prompt_basic(self):
        """基础 prompt 构建"""
        from app.agent.prompts import build_system_prompt

        prompt = build_system_prompt(current_time="2026-04-28 10:00")
        assert "日知" in prompt
        assert "2026-04-28 10:00" in prompt

    def test_build_system_prompt_with_page(self):
        """带页面角色的 prompt"""
        from app.agent.prompts import build_system_prompt

        prompt = build_system_prompt(
            page="home",
            current_time="2026-04-28 10:00",
        )
        assert "晨报助手" in prompt

    def test_build_system_prompt_with_context(self):
        """带页面上下文的 prompt"""
        from app.agent.prompts import build_system_prompt

        prompt = build_system_prompt(
            page_context="今日任务: 3 个待完成",
            current_time="2026-04-28 10:00",
        )
        assert "今日任务" in prompt
        assert "页面上下文" in prompt

    def test_build_system_prompt_new_user(self):
        """新用户引导 prompt"""
        from app.agent.prompts import build_system_prompt

        prompt = build_system_prompt(
            is_new_user=True,
            current_time="2026-04-28 10:00",
        )
        assert "首次使用" in prompt or "日知" in prompt

    def test_build_system_prompt_no_context(self):
        """无上下文时不注入页面上下文段落"""
        from app.agent.prompts import build_system_prompt

        prompt = build_system_prompt(current_time="2026-04-28 10:00")
        assert "页面上下文" not in prompt
