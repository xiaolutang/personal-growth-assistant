"""用户存储 - SQLite users 表"""

import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import bcrypt

from app.infrastructure.storage.markdown import _INBOX_FILE_RE

from app.models.user import User, UserCreate


def get_password_hash(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


class UserStorage:
    """用户 SQLite 存储层"""

    def __init__(self, db_path: str):
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
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """初始化 users 表"""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    hashed_password TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    onboarding_completed BOOLEAN NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_user(self, row: sqlite3.Row) -> User:
        """将数据库行转换为 User 对象"""
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            is_active=bool(row["is_active"]),
            onboarding_completed=bool(row["onboarding_completed"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=(
                datetime.fromisoformat(row["updated_at"])
                if row["updated_at"]
                else None
            ),
        )

    def create_user(self, user_data: UserCreate) -> User:
        """创建用户，返回 User 对象"""
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        hashed = get_password_hash(user_data.password)

        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO users (id, username, email, hashed_password, is_active, created_at) "
                "VALUES (?, ?, ?, ?, 1, ?)",
                (user_id, user_data.username, user_data.email, hashed, now),
            )
            conn.commit()
            return User(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                hashed_password=hashed,
                is_active=True,
                created_at=datetime.fromisoformat(now),
            )
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            if "username" in error_msg:
                raise ValueError(
                    f"用户名 '{user_data.username}' 已存在"
                ) from e
            elif "email" in error_msg:
                raise ValueError(
                    f"邮箱 '{user_data.email}' 已存在"
                ) from e
            raise
        finally:
            conn.close()

    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名查找用户"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_user(row)
        finally:
            conn.close()

    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查找用户"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_user(row)
        finally:
            conn.close()

    def get_by_id(self, user_id: str) -> Optional[User]:
        """根据用户 ID 查找用户"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_user(row)
        finally:
            conn.close()

    def count_users(self) -> int:
        """统计用户数量"""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
            return int(row["cnt"])
        finally:
            conn.close()

    def update_onboarding_completed(self, user_id: str, completed: bool) -> None:
        """更新用户的 onboarding_completed 状态"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE users SET onboarding_completed = ?, updated_at = ? WHERE id = ?",
                (1 if completed else 0, datetime.now().isoformat(), user_id),
            )
            conn.commit()
        finally:
            conn.close()

    def migrate_onboarding_column(self, has_user_data_fn=None) -> None:
        """迁移 onboarding_completed 列（完全幂等）。

        两步拆分：
        1. 检查并添加列（幂等：列已存在则跳过 ALTER）
        2. 独立执行回填（幂等：只处理 onboarding_completed=false 的用户）

        即使部署中断导致列已添加但回填未完成，后续启动也能正确补跑回填。

        Args:
            has_user_data_fn: 可选的 callable(user_id) -> bool，用于判断
                已有用户是否有历史数据。传入后，有历史数据的已有用户
                会被自动标记为 onboarding_completed=true。
                建议同时检查 SQLite 和 Markdown 目录。
        """
        conn = self._get_conn()
        try:
            # ---- 第一步：检查并添加列（幂等）----
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = {row["name"] for row in cursor.fetchall()}
            if "onboarding_completed" not in columns:
                conn.execute(
                    "ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT 0"
                )
                conn.commit()

            # ---- 第二步：独立回填（幂等）----
            # 只处理 onboarding_completed=false 的用户
            if has_user_data_fn is not None:
                rows = conn.execute(
                    "SELECT id FROM users WHERE onboarding_completed = 0"
                ).fetchall()
                for row in rows:
                    try:
                        if has_user_data_fn(row["id"]):
                            conn.execute(
                                "UPDATE users SET onboarding_completed = 1 WHERE id = ?",
                                (row["id"],),
                            )
                    except Exception:
                        pass  # 单个用户失败不影响整体迁移
                conn.commit()
        finally:
            conn.close()


# 白名单子目录：与 MarkdownStorage.CATEGORY_DIRS 中非 INBOX 的目录一致
_WHITELIST_SUBDIRS = ("tasks", "notes", "projects")

# _INBOX_FILE_RE 从 markdown.py 导入，确保与 MarkdownStorage 一致


def check_user_markdown_data(user_data_dir: str) -> bool:
    """检查用户 Markdown 数据目录是否存在业务数据。

    白名单边界（与 MarkdownStorage 一致）：
    - tasks/、notes/、projects/ 子目录下的 .md 文件
    - 根目录的 inbox.md 或 inbox-{id}.md
      （MarkdownStorage._category_from_path 和 list_entries 均支持）

    Args:
        user_data_dir: 用户数据目录的绝对路径

    Returns:
        True 如果检测到业务数据
    """
    user_path = Path(user_data_dir)
    if not user_path.is_dir():
        return False

    try:
        for subdir in _WHITELIST_SUBDIRS:
            subdir_path = user_path / subdir
            if subdir_path.is_dir():
                if any(f.endswith(".md") for f in os.listdir(subdir_path)):
                    return True

        for f in os.listdir(user_path):
            if _INBOX_FILE_RE.match(f):
                return True
    except Exception:
        pass

    return False
