import os
from typing import List

from openai import OpenAI

from app.models import Task, ParsedTaskInput
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI LLM 提供商实现"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def parse_tasks(self, text: str) -> List[Task]:
        """
        TODO: 实现 OpenAI 结构化输出

        提示：
        1. 构造 system prompt，告诉模型如何解析任务
        2. 使用 response_format 参数约束输出格式
        3. 解析返回结果，转换为 List[Task]

        参考文档：https://platform.openai.com/docs/guides/structured-outputs
        """
        # TODO: 在这里实现 OpenAI 结构化输出
        raise NotImplementedError("请在 openai_provider.py 中实现 OpenAI 结构化输出")
