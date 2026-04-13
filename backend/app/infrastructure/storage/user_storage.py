"""用户存储 - SQLite users 表"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import bcrypt

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
