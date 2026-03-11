from typing import List

from app.models import Task
from app.providers import LLMProvider


class TaskParser:
    """任务解析服务"""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def parse(self, text: str) -> List[Task]:
        """
        解析用户输入文本，返回结构化任务列表

        Args:
            text: 用户输入文本

        Returns:
            解析后的任务列表
        """
        return await self.provider.parse_tasks(text)
