"""B84: 反馈状态同步测试 — POST /feedback/sync"""
import importlib.util
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from app.infrastructure.storage.sqlite import SQLiteStorage

MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "feedback.py"
SPEC = importlib.util.spec_from_file_location("feedback_sync_module", MODULE_PATH)
feedback_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(feedback_module)
router = feedback_module.router

_mock_user = MagicMock()
_mock_user.id = "test-user"


class _MockSyncService:
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
    app = FastAPI()
    from app.routers.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: _mock_user

    mock_storage = _MockSyncService()
    with patch.object(feedback_module, "get_storage", return_value=mock_storage):
        with patch.object(feedback_module, "get_settings") as mock_settings:
            mock_settings.return_value.LOG_SERVICE_URL = "http://log-service:8001"
            app.include_router(router)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                c._mock_storage = mock_storage
                yield c

    app.dependency_overrides.clear()
    mock_storage.cleanup()


def _mock_httpx_response(status_code: int, json_data: dict | None = None):
    """构建 mock httpx.Response"""
    resp = MagicMock(spec=Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


def _create_reported_feedback(sqlite, user_id="test-user", title="测试反馈"):
    """创建一条已上报的反馈（带 log_service_issue_id）"""
    fb = sqlite.create_feedback(user_id, title)
    sqlite.update_feedback_status(fb["id"], "reported", log_service_issue_id=100)
    return sqlite.get_feedback_by_id(fb["id"], user_id)


class TestSyncSuccess:
    """正常同步场景"""

    async def test_sync_with_issue_id_success(self, client):
        """有 log_service_issue_id 的反馈同步成功"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "in_progress"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_count"] == 1
        assert data["updated_count"] == 1

    async def test_remote_pending_maps_to_reported(self, client):
        """远程 pending → 本地 reported"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)
        # 先手动把 status 改回 pending 来测试映射
        storage.sqlite.sync_feedback_status(fb["id"], "pending")

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "pending"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        # 找到这条反馈
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "reported"

    async def test_remote_in_progress_updates_status(self, client):
        """远程 in_progress → 本地 in_progress + updated_at 刷新"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "in_progress"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "in_progress"
        assert synced_fb["updated_at"] is not None

    async def test_remote_resolved_updates_status(self, client):
        """远程 resolved → 本地 resolved"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "resolved"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "resolved"

    async def test_remote_status_unchanged_no_update(self, client):
        """远程状态未变更 → updated_at 不变（非首次）"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)
        # 先设置 updated_at（非首次）
        storage.sqlite.sync_feedback_status(fb["id"], "reported", "2026-01-01T00:00:00")
        old_fb = storage.sqlite.get_feedback_by_id(fb["id"], "test-user")

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "pending"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["updated_at"] == "2026-01-01T00:00:00"

    async def test_first_sync_writes_updated_at(self, client):
        """首次同步成功但状态未变 → updated_at 首次写入"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)
        # updated_at 应该是 None（刚创建、从未同步）
        assert fb.get("updated_at") is None

        # 远程也是 pending → 本地 reported（状态不变）
        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "pending"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        # 首次同步：状态不变但 updated_at 应写入
        assert synced_fb["updated_at"] is not None

    async def test_synced_count_updated_count_assertion(self, client):
        """synced_count/updated_count 精确断言"""
        storage: _MockSyncService = client._mock_storage
        _create_reported_feedback(storage.sqlite, title="FB1")
        fb2 = _create_reported_feedback(storage.sqlite, title="FB2")
        storage.sqlite.update_feedback_status(fb2["id"], "reported", log_service_issue_id=101)

        call_count = 0
        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "100" in url:
                return _mock_httpx_response(200, {"id": 100, "status": "in_progress"})
            else:
                return _mock_httpx_response(200, {"id": 101, "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 2
        assert data["updated_count"] == 2

    async def test_get_feedback_after_sync(self, client):
        """同步后 GET /feedback 返回最新状态"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "resolved"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            await client.post("/feedback/sync")

        response = await client.get("/feedback")
        data = response.json()
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "resolved"


class TestSyncDegradation:
    """降级和异常场景"""

    async def test_log_service_unavailable(self, client):
        """log-service 不可用 → synced_count=0，本地状态不变"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock,
                    side_effect=Exception("Connection refused")):
            response = await client.post("/feedback/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_count"] == 0
        assert data["updated_count"] == 0
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "reported"

    async def test_remote_404_keeps_status(self, client):
        """远程 issue 404 → 该条 status 和 updated_at 均不变"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        mock_resp = _mock_httpx_response(404)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 0
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "reported"
        assert synced_fb["updated_at"] is None

    async def test_single_timeout_skips_continues(self, client):
        """单条超时 → 该条跳过，其他继续"""
        storage: _MockSyncService = client._mock_storage
        fb1 = _create_reported_feedback(storage.sqlite, title="FB1")
        fb2 = _create_reported_feedback(storage.sqlite, title="FB2")
        storage.sqlite.update_feedback_status(fb2["id"], "reported", log_service_issue_id=101)

        import httpx as _httpx
        call_count = 0
        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "100" in url:
                raise _httpx.TimeoutException("timeout")
            return _mock_httpx_response(200, {"id": 101, "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 1  # fb2 成功
        assert data["updated_count"] == 1
        # fb1 状态不变
        fb1_after = next(f for f in data["items"] if f["id"] == fb1["id"])
        assert fb1_after["status"] == "reported"
        # fb2 已更新
        fb2_after = next(f for f in data["items"] if f["id"] == fb2["id"])
        assert fb2_after["status"] == "resolved"

    async def test_unknown_status_keeps_original(self, client):
        """远程返回未知 status 值 → 保持原状态不更新"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "unknown_status"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 0
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "reported"


class TestSyncBoundary:
    """边界场景"""

    async def test_no_issue_id_skipped(self, client):
        """无 log_service_issue_id 的反馈跳过同步"""
        storage: _MockSyncService = client._mock_storage
        storage.sqlite.create_feedback("test-user", "无远程ID的反馈")

        response = await client.post("/feedback/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["synced_count"] == 0
        assert data["updated_count"] == 0
        assert data["total"] == 1

    async def test_in_progress_meets_404_keeps_status(self, client):
        """本地已是 in_progress 的反馈遇到远程 404 时保持当前状态不变"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)
        storage.sqlite.sync_feedback_status(fb["id"], "in_progress", "2026-01-01T00:00:00")

        mock_resp = _mock_httpx_response(404)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "in_progress"
        assert synced_fb["updated_at"] == "2026-01-01T00:00:00"

    async def test_batch_sync_20_plus(self, client):
        """大量反馈批量同步（20+）"""
        storage: _MockSyncService = client._mock_storage
        for i in range(25):
            fb = storage.sqlite.create_feedback("test-user", f"反馈{i}")
            storage.sqlite.update_feedback_status(fb["id"], "reported", log_service_issue_id=200 + i)

        async def mock_get(url, **kwargs):
            issue_id = int(url.rstrip("/").split("/")[-1])
            return _mock_httpx_response(200, {"id": issue_id, "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 25
        assert data["updated_count"] == 25
        assert data["total"] == 25

    async def test_idempotent_repeated_sync(self, client):
        """幂等：重复同步不产生副作用"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite)

        mock_resp = _mock_httpx_response(200, {"id": 100, "status": "in_progress"})

        # 第一次同步
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            r1 = await client.post("/feedback/sync")
        d1 = r1.json()

        # 第二次同步（状态已经是 in_progress，updated_at 已有值）
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            r2 = await client.post("/feedback/sync")
        d2 = r2.json()

        fb1 = next(f for f in d1["items"] if f["id"] == fb["id"])
        fb2 = next(f for f in d2["items"] if f["id"] == fb["id"])
        # 第二次状态不变、updated_at 不变
        assert fb2["status"] == fb1["status"] == "in_progress"
        assert fb2["updated_at"] == fb1["updated_at"]


class TestSyncRegression:
    """回归：POST/GET /feedback 行为不变 + 认证"""

    async def test_post_feedback_still_works(self, client):
        """POST /feedback 行为不变"""
        with patch.object(feedback_module, "report_issue", return_value={
            "id": 101, "title": "测试", "status": "open",
        }):
            response = await client.post("/feedback", json={
                "title": "测试提交",
                "severity": "low",
            })

        assert response.status_code == 200
        assert response.json()["success"] is True

    async def test_get_feedback_still_works(self, client):
        """GET /feedback 行为不变"""
        storage: _MockSyncService = client._mock_storage
        storage.sqlite.create_feedback("test-user", "回归测试")

        response = await client.get("/feedback")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    async def test_sync_requires_auth(self):
        """未认证访问 /feedback/sync 返回 401/403"""
        app = FastAPI()
        app.include_router(router)
        with patch.object(feedback_module, "get_storage", return_value=_MockSyncService()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as unauth:
                response = await unauth.post("/feedback/sync")
        assert response.status_code in (401, 403)

    async def test_sync_user_isolation(self, client):
        """不同用户的反馈互不影响"""
        storage: _MockSyncService = client._mock_storage
        # 其他用户的反馈
        other_fb = storage.sqlite.create_feedback("other-user", "别人的反馈")
        storage.sqlite.update_feedback_status(other_fb["id"], "reported", log_service_issue_id=999)
        # 当前用户反馈
        _create_reported_feedback(storage.sqlite)

        async def mock_get(url, **kwargs):
            return _mock_httpx_response(200, {"id": 999, "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        data = response.json()
        # 只同步当前用户的 1 条，不包括 other-user 的
        assert data["synced_count"] == 1
        assert data["total"] == 1
