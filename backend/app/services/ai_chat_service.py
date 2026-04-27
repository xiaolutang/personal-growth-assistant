"""AI 对话服务 — 页面级上下文感知 + 多轮记忆 + 日知角色 + LangGraph 持久化"""
import json
import logging
from datetime import datetime
from typing import Optional, AsyncGenerator, List

from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel

from app.graphs.task_parser_graph import (
    MAX_MESSAGES,
    MAX_TOKENS,
    truncate_messages,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是「日知」，一位博学但不卖弄的朋友。你的风格平实、准确，偶尔温厚。

角色原则：
- 回答简洁有用，不说废话，不卖弄专业术语
- 遇到不确定的内容，坦诚说"我不确定"
- 语气像朋友聊天，不是老师讲课
- 适时鼓励用户，但不说空洞的鸡汤

三种交互模式（根据用户意图自然切换）：
1. 教练模式：用户在寻求建议或规划时，给出可执行的具体步骤
2. 助手模式：用户需要信息或操作帮助时，直接给出答案或指引
3. 镜子模式：用户在反思或倾诉时，帮助用户看清自己的想法，不急于给建议"""

PAGE_ROLE_PROMPTS = {
    "home": "\n当前你是「晨报助手」角色。用户在首页查看今日概览。\n"
    "你的职责：帮助用户规划今日任务优先级、分析学习节奏、推荐聚焦事项、鼓励行动。",
    "explore": "\n当前你是「搜索助手」角色。用户在探索页浏览和搜索内容。\n"
    "你的职责：帮助用户找到想要的内容、理解搜索意图、联想扩展知识网络、建议筛选方式。",
    "review": "\n当前你是「分析助手」角色。用户在回顾页查看统计报告。\n"
    "你的职责：解读统计趋势和环比变化、发现学习模式、比较本期与上期差异、给出改进建议。",
    "entry_detail": "\n当前你是「编辑助手」角色。用户在查看某条内容的详情。\n"
    "你的职责：帮助整理和优化内容、拆解大任务为子任务、生成摘要总结、关联相关知识。",
}

ONBOARDING_PROMPT = (
    "这是新用户首次使用，请主动做简短自我介绍："
    "「你好！我是日知，你的个人成长助手。」"
    "然后给出示例引导："
    "「你可以试试：记灵感（如'想到一个有趣的想法'）、"
    "做任务（如'今天要完成阅读'）、"
    "记笔记（如'读了《xxx》的体会'）。"
    "随意聊就好！」"
)


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None  # { page, selected_items, filters, page_data, messages }
    conversation_id: Optional[str] = None


class AIChatService:
    def __init__(self, llm_caller=None, checkpointer=None):
        self._llm_caller = llm_caller
        self._checkpointer = checkpointer

    def set_llm_caller(self, caller):
        self._llm_caller = caller

    def set_checkpointer(self, checkpointer):
        """注入 LangGraph checkpointer（来自 TaskParserGraph）"""
        self._checkpointer = checkpointer

    def _build_system_prompt(self, context: Optional[dict] = None) -> str:
        parts = [SYSTEM_PROMPT]
        if context:
            page = context.get("page", "")
            if page:
                # 注入页面专属角色指令
                role_prompt = PAGE_ROLE_PROMPTS.get(page)
                if role_prompt:
                    parts.append(role_prompt)
                else:
                    parts.append(f"\n用户当前在「{page}」页面。")
            # 新用户 onboarding 引导
            if context.get("is_new_user"):
                parts.append(ONBOARDING_PROMPT)
            page_data = context.get("page_data", {})
            if page_data:
                data_lines = [f"  - {k}: {v}" for k, v in page_data.items()]
                parts.append("页面数据：\n" + "\n".join(data_lines))
            selected = context.get("selected_items", [])
            if selected:
                parts.append(f"用户选中了以下内容：{json.dumps(selected, ensure_ascii=False)}")
            filters = context.get("filters", {})
            if filters:
                parts.append(f"当前筛选条件：{json.dumps(filters, ensure_ascii=False)}")
        return "\n".join(parts)

    async def load_history(self, thread_id: str, limit: int = 20) -> list[HistoryMessage]:
        """从 LangGraph checkpointer 加载历史消息。

        Args:
            thread_id: 会话线程 ID（格式 page:{page_name}:{user_id}）
            limit: 最多返回的消息条数

        Returns:
            历史消息列表（按时间正序）
        """
        if not self._checkpointer:
            return []

        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = await self._checkpointer.aget_tuple(config)

            if not state or not state.checkpoint:
                return []

            channel_values = state.checkpoint.get("channel_values", {})
            msgs = channel_values.get("messages", [])

            # 取最近 limit 条
            msgs = msgs[-limit:]

            result = []
            for msg in msgs:
                if isinstance(msg, HumanMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    result.append(HistoryMessage(role="user", content=content))
                elif isinstance(msg, AIMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    result.append(HistoryMessage(role="assistant", content=content))
                elif isinstance(msg, dict):
                    role = "user" if msg.get("type") == "human" else "assistant"
                    result.append(HistoryMessage(role=role, content=msg.get("content", "")))

            return result
        except Exception as e:
            logger.debug("加载历史消息失败 thread_id=%s: %s", thread_id, e)
            return []

    async def chat_stream(
        self,
        message: str,
        context: Optional[dict] = None,
        user_id: str = "_default",
        thread_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """流式聊天。

        如果提供 thread_id，则从 LangGraph checkpointer 加载历史消息作为上下文，
        实现持久化。否则使用 context.messages 前端传入的方式（向后兼容）。
        """
        if not self._llm_caller:
            yield "AI 助手暂不可用，请稍后再试。"
            return

        system_prompt = self._build_system_prompt(context)
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if thread_id and self._checkpointer:
            # 持久化模式：从 checkpointer 加载历史
            history_msgs = await self.load_history(thread_id)
            # 截断：复用 task_parser_graph 的统一截断函数
            history_msgs = truncate_messages(
                history_msgs, max_messages=MAX_MESSAGES, max_tokens=MAX_TOKENS,
            )
            for m in history_msgs:
                messages.append({"role": m.role, "content": m.content})
        else:
            # 向后兼容：使用前端传入的历史消息
            if context and context.get("messages"):
                history = context["messages"][-10:]  # 5 轮 = 10 条消息
                for msg in history:
                    if isinstance(msg, dict) and msg.get("role") in ("user", "assistant"):
                        messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": message})

        try:
            async for token in self._llm_caller.stream(messages):
                yield token
        except Exception as e:
            logger.error(f"AI chat stream error: {e}")
            yield f"\n[错误] AI 响应失败: {str(e)}"
