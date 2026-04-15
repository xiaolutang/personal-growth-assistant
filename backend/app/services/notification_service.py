"""通知/提醒服务 — 按需生成、已读状态、偏好管理"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: str
    type: str
    title: str
    message: str
    ref_id: Optional[str] = None
    created_at: str
    dismissed: bool = False


class NotificationResponse(BaseModel):
    items: List[NotificationItem]
    unread_count: int


class NotificationPreferences(BaseModel):
    overdue_task_enabled: bool = True
    stale_inbox_enabled: bool = True
    review_prompt_enabled: bool = True


class NotificationService:
    def __init__(self, sqlite_storage):
        self._sqlite = sqlite_storage

    # === 偏好 ===

    def get_preferences(self, user_id: str, conn=None) -> NotificationPreferences:
        own_conn = conn is None
        if own_conn:
            conn = self._sqlite._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM notification_preferences WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return NotificationPreferences()
            return NotificationPreferences(
                overdue_task_enabled=bool(row["overdue_task_enabled"]),
                stale_inbox_enabled=bool(row["stale_inbox_enabled"]),
                review_prompt_enabled=bool(row["review_prompt_enabled"]),
            )
        finally:
            if own_conn:
                conn.close()

    def update_preferences(self, user_id: str, prefs: NotificationPreferences) -> NotificationPreferences:
        conn = self._sqlite._get_conn()
        try:
            conn.execute(
                """INSERT INTO notification_preferences (user_id, overdue_task_enabled, stale_inbox_enabled, review_prompt_enabled)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                     overdue_task_enabled = excluded.overdue_task_enabled,
                     stale_inbox_enabled = excluded.stale_inbox_enabled,
                     review_prompt_enabled = excluded.review_prompt_enabled
                """,
                (user_id, int(prefs.overdue_task_enabled), int(prefs.stale_inbox_enabled), int(prefs.review_prompt_enabled)),
            )
            conn.commit()
            return prefs
        finally:
            conn.close()

    # === 已读记录 ===

    def dismiss_notification(self, notification_id: str, user_id: str) -> bool:
        today = date.today().isoformat()
        now = datetime.now().isoformat()
        conn = self._sqlite._get_conn()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO notifications (notification_id, user_id, notification_type, ref_id, dismissed_at, created_at)
                   VALUES (?, ?, '', '', ?, ?)
                """,
                (notification_id, user_id, now, today),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def _get_dismissed_ids(self, user_id: str, today: str, conn=None) -> set:
        own_conn = conn is None
        if own_conn:
            conn = self._sqlite._get_conn()
        try:
            rows = conn.execute(
                "SELECT notification_id FROM notifications WHERE user_id = ? AND created_at = ?",
                (user_id, today),
            ).fetchall()
            return {row["notification_id"] for row in rows}
        finally:
            if own_conn:
                conn.close()

    # === 按需生成 ===

    def get_notifications(self, user_id: str) -> NotificationResponse:
        today = date.today().isoformat()
        now = datetime.now().isoformat()

        # 单连接完成全部查询
        conn = self._sqlite._get_conn()
        try:
            prefs = self._get_preferences_conn(conn, user_id)
            dismissed = self._get_dismissed_ids_conn(conn, user_id, today)
            items: List[NotificationItem] = []

            # 1. 逾期任务
            if prefs.overdue_task_enabled:
                overdue = self._get_overdue_tasks_conn(conn, user_id, today)
                for task in overdue:
                    nid = f"overdue_task:{task['id']}:{today}"
                    days_overdue = (date.today() - datetime.fromisoformat(task["planned_date"]).date()).days
                    items.append(NotificationItem(
                        id=nid,
                        type="overdue_task",
                        title="任务已拖延",
                        message=f"「{task['title']}」已超过计划日期 {days_overdue} 天",
                        ref_id=task["id"],
                        created_at=now,
                        dismissed=nid in dismissed,
                    ))

            # 2. 未转化灵感
            if prefs.stale_inbox_enabled:
                stale = self._get_stale_inbox_conn(conn, user_id)
                for inbox in stale:
                    nid = f"stale_inbox:{inbox['id']}:{today}"
                    created = datetime.fromisoformat(inbox["created_at"])
                    days_stale = (datetime.now() - created).days
                    items.append(NotificationItem(
                        id=nid,
                        type="stale_inbox",
                        title="灵感未转化",
                        message=f"「{inbox['title']}」已在收件箱 {days_stale} 天，考虑转化为任务或笔记",
                        ref_id=inbox["id"],
                        created_at=now,
                        dismissed=nid in dismissed,
                    ))

            # 3. 回顾提醒
            if prefs.review_prompt_enabled:
                if self._check_no_recent_activity_conn(conn, user_id):
                    nid = f"review_prompt:{today}"
                    items.append(NotificationItem(
                        id=nid,
                        type="review_prompt",
                        title="回顾提醒",
                        message="你已 2 天没有记录，回顾一下最近的学习进展吧",
                        ref_id=None,
                        created_at=now,
                        dismissed=nid in dismissed,
                    ))

            unread = [i for i in items if not i.dismissed]
            return NotificationResponse(items=items, unread_count=len(unread))
        finally:
            conn.close()

    # === 连接复用版本（内部方法，由 get_notifications 调用） ===

    def _get_preferences_conn(self, conn, user_id: str) -> NotificationPreferences:
        row = conn.execute(
            "SELECT * FROM notification_preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return NotificationPreferences()
        return NotificationPreferences(
            overdue_task_enabled=bool(row["overdue_task_enabled"]),
            stale_inbox_enabled=bool(row["stale_inbox_enabled"]),
            review_prompt_enabled=bool(row["review_prompt_enabled"]),
        )

    def _get_dismissed_ids_conn(self, conn, user_id: str, today: str) -> set:
        rows = conn.execute(
            "SELECT notification_id FROM notifications WHERE user_id = ? AND created_at = ?",
            (user_id, today),
        ).fetchall()
        return {row["notification_id"] for row in rows}

    def _get_overdue_tasks_conn(self, conn, user_id: str, today: str) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """SELECT id, title, planned_date, priority FROM entries
               WHERE user_id = ? AND type = 'task'
                 AND planned_date IS NOT NULL AND planned_date != ''
                 AND status NOT IN ('complete', 'cancelled')
                 AND planned_date < ?
               ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END
               LIMIT 5""",
            (user_id, today),
        ).fetchall()
        result = []
        for r in rows:
            pd = r["planned_date"]
            pd_date = datetime.fromisoformat(pd).date() if "T" in pd else date.fromisoformat(pd)
            result.append({"id": r["id"], "title": r["title"], "planned_date": str(pd_date), "priority": r["priority"] or "medium"})
        return result

    def _get_stale_inbox_conn(self, conn, user_id: str) -> List[Dict[str, Any]]:
        three_days_ago = (datetime.now() - timedelta(days=3)).isoformat()
        rows = conn.execute(
            """SELECT id, title, created_at FROM entries
               WHERE user_id = ? AND type = 'inbox'
                 AND status NOT IN ('complete', 'cancelled')
                 AND created_at <= ?
               LIMIT 5""",
            (user_id, three_days_ago),
        ).fetchall()
        return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"]} for r in rows]

    def _check_no_recent_activity_conn(self, conn, user_id: str) -> bool:
        two_days_ago = (datetime.now() - timedelta(days=2)).isoformat()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM entries WHERE user_id = ? AND created_at >= ?",
            (user_id, two_days_ago),
        ).fetchone()
        return row["cnt"] == 0
