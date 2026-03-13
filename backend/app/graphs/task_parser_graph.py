"""基于 LangGraph 的任务解析图"""
import json
from datetime import datetime
from typing import AsyncGenerator, Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END

from app.callers import LLMCaller


SYSTEM_PROMPT_TEMPLATE = """你是一个任务解析助手。用户会输入一段文字，你需要从中提取出任务、灵感、笔记或项目。

当前时间：{current_time}

## 分类规则

- task: 可执行的具体任务
- inbox: 灵感、想法，暂时不确定是否执行
- note: 学习笔记、知识点
- project: 长期项目，可拆解为多个任务

## 状态规则

- waitStart: 待开始
- doing: 进行中
- complete: 已完成

## 输出要求

根据用户输入，提取出对应的条目，输出 JSON 格式，包含 tasks 数组和 response 字段。
每个 task 包含：
- name: 名称（必填）
- description: 描述（可选，用于补充说明任务细节）
- category: 分类（task/inbox/note/project）
- status: 状态（默认 waitStart）
- planned_date: 计划日期，格式为 YYYY-MM-DD HH:MM（根据当前时间计算相对日期，如"明天"转换为具体日期）

## 特殊情况处理

如果用户的问题与任务解析无关（如询问名字、普通聊天、修改任务等），请在 response 字段中回答：
- 用户问"我叫什么" → response: "根据我们的对话历史，你叫张三"
- 用户说"把刚才的任务改成4点" → response: "好的，已将任务时间修改为下午4点"， 同时更新 tasks 数组
- 用户说"你好" → response: "你好！有什么我可以帮助你的吗？"

注意：
1. 只输出 JSON，不要有其他内容
2. 根据当前时间将相对日期（明天、下周等）转换为具体日期
3. 保持对话历史，理解上下文"""


class TaskParserGraph:
    """基于 LangGraph 的任务解析图，支持对话历史"""

    def __init__(self, caller: LLMCaller):
        self.caller = caller
        self.checkpointer = InMemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        """构建 LangGraph 图"""
        builder = StateGraph(MessagesState)
        builder.add_node("parse", self._parse_node)
        builder.add_edge(START, "parse")
        builder.add_edge("parse", END)
        return builder.compile(checkpointer=self.checkpointer)

    async def _parse_node(self, state: MessagesState):
        """解析节点：调用 LLM 解析任务"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(current_time=current_time)

        # 将 LangChain 消息对象转换为字典格式
        dict_messages = [{"role": "system", "content": system_prompt}]
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                dict_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                dict_messages.append({"role": "assistant", "content": msg.content})

        # 调用 LLM
        response_format = {"type": "json_object"}
        response = await self.caller.call(dict_messages, response_format)

        return {"messages": [AIMessage(content=response)]}

    async def stream_parse(
        self, text: str, thread_id: str = "default"
    ) -> AsyncGenerator[str, None]:
        """
        流式解析，返回 SSE 格式

        Args:
            text: 用户输入
            thread_id: 线程 ID（用于对话历史隔离）

        Yields:
            SSE 格式数据
        """
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}  # type: ignore[typeddict-item]

        # 流式调用图
        async for event in self.graph.astream(
            {"messages": [HumanMessage(content=text)]},
            config,
            stream_mode="values",
        ):
            if "messages" in event:
                last_message = event["messages"][-1]
                if isinstance(last_message, AIMessage):
                    # 返回 SSE 格式
                    data = json.dumps({"content": last_message.content}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

        yield "data: [DONE]\n\n"

    def clear_thread(self, thread_id: str):
        """清空指定线程的对话历史"""
        self.checkpointer.delete_thread(thread_id)
