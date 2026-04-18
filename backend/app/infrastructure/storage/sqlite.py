"""SQLite 索引层 - 快速元数据查询和全文搜索"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.models import Task, Category, TaskStatus, Priority

# update_goal 允许更新的字段白名单，防止 SQL 注入
ALLOWED_GOAL_FIELDS = frozenset({
    "title",
    "description",
    "status",
    "target_value",
    "metric_type",
    "start_date",
    "end_date",
    "auto_tags",
    "checklist_items",
})


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
            'user_id': 'TEXT NOT NULL DEFAULT "_default"',
            'ai_summary': 'TEXT',
            'ai_summary_generated_at': 'TEXT',
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user_id ON entries(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user_created ON entries(user_id, created_at)")

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

            # 反馈表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT DEFAULT 'medium',
                    log_service_issue_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)")

            # 通知已读记录表（复合主键保证用户隔离）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    ref_id TEXT,
                    dismissed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, notification_id)
                )
            """)

            # 通知偏好表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    user_id TEXT PRIMARY KEY,
                    overdue_task_enabled INTEGER DEFAULT 1,
                    stale_inbox_enabled INTEGER DEFAULT 1,
                    review_prompt_enabled INTEGER DEFAULT 1
                )
            """)

            # 条目关联表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entry_links (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, source_id, target_id, relation_type)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_links_source ON entry_links(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_links_target ON entry_links(target_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_links_user_id ON entry_links(user_id)")

            # 目标表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    metric_type TEXT NOT NULL,
                    target_value INTEGER NOT NULL,
                    current_value INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    start_date TEXT,
                    end_date TEXT,
                    auto_tags TEXT,
                    checklist_items TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)")

            # 目标-条目关联表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goal_entries (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    entry_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(goal_id, entry_id),
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal_entries_goal_id ON goal_entries(goal_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal_entries_entry_id ON goal_entries(entry_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal_entries_user_id ON goal_entries(user_id)")

            conn.commit()
        finally:
            conn.close()

    # === 查询辅助 ===

    def entry_belongs_to_user(self, entry_id: str, user_id: str) -> bool:
        """检查条目是否属于指定用户（轻量存在性查询）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM entries WHERE id = ? AND user_id = ? LIMIT 1",
                (entry_id, user_id),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def find_entries_by_tag_overlap(
        self, entry_id: str, tags: List[str], limit: int = 10, user_id: str = "_default"
    ) -> List[dict]:
        """通过标签重叠查找相关条目，按重叠数量降序排列"""
        if not tags:
            return []
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(tags))
            rows = conn.execute(f"""
                SELECT e.id, e.title, e.type as category, COUNT(et.tag_id) as overlap_count
                FROM entries e
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name IN ({placeholders})
                  AND e.id != ?
                  AND e.user_id = ?
                GROUP BY e.id
                ORDER BY overlap_count DESC
                LIMIT ?
            """, (*tags, entry_id, user_id, limit)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_entry_owner(self, entry_id: str) -> Optional[str]:
        """获取条目的当前 owner"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT user_id FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            return row["user_id"] if row else None
        finally:
            conn.close()

    # === CRUD 操作 ===

    def upsert_entry(self, entry: Task, user_id: str = "_default") -> bool:
        """插入或更新条目"""
        conn = self._get_conn()
        try:
            # 插入或更新主表
            conn.execute("""
                INSERT INTO entries (id, type, title, status, priority, file_path, created_at, updated_at,
                                     parent_id, planned_date, time_spent, content, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    content = excluded.content,
                    user_id = excluded.user_id
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
                user_id,
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

    def delete_entry(self, entry_id: str, user_id: str = "_default") -> bool:
        """删除条目"""
        conn = self._get_conn()
        try:
            # 由于有外键约束，删除 entries 会级联删除 entry_tags
            conn.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"SQLite delete 失败: {e}")
            return False
        finally:
            conn.close()

    # === 条目关联操作 ===

    def create_entry_link(
        self, user_id: str, source_id: str, target_id: str, relation_type: str
    ) -> dict[str, Any]:
        """创建条目关联（单向），返回新记录。调用方负责在一个事务中创建双向记录。"""
        import uuid as _uuid
        link_id = _uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO entry_links (id, user_id, source_id, target_id, relation_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (link_id, user_id, source_id, target_id, relation_type, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM entry_links WHERE id = ?", (link_id,)
            ).fetchone()
            return dict(row)
        finally:
            conn.close()

    def create_entry_links_pair(
        self, user_id: str, source_id: str, target_id: str, relation_type: str
    ) -> list[dict[str, Any]]:
        """创建双向条目关联（同一事务），返回两条记录。"""
        import uuid as _uuid
        now = datetime.utcnow().isoformat()
        link_id_fwd = _uuid.uuid4().hex
        link_id_rev = _uuid.uuid4().hex
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO entry_links (id, user_id, source_id, target_id, relation_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (link_id_fwd, user_id, source_id, target_id, relation_type, now),
            )
            conn.execute(
                """INSERT INTO entry_links (id, user_id, source_id, target_id, relation_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (link_id_rev, user_id, target_id, source_id, relation_type, now),
            )
            conn.commit()
            row_fwd = conn.execute("SELECT * FROM entry_links WHERE id = ?", (link_id_fwd,)).fetchone()
            row_rev = conn.execute("SELECT * FROM entry_links WHERE id = ?", (link_id_rev,)).fetchone()
            return [dict(row_fwd), dict(row_rev)]
        finally:
            conn.close()

    def get_entry_link(self, link_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """获取单条关联记录（含用户隔离）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM entry_links WHERE id = ? AND user_id = ?",
                (link_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_entry_links(
        self, entry_id: str, user_id: str, direction: str = "both"
    ) -> list[dict[str, Any]]:
        """列出条目关联。direction: out/in/both"""
        conn = self._get_conn()
        try:
            links = []
            if direction in ("out", "both"):
                rows = conn.execute(
                    "SELECT * FROM entry_links WHERE source_id = ? AND user_id = ? ORDER BY created_at DESC",
                    (entry_id, user_id),
                ).fetchall()
                for r in rows:
                    d = dict(r)
                    d["direction"] = "out"
                    links.append(d)
            if direction in ("in", "both"):
                rows = conn.execute(
                    "SELECT * FROM entry_links WHERE target_id = ? AND user_id = ? ORDER BY created_at DESC",
                    (entry_id, user_id),
                ).fetchall()
                for r in rows:
                    d = dict(r)
                    d["direction"] = "in"
                    links.append(d)
            return links
        finally:
            conn.close()

    def delete_entry_link_pair(self, link_id: str, user_id: str) -> bool:
        """删除关联记录及其配对记录（同一事务）"""
        conn = self._get_conn()
        try:
            # 找到原始记录
            row = conn.execute(
                "SELECT source_id, target_id, relation_type FROM entry_links WHERE id = ? AND user_id = ?",
                (link_id, user_id),
            ).fetchone()
            if not row:
                return False
            # 删除正向和反向
            conn.execute(
                "DELETE FROM entry_links WHERE user_id = ? AND source_id = ? AND target_id = ? AND relation_type = ?",
                (user_id, row["source_id"], row["target_id"], row["relation_type"]),
            )
            conn.execute(
                "DELETE FROM entry_links WHERE user_id = ? AND source_id = ? AND target_id = ? AND relation_type = ?",
                (user_id, row["target_id"], row["source_id"], row["relation_type"]),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def delete_entry_links_by_entry(self, entry_id: str, user_id: str) -> int:
        """删除条目的所有关联（删除条目时级联调用）"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM entry_links WHERE (source_id = ? OR target_id = ?) AND user_id = ?",
                (entry_id, entry_id, user_id),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def check_entry_link_exists(
        self, user_id: str, source_id: str, target_id: str, relation_type: str
    ) -> bool:
        """检查关联是否已存在"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM entry_links WHERE user_id = ? AND source_id = ? AND target_id = ? AND relation_type = ? LIMIT 1",
                (user_id, source_id, target_id, relation_type),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def get_entry(self, entry_id: str, user_id: str = "_default") -> Optional[Dict[str, Any]]:
        """获取单个条目"""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id,))
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
        user_id: Optional[str] = None,
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

        # user_id 过滤
        if user_id is not None:
            conditions.append("e.user_id = ?")
            params.append(user_id)

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
        user_id: str = "_default",
    ) -> List[Dict[str, Any]]:
        """列出条目（支持筛选）"""
        conn = self._get_conn()
        try:
            query, params = self._build_filter_query(
                "SELECT DISTINCT e.* FROM entries e", type, status, tags, parent_id, start_date, end_date, user_id
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
        user_id: str = "_default",
    ) -> int:
        """统计条目数量"""
        conn = self._get_conn()
        try:
            query, params = self._build_filter_query(
                "SELECT COUNT(DISTINCT e.id) as cnt FROM entries e", type, status, tags, parent_id, start_date, end_date, user_id
            )
            cursor = conn.execute(query, params)
            return cursor.fetchone()["cnt"]
        finally:
            conn.close()

    def claim_default_entries(self, target_user_id: str) -> int:
        """将 `_default` 用户下的条目认领到目标用户"""
        if not target_user_id or target_user_id == "_default":
            return 0

        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "UPDATE entries SET user_id = ? WHERE user_id = ?",
                (target_user_id, "_default"),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # === 全文搜索 ===

    def search(self, query: str, limit: int = 10, user_id: str = "_default") -> List[Dict[str, Any]]:
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
                    WHERE entries_fts MATCH ? AND e.user_id = ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, user_id, limit))

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
                    WHERE (title LIKE ? OR content LIKE ?) AND user_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (like_pattern, like_pattern, user_id, limit))

                for row in cursor.fetchall():
                    entry = dict(row)
                    entry["tags"] = self._get_entry_tags(conn, entry["id"])
                    entries.append(entry)

            return entries
        finally:
            conn.close()

    # === 同步操作 ===

    def sync_from_markdown(self, markdown_storage, user_id: str = "_default") -> int:
        """从 Markdown 存储同步所有条目"""
        entries = markdown_storage.scan_all()
        if not entries:
            return 0

        # 批量预取已认领到真实用户的条目 ID，避免逐条查询
        claimed_ids: set[str] = set()
        if user_id == "_default":
            conn = self._get_conn()
            try:
                rows = conn.execute(
                    "SELECT id FROM entries WHERE user_id != ?",
                    ("_default",),
                ).fetchall()
                claimed_ids = {row["id"] for row in rows}
            finally:
                conn.close()

        count = 0
        for entry in entries:
            if entry.id in claimed_ids:
                continue
            if self.upsert_entry(entry, user_id=user_id):
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

    # === AI 摘要操作 ===

    def get_ai_summary(self, entry_id: str, user_id: str = "_default") -> Optional[dict]:
        """获取条目的 AI 摘要缓存，返回 {summary, generated_at} 或 None"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT ai_summary, ai_summary_generated_at FROM entries WHERE id = ? AND user_id = ?",
                (entry_id, user_id),
            ).fetchone()
            if row and row["ai_summary"]:
                return {
                    "summary": row["ai_summary"],
                    "generated_at": row["ai_summary_generated_at"],
                }
            return None
        finally:
            conn.close()

    def save_ai_summary(self, entry_id: str, summary: str, user_id: str = "_default", generated_at: Optional[str] = None) -> bool:
        """保存 AI 摘要到条目"""
        if generated_at is None:
            generated_at = datetime.now().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE entries SET ai_summary = ?, ai_summary_generated_at = ? WHERE id = ? AND user_id = ?",
                (summary, generated_at, entry_id, user_id),
            )
            conn.commit()
            return conn.total_changes > 0
        except Exception as e:
            print(f"保存 AI 摘要失败: {e}")
            return False
        finally:
            conn.close()

    # === 反馈操作 ===

    def create_feedback(
        self,
        user_id: str,
        title: str,
        description: str | None = None,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """创建本地反馈记录，返回新记录"""
        conn = self._get_conn()
        try:
            now = datetime.utcnow().isoformat()
            cursor = conn.execute(
                """
                INSERT INTO feedback (user_id, title, description, severity, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (user_id, title, description, severity, now),
            )
            feedback_id = cursor.lastrowid
            conn.commit()

            # 读回完整记录
            row = conn.execute(
                "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            return dict(row)
        finally:
            conn.close()

    def list_feedbacks_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """列出用户的所有反馈，按创建时间倒序"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_feedback_by_id(
        self, feedback_id: int, user_id: str
    ) -> Optional[dict[str, Any]]:
        """获取单条反馈（含用户隔离）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM feedback WHERE id = ? AND user_id = ?",
                (feedback_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_feedback_status(
        self,
        feedback_id: int,
        status: str,
        log_service_issue_id: int | None = None,
    ) -> bool:
        """更新反馈状态（后台同步后调用）"""
        conn = self._get_conn()
        try:
            if log_service_issue_id is not None:
                conn.execute(
                    "UPDATE feedback SET status = ?, log_service_issue_id = ? WHERE id = ?",
                    (status, log_service_issue_id, feedback_id),
                )
            else:
                conn.execute(
                    "UPDATE feedback SET status = ? WHERE id = ?",
                    (status, feedback_id),
                )
            conn.commit()
            return True
        except Exception as e:
            print(f"更新反馈状态失败: {e}")
            return False
        finally:
            conn.close()

    # === 目标操作 ===

    def create_goal(
        self,
        goal_id: str,
        user_id: str,
        title: str,
        metric_type: str,
        target_value: int,
        description: str | None = None,
        status: str = "active",
        start_date: str | None = None,
        end_date: str | None = None,
        auto_tags: str | None = None,
        checklist_items: str | None = None,
    ) -> dict[str, Any]:
        """创建目标，返回新记录"""
        now = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO goals (id, user_id, title, description, metric_type, target_value,
                   current_value, status, start_date, end_date, auto_tags, checklist_items, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)""",
                (goal_id, user_id, title, description, metric_type, target_value,
                 status, start_date, end_date, auto_tags, checklist_items, now, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
            return dict(row)
        finally:
            conn.close()

    def get_goal(self, goal_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """获取单个目标（含用户隔离）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_goals(
        self, user_id: str, status: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """列出用户的目标"""
        conn = self._get_conn()
        try:
            if status:
                cursor = conn.execute(
                    "SELECT * FROM goals WHERE user_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, status, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM goals WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_goal(
        self,
        goal_id: str,
        user_id: str,
        **fields,
    ) -> Optional[dict[str, Any]]:
        """更新目标（仅更新传入的非 None 字段），返回更新后的记录"""
        # 过滤掉 None 值
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return self.get_goal(goal_id, user_id)

        # 字段名白名单校验，防止 SQL 注入
        invalid_fields = set(updates.keys()) - ALLOWED_GOAL_FIELDS
        if invalid_fields:
            raise ValueError(
                f"非法字段名: {sorted(invalid_fields)}，"
                f"合法值: {sorted(ALLOWED_GOAL_FIELDS)}"
            )

        updates["updated_at"] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [goal_id, user_id]

        conn = self._get_conn()
        try:
            conn.execute(
                f"UPDATE goals SET {set_clause} WHERE id = ? AND user_id = ?",
                values,
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def delete_goal(self, goal_id: str, user_id: str) -> bool:
        """删除目标（含级联删除 goal_entries）"""
        conn = self._get_conn()
        try:
            # 先删除 goal_entries
            conn.execute(
                "DELETE FROM goal_entries WHERE goal_id = ? AND user_id = ?",
                (goal_id, user_id),
            )
            cursor = conn.execute(
                "DELETE FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def count_goal_entries(self, goal_id: str, user_id: str) -> int:
        """统计目标关联的条目数量"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM goal_entries WHERE goal_id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return row["cnt"]
        finally:
            conn.close()

    def count_entries_by_tags(self, tags: list[str], user_id: str) -> int:
        """统计匹配指定标签的条目数量"""
        if not tags:
            return 0
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(tags))
            row = conn.execute(f"""
                SELECT COUNT(DISTINCT e.id) as cnt
                FROM entries e
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name IN ({placeholders}) AND e.user_id = ?
            """, (*tags, user_id)).fetchone()
            return row["cnt"]
        finally:
            conn.close()

    def count_entries_by_tags_in_range(
        self, tags: list[str], user_id: str, start_date: str, end_date: str
    ) -> int:
        """统计指定时间范围内匹配标签的条目数量"""
        if not tags:
            return 0
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(tags))
            row = conn.execute(f"""
                SELECT COUNT(DISTINCT e.id) as cnt
                FROM entries e
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name IN ({placeholders})
                  AND e.user_id = ?
                  AND e.created_at >= ?
                  AND e.created_at < ?
            """, (*tags, user_id, start_date, end_date)).fetchone()
            return row["cnt"]
        finally:
            conn.close()

    def list_entries_by_tags(
        self, tags: list[str], user_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取匹配指定标签的条目列表（用于 tag_auto 目标展示）"""
        if not tags:
            return []
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(tags))
            rows = conn.execute(f"""
                SELECT DISTINCT e.id, e.title, e.status, e.type as category, e.created_at
                FROM entries e
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name IN ({placeholders}) AND e.user_id = ?
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (*tags, user_id, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def list_entries_by_tags_in_range(
        self, tags: list[str], user_id: str, start_date: str, end_date: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取指定时间范围内匹配标签的条目列表"""
        if not tags:
            return []
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(tags))
            rows = conn.execute(f"""
                SELECT DISTINCT e.id, e.title, e.status, e.type as category, e.created_at
                FROM entries e
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name IN ({placeholders})
                  AND e.user_id = ?
                  AND e.created_at >= ?
                  AND e.created_at < ?
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (*tags, user_id, start_date, end_date, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create_goal_entry(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> dict[str, Any]:
        """创建目标-条目关联，返回新记录"""
        import uuid as _uuid
        now = datetime.utcnow().isoformat()
        link_id = _uuid.uuid4().hex
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO goal_entries (id, goal_id, entry_id, user_id, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (link_id, goal_id, entry_id, user_id, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM goal_entries WHERE id = ?", (link_id,)
            ).fetchone()
            return dict(row)
        finally:
            conn.close()

    def delete_goal_entry(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> bool:
        """删除目标-条目关联"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM goal_entries WHERE goal_id = ? AND entry_id = ? AND user_id = ?",
                (goal_id, entry_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_goal_entries(
        self, goal_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        """列出目标关联的条目（JOIN entries 获取条目详情）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT ge.id, ge.goal_id, ge.entry_id, ge.created_at as linked_at,
                          e.id as entry_id, e.title as entry_title, e.status as entry_status,
                          e.type as entry_category, e.created_at as entry_created_at
                   FROM goal_entries ge
                   JOIN entries e ON ge.entry_id = e.id
                   WHERE ge.goal_id = ? AND ge.user_id = ?
                   ORDER BY ge.created_at DESC""",
                (goal_id, user_id),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def update_goal_status(
        self, goal_id: str, user_id: str, status: str
    ) -> Optional[dict[str, Any]]:
        """更新目标状态，返回更新后的记录"""
        return self.update_goal(goal_id, user_id, status=status)

    def check_goal_entry_exists(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> bool:
        """检查目标-条目关联是否已存在"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT 1 FROM goal_entries WHERE goal_id = ? AND entry_id = ? AND user_id = ? LIMIT 1",
                (goal_id, entry_id, user_id),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def list_goals_by_status(
        self, user_id: str, statuses: list[str]
    ) -> list[dict[str, Any]]:
        """按多个状态列出目标"""
        if not statuses:
            return []
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" * len(statuses))
            cursor = conn.execute(
                f"""SELECT * FROM goals
                    WHERE user_id = ? AND status IN ({placeholders})
                    ORDER BY created_at DESC""",
                (user_id, *statuses),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
