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
                user_id TEXT NOT NULL DEFAULT '_default',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # 迁移：为已有表添加 user_id 列
        existing = {row[1] for row in cursor.execute("PRAGMA table_info(session_meta)").fetchall()}
        if "user_id" not in existing:
            cursor.execute("ALTER TABLE session_meta ADD COLUMN user_id TEXT NOT NULL DEFAULT '_default'")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_meta_user_id ON session_meta(user_id)")
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

    def get_all_sessions(self, user_id: str = "_default") -> list[SessionMeta]:
        """获取指定用户的会话，按更新时间倒序"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at
                FROM session_meta
                WHERE user_id = ?
                ORDER BY updated_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [self._row_to_meta(row) for row in rows]

    def get_session(self, session_id: str, user_id: str = "_default") -> Optional[SessionMeta]:
        """获取指定会话"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, created_at, updated_at
                FROM session_meta
                WHERE id = ? AND user_id = ?
            """, (session_id, user_id))
            row = cursor.fetchone()
            return self._row_to_meta(row) if row else None

    def create_session(self, session_id: str, title: str = "新对话", user_id: str = "_default") -> SessionMeta:
        """创建新会话元数据"""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO session_meta (id, title, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, title, user_id, now.isoformat(), now.isoformat()))
            conn.commit()
        return SessionMeta(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
        )

    def update_title(self, session_id: str, title: str, user_id: str = "_default") -> bool:
        """更新会话标题"""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE session_meta
                SET title = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (title, now.isoformat(), session_id, user_id))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def touch_session(self, session_id: str, user_id: str = "_default") -> bool:
        """更新会话的 updated_at 时间戳"""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE session_meta
                SET updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (now.isoformat(), session_id, user_id))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def delete_session(self, session_id: str, user_id: str = "_default") -> bool:
        """删除会话元数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM session_meta WHERE id = ? AND user_id = ?", (session_id, user_id))
            affected = cursor.rowcount
            conn.commit()
            return affected > 0

    def session_exists(self, session_id: str, user_id: str = "_default") -> bool:
        """检查会话是否存在"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM session_meta WHERE id = ? AND user_id = ?", (session_id, user_id))
            return cursor.fetchone() is not None

    def claim_default_sessions(self, target_user_id: str) -> int:
        """将 `_default` 用户下的会话元数据认领到目标用户"""
        if not target_user_id or target_user_id == "_default":
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE session_meta SET user_id = ? WHERE user_id = ?",
                (target_user_id, "_default"),
            )
            affected = cursor.rowcount
            conn.commit()
            return affected
