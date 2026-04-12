"""Auth API 单元测试 - 注册/登录/登出/me"""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.infrastructure.storage.user_storage import UserStorage
from app.models.user import UserCreate
from app.routers import deps


# --- Fixtures ---


@pytest.fixture
def user_storage(tmp_path):
    """创建使用临时数据库的 UserStorage"""
    db_path = str(tmp_path / "test_users.db")
    return UserStorage(db_path)


@pytest.fixture
def client(user_storage):
    """创建 TestClient，注入 user_storage 到 deps"""
    # 设置 JWT_SECRET 环境变量（在 import 之前 mock）
    with patch.dict("os.environ", {"JWT_SECRET": "test-secret-key-for-testing"}):
        # 清除缓存的 settings
        from app.core.config import get_settings
        get_settings.cache_clear()

        from app.main import app
        deps._user_storage = user_storage
        yield TestClient(app)

        # 清理
        deps._user_storage = None
        get_settings.cache_clear()


@pytest.fixture
def sample_user():
    """示例注册数据"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "secret123",
    }


# --- Register Tests ---


class TestRegister:
    """POST /auth/register"""

    def test_register_success(self, client, sample_user):
        """注册成功返回 201 + UserResponse"""
        resp = client.post("/auth/register", json=sample_user)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "created_at" in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client, sample_user):
        """重复 username 返回 409"""
        client.post("/auth/register", json=sample_user)
        dup = {**sample_user, "email": "other@example.com"}
        resp = client.post("/auth/register", json=dup)
        assert resp.status_code == 409

    def test_register_duplicate_email(self, client, sample_user):
        """重复 email 返回 409"""
        client.post("/auth/register", json=sample_user)
        dup = {**sample_user, "username": "otheruser"}
        resp = client.post("/auth/register", json=dup)
        assert resp.status_code == 409

    def test_register_short_username(self, client):
        """username < 3 字符返回 422"""
        resp = client.post("/auth/register", json={
            "username": "ab",
            "email": "test@example.com",
            "password": "secret123",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client):
        """无效 email 返回 422"""
        resp = client.post("/auth/register", json={
            "username": "testuser",
            "email": "not-an-email",
            "password": "secret123",
        })
        assert resp.status_code == 422

    def test_register_short_password(self, client):
        """password < 6 字符返回 422"""
        resp = client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "12345",
        })
        assert resp.status_code == 422


# --- Login Tests ---


class TestLogin:
    """POST /auth/login"""

    def test_login_success(self, client, sample_user):
        """登录成功返回 access_token + user"""
        client.post("/auth/register", json=sample_user)

        resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "secret123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 604800
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"

    def test_login_wrong_password(self, client, sample_user):
        """错误密码返回 401"""
        client.post("/auth/register", json=sample_user)

        resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """不存在的用户返回 401（不暴露是用户名不存在）"""
        resp = client.post("/auth/login", json={
            "username": "ghost",
            "password": "secret123",
        })
        assert resp.status_code == 401
        assert "用户名或密码错误" in resp.json()["detail"]

    def test_login_error_message_same_for_both(self, client, sample_user):
        """用户名不存在和密码错误返回相同的错误信息"""
        client.post("/auth/register", json=sample_user)

        resp_wrong_pwd = client.post("/auth/login", json={
            "username": "testuser",
            "password": "wrong",
        })
        resp_no_user = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "secret123",
        })
        # 两种情况错误信息必须一致
        assert resp_wrong_pwd.json()["detail"] == resp_no_user.json()["detail"]


# --- Logout Tests ---


class TestLogout:
    """POST /auth/logout"""

    def test_logout_success(self, client, sample_user):
        """登出返回确认消息"""
        client.post("/auth/register", json=sample_user)
        login_resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "secret123",
        })
        token = login_resp.json()["access_token"]

        resp = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "logged out"

    def test_logout_no_token(self, client):
        """无 token 请求 logout 返回 401"""
        resp = client.post("/auth/logout")
        assert resp.status_code == 401


# --- Me Tests ---


class TestMe:
    """GET /auth/me"""

    def test_me_success(self, client, sample_user):
        """带有效 token 获取用户信息"""
        client.post("/auth/register", json=sample_user)
        login_resp = client.post("/auth/login", json={
            "username": "testuser",
            "password": "secret123",
        })
        token = login_resp.json()["access_token"]

        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_me_no_token(self, client):
        """无 token 请求 /me 返回 401"""
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        """无效 token 返回 401"""
        resp = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401

    def test_me_expired_token(self, client, sample_user):
        """过期 token 返回 401"""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        # 手动创建一个过期 token
        expired_payload = {
            "sub": "usr_nonexistent",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
        }
        expired_token = pyjwt.encode(expired_payload, "test-secret-key-for-testing", algorithm="HS256")

        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_me_user_not_found(self, client):
        """token 对应的用户不存在返回 401"""
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone

        payload = {
            "sub": "usr_ghost_user",
            "exp": datetime.now(timezone.utc) + timedelta(days=1),
            "type": "access",
        }
        token = pyjwt.encode(payload, "test-secret-key-for-testing", algorithm="HS256")

        resp = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "用户不存在" in resp.json()["detail"]
