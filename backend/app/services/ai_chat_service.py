"""AI 对话服务 — 页面级上下文感知"""
import json
import logging
from typing import Optional, AsyncGenerator

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    message: str
    context: Optional[dict] = None  # { page, selected_items, filters }
    conversation_id: Optional[str] = None


class AIChatService:
    def __init__(self, llm_caller=None):
        self._llm_caller = llm_caller

    def set_llm_caller(self, caller):
        self._llm_caller = caller

    def _build_system_prompt(self, context: Optional[dict] = None) -> str:
        base = "你是个人成长助手「日知」，帮助用户管理任务、记录灵感、追踪学习进度。"
        if context:
            page = context.get("page", "")
            parts = [base]
            if page:
                parts.append(f"用户当前在「{page}」页面。")
            selected = context.get("selected_items", [])
            if selected:
                parts.append(f"用户选中了以下内容：{json.dumps(selected, ensure_ascii=False)}")
            filters = context.get("filters", {})
            if filters:
                parts.append(f"当前筛选条件：{json.dumps(filters, ensure_ascii=False)}")
            return "\n".join(parts)
        return base

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
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        try:
            async for token in self._llm_caller.stream(messages):
                yield token
        except Exception as e:
            logger.error(f"AI chat stream error: {e}")
            yield f"\n[错误] AI 响应失败: {str(e)}"
