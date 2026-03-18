"""共享依赖"""
from typing import TYPE_CHECKING
from fastapi import HTTPException

if TYPE_CHECKING:
    from app.storage.sync import SyncService

# 全局存储服务（由 main.py 初始化）
storage: "SyncService" = None


def get_storage() -> "SyncService":
    """获取存储服务的依赖函数"""
    global storage
    if storage is None:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    return storage
