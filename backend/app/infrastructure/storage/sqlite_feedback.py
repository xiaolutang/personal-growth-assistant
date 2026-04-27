"""SQLite 反馈层 - feedback 操作"""
from datetime import datetime, timezone
from typing import Optional, Any

import logging

logger = logging.getLogger(__name__)


class SQLiteFeedbackMixin:
    """feedback 相关操作 Mixin"""

    def create_feedback(
        self,
        user_id: str,
        title: str,
        description: str | None = None,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """创建本地反馈记录，返回新记录"""
        with self._conn() as conn:
            now = datetime.now(timezone.utc).isoformat()
            cursor = conn.execute(
                """
                INSERT INTO feedback (user_id, title, description, severity, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (user_id, title, description, severity, now),
            )
            feedback_id = cursor.lastrowid

            # 读回完整记录
            row = conn.execute(
                "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
            ).fetchone()
            return dict(row)

    def list_feedbacks_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """列出用户的所有反馈，按创建时间倒序"""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_feedback_by_id(
        self, feedback_id: int, user_id: str
    ) -> Optional[dict[str, Any]]:
        """获取单条反馈（含用户隔离）"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM feedback WHERE id = ? AND user_id = ?",
                (feedback_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def update_feedback_status(
        self,
        feedback_id: int,
        status: str,
        log_service_issue_id: int | None = None,
    ) -> bool:
        """更新反馈状态（后台同步后调用）"""
        try:
            with self._conn() as conn:
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
                return True
        except Exception as e:
            logger.error("更新反馈状态失败: %s", e)
            return False

    def list_feedbacks_with_issue_id(self, user_id: str) -> list[dict[str, Any]]:
        """列出有 log_service_issue_id 的反馈（用于同步）"""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM feedback WHERE user_id = ? AND log_service_issue_id IS NOT NULL",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def sync_feedback_status(
        self,
        feedback_id: int,
        status: str,
        updated_at: str | None = None,
    ) -> bool:
        """同步远程状态到本地反馈记录（status + updated_at 同时写入）"""
        try:
            with self._conn() as conn:
                conn.execute(
                    "UPDATE feedback SET status = ?, updated_at = ? WHERE id = ?",
                    (status, updated_at, feedback_id),
                )
                return True
        except Exception as e:
            logger.error("同步反馈状态失败: %s", e)
            return False
