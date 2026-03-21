"""会话元数据存储 - 管理对话会话的标题等元信息"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class SessionMeta:
    """会话元数据"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class SessionMetaStore:
    """
    会话元数据存储（SQLite）

    由于 LangGraph checkpointer 只存储消息，不存储标题等元数据，
    需要单独存储会话元信息。
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        # 确保目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_meta (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '新对话',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def _row_to_meta(self, row: tuple) -> SessionMeta:
        """将数据库行转换为 SessionMeta"""
        return SessionMeta(
            id=row[0],
            title=row[1],
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
        )

    def get_all_sessions(self) -> list[SessionMeta]:
        """获取所有会话，按更新时间倒序"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at
                FROM session_meta
                ORDER BY updated_at DESC
            """)
            rows = cursor.fetchall()
            return [self._row_to_meta(row) for row in rows]

    def get_session(self, session_id: str) -> Optional[SessionMeta]:
        """获取指定会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at
                FROM session_meta
                WHERE id = ?
            """, (session_id,))
            row = cursor.fetchone()
            return self._row_to_meta(row) if row else None

    def create_session(self, session_id: str, title: str = "新对话") -> SessionMeta:
        """创建新会话元数据"""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO session_meta (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (session_id, title, now.isoformat(), now.isoformat()))
            conn.commit()
        return SessionMeta(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

    def update_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE session_meta
                SET title = ?, updated_at = ?
                WHERE id = ?
            """, (title, now.isoformat(), session_id))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def touch_session(self, session_id: str) -> bool:
        """更新会话的 updated_at 时间戳"""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE session_meta
                SET updated_at = ?
                WHERE id = ?
            """, (now.isoformat(), session_id))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def delete_session(self, session_id: str) -> bool:
        """删除会话元数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM session_meta WHERE id = ?", (session_id,))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM session_meta WHERE id = ?", (session_id,))
            return cursor.fetchone() is not None
