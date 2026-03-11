"""应用配置"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env 文件
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class LLMConfig:
    """LLM 配置 - 所有配置必须从 .env 读取"""

    API_KEY: str = os.getenv("LLM_API_KEY", "")
    BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    MODEL: str = os.getenv("LLM_MODEL", "")

    @classmethod
    def validate(cls) -> bool:
        """验证配置是否完整"""
        missing = []
        if not cls.API_KEY:
            missing.append("LLM_API_KEY")
        if not cls.BASE_URL:
            missing.append("LLM_BASE_URL")
        if not cls.MODEL:
            missing.append("LLM_MODEL")

        if missing:
            raise ValueError(f"以下配置未设置: {', '.join(missing)}，请检查 .env 文件")
        return True
