"""SQLite 索引层 - 快速元数据查询和全文搜索"""
import sqlite3
from datetime import datetime, timezone
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

        # feedback 表 updated_at 列迁移
        fb_cursor = conn.execute("PRAGMA table_info(feedback)")
        fb_columns = {row[1] for row in fb_cursor.fetchall()}
        if "updated_at" not in fb_columns:
            try:
                conn.execute("ALTER TABLE feedback ADD COLUMN updated_at TEXT")
                print("数据库迁移: feedback 表添加 updated_at 列")
            except Exception as e:
                print(f"迁移失败 feedback.updated_at: {e}")

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（公共接口，替代外部直接调用 _get_conn）"""
        return self._get_conn()

    # === 公共聚合查询方法 ===

    def get_active_dates(self, user_id: str, days: int = 90) -> list[str]:
        """获取最近 N 天内有条目的日期列表（YYYY-MM-DD 格式，降序）

        Args:
            user_id: 用户 ID
            days: 回溯天数，默认 90

        Returns:
            日期字符串列表，如 ["2026-04-19", "2026-04-18"]
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT DISTINCT DATE(created_at) AS d
                   FROM entries
                   WHERE user_id = ? AND created_at >= date('now', ?)
                   ORDER BY d DESC""",
                (user_id, f"-{days} days"),
            ).fetchall()
        finally:
            conn.close()
        return [row["d"] for row in rows]

    def get_daily_activity_counts(
        self, user_id: str, start_date: str, end_date: str
    ) -> dict[str, int]:
        """获取指定日期范围内每日的活动条目数

        Args:
            user_id: 用户 ID
            start_date: 起始日期字符串，如 "2026-01-01"
            end_date: 结束日期字符串（含），如 "2026-12-31T23:59:59"

        Returns:
            日期字符串到条目数的映射，如 {"2026-04-19": 3, "2026-04-18": 5}
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT DATE(created_at) AS d, COUNT(*) AS cnt
                   FROM entries
                   WHERE user_id = ? AND created_at >= ? AND created_at <= ?
                   GROUP BY DATE(created_at)""",
                (user_id, start_date, end_date),
            ).fetchall()
        finally:
            conn.close()
        return {row["d"]: row["cnt"] for row in rows}

    def get_trend_aggregation(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict]:
        """获取指定日期范围内按日期+category+status 的聚合统计

        用于趋势数据，单次 SQL 替代 N+1 循环查询。

        Args:
            user_id: 用户 ID
            start_date: 起始日期字符串，如 "2026-01-01"
            end_date: 结束日期字符串（不含），如 "2026-01-08"

        Returns:
            行列表，每行含 d(日期), category, status, cnt(数量)
        """
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT DATE(created_at) AS d, type AS category, status, COUNT(*) AS cnt
                   FROM entries
                   WHERE user_id = ? AND created_at >= ? AND created_at < ?
                   GROUP BY DATE(created_at), type, status""",
                (user_id, start_date, end_date),
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    # === 知识图谱聚合查询（替代 list_entries(limit=10000) 全表扫描） ===

    def get_tag_stats_for_knowledge_map(self, user_id: str = "_default") -> dict:
        """获取所有标签的统计数据和共现边，用于构建知识图谱。

        Returns:
            {
                "tags": [{"name": str, "entry_count": int, "note_count": int, "recent_count": int}],
                "co_occurrence_pairs": [(source, target), ...]
            }
        """
        thirty_days_ago = (datetime.now() - __import__("datetime").timedelta(days=30)).isoformat()
        conn = self._get_conn()
        try:
            # 1. 标签统计：entry_count, note_count, recent_count
            tag_rows = conn.execute("""
                SELECT t.name AS tag_name,
                       COUNT(DISTINCT e.id) AS entry_count,
                       SUM(CASE WHEN e.type = 'note' THEN 1 ELSE 0 END) AS note_count,
                       SUM(CASE WHEN e.updated_at >= ? THEN 1 ELSE 0 END) AS recent_count
                FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                JOIN entries e ON et.entry_id = e.id
                WHERE e.user_id = ?
                GROUP BY t.name
            """, (thirty_days_ago, user_id)).fetchall()

            tags = [
                {
                    "name": row["tag_name"],
                    "entry_count": row["entry_count"],
                    "note_count": row["note_count"] or 0,
                    "recent_count": row["recent_count"] or 0,
                }
                for row in tag_rows
            ]

            # 2. 共现边：同一 entry 中出现的标签对
            pair_rows = conn.execute("""
                SELECT DISTINCT t1.name AS tag_a, t2.name AS tag_b
                FROM entry_tags et1
                JOIN entry_tags et2 ON et1.entry_id = et2.entry_id AND et1.tag_id < et2.tag_id
                JOIN tags t1 ON et1.tag_id = t1.id
                JOIN tags t2 ON et2.tag_id = t2.id
                JOIN entries e ON et1.entry_id = e.id
                WHERE e.user_id = ?
            """, (user_id,)).fetchall()

            co_occurrence_pairs = [
                (row["tag_a"], row["tag_b"])
                for row in pair_rows
            ]

            return {
                "tags": tags,
                "co_occurrence_pairs": co_occurrence_pairs,
            }
        finally:
            conn.close()

    def get_tag_stats_in_range(
        self, user_id: str, start_date: str, end_date: str, top_n: int = 10,
    ) -> list[tuple[str, int]]:
        """获取指定时间范围内的标签频次 top N（SQL 聚合）。

        Args:
            user_id: 用户 ID
            start_date: 起始日期 (YYYY-MM-DD)，包含当天
            end_date: 结束日期 (YYYY-MM-DD)，包含当天
            top_n: 返回前 N 个标签

        Returns:
            [(tag_name, frequency), ...] 按频次降序、标签名升序

        Note:
            日期范围使用 end_date + "\\uffff" 作为上界，要求 created_at
            存储为 ISO 日期格式 (YYYY-MM-DDTHH:MM:SS)。
        """
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT t.name AS tag_name, COUNT(DISTINCT e.id) AS freq
                FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                JOIN entries e ON et.entry_id = e.id
                WHERE e.user_id = ? AND e.created_at >= ? AND e.created_at < ?
                GROUP BY t.name
                ORDER BY freq DESC, tag_name ASC
                LIMIT ?
            """, (user_id, start_date, end_date + "\uffff", top_n)).fetchall()
            return [(row["tag_name"], row["freq"]) for row in rows]
        finally:
            conn.close()

    def search_tags_by_keyword(
        self, keyword: str, limit: int = 20, user_id: str = "_default"
    ) -> list[dict]:
        """按关键词搜索标签及其出现次数。

        Returns:
            [{"name": str, "entry_count": int}]
        """
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT t.name AS tag_name, COUNT(DISTINCT e.id) AS entry_count
                FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                JOIN entries e ON et.entry_id = e.id
                WHERE e.user_id = ? AND t.name LIKE ?
                GROUP BY t.name
                ORDER BY entry_count DESC
                LIMIT ?
            """, (user_id, f"%{keyword}%", limit)).fetchall()

            return [{"name": row["tag_name"], "entry_count": row["entry_count"]} for row in rows]
        finally:
            conn.close()

    def find_entries_by_concept(
        self, concept: str, days: int = 90, user_id: str = "_default"
    ) -> list[dict]:
        """按概念词查找条目（匹配 tags、title、content），用于时间线。

        Args:
            concept: 概念名称
            days: 回溯天数
            user_id: 用户 ID

        Returns:
            条目列表，每项含 id, title, type, created_at, updated_at
        """
        like_pattern = f"%{concept}%"
        days_ago = (datetime.now() - __import__("datetime").timedelta(days=days)).isoformat()
        conn = self._get_conn()
        try:
            # 通过 tag 匹配
            rows_by_tag = conn.execute("""
                SELECT DISTINCT e.id, e.title, e.type, e.created_at, e.updated_at
                FROM entries e
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE e.user_id = ? AND t.name = ? AND e.created_at >= ?
            """, (user_id, concept, days_ago)).fetchall()

            ids_by_tag = {row["id"] for row in rows_by_tag}

            # 通过 title/content LIKE 匹配
            rows_by_text = conn.execute("""
                SELECT id, title, type, created_at, updated_at
                FROM entries
                WHERE user_id = ? AND (title LIKE ? OR content LIKE ?) AND created_at >= ?
            """, (user_id, like_pattern, like_pattern, days_ago)).fetchall()

            # 合并去重
            seen = set(ids_by_tag)
            all_rows = list(rows_by_tag)
            for row in rows_by_text:
                if row["id"] not in seen:
                    seen.add(row["id"])
                    all_rows.append(row)

            return [dict(row) for row in all_rows]
        finally:
            conn.close()

    def get_tag_stats_for_concept_stats(self, user_id: str = "_default") -> dict:
        """获取标签统计和共现边数，用于 _stats_from_sqlite。

        Returns:
            {
                "concept_count": int,
                "tags": [{"name": str, "entry_count": int, "category": str}],
                "edge_count": int
            }
        """
        conn = self._get_conn()
        try:
            # 标签计数
            tag_rows = conn.execute("""
                SELECT t.name AS tag_name, COUNT(DISTINCT e.id) AS entry_count
                FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                JOIN entries e ON et.entry_id = e.id
                WHERE e.user_id = ?
                GROUP BY t.name
                ORDER BY entry_count DESC
            """, (user_id,)).fetchall()

            tags = [
                {"name": row["tag_name"], "entry_count": row["entry_count"], "category": "tag"}
                for row in tag_rows
            ]

            # 共现边计数
            edge_row = conn.execute("""
                SELECT COUNT(DISTINCT CASE WHEN et1.tag_id < et2.tag_id
                                      THEN et1.entry_id || '-' || et1.tag_id || '-' || et2.tag_id
                                      ELSE et2.entry_id || '-' || et2.tag_id || '-' || et1.tag_id
                                 END) AS edge_count
                FROM entry_tags et1
                JOIN entry_tags et2 ON et1.entry_id = et2.entry_id AND et1.tag_id < et2.tag_id
                JOIN entries e ON et1.entry_id = e.id
                WHERE e.user_id = ?
            """, (user_id,)).fetchone()

            return {
                "concept_count": len(tags),
                "tags": tags,
                "edge_count": edge_row["edge_count"] if edge_row else 0,
            }
        finally:
            conn.close()

    def get_tag_stats_for_subgraph(
        self, seed_concepts: list[str], user_id: str = "_default"
    ) -> dict:
        """获取种子概念的 tag 共现子图数据。

        只返回包含至少一个种子概念的条目中的标签统计和共现边。

        Args:
            seed_concepts: 种子概念名称列表
            user_id: 用户 ID

        Returns:
            {
                "tags": [{"name": str, "entry_count": int, "note_count": int, "recent_count": int}],
                "co_occurrence_pairs": [(source, target), ...]
            }
        """
        if not seed_concepts:
            return {"tags": [], "co_occurrence_pairs": []}

        thirty_days_ago = (datetime.now() - __import__("datetime").timedelta(days=30)).isoformat()
        seed_placeholders = ",".join("?" * len(seed_concepts))
        conn = self._get_conn()
        try:
            # 1. 标签统计：只统计包含至少一个种子概念的条目
            tag_rows = conn.execute(f"""
                SELECT t.name AS tag_name,
                       COUNT(DISTINCT e.id) AS entry_count,
                       SUM(CASE WHEN e.type = 'note' THEN 1 ELSE 0 END) AS note_count,
                       SUM(CASE WHEN e.updated_at >= ? THEN 1 ELSE 0 END) AS recent_count
                FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                JOIN entries e ON et.entry_id = e.id
                WHERE e.user_id = ?
                  AND e.id IN (
                      SELECT DISTINCT et2.entry_id
                      FROM entry_tags et2
                      JOIN tags t2 ON et2.tag_id = t2.id
                      WHERE t2.name IN ({seed_placeholders})
                  )
                GROUP BY t.name
            """, (thirty_days_ago, user_id, *seed_concepts)).fetchall()

            tags = [
                {
                    "name": row["tag_name"],
                    "entry_count": row["entry_count"],
                    "note_count": row["note_count"] or 0,
                    "recent_count": row["recent_count"] or 0,
                }
                for row in tag_rows
            ]

            # 2. 共现边
            pair_rows = conn.execute(f"""
                SELECT DISTINCT t1.name AS tag_a, t2.name AS tag_b
                FROM entry_tags et1
                JOIN entry_tags et2 ON et1.entry_id = et2.entry_id AND et1.tag_id < et2.tag_id
                JOIN tags t1 ON et1.tag_id = t1.id
                JOIN tags t2 ON et2.tag_id = t2.id
                JOIN entries e ON et1.entry_id = e.id
                WHERE e.user_id = ?
                  AND e.id IN (
                      SELECT DISTINCT et3.entry_id
                      FROM entry_tags et3
                      JOIN tags t3 ON et3.tag_id = t3.id
                      WHERE t3.name IN ({seed_placeholders})
                  )
            """, (user_id, *seed_concepts)).fetchall()

            co_occurrence_pairs = [
                (row["tag_a"], row["tag_b"])
                for row in pair_rows
            ]

            return {
                "tags": tags,
                "co_occurrence_pairs": co_occurrence_pairs,
            }
        finally:
            conn.close()

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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user_parent ON entries(user_id, parent_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user_planned ON entries(user_id, planned_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user_status_updated ON entries(user_id, status, updated_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_user_type_updated ON entries(user_id, type, updated_at DESC)")

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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_tags_tag_id ON entry_tags(tag_id, entry_id)")

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
                    created_at TEXT NOT NULL,
                    updated_at TEXT
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goals_user_status_created ON goals(user_id, status, created_at DESC)")

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
        now = datetime.now(timezone.utc).isoformat()
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
        now = datetime.now(timezone.utc).isoformat()
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
        due: Optional[str] = None,
    ) -> tuple[str, List]:
        """构建筛选查询（复用逻辑）

        Args:
            due: 到期过滤，可选 "today" 或 "overdue"
                - today: planned_date == 今天 (UTC)
                - overdue: planned_date < 今天 (UTC) 且 status != 'complete'
        """
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
            from datetime import timedelta
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            next_day = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            params.append(next_day)

        # 到期过滤（基于 planned_date，UTC midnight 日界规则）
        # planned_date 存储为 ISO 格式（如 2026-04-26T00:00:00），用 DATE() 提取日期部分比较
        if due == "today":
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            conditions.append("DATE(e.planned_date) = ?")
            params.append(today_str)
        elif due == "overdue":
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            conditions.append("e.planned_date IS NOT NULL")
            conditions.append("e.planned_date != ''")
            conditions.append("DATE(e.planned_date) < ?")
            params.append(today_str)
            conditions.append("e.status != 'complete'")

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
        due: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """列出条目（支持筛选）"""
        conn = self._get_conn()
        try:
            query, params = self._build_filter_query(
                "SELECT DISTINCT e.* FROM entries e", type, status, tags, parent_id, start_date, end_date, user_id, due
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
        due: Optional[str] = None,
    ) -> int:
        """统计条目数量"""
        conn = self._get_conn()
        try:
            query, params = self._build_filter_query(
                "SELECT COUNT(DISTINCT e.id) as cnt FROM entries e", type, status, tags, parent_id, start_date, end_date, user_id, due
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
                    SELECT e.id, e.type, e.title, e.content, e.status, e.file_path,
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
                    SELECT id, type, title, content, status, file_path,
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
            now = datetime.now(timezone.utc).isoformat()
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

    def list_feedbacks_with_issue_id(self, user_id: str) -> list[dict[str, Any]]:
        """列出有 log_service_issue_id 的反馈（用于同步）"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM feedback WHERE user_id = ? AND log_service_issue_id IS NOT NULL",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def sync_feedback_status(
        self,
        feedback_id: int,
        status: str,
        updated_at: str | None = None,
    ) -> bool:
        """同步远程状态到本地反馈记录（status + updated_at 同时写入）"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE feedback SET status = ?, updated_at = ? WHERE id = ?",
                (status, updated_at, feedback_id),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"同步反馈状态失败: {e}")
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
        now = datetime.now(timezone.utc).isoformat()
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

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

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
        now = datetime.now(timezone.utc).isoformat()
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

    def get_growth_curve_tag_stats(
        self, user_id: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """按周 + tag 分组聚合 entry_count / note_count / recent_count。

        周归属规则（与旧 list_entries 实现等价）：
        条目按 created_at 或 updated_at 落入某周即归属该周。
        同一条目可出现在多个周（创建于周 A、更新于周 B 时两处都计数）。
        同一周内去重（created_at 和 updated_at 在同一周只计一次）。

        内部使用 strftime('%Y-%W') 做周编号（Monday-based, 00-53），
        Python 层 get_growth_curve 用同样的 key 做查找，再转换为 ISO 周标签。

        Args:
            user_id: 用户 ID
            start_date: 起始日期 (YYYY-MM-DD)，包含当天
            end_date: 结束日期 (YYYY-MM-DD)，包含当天

        Returns:
            [
                {
                    "year_week": str,       # "%Y-%W" 格式，如 "2026-16"
                    "tag_name": str,
                    "entry_count": int,
                    "note_count": int,
                    "recent_count": int,
                },
                ...
            ]
            如果某周无 entries，则不返回该周行。

        Note:
            - 主过滤按 created_at 在范围内筛选条目（与旧 list_entries 一致）
            - 周归属同时考虑 created_at 和 updated_at
            - recent_count 基于 updated_at 是否在最近 30 天内
        """
        thirty_days_ago = (datetime.now() - __import__("datetime").timedelta(days=30)).isoformat()
        end_upper = end_date + "T23:59:59"
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                WITH base_entries AS (
                    SELECT e.id, e.type, e.updated_at, e.created_at
                    FROM entries e
                    WHERE e.user_id = ?
                      AND e.created_at >= ?
                      AND e.created_at <= ?
                ),
                entry_weeks AS (
                    SELECT strftime('%Y-%W', created_at) AS year_week, id
                    FROM base_entries
                    UNION
                    SELECT strftime('%Y-%W', updated_at) AS year_week, id
                    FROM base_entries
                )
                SELECT ew.year_week,
                       t.name AS tag_name,
                       COUNT(DISTINCT ew.id) AS entry_count,
                       SUM(CASE WHEN be.type = 'note' THEN 1 ELSE 0 END) AS note_count,
                       SUM(CASE WHEN be.updated_at >= ? THEN 1 ELSE 0 END) AS recent_count
                FROM entry_weeks ew
                JOIN base_entries be ON ew.id = be.id
                JOIN entry_tags et ON be.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                GROUP BY ew.year_week, t.name
                ORDER BY ew.year_week, t.name
            """, (user_id, start_date, end_upper, thirty_days_ago)).fetchall()

            return [
                {
                    "year_week": row["year_week"] or "",
                    "tag_name": row["tag_name"],
                    "entry_count": row["entry_count"],
                    "note_count": row["note_count"] or 0,
                    "recent_count": row["recent_count"] or 0,
                }
                for row in rows
            ]
        finally:
            conn.close()
