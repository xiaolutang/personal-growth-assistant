"""Auth API 单元测试 - 注册/登录/登出/me"""

import sys
import types
import pytest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

if "langgraph.checkpoint.sqlite.aio" not in sys.modules:
    sqlite_pkg = types.ModuleType("langgraph.checkpoint.sqlite")
    aio_pkg = types.ModuleType("langgraph.checkpoint.sqlite.aio")

    class AsyncSqliteSaver:  # pragma: no cover - 仅为测试导入兜底
        pass

    aio_pkg.AsyncSqliteSaver = AsyncSqliteSaver
    sys.modules["langgraph.checkpoint.sqlite"] = sqlite_pkg
    sys.modules["langgraph.checkpoint.sqlite.aio"] = aio_pkg

from app.infrastructure.storage.sqlite import SQLiteStorage
from app.infrastructure.storage.storage_factory import StorageFactory
from app.infrastructure.storage.user_storage import UserStorage
from app.models import Category, Priority, Task, TaskStatus
import app.routers.deps as deps
from app.services.sync_service import SyncService
from app.services.session_meta_store import SessionMetaStore

from app.routers.auth import router as auth_router
from tests.conftest import _make_entry


# --- Fixtures ---


@pytest.fixture
def user_storage(tmp_path):
    """创建使用临时数据库的 UserStorage"""
    db_path = str(tmp_path / "test_users.db")
    return UserStorage(db_path)


@pytest.fixture
def client(user_storage):
    """创建 TestClient，注入 user_storage 到 deps"""
    data_dir = None
    # 设置 JWT_SECRET 环境变量（在 import 之前 mock）
    with patch.dict("os.environ", {"JWT_SECRET": "test-secret-key-for-testing", "DATA_DIR": str(user_storage.db_path.rsplit("/", 1)[0] + "/data")}):
        # 清除缓存的 settings
        from app.core.config import get_settings
        get_settings.cache_clear()

        settings = get_settings()
        data_dir = settings.DATA_DIR
        app = FastAPI()
        app.include_router(auth_router)
        deps._user_storage = user_storage
        storage_factory = StorageFactory(data_dir)
        deps.storage = SyncService(
            markdown_storage=storage_factory.get_markdown_storage("_default"),
            storage_factory=storage_factory,
            sqlite_storage=SQLiteStorage(f"{data_dir}/index.db"),
        )
        yield TestClient(app)

        # 清理
        deps._user_storage = None
        deps.storage = None
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

    def test_login_auto_claims_default_data_for_first_user(self, client, sample_user):
        """首个真实用户登录时自动认领 `_default` 历史数据"""
        from app.core.config import get_settings

        settings = get_settings()
        deps.storage.sqlite.upsert_entry(_make_entry("legacy-task"), user_id="_default")
        StorageFactory(settings.DATA_DIR).get_markdown_storage("_default").write_entry(_make_entry("legacy-task"))
        SessionMetaStore(settings.sqlite_checkpoints_path.replace(".db", "_meta.db")).create_session(
            "legacy-session", "旧会话", user_id="_default"
        )

        client.post("/auth/register", json=sample_user)
        resp = client.post("/auth/login", json={"username": "testuser", "password": "secret123"})

        assert resp.status_code == 200
        user_id = resp.json()["user"]["id"]
        assert deps.storage.sqlite.count_entries(user_id="_default") == 0
        assert deps.storage.sqlite.count_entries(user_id=user_id) == 1
        assert SessionMetaStore(settings.sqlite_checkpoints_path.replace(".db", "_meta.db")).session_exists(
            "legacy-session", user_id=user_id
        )

    def test_login_does_not_auto_claim_when_multiple_users_exist(self, client, sample_user):
        """多用户场景下不自动认领，避免误归属"""
        deps.storage.sqlite.upsert_entry(_make_entry("legacy-task"), user_id="_default")
        client.post("/auth/register", json=sample_user)
        client.post(
            "/auth/register",
            json={"username": "user2", "email": "user2@example.com", "password": "secret123"},
        )

        resp = client.post("/auth/login", json={"username": "testuser", "password": "secret123"})

        assert resp.status_code == 200
        assert deps.storage.sqlite.count_entries(user_id="_default") == 1


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


class TestClaimDefaultData:
    """POST /auth/claim-default-data"""

    def test_claim_default_data_success(self, client, sample_user):
        """显式认领 `_default` 数据"""
        from app.core.config import get_settings

        settings = get_settings()
        deps.storage.sqlite.upsert_entry(_make_entry("legacy-task"), user_id="_default")
        StorageFactory(settings.DATA_DIR).get_markdown_storage("_default").write_entry(_make_entry("legacy-task"))

        client.post("/auth/register", json=sample_user)
        client.post(
            "/auth/register",
            json={"username": "user2", "email": "user2@example.com", "password": "secret123"},
        )
        login_resp = client.post("/auth/login", json={"username": "user2", "password": "secret123"})
        token = login_resp.json()["access_token"]
        user_id = login_resp.json()["user"]["id"]

        resp = client.post(
            "/auth/claim-default-data",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["claimed"] is True
        assert data["sqlite_entries_claimed"] == 1
        assert deps.storage.sqlite.count_entries(user_id=user_id) == 1

    def test_claim_default_data_is_idempotent(self, client, sample_user):
        """重复认领返回 no_default_data"""
        deps.storage.sqlite.upsert_entry(_make_entry("legacy-task"), user_id="_default")
        client.post("/auth/register", json=sample_user)
        client.post(
            "/auth/register",
            json={"username": "user2", "email": "user2@example.com", "password": "secret123"},
        )
        login_resp = client.post("/auth/login", json={"username": "user2", "password": "secret123"})
        token = login_resp.json()["access_token"]

        first = client.post(
            "/auth/claim-default-data",
            headers={"Authorization": f"Bearer {token}"},
        )
        second = client.post(
            "/auth/claim-default-data",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["claimed"] is False
        assert second.json()["reason"] == "no_default_data"
