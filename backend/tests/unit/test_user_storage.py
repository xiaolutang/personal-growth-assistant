"""UserStorage 单元测试"""

import pytest

from app.infrastructure.storage.user_storage import (
    UserStorage,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserCreate


@pytest.fixture
def storage(tmp_path):
    """创建使用临时数据库的 UserStorage 实例"""
    db_path = str(tmp_path / "test_users.db")
    return UserStorage(db_path)


@pytest.fixture
def sample_user_data():
    """创建示例用户数据"""
    return UserCreate(
        username="testuser",
        email="test@example.com",
        password="secret123",
    )


class TestCreateUser:
    """创建用户测试"""

    def test_create_user_success(self, storage, sample_user_data):
        """创建用户成功，返回 User 对象"""
        user = storage.create_user(sample_user_data)

        assert isinstance(user, User)
        assert user.id.startswith("usr_")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.created_at is not None
        # 返回的对象不含明文密码
        assert user.hashed_password != "secret123"
        assert user.hashed_password.startswith("$2")

    def test_create_user_duplicate_username(self, storage, sample_user_data):
        """重复 username 创建失败，抛出 ValueError"""
        storage.create_user(sample_user_data)

        duplicate = UserCreate(
            username="testuser",
            email="other@example.com",
            password="another456",
        )
        with pytest.raises(ValueError, match="用户名.*已存在"):
            storage.create_user(duplicate)

    def test_create_user_duplicate_email(self, storage, sample_user_data):
        """重复 email 创建失败，抛出 ValueError"""
        storage.create_user(sample_user_data)

        duplicate = UserCreate(
            username="otheruser",
            email="test@example.com",
            password="another456",
        )
        with pytest.raises(ValueError, match="邮箱.*已存在"):
            storage.create_user(duplicate)


class TestGetUser:
    """查询用户测试"""

    def test_get_by_username_found(self, storage, sample_user_data):
        """get_by_username 找到用户返回 User"""
        created = storage.create_user(sample_user_data)

        found = storage.get_by_username("testuser")
        assert found is not None
        assert found.id == created.id
        assert found.username == "testuser"
        assert found.email == "test@example.com"

    def test_get_by_username_not_found(self, storage):
        """get_by_username 找不到返回 None"""
        assert storage.get_by_username("nonexistent") is None

    def test_get_by_email_found(self, storage, sample_user_data):
        """get_by_email 找到用户返回 User"""
        created = storage.create_user(sample_user_data)

        found = storage.get_by_email("test@example.com")
        assert found is not None
        assert found.id == created.id
        assert found.email == "test@example.com"

    def test_get_by_email_not_found(self, storage):
        """get_by_email 找不到返回 None"""
        assert storage.get_by_email("noone@example.com") is None

    def test_get_by_id_found(self, storage, sample_user_data):
        """get_by_id 找到用户返回 User"""
        created = storage.create_user(sample_user_data)

        found = storage.get_by_id(created.id)
        assert found is not None
        assert found.id == created.id
        assert found.username == "testuser"

    def test_get_by_id_not_found(self, storage):
        """get_by_id 找不到返回 None"""
        assert storage.get_by_id("usr_nonexistent") is None


class TestPasswordHash:
    """密码哈希测试"""

    def test_verify_password_correct(self):
        """正确密码验证返回 True"""
        hashed = get_password_hash("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_password_wrong(self):
        """错误密码验证返回 False"""
        hashed = get_password_hash("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_hash_not_contain_plaintext(self):
        """哈希值不包含明文密码"""
        plain = "secret123"
        hashed = get_password_hash(plain)
        assert plain not in hashed
        # bcrypt 哈希应以 $2 开头
        assert hashed.startswith("$2")

    def test_different_hashes_for_same_password(self):
        """相同密码每次生成不同的哈希（bcrypt 自动加盐）"""
        hashed1 = get_password_hash("samepassword")
        hashed2 = get_password_hash("samepassword")
        assert hashed1 != hashed2
        # 但两个哈希都能验证通过
        assert verify_password("samepassword", hashed1) is True
        assert verify_password("samepassword", hashed2) is True
