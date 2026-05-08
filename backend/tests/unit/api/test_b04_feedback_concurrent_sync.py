"""B04: sync_feedbacks 并发化测试 — asyncio.gather + semaphore 限流"""
import importlib.util
import os
import tempfile
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from app.infrastructure.storage.sqlite import SQLiteStorage

MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "feedback.py"
SPEC = importlib.util.spec_from_file_location("feedback_b04_module", MODULE_PATH)
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


def _create_reported_feedback(sqlite, user_id="test-user", title="测试反馈", issue_id=100):
    """创建一条已上报的反馈（带 log_service_issue_id）"""
    fb = sqlite.create_feedback(user_id, title)
    sqlite.update_feedback_status(fb["id"], "reported", log_service_issue_id=issue_id)
    return sqlite.get_feedback_by_id(fb["id"], user_id)


class TestConcurrentSync:
    """并发行为测试：验证 asyncio.gather 调用"""

    async def test_gather_concurrent_requests(self, client):
        """sync_feedbacks 使用 asyncio.gather 并发请求（验证 gather 调用）"""
        storage: _MockSyncService = client._mock_storage
        _create_reported_feedback(storage.sqlite, title="FB1", issue_id=100)
        _create_reported_feedback(storage.sqlite, title="FB2", issue_id=101)

        async def mock_get(url, **kwargs):
            return _mock_httpx_response(200, {"id": int(url.rstrip("/").split("/")[-1]), "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            # 捕获 asyncio.gather 调用
            original_gather = asyncio.gather
            gather_called = False
            gather_args_count = 0

            async def tracking_gather(*args, **kwargs):
                nonlocal gather_called, gather_args_count
                gather_called = True
                gather_args_count = len(args)
                return await original_gather(*args, **kwargs)

            with patch("asyncio.gather", side_effect=tracking_gather):
                response = await client.post("/feedback/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_count"] == 2
        assert gather_called, "asyncio.gather should be called"
        assert gather_args_count == 2, f"Expected 2 gather args, got {gather_args_count}"

    async def test_semaphore_limits_concurrency(self, client):
        """semaphore 限流上限测试：>10 个反馈只并发 10 个"""
        storage: _MockSyncService = client._mock_storage
        # 创建 15 条反馈
        for i in range(15):
            _create_reported_feedback(storage.sqlite, title=f"FB{i}", issue_id=200 + i)

        max_concurrent = 0
        current_concurrent = 0

        async def mock_get(url, **kwargs):
            nonlocal max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            # 模拟一些延迟以让并发体现
            await asyncio.sleep(0.01)
            current_concurrent -= 1
            issue_id = int(url.rstrip("/").split("/")[-1])
            return _mock_httpx_response(200, {"id": issue_id, "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["synced_count"] == 15
        # semaphore 限制并发不超过 10
        assert max_concurrent <= 10, f"Max concurrency should be <=10, got {max_concurrent}"


class TestTimeoutIsolation:
    """timeout 场景：单个 HTTP 请求超时不阻塞其他"""

    async def test_single_timeout_does_not_block_others(self, client):
        """单个 HTTP 请求超时不阻塞其他反馈同步"""
        storage: _MockSyncService = client._mock_storage
        fb1 = _create_reported_feedback(storage.sqlite, title="FB1", issue_id=300)
        fb2 = _create_reported_feedback(storage.sqlite, title="FB2", issue_id=301)

        import httpx as _httpx

        async def mock_get(url, **kwargs):
            if "300" in url:
                raise _httpx.TimeoutException("timeout")
            return _mock_httpx_response(200, {"id": 301, "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 1
        assert data["updated_count"] == 1
        # fb1 超时，状态不变
        fb1_after = next(f for f in data["items"] if f["id"] == fb1["id"])
        assert fb1_after["status"] == "reported"
        # fb2 成功
        fb2_after = next(f for f in data["items"] if f["id"] == fb2["id"])
        assert fb2_after["status"] == "resolved"


class TestNon200Isolation:
    """non-200 响应：单个 500 不影响其他反馈同步"""

    async def test_single_500_does_not_affect_others(self, client):
        """单个 500 不影响其他反馈同步"""
        storage: _MockSyncService = client._mock_storage
        fb1 = _create_reported_feedback(storage.sqlite, title="FB1", issue_id=400)
        fb2 = _create_reported_feedback(storage.sqlite, title="FB2", issue_id=401)

        async def mock_get(url, **kwargs):
            if "400" in url:
                return _mock_httpx_response(500, {"error": "internal"})
            return _mock_httpx_response(200, {"id": 401, "status": "resolved"})

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 1
        # fb1 500 → 跳过
        fb1_after = next(f for f in data["items"] if f["id"] == fb1["id"])
        assert fb1_after["status"] == "reported"
        # fb2 成功
        fb2_after = next(f for f in data["items"] if f["id"] == fb2["id"])
        assert fb2_after["status"] == "resolved"


class TestUnknownStatus:
    """unknown remote status：未知状态值处理"""

    async def test_unknown_status_skipped(self, client):
        """未知状态值不更新本地状态"""
        storage: _MockSyncService = client._mock_storage
        fb = _create_reported_feedback(storage.sqlite, title="FB1", issue_id=500)

        mock_resp = _mock_httpx_response(200, {"id": 500, "status": "weird_status"})
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
            response = await client.post("/feedback/sync")

        data = response.json()
        assert data["synced_count"] == 0
        synced_fb = next(f for f in data["items"] if f["id"] == fb["id"])
        assert synced_fb["status"] == "reported"


class TestMixedSuccessFailure:
    """mixed success-failure：部分成功部分失败的批次结果"""

    async def test_mixed_batch_partial_success(self, client):
        """部分成功部分失败的批次结果"""
        storage: _MockSyncService = client._mock_storage
        fb1 = _create_reported_feedback(storage.sqlite, title="FB1", issue_id=600)
        fb2 = _create_reported_feedback(storage.sqlite, title="FB2", issue_id=601)
        fb3 = _create_reported_feedback(storage.sqlite, title="FB3", issue_id=602)
        fb4 = _create_reported_feedback(storage.sqlite, title="FB4", issue_id=603)

        import httpx as _httpx

        async def mock_get(url, **kwargs):
            issue_id = int(url.rstrip("/").split("/")[-1])
            if issue_id == 600:
                return _mock_httpx_response(200, {"id": 600, "status": "resolved"})
            elif issue_id == 601:
                raise _httpx.TimeoutException("timeout")
            elif issue_id == 602:
                return _mock_httpx_response(500, {"error": "internal"})
            elif issue_id == 603:
                return _mock_httpx_response(200, {"id": 603, "status": "weird"})
            return _mock_httpx_response(404)

        with patch("httpx.AsyncClient.get", side_effect=mock_get):
            response = await client.post("/feedback/sync")

        data = response.json()
        # 只有 fb1 成功同步
        assert data["synced_count"] == 1
        assert data["updated_count"] == 1

        fb1_after = next(f for f in data["items"] if f["id"] == fb1["id"])
        assert fb1_after["status"] == "resolved"

        # 其余状态不变
        for fb_orig in [fb2, fb3, fb4]:
            fb_after = next(f for f in data["items"] if f["id"] == fb_orig["id"])
            assert fb_after["status"] == "reported"


class TestNoDeprecationWarning:
    """验证不再使用 asyncio.get_event_loop()"""

    async def test_no_get_event_loop_in_feedback_module(self):
        """feedback.py 中不再使用 asyncio.get_event_loop()"""
        import inspect
        source = inspect.getsource(feedback_module)
        assert "get_event_loop()" not in source, (
            "feedback.py still uses asyncio.get_event_loop(), should use get_running_loop()"
        )


class TestAnalyticsServiceConnManager:
    """AnalyticsService 连接管理回归测试 — 使用 _conn() 上下文管理器"""

    def test_ensure_table_uses_conn_context_manager(self, tmp_path):
        """ensure_table 使用 _conn() 上下文管理器，不再手动 get_connection/close"""
        from app.infrastructure.storage.sqlite import SQLiteStorage
        from app.services.analytics_service import AnalyticsService
        import inspect

        source = inspect.getsource(AnalyticsService.ensure_table)
        assert "get_connection" not in source, (
            "ensure_table should not use get_connection()"
        )
        assert "conn.close()" not in source, (
            "ensure_table should not manually close connections"
        )
        assert "_conn()" in source, (
            "ensure_table should use _conn() context manager"
        )

    def test_record_event_uses_conn_context_manager(self):
        """record_event 使用 _conn() 上下文管理器"""
        from app.services.analytics_service import AnalyticsService
        import inspect

        source = inspect.getsource(AnalyticsService.record_event)
        assert "get_connection" not in source
        assert "conn.close()" not in source
        assert "_conn()" in source

    def test_analytics_no_manual_close_pattern(self):
        """AnalyticsService 整体不再有手动 get_connection + commit + close 模式"""
        from app.services.analytics_service import AnalyticsService
        import inspect

        source = inspect.getsource(AnalyticsService)
        assert "conn.close()" not in source, (
            "AnalyticsService should not have manual conn.close()"
        )
        assert "conn.commit()" not in source, (
            "AnalyticsService should not have manual conn.commit()"
        )

    def test_analytics_functional_with_conn(self, tmp_path):
        """功能验证：ensure_table + record_event 通过 _conn() 正常工作"""
        from app.infrastructure.storage.sqlite import SQLiteStorage
        from app.services.analytics_service import AnalyticsService

        db_path = str(tmp_path / "analytics_test.db")
        sqlite_storage = SQLiteStorage(db_path=db_path)
        svc = AnalyticsService(sqlite_storage=sqlite_storage)

        # ensure_table
        svc.ensure_table()

        # record_event
        svc.record_event("user-1", "page_viewed", {"page": "home"})

        # 验证数据已写入
        with sqlite_storage._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, event_type, metadata FROM analytics_events"
            ).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == "user-1"
            assert rows[0][1] == "page_viewed"

    def test_record_event_failure_silent(self, tmp_path):
        """record_event 失败时静默（best-effort）"""
        from app.infrastructure.storage.sqlite import SQLiteStorage
        from app.services.analytics_service import AnalyticsService
        from unittest.mock import patch, MagicMock

        db_path = str(tmp_path / "analytics_test.db")
        sqlite_storage = SQLiteStorage(db_path=db_path)
        svc = AnalyticsService(sqlite_storage=sqlite_storage)

        # 模拟 _conn 抛异常
        with patch.object(sqlite_storage, "_conn", side_effect=Exception("DB error")):
            # 不抛异常，静默失败
            svc.record_event("user-1", "page_viewed")

    def test_no_get_event_loop_in_analytics(self):
        """analytics_service.py 不使用 asyncio.get_event_loop()"""
        from app.services import analytics_service
        import inspect

        source = inspect.getsource(analytics_service)
        assert "get_event_loop()" not in source
