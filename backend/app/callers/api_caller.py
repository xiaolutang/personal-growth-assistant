from typing import Any

from openai import OpenAI

from app.config import LLMConfig

from .base import LLMCaller


class APICaller(LLMCaller):
    """
    通过 OpenAI 兼容 API 调用 LLM

    支持所有兼容 OpenAI API 的模型：
    - 通义千问（DashScope）
    - DeepSeek
    - Moonshot
    - OpenAI
    - GLM（智谱）
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        """
        初始化 API 调用器

        Args:
            api_key: API 密钥，默认从配置读取
            base_url: API 地址，默认从配置读取
            model: 模型名称，默认从配置读取
        """
        self.api_key = api_key or LLMConfig.API_KEY
        self.base_url = base_url or LLMConfig.BASE_URL
        self.model = model or LLMConfig.MODEL

        if not self.api_key:
            LLMConfig.validate()  # 抛出友好的错误信息

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def call(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """
        调用 LLM API

        Args:
            messages: 消息列表
            response_format: 响应格式约束（如 {"type": "json_object"}）

        Returns:
            LLM 返回的文本
        """
        params = {
            "model": self.model,
            "messages": messages,
        }
        if response_format:
            params["response_format"] = response_format

        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content or ""
