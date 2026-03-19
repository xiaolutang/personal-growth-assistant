"""共享依赖"""
from typing import TYPE_CHECKING
from fastapi import HTTPException

if TYPE_CHECKING:
    from app.storage.sync import SyncService
    from app.services.entry_service import EntryService

# 全局存储服务（由 main.py 初始化）
storage: "SyncService" = None

# 全局服务实例
_entry_service: "EntryService" = None


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
