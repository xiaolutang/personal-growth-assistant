"""LangGraph ReAct Agent 图

使用 StateGraph(MessagesState) 构建 Agent Node + ToolNode 循环。
条件边判断：
- LLM 无 tool_calls → END
- 有 tool_calls 且包含 ask_user → 执行 ToolNode 后路由到 END（中断等待用户回复）
- 其他 tool_calls → 继续循环

循环上限 5 轮。System prompt 支持页面上下文注入。
保留 AsyncSqliteSaver checkpointer。
"""

import json
import logging
from datetime import datetime
from typing import Any, Callable, Optional, Sequence

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, MessagesState, StateGraph

from app.agent.prompts import build_system_prompt

logger = logging.getLogger(__name__)

# ── 循环上限 ──
MAX_ITERATIONS = 5

# ── 路由常量 ──
ROUTE_TOOLS = "tools"
ROUTE_END = "__end__"


# ── 自定义 Chat Model（基于 OpenAI 兼容 API）──


class OpenAICompatibleChatModel(BaseChatModel):
    """基于 AsyncOpenAI 的 ChatModel 实现，支持 bind_tools。

    由于项目未依赖 langchain-openai，需要自定义 BaseChatModel 子类
    来支持 LangGraph ReAct Agent 所需的 tool_calls 功能。
    """

    client: Any  # AsyncOpenAI instance
    model_name: str = ""

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "openai-compatible"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成（本项目使用异步，此方法为接口完整性保留）"""
        raise NotImplementedError("请使用异步调用 _agenerate")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成，支持 tool_calls"""
        # 转换消息格式
        openai_messages = self._convert_messages(messages)

        params: dict[str, Any] = {
            "model": self.model_name,
            "messages": openai_messages,
        }
        if stop:
            params["stop"] = stop

        # 处理 bind_tools 传入的 tools 参数
        tools = kwargs.get("tools")
        if tools:
            params["tools"] = tools

        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]
        message = choice.message

        # 构建 AIMessage
        ai_message_kwargs: dict[str, Any] = {
            "content": message.content or "",
        }

        # 处理 tool_calls
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append(
                    {
                        "name": tc.function.name,
                        "args": json.loads(tc.function.arguments)
                        if isinstance(tc.function.arguments, str)
                        else tc.function.arguments,
                        "id": tc.id,
                        "type": "tool_call",
                    }
                )
            ai_message_kwargs["tool_calls"] = tool_calls

        ai_message = AIMessage(**ai_message_kwargs)
        generation = ChatGeneration(message=ai_message)

        return ChatResult(generations=[generation])

    def _convert_messages(self, messages: list[BaseMessage]) -> list[dict]:
        """将 LangChain 消息转换为 OpenAI 格式"""
        openai_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                openai_messages.append(
                    {"role": "system", "content": msg.content}
                )
            elif isinstance(msg, HumanMessage):
                openai_messages.append(
                    {"role": "user", "content": msg.content}
                )
            elif isinstance(msg, AIMessage):
                ai_msg: dict[str, Any] = {"role": "assistant"}
                if msg.content:
                    ai_msg["content"] = msg.content
                if msg.tool_calls:
                    ai_msg["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(
                                    tc["args"], ensure_ascii=False
                                ),
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                # 如果没有 content 也没有 tool_calls，添加空 content
                if "content" not in ai_msg and "tool_calls" not in ai_msg:
                    ai_msg["content"] = ""
                openai_messages.append(ai_msg)
            elif isinstance(msg, ToolMessage):
                openai_messages.append(
                    {
                        "role": "tool",
                        "content": msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content),
                        "tool_call_id": msg.tool_call_id,
                    }
                )
            else:
                # Fallback: 用 content 作为 user message
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                openai_messages.append({"role": "user", "content": content})
        return openai_messages

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ):
        """绑定工具，返回 RunnableBinding。

        将 LangChain Tool 转换为 OpenAI function calling 格式，
        通过 kwargs['tools'] 传递给 _agenerate。
        """
        openai_tools = []
        for tool in tools:
            if isinstance(tool, BaseTool):
                schema = tool.args_schema.schema()
                # 移除 title 字段（OpenAI 不需要）
                properties = schema.get("properties", {})
                required = schema.get("required", [])

                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": {
                                "type": "object",
                                "properties": properties,
                                "required": required,
                            },
                        },
                    }
                )
            elif isinstance(tool, dict) and "function" in tool:
                openai_tools.append(tool)
            else:
                logger.warning("Unsupported tool type: %s", type(tool))

        # 使用 RunnableBinding 传递 tools 参数
        return self.bind(tools=openai_tools, tool_choice=tool_choice, **kwargs)


# ── Agent State ──


class ReActAgentState(MessagesState):
    """ReAct Agent 状态，扩展 MessagesState 添加迭代计数。"""

    iteration_count: int = 0


# ── ReAct Agent Graph ──


class ReActAgentGraph:
    """LangGraph ReAct Agent 图

    使用 StateGraph(MessagesState) 构建 Agent Node + ToolNode 循环。

    条件边路由逻辑：
    1. LLM 无 tool_calls → END（纯对话回复）
    2. 有 tool_calls 且包含 ask_user → ToolNode → END（中断等待用户回复）
    3. 其他 tool_calls → ToolNode → 继续循环
    4. 循环超过 MAX_ITERATIONS → END（自动结束）
    """

    def __init__(
        self,
        chat_model: BaseChatModel,
        tools: list[BaseTool],
        checkpointer: AsyncSqliteSaver,
        max_iterations: int = MAX_ITERATIONS,
    ):
        self.chat_model = chat_model
        self.tools = tools
        self.checkpointer = checkpointer
        self.max_iterations = max_iterations

        # 将 tools 绑定到 chat_model
        self.bound_model = chat_model.bind_tools(tools)

        # 构建图
        self.graph = self._build_graph()

    @classmethod
    async def create(
        cls,
        api_key: str,
        base_url: str,
        model: str,
        tools: list[BaseTool],
        db_path: str | None = None,
        max_iterations: int = MAX_ITERATIONS,
    ) -> "ReActAgentGraph":
        """工厂方法：创建 ReActAgentGraph 实例。

        Args:
            api_key: OpenAI 兼容 API 密钥
            base_url: API 地址
            model: 模型名称
            tools: Tool 列表
            db_path: SQLite 数据库路径（checkpointer 用）
            max_iterations: 最大迭代次数
        """
        import aiosqlite
        from openai import AsyncOpenAI

        from app.core.config import get_settings

        if db_path is None:
            db_path = get_settings().sqlite_checkpoints_path

        # 创建 AsyncOpenAI client
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # 创建自定义 ChatModel
        chat_model = OpenAICompatibleChatModel(
            client=client, model_name=model
        )

        # 创建 checkpointer
        conn = await aiosqlite.connect(db_path)
        checkpointer = AsyncSqliteSaver(conn)
        await checkpointer.setup()

        return cls(
            chat_model=chat_model,
            tools=tools,
            checkpointer=checkpointer,
            max_iterations=max_iterations,
        )

    def _build_graph(self):
        """构建 LangGraph ReAct 图"""
        builder = StateGraph(ReActAgentState)

        # 添加节点
        builder.add_node("agent", self._agent_node)
        builder.add_node("tools", self._tool_node)

        # 入口边
        builder.add_edge(START, "agent")

        # 条件边：从 agent 节点根据 LLM 响应路由
        builder.add_conditional_edges(
            "agent",
            self._route_after_agent,
            {
                ROUTE_TOOLS: "tools",
                ROUTE_END: END,
            },
        )

        # 条件边：从 tools 节点根据执行结果路由
        builder.add_conditional_edges(
            "tools",
            self._route_after_tools,
            {
                "agent": "agent",
                ROUTE_END: END,
            },
        )

        return builder.compile(checkpointer=self.checkpointer)

    async def _agent_node(
        self, state: ReActAgentState, config: RunnableConfig
    ) -> dict:
        """Agent 节点：调用 LLM 决策。

        构建 system prompt 并调用绑定了 tools 的 LLM。
        """
        iteration_count = state.get("iteration_count", 0)

        # 检查循环上限
        if iteration_count >= self.max_iterations:
            logger.warning(
                "ReAct Agent 达到循环上限 %d，自动结束",
                self.max_iterations,
            )
            return {
                "messages": [
                    AIMessage(
                        content="我已经尽力处理了，但可能还有遗漏。"
                        "如果需要继续，请告诉我更多细节。"
                    )
                ],
                "iteration_count": iteration_count,
            }

        # 构建 system prompt
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        configurable = config.get("configurable", {})
        page = configurable.get("page", "")
        page_context = configurable.get("page_context", "")
        is_new_user = configurable.get("is_new_user", False)

        system_prompt = build_system_prompt(
            page_context=page_context,
            page=page,
            is_new_user=is_new_user,
            current_time=current_time,
        )

        # 构建消息列表
        messages = list(state["messages"])

        # 准备 LLM 调用
        all_messages = [SystemMessage(content=system_prompt)] + messages

        try:
            response = await self.bound_model.ainvoke(all_messages)
        except Exception as e:
            logger.error("ReAct Agent LLM 调用异常: %s", e, exc_info=True)
            return {
                "messages": [
                    AIMessage(
                        content=f"抱歉，处理时遇到了问题：{str(e)}。请稍后再试。"
                    )
                ],
                "iteration_count": iteration_count,
            }

        return {
            "messages": [response],
            "iteration_count": iteration_count,
        }

    async def _tool_node(
        self, state: ReActAgentState, config: RunnableConfig
    ) -> dict:
        """Tool 节点：手动执行 tool 调用并注入 dependencies 和 user_id。

        由于 tool 函数使用 keyword-only 参数 (dependencies, user_id)，
        我们手动遍历 tool_calls 并调用对应 tool 的底层协程函数，
        而非使用 LangGraph ToolNode 的标准流程。
        """
        configurable = config.get("configurable", {})
        dependencies = configurable.get("dependencies")
        user_id = configurable.get("user_id", "_default")

        # 从最后一条 AIMessage 获取 tool_calls
        last_ai_message = None
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                last_ai_message = msg
                break

        if last_ai_message is None:
            return {
                "messages": [],
                "iteration_count": state.get("iteration_count", 0) + 1,
            }

        # 构建 tool 名称 → tool 实例的映射
        tools_by_name = {t.name: t for t in self.tools}

        tool_messages = []
        for tc in last_ai_message.tool_calls:
            tool_name = tc["name"]
            tool_args = dict(tc["args"])

            tool = tools_by_name.get(tool_name)
            if tool is None:
                tool_messages.append(
                    ToolMessage(
                        content=f"未知工具: {tool_name}",
                        tool_call_id=tc["id"],
                    )
                )
                continue

            try:
                # 注入 keyword-only 参数
                kwargs = {**tool_args}
                if dependencies is not None:
                    kwargs["dependencies"] = dependencies
                kwargs["user_id"] = user_id

                # 调用底层协程函数
                result = await tool.coroutine(**kwargs)
                content = (
                    json.dumps(result, ensure_ascii=False)
                    if isinstance(result, dict)
                    else str(result)
                )
                tool_messages.append(
                    ToolMessage(content=content, tool_call_id=tc["id"])
                )
            except Exception as e:
                logger.error(
                    "ReAct Agent tool '%s' 执行异常: %s", tool_name, e, exc_info=True
                )
                tool_messages.append(
                    ToolMessage(
                        content=f"工具执行失败: {str(e)}",
                        tool_call_id=tc["id"],
                    )
                )

        # 递增迭代计数
        iteration_count = state.get("iteration_count", 0) + 1

        return {
            "messages": tool_messages,
            "iteration_count": iteration_count,
        }

    def _route_after_agent(
        self, state: ReActAgentState
    ) -> str:
        """条件边：Agent 节点后的路由判断。

        Returns:
            ROUTE_TOOLS: 执行 tool 调用
            ROUTE_END: 结束
        """
        iteration_count = state.get("iteration_count", 0)

        # 循环上限检查
        if iteration_count >= self.max_iterations:
            return ROUTE_END

        messages = state["messages"]
        if not messages:
            return ROUTE_END

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage):
            return ROUTE_END

        # 无 tool_calls → END
        if not last_message.tool_calls:
            return ROUTE_END

        # 有 tool_calls → 执行 tools
        return ROUTE_TOOLS

    def _route_after_tools(
        self, state: ReActAgentState
    ) -> str:
        """条件边：Tool 节点后的路由判断。

        检查 Agent 最后一次产生的 tool_calls 中是否包含 ask_user。
        如果包含 ask_user → END（中断等待用户回复）
        否则 → 继续循环回 agent 节点

        Returns:
            "agent": 继续循环
            ROUTE_END: 结束（ask_user 中断或循环上限）
        """
        iteration_count = state.get("iteration_count", 0)

        # 循环上限检查
        if iteration_count >= self.max_iterations:
            return ROUTE_END

        # 查找最后一条 AIMessage（包含 tool_calls 的那条）
        messages = state["messages"]
        last_ai_message = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                last_ai_message = msg
                break

        if last_ai_message is None:
            # 没有 tool_calls，结束
            return ROUTE_END

        # 检查是否包含 ask_user
        for tc in last_ai_message.tool_calls:
            if tc["name"] == "ask_user":
                return ROUTE_END

        # 其他 tool_calls → 继续循环
        return "agent"

    async def invoke(
        self,
        message: str,
        thread_id: str = "default",
        *,
        user_id: str = "_default",
        dependencies: Any = None,
        page: str = "",
        page_context: str = "",
        is_new_user: bool = False,
    ) -> dict:
        """调用 ReAct Agent，返回最终状态。

        Args:
            message: 用户输入
            thread_id: 线程 ID（用于对话历史隔离）
            user_id: 用户 ID
            dependencies: Tool 依赖容器
            page: 当前页面名称
            page_context: 页面上下文数据
            is_new_user: 是否新用户

        Returns:
            包含 messages 和 iteration_count 的状态字典
        """
        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "dependencies": dependencies,
                "page": page,
                "page_context": page_context,
                "is_new_user": is_new_user,
            }
        }

        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config,
        )
        return result

    async def stream(
        self,
        message: str,
        thread_id: str = "default",
        *,
        user_id: str = "_default",
        dependencies: Any = None,
        page: str = "",
        page_context: str = "",
        is_new_user: bool = False,
    ):
        """流式调用 ReAct Agent。

        Args:
            message: 用户输入
            thread_id: 线程 ID
            user_id: 用户 ID
            dependencies: Tool 依赖容器
            page: 当前页面名称
            page_context: 页面上下文数据
            is_new_user: 是否新用户

        Yields:
            事件字典，包含节点名和输出数据
        """
        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
                "dependencies": dependencies,
                "page": page,
                "page_context": page_context,
                "is_new_user": is_new_user,
            }
        }

        async for event in self.graph.astream(
            {"messages": [HumanMessage(content=message)]},
            config,
            stream_mode="values",
        ):
            yield event

    async def clear_thread(self, thread_id: str):
        """清空指定线程的对话历史"""
        await self.checkpointer.adelete_thread(thread_id)
