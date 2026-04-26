"""Analytics 埋点服务 — 事件写入（best-effort）"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analytics_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id
ON analytics_events (user_id)
"""


class AnalyticsService:
    """埋点事件写入服务"""

    def __init__(self, sqlite_storage):
        """
        Args:
            sqlite_storage: SQLiteStorage 实例，需提供 get_connection() 方法
        """
        self._sqlite = sqlite_storage

    def ensure_table(self) -> None:
        """启动时创建 analytics_events 表（幂等）"""
        conn = None
        try:
            conn = self._get_conn()
            conn.execute(CREATE_TABLE_SQL)
            conn.execute(CREATE_INDEX_SQL)
            conn.commit()
            logger.info("analytics_events 表就绪")
        except Exception as e:
            logger.error("Failed to create analytics_events table: %s", e)
        finally:
            if conn:
                conn.close()

    def record_event(
        self,
        user_id: str,
        event_type: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        记录一条埋点事件（best-effort，失败静默）。

        Args:
            user_id: 用户 ID
            event_type: 事件类型
            metadata: 可选元数据 dict
        """
        conn = None
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO analytics_events (user_id, event_type, metadata, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    user_id,
                    event_type,
                    json.dumps(metadata) if metadata else None,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        except Exception as e:
            logger.error("Failed to record analytics event: %s", e)
        finally:
            if conn:
                conn.close()

    # ---- internal helpers ----

    def _get_conn(self) -> sqlite3.Connection:
        """获取 SQLite 连接"""
        return self._sqlite.get_connection()
