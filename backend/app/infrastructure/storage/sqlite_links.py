"""SQLite 关联层 - entry_links + note_references + backlinks 操作"""
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set

from app.models import Task


class SQLiteLinksMixin:
    """entry_links + note_references + backlinks 相关操作 Mixin"""

    # === 条目关联操作 ===

    def create_entry_link(
        self, user_id: str, source_id: str, target_id: str, relation_type: str
    ) -> dict[str, Any]:
        """创建条目关联（单向），返回新记录。调用方负责在一个事务中创建双向记录。"""
        import uuid as _uuid
        link_id = _uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO entry_links (id, user_id, source_id, target_id, relation_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (link_id, user_id, source_id, target_id, relation_type, now),
            )
            row = conn.execute(
                "SELECT * FROM entry_links WHERE id = ?", (link_id,)
            ).fetchone()
            return dict(row)

    def create_entry_links_pair(
        self, user_id: str, source_id: str, target_id: str, relation_type: str
    ) -> list[dict[str, Any]]:
        """创建双向条目关联（同一事务），返回两条记录。"""
        import uuid as _uuid
        now = datetime.now(timezone.utc).isoformat()
        link_id_fwd = _uuid.uuid4().hex
        link_id_rev = _uuid.uuid4().hex
        with self._conn() as conn:
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
            row_fwd = conn.execute("SELECT * FROM entry_links WHERE id = ?", (link_id_fwd,)).fetchone()
            row_rev = conn.execute("SELECT * FROM entry_links WHERE id = ?", (link_id_rev,)).fetchone()
            return [dict(row_fwd), dict(row_rev)]

    def get_entry_link(self, link_id: str, user_id: str) -> Optional[dict[str, Any]]:
        """获取单条关联记录（含用户隔离）"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM entry_links WHERE id = ? AND user_id = ?",
                (link_id, user_id),
            ).fetchone()
            return dict(row) if row else None

    def list_entry_links(
        self, entry_id: str, user_id: str, direction: str = "both"
    ) -> list[dict[str, Any]]:
        """列出条目关联。direction: out/in/both"""
        with self._conn() as conn:
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

    def delete_entry_link_pair(self, link_id: str, user_id: str) -> bool:
        """删除关联记录及其配对记录（同一事务）"""
        with self._conn() as conn:
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
            return True

    def delete_entry_links_by_entry(self, entry_id: str, user_id: str) -> int:
        """删除条目的所有关联（删除条目时级联调用）"""
        with self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM entry_links WHERE (source_id = ? OR target_id = ?) AND user_id = ?",
                (entry_id, entry_id, user_id),
            )
            return cursor.rowcount

    def check_entry_link_exists(
        self, user_id: str, source_id: str, target_id: str, relation_type: str
    ) -> bool:
        """检查关联是否已存在"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM entry_links WHERE user_id = ? AND source_id = ? AND target_id = ? AND relation_type = ? LIMIT 1",
                (user_id, source_id, target_id, relation_type),
            ).fetchone()
            return row is not None

    # === 笔记双链引用 ===

    # 双链语法正则: [[note-id]] 或 [[note-id|显示标题]]
    _WIKILINK_RE = re.compile(r'\[\[([^\]|]+?)(?:\|[^\]]*?)?\]\]')

    @staticmethod
    def parse_wikilinks(content: str) -> Set[str]:
        """从 Markdown 内容中解析双链引用，返回去重的 note-id 集合。

        支持:
          - [[note-abc123]]       简写语法
          - [[note-abc123|标题]]  完整语法

        过滤:
          - 空字符串
          - 自引用（调用方判断）
          - 无效 ID（不匹配 {category}-{hex} 格式的）
        """
        if not content:
            return set()
        matches = SQLiteLinksMixin._WIKILINK_RE.findall(content)
        # 去重并清理空白
        return {m.strip() for m in matches if m.strip()}

    def upsert_note_references(self, source_id: str, target_ids: Set[str], user_id: str):
        """更新某个条目的所有出引用（幂等：先删旧引用再写入新引用）"""
        with self._conn() as conn:
            # 删除旧引用
            conn.execute(
                "DELETE FROM note_references WHERE source_id = ? AND user_id = ?",
                (source_id, user_id),
            )
            # 写入新引用
            for target_id in target_ids:
                # 跳过自引用
                if target_id == source_id:
                    continue
                # 跳过无效 ID（至少要有 category- 前缀）
                if '-' not in target_id:
                    continue
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO note_references (source_id, target_id, user_id) VALUES (?, ?, ?)",
                        (source_id, target_id, user_id),
                    )
                except Exception:
                    pass  # 忽略无效插入

    def delete_note_references(self, entry_id: str, user_id: str):
        """删除条目的所有引用关系（作为 source 和 target 都删）"""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM note_references WHERE (source_id = ? OR target_id = ?) AND user_id = ?",
                (entry_id, entry_id, user_id),
            )

    def get_backlinks(self, entry_id: str, user_id: str) -> List[Dict[str, Any]]:
        """获取反向引用列表（谁引用了 entry_id），返回 source 条目的 id、title、category"""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT DISTINCT e.id, e.title, e.type AS category
                   FROM note_references nr
                   JOIN entries e ON e.id = nr.source_id AND e.user_id = nr.user_id
                   WHERE nr.target_id = ? AND nr.user_id = ?
                   ORDER BY e.updated_at DESC""",
                (entry_id, user_id),
            ).fetchall()
            return [dict(row) for row in rows]

    def is_backlinks_indexed(self, user_id: str) -> bool:
        """检查用户是否已完成 backlinks 索引"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM backlinks_index_status WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
            return row is not None

    def mark_backlinks_indexed(self, user_id: str):
        """标记用户已完成 backlinks 索引"""
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO backlinks_index_status (user_id, indexed_at) VALUES (?, ?)",
                (user_id, datetime.now(timezone.utc).isoformat()),
            )
