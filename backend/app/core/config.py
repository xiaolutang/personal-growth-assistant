"""应用配置 - 使用 Pydantic Settings 统一管理"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（配置文件所在目录的父目录）
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR_DEFAULT = str(PROJECT_ROOT / "data")


class Settings(BaseSettings):
    """应用配置 - 所有配置从环境变量读取"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用配置
    APP_NAME: str = "Personal Growth Assistant"
    APP_VERSION: str = "0.3.0"
    DEBUG: bool = False

    # 数据目录（默认使用项目根目录的 data/）
    DATA_DIR: str = DATA_DIR_DEFAULT

    # LLM 配置
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""

    # Embedding 配置
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # Neo4j 配置（可选）
    NEO4J_URI: Optional[str] = None
    NEO4J_USERNAME: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None

    # Qdrant 配置（可选）
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None

    # SQLite 配置
    SQLITE_PATH: Optional[str] = None
    SQLITE_CHECKPOINTS_PATH: Optional[str] = None  # LangGraph 对话历史存储，默认 {DATA_DIR}/checkpoints.db

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_SERVICE_URL: str = "http://localhost:8001"

    # LangSmith 可观测性配置（可选）
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_TRACING: bool = False
    LANGSMITH_PROJECT: str = "personal-growth-assistant"

    # CORS 配置
    ALLOWED_ORIGINS_ENV: str = ""  # 逗号分隔的域名列表，如 "http://localhost:3000,http://localhost"

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        """获取允许的 CORS 源列表"""
        if not self.ALLOWED_ORIGINS_ENV:
            # 默认只允许本地开发
            return ["http://localhost:3000", "http://localhost", "http://localhost:80"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_ENV.split(",") if origin.strip()]

    def validate_llm(self) -> bool:
        """验证 LLM 配置是否完整"""
        missing = []
        if not self.LLM_API_KEY:
            missing.append("LLM_API_KEY")
        if not self.LLM_BASE_URL:
            missing.append("LLM_BASE_URL")
        if not self.LLM_MODEL:
            missing.append("LLM_MODEL")

        if missing:
            raise ValueError(f"以下配置未设置: {', '.join(missing)}，请检查 .env 文件")
        return True

    @property
    def sqlite_db_path(self) -> str:
        """获取 SQLite 数据库路径"""
        return self.SQLITE_PATH or f"{self.DATA_DIR}/index.db"

    @property
    def sqlite_checkpoints_path(self) -> str:
        """获取 LangGraph checkpoints 存储路径"""
        return self.SQLITE_CHECKPOINTS_PATH or f"{self.DATA_DIR}/checkpoints.db"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
