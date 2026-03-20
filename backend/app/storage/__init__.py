"""存储层"""
from .markdown import MarkdownStorage
from .sqlite import SQLiteStorage

# 可选依赖
try:
    from .neo4j_client import Neo4jClient
except ImportError:
    Neo4jClient = None

try:
    from .qdrant_client import QdrantClient
except ImportError:
    QdrantClient = None

# 注意：SyncService 和 init_storage 已移到 app.services.sync_service
# 请使用: from app.services import SyncService, init_storage
# 或: from app.services.sync_service import SyncService, init_storage

__all__ = [
    "MarkdownStorage",
    "SQLiteStorage",
    "Neo4jClient",
    "QdrantClient",
]
