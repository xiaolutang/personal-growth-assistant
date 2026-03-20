"""向后兼容层 - callers 模块已迁移到 infrastructure/llm

请使用: from app.infrastructure.llm import APICaller, MockCaller
"""
import warnings

warnings.warn(
    "app.callers 模块已弃用，请使用 app.infrastructure.llm",
    DeprecationWarning,
    stacklevel=2
)

from app.infrastructure.llm import APICaller, MockCaller, LLMCaller

__all__ = ["APICaller", "MockCaller", "LLMCaller"]
