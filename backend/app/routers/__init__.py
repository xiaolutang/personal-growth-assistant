"""路由模块"""
from .entries import router as entries_router
from .search import router as search_router
from .knowledge import router as knowledge_router
from .review import router as review_router
from .parse import router as parse_router
from .playground import router as playground_router
from .feedback import router as feedback_router
from .auth import router as auth_router
from .sessions import router as sessions_router
from .notifications import router as notifications_router
from .goals import router as goals_router
from .analytics import router as analytics_router

__all__ = [
    "entries_router",
    "search_router",
    "knowledge_router",
    "review_router",
    "parse_router",
    "playground_router",
    "feedback_router",
    "auth_router",
    "sessions_router",
    "notifications_router",
    "goals_router",
    "analytics_router",
]
