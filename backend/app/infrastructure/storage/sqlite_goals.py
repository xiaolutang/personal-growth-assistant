"""SQLite 目标层 - goals/goal_entries/milestones 操作"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, TYPE_CHECKING

import logging

logger = logging.getLogger(__name__)

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


class SQLiteGoalsMixin:
    """goals/goal_entries/milestones 相关操作 Mixin"""

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
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO goals (id, user_id, title, description, metric_type, target_value,
                   current_value, status, start_date, end_date, auto_tags, checklist_items, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)""",
                (goal_id, user_id, title, description, metric_type, target_value,
                 status, start_date, end_date, auto_tags, checklist_items, now, now),
            )
            row = conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
            return dict(row)

    def get_goal(self, goal_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """获取单个目标（含用户隔离）"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def list_goals(
        self, user_id: str, status: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """列出用户的目标"""
        with self._conn() as conn:
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

        with self._conn() as conn:
            conn.execute(
                f"UPDATE goals SET {set_clause} WHERE id = ? AND user_id = ?",
                values,
            )
            row = conn.execute(
                "SELECT * FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def delete_goal(self, goal_id: str, user_id: str) -> bool:
        """删除目标（含级联删除 goal_entries）"""
        with self._conn() as conn:
            # 先删除 goal_entries
            conn.execute(
                "DELETE FROM goal_entries WHERE goal_id = ? AND user_id = ?",
                (goal_id, user_id),
            )
            cursor = conn.execute(
                "DELETE FROM goals WHERE id = ? AND user_id = ?",
                (goal_id, user_id),
            )
            return cursor.rowcount > 0

    def count_goal_entries(self, goal_id: str, user_id: str) -> int:
        """统计目标关联的条目数量"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM goal_entries WHERE goal_id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return row["cnt"]

    def count_entries_by_tags(self, tags: list[str], user_id: str) -> int:
        """统计匹配指定标签的条目数量"""
        if not tags:
            return 0
        with self._conn() as conn:
            placeholders = ",".join("?" * len(tags))
            row = conn.execute(f"""
                SELECT COUNT(DISTINCT e.id) as cnt
                FROM entries e
                JOIN entry_tags et ON e.id = et.entry_id
                JOIN tags t ON et.tag_id = t.id
                WHERE t.name IN ({placeholders}) AND e.user_id = ?
            """, (*tags, user_id)).fetchone()
            return row["cnt"]

    def count_entries_by_tags_in_range(
        self, tags: list[str], user_id: str, start_date: str, end_date: str
    ) -> int:
        """统计指定时间范围内匹配标签的条目数量"""
        if not tags:
            return 0
        with self._conn() as conn:
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

    def list_entries_by_tags(
        self, tags: list[str], user_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取匹配指定标签的条目列表（用于 tag_auto 目标展示）"""
        if not tags:
            return []
        with self._conn() as conn:
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

    def list_entries_by_tags_in_range(
        self, tags: list[str], user_id: str, start_date: str, end_date: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """获取指定时间范围内匹配标签的条目列表"""
        if not tags:
            return []
        with self._conn() as conn:
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

    def create_goal_entry(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> dict[str, Any]:
        """创建目标-条目关联，返回新记录"""
        import uuid as _uuid
        now = datetime.now(timezone.utc).isoformat()
        link_id = _uuid.uuid4().hex
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO goal_entries (id, goal_id, entry_id, user_id, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (link_id, goal_id, entry_id, user_id, now),
            )
            row = conn.execute(
                "SELECT * FROM goal_entries WHERE id = ?", (link_id,)
            ).fetchone()
            return dict(row)

    def delete_goal_entry(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> bool:
        """删除目标-条目关联"""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM goal_entries WHERE goal_id = ? AND entry_id = ? AND user_id = ?",
                (goal_id, entry_id, user_id),
            )
            return cursor.rowcount > 0

    def list_goal_entries(
        self, goal_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        """列出目标关联的条目（JOIN entries 获取条目详情）"""
        with self._conn() as conn:
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

    def update_goal_status(
        self, goal_id: str, user_id: str, status: str
    ) -> Optional[dict[str, Any]]:
        """更新目标状态，返回更新后的记录"""
        return self.update_goal(goal_id, user_id, status=status)

    def check_goal_entry_exists(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> bool:
        """检查目标-条目关联是否已存在"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM goal_entries WHERE goal_id = ? AND entry_id = ? AND user_id = ? LIMIT 1",
                (goal_id, entry_id, user_id),
            ).fetchone()
            return row is not None

    def list_goals_by_status(
        self, user_id: str, statuses: list[str]
    ) -> list[dict[str, Any]]:
        """按多个状态列出目标"""
        if not statuses:
            return []
        with self._conn() as conn:
            placeholders = ",".join("?" * len(statuses))
            cursor = conn.execute(
                f"""SELECT * FROM goals
                    WHERE user_id = ? AND status IN ({placeholders})
                    ORDER BY created_at DESC""",
                (user_id, *statuses),
            )
            return [dict(row) for row in cursor.fetchall()]

    # === 进度快照 ===

    def upsert_progress_snapshot(
        self,
        goal_id: str,
        user_id: str,
        current_value: int,
        target_value: int,
        percentage: float,
        snapshot_date: str,
    ) -> dict[str, Any]:
        """按 (goal_id, snapshot_date) 去重 upsert 快照"""
        import uuid as _uuid
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            # 检查是否已有当日快照
            existing = conn.execute(
                "SELECT id FROM goal_progress_snapshots WHERE goal_id = ? AND snapshot_date = ?",
                (goal_id, snapshot_date),
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE goal_progress_snapshots
                       SET current_value = ?, target_value = ?, percentage = ?, created_at = ?
                       WHERE goal_id = ? AND snapshot_date = ?""",
                    (current_value, target_value, percentage, now, goal_id, snapshot_date),
                )
                snapshot_id = existing["id"]
            else:
                snapshot_id = _uuid.uuid4().hex
                conn.execute(
                    """INSERT INTO goal_progress_snapshots
                       (id, goal_id, user_id, current_value, target_value, percentage, snapshot_date, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (snapshot_id, goal_id, user_id, current_value, target_value, percentage, snapshot_date, now),
                )

            row = conn.execute(
                "SELECT * FROM goal_progress_snapshots WHERE id = ?", (snapshot_id,)
            ).fetchone()
            return dict(row)

    def get_progress_history(
        self,
        goal_id: str,
        user_id: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """获取目标最近 N 天的进度历史

        Args:
            goal_id: 目标 ID
            user_id: 用户 ID
            days: 回溯天数，使用 WHERE snapshot_date >= date('now', '-N days') 过滤
        """
        with self._conn() as conn:
            cursor = conn.execute(
                """SELECT * FROM goal_progress_snapshots
                   WHERE goal_id = ? AND user_id = ?
                     AND snapshot_date >= date('now', ? || ' days')
                   ORDER BY snapshot_date DESC
                   LIMIT 1000""",
                (goal_id, user_id, f"-{days}"),
            )
            return [dict(row) for row in cursor.fetchall()]

    # === 里程碑 CRUD ===

    def create_milestone(
        self,
        milestone_id: str,
        goal_id: str,
        user_id: str,
        title: str,
        description: str | None = None,
        due_date: str | None = None,
        sort_order: int = 0,
    ) -> dict[str, Any]:
        """创建里程碑，返回新记录"""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO milestones
                   (id, goal_id, user_id, title, description, due_date, status, sort_order, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
                (milestone_id, goal_id, user_id, title, description, due_date, sort_order, now, now),
            )
            row = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,)).fetchone()
            return dict(row)

    def get_max_milestone_sort_order(self, goal_id: str, user_id: str) -> int:
        """获取目标下里程碑的最大 sort_order，无记录时返回 -1"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) as max_sort FROM milestones WHERE goal_id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return row["max_sort"] if row else -1

    def get_milestones(
        self, goal_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        """获取目标下所有里程碑（按 sort_order 排序）"""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM milestones WHERE goal_id = ? AND user_id = ? ORDER BY sort_order ASC, created_at ASC",
                (goal_id, user_id),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_milestone(self, milestone_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """获取单个里程碑"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM milestones WHERE id = ? AND user_id = ?",
                (milestone_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def update_milestone(
        self,
        milestone_id: str,
        user_id: str,
        **fields,
    ) -> Optional[dict[str, Any]]:
        """更新里程碑（仅更新传入的非 None 字段），返回更新后的记录"""
        ALLOWED_MILESTONE_FIELDS = frozenset({
            "title", "description", "due_date", "status", "sort_order",
        })
        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return self.get_milestone(milestone_id, user_id)

        invalid_fields = set(updates.keys()) - ALLOWED_MILESTONE_FIELDS
        if invalid_fields:
            raise ValueError(f"非法字段名: {sorted(invalid_fields)}")

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [milestone_id, user_id]

        with self._conn() as conn:
            conn.execute(
                f"UPDATE milestones SET {set_clause} WHERE id = ? AND user_id = ?",
                values,
            )
            row = conn.execute(
                "SELECT * FROM milestones WHERE id = ? AND user_id = ?",
                (milestone_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def delete_milestone(self, milestone_id: str, user_id: str) -> bool:
        """删除里程碑"""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM milestones WHERE id = ? AND user_id = ?",
                (milestone_id, user_id),
            )
            return cursor.rowcount > 0

    def reorder_milestones(
        self, goal_id: str, user_id: str, ordered_ids: list[str]
    ) -> list[dict[str, Any]]:
        """重排序里程碑：按 ordered_ids 的顺序设置 sort_order"""
        with self._conn() as conn:
            now = datetime.now(timezone.utc).isoformat()
            for idx, mid in enumerate(ordered_ids):
                conn.execute(
                    "UPDATE milestones SET sort_order = ?, updated_at = ? WHERE id = ? AND goal_id = ? AND user_id = ?",
                    (idx, now, mid, goal_id, user_id),
                )
            # 返回重排后的列表
            cursor = conn.execute(
                "SELECT * FROM milestones WHERE goal_id = ? AND user_id = ? ORDER BY sort_order ASC",
                (goal_id, user_id),
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_milestones(self, goal_id: str, user_id: str) -> int:
        """统计目标下里程碑总数"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM milestones WHERE goal_id = ? AND user_id = ?",
                (goal_id, user_id),
            ).fetchone()
            return row["cnt"]

    def count_completed_milestones(self, goal_id: str, user_id: str) -> int:
        """统计目标下已完成里程碑数"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM milestones WHERE goal_id = ? AND user_id = ? AND status = 'completed'",
                (goal_id, user_id),
            ).fetchone()
            return row["cnt"]

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
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        end_upper = end_date + "T23:59:59"
        with self._conn() as conn:
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
