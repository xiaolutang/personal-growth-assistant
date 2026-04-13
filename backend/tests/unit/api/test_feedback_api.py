"""反馈 API 测试"""
import importlib.util
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.infrastructure.storage.sqlite import SQLiteStorage

MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "feedback.py"
SPEC = importlib.util.spec_from_file_location("feedback_router_module", MODULE_PATH)
feedback_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(feedback_module)
router = feedback_module.router

# Mock user for auth bypass
_mock_user = MagicMock()
_mock_user.id = "test-user"


class _MockSyncService:
    """轻量 mock，持有临时文件 SQLite（:memory: 在 SQLiteStorage 中每次连接会创建新库）"""

    def __init__(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.sqlite = SQLiteStorage(self._tmp.name)

    def cleanup(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass


@pytest.fixture
async def client():
    """创建带 mock storage 的测试客户端"""
    app = FastAPI()

    # Override auth
    from app.routers.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: _mock_user

    # Override storage via module-level patch
    mock_storage = _MockSyncService()
    with patch.object(feedback_module, "get_storage", return_value=mock_storage):
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            # 将 storage 挂到 client 上方便测试直接访问
            test_client._mock_storage = mock_storage
            yield test_client

    app.dependency_overrides.clear()
    mock_storage.cleanup()


class TestFeedbackAPI:
    """POST /feedback 测试"""

    async def test_submit_feedback_success(self, client):
        with patch.object(feedback_module, "report_issue", return_value={
            "id": 101,
            "title": "搜索功能响应慢",
            "status": "open",
            "created_at": "2026-04-12T10:00:00Z",
        }):
            response = await client.post("/feedback", json={
                "title": "搜索功能响应慢",
                "description": "任务列表存在卡顿",
                "severity": "medium",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["feedback"]["title"] == "搜索功能响应慢"
        assert data["feedback"]["status"] == "pending"
        assert data["feedback"]["user_id"] == "test-user"
        assert "id" in data["feedback"]

    async def test_submit_feedback_local_write_visible(self, client):
        """POST 后本地立即可查到"""
        storage: _MockSyncService = client._mock_storage

        with patch.object(feedback_module, "report_issue", return_value={
            "id": 102,
            "title": "测试反馈",
            "status": "open",
        }):
            await client.post("/feedback", json={
                "title": "测试反馈",
                "severity": "low",
            })

        # 直接查 SQLite，确认记录存在
        feedbacks = storage.sqlite.list_feedbacks_by_user("test-user")
        assert len(feedbacks) == 1
        assert feedbacks[0]["title"] == "测试反馈"
        assert feedbacks[0]["status"] == "pending"

    async def test_submit_feedback_returns_422_for_empty_title(self, client):
        response = await client.post("/feedback", json={
            "title": "   ",
            "severity": "low",
        })

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail[0]["loc"] == ["body", "title"]

    async def test_submit_feedback_returns_422_for_invalid_severity(self, client):
        response = await client.post("/feedback", json={
            "title": "严重级别错误",
            "severity": "urgent",
        })

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail[0]["loc"] == ["body", "severity"]


class TestFeedbackListAndGet:
    """GET /feedback 和 GET /feedback/{id} 测试"""

    async def test_list_feedbacks_returns_user_feedbacks(self, client):
        """GET /feedback 返回当前用户的反馈列表"""
        storage: _MockSyncService = client._mock_storage
        storage.sqlite.create_feedback("test-user", "反馈A", "描述A", "low")
        storage.sqlite.create_feedback("test-user", "反馈B", "描述B", "high")

        response = await client.get("/feedback")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = [item["title"] for item in data["items"]]
        assert "反馈A" in titles
        assert "反馈B" in titles

    async def test_list_feedbacks_excludes_other_users(self, client):
        """GET /feedback 不返回其他用户的反馈"""
        storage: _MockSyncService = client._mock_storage
        storage.sqlite.create_feedback("test-user", "我的反馈")
        storage.sqlite.create_feedback("other-user", "别人的反馈")

        response = await client.get("/feedback")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "我的反馈"

    async def test_get_feedback_by_id(self, client):
        """GET /feedback/{id} 返回单条反馈"""
        storage: _MockSyncService = client._mock_storage
        fb = storage.sqlite.create_feedback("test-user", "详情反馈", "详情描述", "critical")

        response = await client.get(f"/feedback/{fb['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == fb["id"]
        assert data["title"] == "详情反馈"
        assert data["description"] == "详情描述"
        assert data["severity"] == "critical"

    async def test_get_feedback_other_user_returns_404(self, client):
        """GET /feedback/{id} 对其他用户的反馈返回 404"""
        storage: _MockSyncService = client._mock_storage
        fb = storage.sqlite.create_feedback("other-user", "别人的反馈")

        response = await client.get(f"/feedback/{fb['id']}")
        assert response.status_code == 404

    async def test_get_feedback_nonexistent_returns_404(self, client):
        """GET /feedback/{id} 对不存在的 ID 返回 404"""
        response = await client.get("/feedback/99999")
        assert response.status_code == 404


class TestFeedbackAuth:
    """认证测试 - 无 token 时返回 401/403"""

    async def test_list_feedbacks_requires_auth(self):
        app = FastAPI()
        app.include_router(router)
        # 不 override get_current_user
        with patch.object(feedback_module, "get_storage", return_value=_MockSyncService()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as unauth_client:
                response = await unauth_client.get("/feedback")
        assert response.status_code in (401, 403)

    async def test_get_feedback_requires_auth(self):
        app = FastAPI()
        app.include_router(router)
        with patch.object(feedback_module, "get_storage", return_value=_MockSyncService()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as unauth_client:
                response = await unauth_client.get("/feedback/1")
        assert response.status_code in (401, 403)
