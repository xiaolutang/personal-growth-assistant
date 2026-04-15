"""AI 对话服务 — 页面级上下文感知 + 多轮记忆 + 日知角色"""
import json
import logging
from typing import Optional, AsyncGenerator, List

from pydantic import BaseModel

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


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None  # { page, selected_items, filters, page_data, messages }
    conversation_id: Optional[str] = None


class AIChatService:
    def __init__(self, llm_caller=None):
        self._llm_caller = llm_caller

    def set_llm_caller(self, caller):
        self._llm_caller = caller

    def _build_system_prompt(self, context: Optional[dict] = None) -> str:
        parts = [SYSTEM_PROMPT]
        if context:
            page = context.get("page", "")
            if page:
                parts.append(f"\n用户当前在「{page}」页面。")
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

    async def chat_stream(
        self,
        message: str,
        context: Optional[dict] = None,
        user_id: str = "_default",
    ) -> AsyncGenerator[str, None]:
        if not self._llm_caller:
            yield "AI 助手暂不可用，请稍后再试。"
            return

        system_prompt = self._build_system_prompt(context)
        messages = [{"role": "system", "content": system_prompt}]

        # 注入历史对话（最多 5 轮）
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
