from abc import ABC, abstractmethod
from typing import List

from app.models import Task


class LLMProvider(ABC):
    """LLM 提供商抽象接口"""

    @abstractmethod
    async def parse_tasks(self, text: str) -> List[Task]:
        """
        解析文本，返回结构化任务列表

        Args:
            text: 用户输入的文本，如 "今天学完 FastAPI，明天开始 MCP"

        Returns:
            解析后的任务列表
        """
        pass
