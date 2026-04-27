"""SQLite 条目层 - entries/tags/FTS CRUD 操作"""
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from app.models import Task

import logging

logger = logging.getLogger(__name__)


class SQLiteEntriesMixin:
    """entries/tags/FTS 相关操作 Mixin"""

    # === 查询辅助 ===

    def entry_belongs_to_user(self, entry_id: str, user_id: str) -> bool:
        """检查条目是否属于指定用户（轻量存在性查询）"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM entries WHERE id = ? AND user_id = ? LIMIT 1",
                (entry_id, user_id),
            ).fetchone()
            return row is not None

    def batch_entry_belongs_to_user(
        self, entry_ids: List[str], user_id: str
    ) -> set[str]:
        """批量检查条目是否属于指定用户，返回存在的 entry_id 集合。

        单次 SQL IN 查询，替代多次 entry_belongs_to_user 循环调用。
        """
        if not entry_ids:
            return set()
        with self._conn() as conn:
            placeholders = ",".join("?" * len(entry_ids))
            rows = conn.execute(
                f"SELECT id FROM entries WHERE id IN ({placeholders}) AND user_id = ?",
                (*entry_ids, user_id),
            ).fetchall()
            return {row["id"] for row in rows}

    def batch_get_entry_summaries(
        self, entry_ids: List[str], user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """批量获取条目摘要信息（id, title, type）。

        单次 SQL IN 查询，替代多次 get_entry 循环调用。
        返回 {entry_id: {"id": ..., "title": ..., "type": ...}} 字典。
        """
        if not entry_ids:
            return {}
        with self._conn() as conn:
            placeholders = ",".join("?" * len(entry_ids))
            rows = conn.execute(
                f"SELECT id, title, type FROM entries WHERE id IN ({placeholders}) AND user_id = ?",
                (*entry_ids, user_id),
            ).fetchall()
            return {row["id"]: dict(row) for row in rows}

    def find_entries_by_tag_overlap(
        self, entry_id: str, tags: List[str], limit: int = 10, user_id: str = "_default"
    ) -> List[dict]:
        """通过标签重叠查找相关条目，按重叠数量降序排列"""
        if not tags:
            return []
        with self._conn() as conn:
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

    def get_entry_owner(self, entry_id: str) -> Optional[str]:
        """获取条目的当前 owner"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT user_id FROM entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            return row["user_id"] if row else None

    # === CRUD 操作 ===

    def upsert_entry(self, entry: Task, user_id: str = "_default") -> bool:
        """插入或更新条目"""
        try:
            with self._conn() as conn:
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

                return True
        except Exception as e:
            logger.error("SQLite upsert 失败: %s", e)
            return False

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
        try:
            with self._conn() as conn:
                # 由于有外键约束，删除 entries 会级联删除 entry_tags
                conn.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id,))
                return True
        except Exception as e:
            logger.error("SQLite delete 失败: %s", e)
            return False

    def get_entry(self, entry_id: str, user_id: str = "_default") -> Optional[Dict[str, Any]]:
        """获取单个条目"""
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id,))
            row = cursor.fetchone()
            if not row:
                return None

            entry = dict(row)
            # 获取标签
            entry["tags"] = self._get_entry_tags(conn, entry_id)
            return entry

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
        priority: Optional[str] = None,
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

        # priority 过滤（仅接受合法值，非法值忽略）
        _VALID_PRIORITIES = {"high", "medium", "low"}
        if priority and priority in _VALID_PRIORITIES:
            conditions.append("e.priority = ?")
            params.append(priority)

        if parent_id:
            conditions.append("e.parent_id = ?")
            params.append(parent_id)

        # 时间范围筛选（基于 created_at）
        if start_date:
            conditions.append("e.created_at >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("e.created_at < ?")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            next_day = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            params.append(next_day)

        # 到期过滤（基于 planned_date，UTC midnight 日界规则）
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
        priority: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """列出条目（支持筛选）"""
        with self._conn() as conn:
            query, params = self._build_filter_query(
                "SELECT DISTINCT e.* FROM entries e", type, status, tags, parent_id, start_date, end_date, user_id, due, priority
            )

            # 排序逻辑
            _PRIORITY_ORDER = "CASE e.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END"
            if sort_by == "priority":
                query += f" ORDER BY {_PRIORITY_ORDER} ASC, e.updated_at DESC"
            else:
                query += " ORDER BY e.updated_at DESC"

            query += " LIMIT ? OFFSET ?"
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
        priority: Optional[str] = None,
    ) -> int:
        """统计条目数量"""
        with self._conn() as conn:
            query, params = self._build_filter_query(
                "SELECT COUNT(DISTINCT e.id) as cnt FROM entries e", type, status, tags, parent_id, start_date, end_date, user_id, due, priority
            )
            cursor = conn.execute(query, params)
            return cursor.fetchone()["cnt"]

    def claim_default_entries(self, target_user_id: str) -> int:
        """将 `_default` 用户下的条目认领到目标用户"""
        if not target_user_id or target_user_id == "_default":
            return 0

        with self._conn() as conn:
            cursor = conn.execute(
                "UPDATE entries SET user_id = ? WHERE user_id = ?",
                (target_user_id, "_default"),
            )
            return cursor.rowcount

    # === 全文搜索 ===

    def search(self, query: str, limit: int = 10, user_id: str = "_default") -> List[Dict[str, Any]]:
        """全文搜索（支持中英文）"""
        with self._conn() as conn:
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

    # === 同步操作 ===

    def sync_from_markdown(self, markdown_storage, user_id: str = "_default") -> int:
        """从 Markdown 存储同步所有条目"""
        entries = markdown_storage.scan_all()
        if not entries:
            return 0

        # 批量预取已认领到真实用户的条目 ID，避免逐条查询
        claimed_ids: set[str] = set()
        if user_id == "_default":
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT id FROM entries WHERE user_id != ?",
                    ("_default",),
                ).fetchall()
                claimed_ids = {row["id"] for row in rows}

        count = 0
        for entry in entries:
            if entry.id in claimed_ids:
                continue
            if self.upsert_entry(entry, user_id=user_id):
                count += 1
        return count

    def clear_all(self) -> bool:
        """清空所有数据"""
        try:
            with self._conn() as conn:
                conn.execute("DELETE FROM entry_tags")
                conn.execute("DELETE FROM entries")
                conn.execute("DELETE FROM tags")
                return True
        except Exception as e:
            logger.error("清空失败: %s", e)
            return False

    # === AI 摘要操作 ===

    def get_ai_summary(self, entry_id: str, user_id: str = "_default") -> Optional[dict]:
        """获取条目的 AI 摘要缓存，返回 {summary, generated_at} 或 None"""
        with self._conn() as conn:
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

    def save_ai_summary(self, entry_id: str, summary: str, user_id: str = "_default", generated_at: Optional[str] = None) -> bool:
        """保存 AI 摘要到条目"""
        if generated_at is None:
            generated_at = datetime.now().isoformat()
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE entries SET ai_summary = ?, ai_summary_generated_at = ? WHERE id = ? AND user_id = ?",
                    (summary, generated_at, entry_id, user_id),
                )
                return conn.total_changes > 0
        except Exception as e:
            logger.error("保存 AI 摘要失败: %s", e)
            return False
