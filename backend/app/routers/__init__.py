"""路由模块"""
from .entries import router as entries_router
from .search import router as search_router
from .knowledge import router as knowledge_router
from .review import router as review_router
from .intent import router as intent_router
from .parse import router as parse_router
from .playground import router as playground_router
from .feedback import router as feedback_router

__all__ = [
    "entries_router",
    "search_router",
    "knowledge_router",
    "review_router",
    "intent_router",
    "parse_router",
    "playground_router",
    "feedback_router",
]
