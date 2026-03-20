"""SQLite 索引层 - 快速元数据查询和全文搜索"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.models import Task, Category, TaskStatus, Priority


class SQLiteStorage:
    """SQLite 索引层"""

    def __init__(self, db_path: str = "./data/index.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _migrate_schema(self, conn: sqlite3.Connection):
        """数据库迁移：添加缺失的列"""
        # 获取现有列
        cursor = conn.execute("PRAGMA table_info(entries)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # 需要确保存在的列
        required_columns = {
            'priority': 'TEXT DEFAULT "medium"',
            'parent_id': 'TEXT',
            'planned_date': 'DATE',
            'time_spent': 'INTEGER',
        }

        # 添加缺失的列
        for col_name, col_def in required_columns.items():
            if col_name not in existing_columns:
                try:
                    conn.execute(f"ALTER TABLE entries ADD COLUMN {col_name} {col_def}")
                    print(f"数据库迁移: 添加列 {col_name}")
                except Exception as e:
                    print(f"迁移失败 {col_name}: {e}")

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        try:
            # 主索引表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT,
                    status TEXT,
                    priority TEXT DEFAULT 'medium',
                    file_path TEXT NOT NULL,
                    created_at DATETIME,
                    updated_at DATETIME,
                    parent_id TEXT,
                    planned_date DATE,
                    time_spent INTEGER,
                    content TEXT
                )
            """)

            # 数据库迁移：添加缺失的列
            self._migrate_schema(conn)

            # 索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_type ON entries(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_updated ON entries(updated_at DESC)")

            # 标签表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
            """)

            # 条目-标签关联
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entry_tags (
                    entry_id TEXT NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (entry_id, tag_id),
                    FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            """)

            # 全文搜索（FTS5）
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                    id,
                    title,
                    content,
                    content='entries',
                    content_rowid='rowid'
                )
            """)

            # FTS 触发器：插入
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
                    INSERT INTO entries_fts(rowid, id, title, content)
                    VALUES (new.rowid, new.id, new.title, new.content);
                END
            """)

            # FTS 触发器：删除
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
                    INSERT INTO entries_fts(entries_fts, rowid, id, title, content)
                    VALUES('delete', old.rowid, old.id, old.title, old.content);
                END
            """)

            # FTS 触发器：更新
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
                    INSERT INTO entries_fts(entries_fts, rowid, id, title, content)
                    VALUES('delete', old.rowid, old.id, old.title, old.content);
                    INSERT INTO entries_fts(rowid, id, title, content)
                    VALUES (new.rowid, new.id, new.title, new.content);
                END
            """)

            conn.commit()
        finally:
            conn.close()

    # === CRUD 操作 ===

    def upsert_entry(self, entry: Task) -> bool:
        """插入或更新条目"""
        conn = self._get_conn()
        try:
            # 插入或更新主表
            conn.execute("""
                INSERT INTO entries (id, type, title, status, priority, file_path, created_at, updated_at,
                                     parent_id, planned_date, time_spent, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    title = excluded.title,
                    status = excluded.status,
                    priority = excluded.priority,
                    file_path = excluded.file_path,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    parent_id = excluded.parent_id,
                    planned_date = excluded.planned_date,
                    time_spent = excluded.time_spent,
                    content = excluded.content
            """, (
                entry.id,
                entry.category.value,
                entry.title,
                entry.status.value,
                entry.priority.value if hasattr(entry, 'priority') and entry.priority else 'medium',
                entry.file_path,
                entry.created_at.isoformat() if entry.created_at else None,
                entry.updated_at.isoformat() if entry.updated_at else None,
                entry.parent_id,
                entry.planned_date.isoformat() if entry.planned_date else None,
                entry.time_spent,
                entry.content,
            ))

            # 更新标签
            self._update_tags(conn, entry.id, entry.tags)

            conn.commit()
            return True
        except Exception as e:
            print(f"SQLite upsert 失败: {e}")
            return False
        finally:
            conn.close()

    def _update_tags(self, conn: sqlite3.Connection, entry_id: str, tags: List[str]):
        """更新条目标签"""
        # 删除旧标签关联
        conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))

        # 插入新标签
        for tag in tags:
            # 确保标签存在
            conn.execute(
                "INSERT OR IGNORE INTO tags (name) VALUES (?)",
                (tag,)
            )
            # 获取标签 ID
            cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,))
            row = cursor.fetchone()
            if row:
                conn.execute(
                    "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                    (entry_id, row["id"])
                )

    def delete_entry(self, entry_id: str) -> bool:
        """删除条目"""
        conn = self._get_conn()
        try:
            # 由于有外键约束，删除 entries 会级联删除 entry_tags
            conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"SQLite delete 失败: {e}")
            return False
        finally:
            conn.close()

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """获取单个条目"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            if not row:
                return None

            entry = dict(row)
            # 获取标签
            entry["tags"] = self._get_entry_tags(conn, entry_id)
            return entry
        finally:
            conn.close()

    def _get_entry_tags(self, conn: sqlite3.Connection, entry_id: str) -> List[str]:
        """获取条目的标签列表"""
        cursor = conn.execute("""
            SELECT t.name FROM tags t
            JOIN entry_tags et ON t.id = et.tag_id
            WHERE et.entry_id = ?
        """, (entry_id,))
        return [row["name"] for row in cursor.fetchall()]

    # === 查询操作 ===

    def _build_filter_query(
        self,
        base_select: str,
        type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> tuple[str, List]:
        """构建筛选查询（复用逻辑）"""
        query = base_select
        params = []
        conditions = []

        if tags:
            placeholders = ",".join("?" * len(tags))
            query += f"""
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name IN ({placeholders})
            """
            params.extend(tags)

        if type:
            conditions.append("e.type = ?")
            params.append(type)

        if status:
            conditions.append("e.status = ?")
            params.append(status)

        if parent_id:
            conditions.append("e.parent_id = ?")
            params.append(parent_id)

        # 时间范围筛选（基于 created_at）
        # created_at 是 ISO 格式时间戳如 "2026-03-19T10:47:22"
        # start_date/end_date 是日期格式如 "2026-03-19"
        if start_date:
            # >= start_date 00:00:00
            conditions.append("e.created_at >= ?")
            params.append(start_date)

        if end_date:
            # <= end_date 23:59:59 (使用日期前缀匹配)
            conditions.append("e.created_at < ?")
            # 下一天的开始 = 当前 end_date + 1 天
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            next_day = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            params.append(next_day)

        if conditions:
            if tags:
                query += " AND " + " AND ".join(conditions)
            else:
                query += " WHERE " + " AND ".join(conditions)

        return query, params

    def list_entries(
        self,
        type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """列出条目（支持筛选）"""
        conn = self._get_conn()
        try:
            query, params = self._build_filter_query(
                "SELECT DISTINCT e.* FROM entries e", type, status, tags, parent_id, start_date, end_date
            )
            query += " ORDER BY e.updated_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            entries = []
            entry_ids = []

            for row in cursor.fetchall():
                entry = dict(row)
                entry["tags"] = []  # 先设为空，后面批量填充
                entries.append(entry)
                entry_ids.append(entry["id"])

            # 批量获取所有标签（避免 N+1）
            if entry_ids:
                placeholders = ",".join("?" * len(entry_ids))
                tag_cursor = conn.execute(f"""
                    SELECT et.entry_id, t.name FROM entry_tags et
                    JOIN tags t ON et.tag_id = t.id
                    WHERE et.entry_id IN ({placeholders})
                """, entry_ids)

                tags_map: Dict[str, List[str]] = {}
                for row in tag_cursor.fetchall():
                    entry_id = row["entry_id"]
                    if entry_id not in tags_map:
                        tags_map[entry_id] = []
                    tags_map[entry_id].append(row["name"])

                for entry in entries:
                    entry["tags"] = tags_map.get(entry["id"], [])

            return entries
        finally:
            conn.close()

    def count_entries(
        self,
        type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """统计条目数量"""
        conn = self._get_conn()
        try:
            query, params = self._build_filter_query(
                "SELECT COUNT(DISTINCT e.id) as cnt FROM entries e", type, status, tags, parent_id, start_date, end_date
            )
            cursor = conn.execute(query, params)
            return cursor.fetchone()["cnt"]
        finally:
            conn.close()

    # === 全文搜索 ===

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """全文搜索（支持中英文）"""
        conn = self._get_conn()
        try:
            entries = []

            # 1. 尝试 FTS5 搜索（对英文更高效）
            try:
                cursor = conn.execute("""
                    SELECT e.id, e.type, e.title, e.status, e.file_path,
                           e.created_at, e.updated_at, e.parent_id
                    FROM entries e
                    JOIN entries_fts fts ON e.id = fts.id
                    WHERE entries_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit))

                for row in cursor.fetchall():
                    entry = dict(row)
                    entry["tags"] = self._get_entry_tags(conn, entry["id"])
                    entries.append(entry)
            except Exception:
                pass  # FTS5 失败则回退到 LIKE

            # 2. 如果 FTS5 没有结果，使用 LIKE（支持中文）
            if not entries:
                like_pattern = f"%{query}%"
                cursor = conn.execute("""
                    SELECT id, type, title, status, file_path,
                           created_at, updated_at, parent_id
                    FROM entries
                    WHERE title LIKE ? OR content LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (like_pattern, like_pattern, limit))

                for row in cursor.fetchall():
                    entry = dict(row)
                    entry["tags"] = self._get_entry_tags(conn, entry["id"])
                    entries.append(entry)

            return entries
        finally:
            conn.close()

    # === 同步操作 ===

    def sync_from_markdown(self, markdown_storage) -> int:
        """从 Markdown 存储同步所有条目"""
        entries = markdown_storage.scan_all()
        count = 0
        for entry in entries:
            if self.upsert_entry(entry):
                count += 1
        return count

    def clear_all(self) -> bool:
        """清空所有数据"""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM entry_tags")
            conn.execute("DELETE FROM entries")
            conn.execute("DELETE FROM tags")
            conn.commit()
            return True
        except Exception as e:
            print(f"清空失败: {e}")
            return False
        finally:
            conn.close()
