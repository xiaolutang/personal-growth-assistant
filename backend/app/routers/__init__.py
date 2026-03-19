"""路由模块"""
from .entries import router as entries_router
from .search import router as search_router
from .knowledge import router as knowledge_router
from .review import router as review_router

__all__ = ["entries_router", "search_router", "knowledge_router", "review_router"]
