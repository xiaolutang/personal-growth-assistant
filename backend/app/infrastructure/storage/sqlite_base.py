"""SQLite 基础层 - 连接管理、数据库迁移、公共聚合查询"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from app.models import Task, Category, TaskStatus, Priority

import logging

logger = logging.getLogger(__name__)


class SQLiteStorageBase:
    """SQLite 基础层：连接管理 + 迁移 + 公共聚合查询"""

    def __init__(self, db_path: str = "./data/index.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def _conn(self):
        """连接上下文管理器，自动 commit/rollback/close"""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（公共接口，替代外部直接调用 _get_conn）"""
        return self._get_conn()

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
            'type_history': 'TEXT DEFAULT "[]"',
        }

        # 添加缺失的列
        for col_name, col_def in required_columns.items():
            if col_name not in existing_columns:
                try:
                    conn.execute(f"ALTER TABLE entries ADD COLUMN {col_name} {col_def}")
                    logger.info("数据库迁移: 添加列 %s", col_name)
                except Exception as e:
                    logger.warning("迁移失败 %s: %s", col_name, e)

        # feedback 表迁移在 _migrate_feedback_schema 中执行（在 feedback 表创建后调用）

    def _migrate_feedback_schema(self, conn: sqlite3.Connection):
        """feedback 表迁移：为已有数据库添加新列"""
        fb_cursor = conn.execute("PRAGMA table_info(feedback)")
        fb_columns = {row[1] for row in fb_cursor.fetchall()}

        fb_migrations = {
            "updated_at": "TEXT",
            "feedback_type": "TEXT DEFAULT 'general'",
            "message_id": "TEXT",
            "reason": "TEXT",
            "detail": "TEXT",
        }
        for col_name, col_def in fb_migrations.items():
            if col_name not in fb_columns:
                try:
                    conn.execute(f"ALTER TABLE feedback ADD COLUMN {col_name} {col_def}")
                    logger.info("数据库迁移: feedback 表添加 %s 列", col_name)
                except Exception as e:
                    logger.warning("迁移失败 feedback.%s: %s", col_name, e)

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
                    updated_at TEXT,
                    feedback_type TEXT DEFAULT 'general',
                    message_id TEXT,
                    reason TEXT,
                    detail TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type)")

            # feedback 表迁移：为已有数据库添加新列
            self._migrate_feedback_schema(conn)

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

            # 目标进度快照表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goal_progress_snapshots (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    current_value INTEGER NOT NULL,
                    target_value INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(goal_id, snapshot_date),
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal_snapshots_goal_id ON goal_progress_snapshots(goal_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal_snapshots_user_date ON goal_progress_snapshots(user_id, snapshot_date DESC)")

            # 里程碑表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS milestones (
                    id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_milestones_goal_id ON milestones(goal_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_milestones_user_id ON milestones(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_milestones_goal_sort ON milestones(goal_id, sort_order)")

            # 笔记双链引用表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS note_references (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id, user_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_note_refs_source ON note_references(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_note_refs_target ON note_references(target_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_note_refs_user_id ON note_references(user_id)")

            # backlinks 索引状态表（延迟初始化标记）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS backlinks_index_status (
                    user_id TEXT PRIMARY KEY,
                    indexed_at TEXT NOT NULL
                )
            """)

            conn.commit()
        finally:
            conn.close()

    # === 公共聚合查询方法 ===

    def get_active_dates(self, user_id: str, days: int = 90) -> list[str]:
        """获取最近 N 天内有条目的日期列表（YYYY-MM-DD 格式，降序）

        Args:
            user_id: 用户 ID
            days: 回溯天数，默认 90

        Returns:
            日期字符串列表，如 ["2026-04-19", "2026-04-18"]
        """
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT DISTINCT DATE(created_at) AS d
                   FROM entries
                   WHERE user_id = ? AND created_at >= date('now', ?)
                   ORDER BY d DESC""",
                (user_id, f"-{days} days"),
            ).fetchall()
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
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT DATE(created_at) AS d, COUNT(*) AS cnt
                   FROM entries
                   WHERE user_id = ? AND created_at >= ? AND created_at <= ?
                   GROUP BY DATE(created_at)""",
                (user_id, start_date, end_date),
            ).fetchall()
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
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT DATE(created_at) AS d, type AS category, status, COUNT(*) AS cnt
                   FROM entries
                   WHERE user_id = ? AND created_at >= ? AND created_at < ?
                   GROUP BY DATE(created_at), type, status""",
                (user_id, start_date, end_date),
            ).fetchall()
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
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        with self._conn() as conn:
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
        with self._conn() as conn:
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

    def get_tag_last_seen_batch(
        self, user_id: str, tag_names: list[str],
    ) -> dict[str, str]:
        """批量获取标签最后一次出现的日期

        Args:
            user_id: 用户 ID
            tag_names: 标签名列表

        Returns:
            {tag_name: last_created_at_iso} 字典，未找到的标签不在结果中
        """
        if not tag_names:
            return {}
        with self._conn() as conn:
            placeholders = ",".join("?" for _ in tag_names)
            rows = conn.execute(f"""
                SELECT t.name AS tag_name, MAX(e.created_at) AS last_seen
                FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                JOIN entries e ON et.entry_id = e.id
                WHERE e.user_id = ? AND t.name IN ({placeholders})
                GROUP BY t.name
            """, (user_id, *tag_names)).fetchall()
            return {row["tag_name"]: row["last_seen"] for row in rows}

    def search_tags_by_keyword(
        self, keyword: str, limit: int = 20, user_id: str = "_default"
    ) -> list[dict]:
        """按关键词搜索标签及其出现次数。

        Returns:
            [{"name": str, "entry_count": int}]
        """
        with self._conn() as conn:
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
        days_ago = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
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

    def get_tag_stats_for_concept_stats(self, user_id: str = "_default") -> dict:
        """获取标签统计和共现边数，用于 _stats_from_sqlite。

        Returns:
            {
                "concept_count": int,
                "tags": [{"name": str, "entry_count": int, "category": str}],
                "edge_count": int
            }
        """
        with self._conn() as conn:
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

        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        seed_placeholders = ",".join("?" * len(seed_concepts))
        with self._conn() as conn:
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
