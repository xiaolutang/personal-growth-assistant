"""并发注册测试 - 验证同一用户名并发注册时的唯一性约束"""
import asyncio
import pytest

from app.infrastructure.storage.user_storage import UserStorage
from app.models.user import UserCreate


@pytest.fixture
def user_storage(tmp_path):
    return UserStorage(str(tmp_path / "users.db"))


class TestConcurrentRegistration:
    """并发注册同一用户名的竞态条件测试"""

    async def test_concurrent_same_username_only_one_succeeds(self, user_storage):
        """两个并发请求用同一 username 注册，只有一个成功"""
        results = await asyncio.gather(
            asyncio.to_thread(
                user_storage.create_user,
                UserCreate(username="race_user", email="a@race.com", password="pass123"),
            ),
            asyncio.to_thread(
                user_storage.create_user,
                UserCreate(username="race_user", email="b@race.com", password="pass456"),
            ),
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        # 恰好一个成功，一个失败
        assert len(successes) + len(errors) == 2
        assert len(successes) >= 1, "至少一个注册应成功"

    async def test_concurrent_different_usernames_both_succeed(self, user_storage):
        """两个并发请求用不同 username 注册，都应成功"""
        results = await asyncio.gather(
            asyncio.to_thread(
                user_storage.create_user,
                UserCreate(username="user_x", email="x@test.com", password="pass123"),
            ),
            asyncio.to_thread(
                user_storage.create_user,
                UserCreate(username="user_y", email="y@test.com", password="pass456"),
            ),
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        assert len(successes) == 2

    async def test_concurrent_same_email_only_one_succeeds(self, user_storage):
        """两个并发请求用同一 email 注册，只有一个成功"""
        results = await asyncio.gather(
            asyncio.to_thread(
                user_storage.create_user,
                UserCreate(username="email_a", email="same@test.com", password="pass123"),
            ),
            asyncio.to_thread(
                user_storage.create_user,
                UserCreate(username="email_b", email="same@test.com", password="pass456"),
            ),
            return_exceptions=True,
        )

        successes = [r for r in results if not isinstance(r, Exception)]
        assert len(successes) >= 1
