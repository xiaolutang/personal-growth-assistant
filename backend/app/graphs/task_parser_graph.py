"""基于 LangGraph 的任务解析图"""
import json
from datetime import datetime
from typing import AsyncGenerator, Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, MessagesState, START, END

from app.callers import LLMCaller
from app.core.config import get_settings


SYSTEM_PROMPT_TEMPLATE = """你是一个任务解析助手。用户会输入一段文字，你需要从中提取出任务、灵感、笔记或项目，同时提取知识图谱概念。

当前时间：{current_time}

## 分类规则

- project: 长期项目，可拆解为多个任务
- task: 可执行的具体任务
- note: 学习笔记、知识点
- inbox: 灵感、想法，暂时不确定是否执行

## 状态规则

- waitStart: 待开始
- doing: 进行中
- complete: 已完成

## 输出要求

根据用户输入，提取出对应的条目，输出 JSON 格式，包含 tasks 数组和 response 字段。
每个 task 包含：
- title: 标题（必填）
- content: 内容描述（可选，用于补充说明任务细节）
- category: 分类（project/task/note/inbox）
- status: 状态（默认 waitStart）
- planned_date: 计划日期，格式为 YYYY-MM-DD HH:MM（根据当前时间计算相对日期）
- tags: 标签列表（从内容中提取关键词）
- concepts: 概念列表（技术概念、方法、工具等）
- relations: 概念之间的关系

## 知识图谱提取规则

从内容中识别技术概念和方法，例如：
- 如果提到 "MCP"，识别为概念，并建立与 "LLM应用开发" 的关系
- 如果提到 "RAG"，识别为概念，并建立与 "向量检索"、"Embedding" 的关系

关系类型：
- PART_OF: A 是 B 的一部分（如 MCP 是 LLM应用开发 的一部分）
- RELATED_TO: A 和 B 相关
- PREREQUISITE: 学习 A 需要先了解 B

## 特殊情况处理

如果用户的问题与任务解析无关（如询问名字、普通聊天、修改任务等），请在 response 字段中回答。

注意：
1. 只输出 JSON，不要有其他内容
2. 根据当前时间将相对日期（明天、下周等）转换为具体日期
3. 保持对话历史，理解上下文
4. 尽可能提取技术概念和知识关系

## 输出示例

```json
{{
  "tasks": [
    {{
      "title": "学习 MCP 协议",
      "content": "理解 Host/Client/Server 架构",
      "category": "note",
      "status": "doing",
      "tags": ["MCP", "LLM应用开发"],
      "concepts": [
        {{"name": "MCP", "category": "技术"}},
        {{"name": "Host", "category": "概念"}},
        {{"name": "LLM应用开发", "category": "领域"}}
      ],
      "relations": [
        {{"from": "MCP", "to": "LLM应用开发", "type": "PART_OF"}},
        {{"from": "Host", "to": "MCP", "type": "PART_OF"}}
      ]
    }}
  ],
  "response": "已记录你的 MCP 学习笔记"
}}
```"""


class TaskParserGraph:
    """基于 LangGraph 的任务解析图，支持对话历史"""

    def __init__(self, caller: LLMCaller, checkpointer: SqliteSaver):
        self.caller = caller
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    @classmethod
    def create(cls, caller: LLMCaller, db_path: str | None = None) -> "TaskParserGraph":
        """
        工厂方法：创建 TaskParserGraph 实例

        Args:
            caller: LLM 调用器
            db_path: SQLite 数据库路径，默认从配置读取
        """
        if db_path is None:
            db_path = get_settings().sqlite_checkpoints_path

        # 使用同步的 SqliteSaver
        import sqlite3
        conn = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)
        checkpointer.setup()
        return cls(caller, checkpointer)

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
        dict_messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                dict_messages.append({"role": "user", "content": content})
            elif isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                dict_messages.append({"role": "assistant", "content": content})

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
                    content = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
                    data = json.dumps({"content": content}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

        yield "data: [DONE]\n\n"

    def clear_thread(self, thread_id: str):
        """清空指定线程的对话历史"""
        self.checkpointer.delete_thread(thread_id)
