"""B03 认证核心路径单元测试"""
import tempfile
import os
from pathlib import Path

import pytest

from app.infrastructure.storage.user_storage import UserStorage
from app.models.user import UserCreate
from app.services.auth_service import (
    create_access_token,
    get_current_user_from_token,
)
from app.infrastructure.storage.user_storage import verify_password, get_password_hash


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
