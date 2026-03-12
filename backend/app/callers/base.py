from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class LLMCaller(ABC):
    """LLM 调用抽象接口"""

    @abstractmethod
    async def call(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """
        调用 LLM，返回原始响应字符串

        Args:
            messages: 消息列表，如 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            response_format: 响应格式约束（可选，如 {"type": "json_object"}）

        Returns:
            LLM 返回的原始字符串
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM，逐个返回 token

        Args:
            messages: 消息列表
            response_format: 响应格式约束

        Yields:
            每个 token 的内容
        """
        pass
