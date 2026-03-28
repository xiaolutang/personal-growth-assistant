"""共享依赖"""
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from app.services.sync_service import SyncService
    from app.services.entry_service import EntryService
    from app.services.intent_service import IntentService
    from app.services.review_service import ReviewService
    from app.services.knowledge_service import KnowledgeService

# 全局存储服务（由 main.py 初始化）
storage: "SyncService" = None

# 全局服务实例
_entry_service: "EntryService" = None
_intent_service: "IntentService" = None
_review_service: "ReviewService" = None
_knowledge_service: "KnowledgeService" = None


def get_storage() -> "SyncService":
    """获取存储服务的依赖函数"""
    global storage
    if storage is None:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    return storage


def get_entry_service() -> "EntryService":
    """获取条目服务的依赖函数"""
    global _entry_service, storage
    if _entry_service is None:
        if storage is None:
            raise HTTPException(status_code=503, detail="存储服务未初始化")
        from app.services.entry_service import EntryService
        _entry_service = EntryService(storage)
    return _entry_service


def get_intent_service() -> "IntentService":
    """获取意图识别服务的依赖函数"""
    global _intent_service, storage
    if _intent_service is None:
        from app.services.intent_service import IntentService
        _intent_service = IntentService()
        # 如果有 LLM caller，设置它
        if storage and hasattr(storage, "llm_caller") and storage.llm_caller:
            _intent_service.set_llm_caller(storage.llm_caller)
    return _intent_service


def get_review_service() -> "ReviewService":
    """获取回顾统计服务的依赖函数"""
    global _review_service, storage
    if storage is None:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    if _review_service is None:
        from app.services.review_service import ReviewService
        _review_service = ReviewService()
    # 每次都更新 sqlite 存储（解决测试环境的问题）
    if storage.sqlite:
        _review_service.set_sqlite_storage(storage.sqlite)
    return _review_service


def get_knowledge_service() -> "KnowledgeService":
    """获取知识图谱服务的依赖函数"""
    global _knowledge_service, storage
    if storage is None:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    if _knowledge_service is None:
        from app.services.knowledge_service import KnowledgeService
        _knowledge_service = KnowledgeService()
    # 每次都更新存储（解决测试环境的问题）
    if storage.neo4j:
        _knowledge_service.set_neo4j_client(storage.neo4j)
    if storage.sqlite:
        _knowledge_service.set_sqlite_storage(storage.sqlite)
    return _knowledge_service


def reset_all_services():
    """重置所有服务缓存（用于测试）"""
    global _entry_service, _intent_service, _review_service, _knowledge_service
    _entry_service = None
    _intent_service = None
    _review_service = None
    _knowledge_service = None


# 向后兼容
reset_entry_service = reset_all_services
