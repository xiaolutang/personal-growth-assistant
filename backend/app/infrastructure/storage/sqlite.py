"""SQLite 索引层 - 快速元数据查询和全文搜索

入口文件：通过多继承组合各领域 Mixin，对外接口不变。
"""
from app.infrastructure.storage.sqlite_base import SQLiteStorageBase
from app.infrastructure.storage.sqlite_entries import SQLiteEntriesMixin
from app.infrastructure.storage.sqlite_goals import SQLiteGoalsMixin
from app.infrastructure.storage.sqlite_feedback import SQLiteFeedbackMixin
from app.infrastructure.storage.sqlite_links import SQLiteLinksMixin


class SQLiteStorage(
    SQLiteEntriesMixin,
    SQLiteGoalsMixin,
    SQLiteFeedbackMixin,
    SQLiteLinksMixin,
    SQLiteStorageBase,
):
    """SQLite 索引层 - 组合各领域 Mixin，保持原有接口不变"""
    pass
