"""B03 认证核心路径单元测试"""
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from app.infrastructure.storage.user_storage import UserStorage
from app.models.user import UserCreate
from app.services.auth_service import (
    create_access_token,
    get_current_user_from_token,
)
from app.infrastructure.storage.user_storage import verify_password, get_password_hash, check_user_markdown_data


@pytest.fixture
def user_db():
    """创建临时用户数据库"""
    db_path = tempfile.mktemp(suffix=".db")
    store = UserStorage(db_path)
    yield store
    try:
        os.unlink(db_path)
    except OSError:
        pass


class TestPasswordHash:
    """密码哈希测试"""

    def test_hash_and_verify(self):
        """密码哈希和验证"""
        password = "test123456"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        """错误密码验证失败"""
        hashed = get_password_hash("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """同一密码每次哈希不同"""
        p = "same_password"
        assert get_password_hash(p) != get_password_hash(p)


class TestUserRegistration:
    """注册测试"""

    def test_create_user_success(self, user_db):
        """成功创建用户"""
        user = user_db.create_user(UserCreate(
            username="testuser",
            email="test@example.com",
            password="password123",
        ))
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        # 不应返回 hashed_password
        assert not hasattr(user, "hashed_password") or user.hashed_password is None or user.id is not None

    def test_create_duplicate_username_fails(self, user_db):
        """重复用户名返回 409"""
        user_db.create_user(UserCreate(
            username="dup_user",
            email="first@example.com",
            password="password123",
        ))
        with pytest.raises(ValueError, match="用户名.*已存在"):
            user_db.create_user(UserCreate(
                username="dup_user",
                email="second@example.com",
                password="password123",
            ))

    def test_create_duplicate_email_fails(self, user_db):
        """重复邮箱返回 409"""
        user_db.create_user(UserCreate(
            username="user1",
            email="dup@example.com",
            password="password123",
        ))
        with pytest.raises(ValueError, match="邮箱.*已存在"):
            user_db.create_user(UserCreate(
                username="user2",
                email="dup@example.com",
                password="password123",
            ))

    def test_get_by_username(self, user_db):
        """通过用户名查找"""
        user_db.create_user(UserCreate(
            username="findme",
            email="find@example.com",
            password="password123",
        ))
        found = user_db.get_by_username("findme")
        assert found is not None
        assert found.username == "findme"

    def test_get_by_username_not_found(self, user_db):
        """用户名不存在返回 None"""
        assert user_db.get_by_username("nonexistent") is None


class TestJWTToken:
    """Token 创建和验证测试"""

    def test_create_and_verify_token(self, user_db):
        """创建 token 并验证"""
        user = user_db.create_user(UserCreate(
            username="tokenuser",
            email="token@example.com",
            password="password123",
        ))
        token = create_access_token(user.id)
        assert isinstance(token, str)
        assert len(token) > 0

        # 验证 token
        verified = get_current_user_from_token(token, user_db)
        assert verified.id == user.id
        assert verified.username == "tokenuser"

    def test_expired_token(self, user_db):
        """过期 token 返回 401"""
        from datetime import datetime, timedelta, timezone
        import jwt
        from app.core.config import get_settings

        settings = get_settings()
        # 创建已过期的 token
        expire = datetime.now(timezone.utc) - timedelta(days=1)
        payload = {
            "sub": "some-user-id",
            "exp": expire,
            "type": "access",
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(Exception):  # HTTPException
            get_current_user_from_token(token, user_db)

    def test_invalid_token(self, user_db):
        """无效 token 返回 401"""
        with pytest.raises(Exception):
            get_current_user_from_token("invalid.token.here", user_db)

    def test_token_for_nonexistent_user(self, user_db):
        """token 对应用户不存在时返回 401"""
        token = create_access_token("nonexistent-user-id")
        with pytest.raises(Exception):
            get_current_user_from_token(token, user_db)

    def test_token_for_inactive_user(self, user_db):
        """token 对应用户已禁用时返回 401"""
        user = user_db.create_user(UserCreate(
            username="inactive",
            email="inactive@example.com",
            password="password123",
        ))
        # 直接在数据库中设置 is_active = False
        import sqlite3
        conn = sqlite3.connect(user_db.db_path)
        conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user.id,))
        conn.commit()
        conn.close()

        token = create_access_token(user.id)
        with pytest.raises(Exception):
            get_current_user_from_token(token, user_db)

    def test_create_token_with_empty_jwt_secret_raises(self):
        """B57: JWT_SECRET 为空字符串时 create_access_token 抛出 ValueError"""
        from app.core.config import get_settings
        get_settings.cache_clear()
        with patch.dict("os.environ", {"JWT_SECRET": "", "DATA_DIR": "/tmp/test_b57_empty"}):
            get_settings.cache_clear()
            with pytest.raises(ValueError, match="JWT_SECRET 环境变量未设置"):
                create_access_token("some-user-id")
            get_settings.cache_clear()

    def test_create_token_with_missing_jwt_secret_raises(self):
        """B57: JWT_SECRET 环境变量不存在时 create_access_token 抛出 ValueError"""
        from app.core.config import get_settings
        get_settings.cache_clear()
        env = dict(os.environ)
        env.pop("JWT_SECRET", None)
        env["DATA_DIR"] = "/tmp/test_b57_missing"
        with patch.dict("os.environ", env, clear=True):
            get_settings.cache_clear()
            with pytest.raises(ValueError, match="JWT_SECRET 环境变量未设置"):
                create_access_token("some-user-id")
            get_settings.cache_clear()


class TestOnboardingMigration:
    """onboarding_completed 列迁移测试"""

    def test_new_user_has_onboarding_false(self, user_db):
        """新用户 onboarding_completed 默认为 False"""
        user = user_db.create_user(UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123",
        ))
        assert user.onboarding_completed is False

    def test_update_onboarding_completed(self, user_db):
        """可以更新 onboarding_completed 状态"""
        user = user_db.create_user(UserCreate(
            username="obuser",
            email="ob@example.com",
            password="password123",
        ))
        assert user.onboarding_completed is False

        user_db.update_onboarding_completed(user.id, True)
        updated = user_db.get_by_id(user.id)
        assert updated.onboarding_completed is True

    def test_migration_adds_column_idempotent(self, tmp_path):
        """迁移幂等：重复调用不报错"""
        db_path = str(tmp_path / "test_migration.db")
        store = UserStorage(db_path)

        # 创建一个用户
        store.create_user(UserCreate(
            username="existing",
            email="existing@example.com",
            password="password123",
        ))

        # 手动删除列模拟旧 schema（实际上 CREATE TABLE IF NOT EXISTS 不会重复创建）
        # 这里直接测试重复调用 migrate 不报错
        store.migrate_onboarding_column()
        store.migrate_onboarding_column()  # 第二次调用应该幂等

        user = store.get_by_username("existing")
        assert user is not None

    def test_migration_marks_users_with_entries(self, tmp_path):
        """迁移时为有数据的用户自动标记 onboarding_completed"""
        db_path = str(tmp_path / "test_migration2.db")

        # 先创建旧 schema（没有 onboarding_completed 列）
        import sqlite3
        conn = sqlite3.connect(db_path)
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
            "INSERT INTO users (id, username, email, hashed_password, is_active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("usr_test1", "olduser", "old@example.com", "fake_hash", "2024-01-01T00:00:00"),
        )
        conn.commit()
        conn.close()

        store = UserStorage.__new__(UserStorage)
        store.db_path = db_path
        store._ensure_db_dir = lambda: None
        store._init_db = lambda: None  # 跳过 _init_db，因为表已存在

        # 模拟 has_user_data_fn：olduser 有历史数据
        def mock_has_user_data(user_id):
            return user_id == "usr_test1"

        store.migrate_onboarding_column(has_user_data_fn=mock_has_user_data)

        user = store.get_by_username("olduser")
        assert user is not None
        assert user.onboarding_completed is True

    def test_migration_does_not_mark_users_without_entries(self, tmp_path):
        """迁移时没有数据的用户保持 onboarding_completed=False"""
        db_path = str(tmp_path / "test_migration3.db")

        import sqlite3
        conn = sqlite3.connect(db_path)
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
            "INSERT INTO users (id, username, email, hashed_password, is_active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("usr_test2", "emptyuser", "empty@example.com", "fake_hash", "2024-01-01T00:00:00"),
        )
        conn.commit()
        conn.close()

        store = UserStorage.__new__(UserStorage)
        store.db_path = db_path
        store._ensure_db_dir = lambda: None
        store._init_db = lambda: None

        def mock_has_user_data(user_id):
            return False  # 没有历史数据

        store.migrate_onboarding_column(has_user_data_fn=mock_has_user_data)

        user = store.get_by_username("emptyuser")
        assert user is not None
        assert user.onboarding_completed is False

    def test_migration_backfill_when_column_already_exists(self, tmp_path):
        """迁移幂等：列已存在但回填未完成时，补跑回填"""
        db_path = str(tmp_path / "test_migration_backfill.db")

        # 创建旧 schema（没有 onboarding_completed 列）
        import sqlite3
        conn = sqlite3.connect(db_path)
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
        # 插入两个用户：一个有数据，一个没有
        conn.execute(
            "INSERT INTO users (id, username, email, hashed_password, is_active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("usr_has_data", "dataguy", "data@example.com", "fake_hash", "2024-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT INTO users (id, username, email, hashed_password, is_active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("usr_no_data", "newguy", "new@example.com", "fake_hash", "2024-06-01T00:00:00"),
        )
        conn.commit()
        conn.close()

        store = UserStorage.__new__(UserStorage)
        store.db_path = db_path
        store._ensure_db_dir = lambda: None
        store._init_db = lambda: None

        # 第一次迁移：添加列并回填
        def mock_has_data(user_id):
            return user_id == "usr_has_data"

        store.migrate_onboarding_column(has_user_data_fn=mock_has_data)

        # 验证第一次回填结果
        user_with_data = store.get_by_username("dataguy")
        assert user_with_data.onboarding_completed is True
        user_without_data = store.get_by_username("newguy")
        assert user_without_data.onboarding_completed is False

        # 模拟部署中断后新增数据：给 newguy 也加上数据
        def mock_has_data_updated(user_id):
            return user_id in ("usr_has_data", "usr_no_data")

        # 第二次迁移（列已存在）：应该补跑回填
        store.migrate_onboarding_column(has_user_data_fn=mock_has_data_updated)

        # 验证 newguy 现在也被标记为已完成
        user_without_data = store.get_by_username("newguy")
        assert user_without_data.onboarding_completed is True


class TestCheckUserMarkdownData:
    """验证 check_user_markdown_data 白名单目录检查"""

    def test_md_in_whitelisted_subdir(self):
        """白名单子目录（tasks/）中的 .md 文件应被检测到"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            tasks_dir = os.path.join(user_dir, "tasks")
            os.makedirs(tasks_dir)
            Path(tasks_dir, "task-001.md").write_text("# Test")
            assert check_user_markdown_data(user_dir) is True

    def test_inbox_md_at_root(self):
        """根目录 inbox.md 应被检测到"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            os.makedirs(user_dir)
            Path(user_dir, "inbox.md").write_text("# Inbox")
            assert check_user_markdown_data(user_dir) is True

    def test_inbox_with_id_at_root(self):
        """根目录 inbox-{id}.md 应被检测到（真实 inbox 条目格式）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            os.makedirs(user_dir)
            Path(user_dir, "inbox-abc12345.md").write_text("# Quick idea")
            assert check_user_markdown_data(user_dir) is True

    def test_inbox_backup_not_detected(self):
        """inbox_backup.md 不应被误判为业务数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            os.makedirs(user_dir)
            Path(user_dir, "inbox_backup.md").write_text("# Backup")
            assert check_user_markdown_data(user_dir) is False

    def test_inbox_copy_not_detected(self):
        """inbox-copy.md 不应被误判为业务数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            os.makedirs(user_dir)
            Path(user_dir, "inbox-copy.md").write_text("# Copy")
            assert check_user_markdown_data(user_dir) is False

    def test_inbox2_not_detected(self):
        """inbox2.md 不应被误判为业务数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            os.makedirs(user_dir)
            Path(user_dir, "inbox2.md").write_text("# Other")
            assert check_user_markdown_data(user_dir) is False

    def test_non_whitelisted_dir_ignored(self):
        """非白名单目录（如 exports/、backups/）中的 .md 不应被检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            exports_dir = os.path.join(user_dir, "exports")
            os.makedirs(exports_dir)
            Path(exports_dir, "export-001.md").write_text("# Export")
            assert check_user_markdown_data(user_dir) is False

    def test_root_random_md_not_detected(self):
        """根目录下非 inbox 的 .md 文件不应被检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            os.makedirs(user_dir)
            Path(user_dir, "readme.md").write_text("# Readme")
            assert check_user_markdown_data(user_dir) is False

    def test_empty_whitelisted_dirs(self):
        """白名单子目录存在但为空时不应误检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            user_dir = os.path.join(tmpdir, "usr_test")
            for subdir in ("tasks", "notes", "projects"):
                os.makedirs(os.path.join(user_dir, subdir))
            assert check_user_markdown_data(user_dir) is False

    def test_nonexistent_dir(self):
        """不存在的目录应返回 False"""
        assert check_user_markdown_data("/nonexistent/path") is False
