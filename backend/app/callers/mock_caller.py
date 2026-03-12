from typing import Any, AsyncGenerator

from .base import LLMCaller


class MockCaller(LLMCaller):
    """
    测试用的 Mock 调用器

    不调用真实 API，返回预设的固定数据
    用于单元测试，不消耗 API 配额
    """

    def __init__(self, response: str = '{"tasks": []}'):
        """
        初始化 Mock 调用器

        Args:
            response: 预设的返回数据
        """
        self.response = response

    async def call(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """返回预设的响应数据"""
        return self.response

    async def stream(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """模拟流式返回，一次性返回完整响应"""
        yield self.response
