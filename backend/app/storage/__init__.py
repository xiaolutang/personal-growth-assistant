"""向后兼容层 - storage 模块已迁移到 infrastructure/storage

请使用: from app.infrastructure.storage import MarkdownStorage, SQLiteStorage, Neo4jClient, QdrantClient
注意: SyncService 和 init_storage 已移到 app.services.sync_service
"""
import warnings

warnings.warn(
    "app.storage 模块已弃用，请使用 app.infrastructure.storage",
    DeprecationWarning,
    stacklevel=2
)

from app.infrastructure.storage import (
    MarkdownStorage,
    SQLiteStorage,
    Neo4jClient,
    QdrantClient,
)

__all__ = [
    "MarkdownStorage",
    "SQLiteStorage",
    "Neo4jClient",
    "QdrantClient",
]
