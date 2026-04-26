"""B111 Analytics 埋点 API 测试 — 8 个场景"""

import sqlite3
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock

from app.main import app
from app.services.auth_service import create_access_token
from app.routers import deps
from app.infrastructure.storage.user_storage import UserStorage
from app.models.user import UserCreate
import tempfile


# === 辅助 ===

async def _make_user_client(user_id: str) -> AsyncClient:
    """为指定 user_id 创建带认证的 client"""
    token = create_access_token(user_id)
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test", timeout=60.0)
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# === 测试 ===

@pytest.mark.asyncio
class TestAnalyticsAPI:

    @pytest.fixture(autouse=True)
    async def _ensure_analytics_table(self, storage):
        """每个测试前确保 analytics_events 表已创建"""
        from app.services.analytics_service import AnalyticsService
        svc = AnalyticsService(sqlite_storage=storage.sqlite)
        svc.ensure_table()

    async def test_post_event_normal(self, client, storage, test_user):
        """POST /analytics/event 正常存储"""
        resp = await client.post("/analytics/event", json={
            "event_type": "entry_created",
            "metadata": {"category": "note"},
        })
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # 验证数据库有记录
        conn = storage.sqlite.get_connection()
        try:
            rows = conn.execute(
                "SELECT user_id, event_type, metadata FROM analytics_events WHERE user_id = ?",
                (test_user.id,),
            ).fetchall()
            assert len(rows) == 1
            assert rows[0][0] == test_user.id
            assert rows[0][1] == "entry_created"
            assert rows[0][2] is not None  # metadata JSON
        finally:
            conn.close()

    async def test_event_isolated_by_user_id(self, client, storage, test_user):
        """事件按 user_id 隔离"""
        # 用户 A 创建事件
        await client.post("/analytics/event", json={"event_type": "page_viewed"})

        # 创建用户 B
        user_b = deps._user_storage.create_user(UserCreate(
            username="user_b_analytics", email="b_analytics@example.com", password="pass123"
        ))
        client_b = await _make_user_client(user_b.id)
        try:
            await client_b.post("/analytics/event", json={"event_type": "search_performed"})

            # 用户 B 只能看到自己的事件
            conn = storage.sqlite.get_connection()
            try:
                rows_b = conn.execute(
                    "SELECT event_type FROM analytics_events WHERE user_id = ?",
                    (user_b.id,),
                ).fetchall()
                assert len(rows_b) == 1
                assert rows_b[0][0] == "search_performed"

                # 用户 A 只有自己的一条
                rows_a = conn.execute(
                    "SELECT event_type FROM analytics_events WHERE user_id = ?",
                    (test_user.id,),
                ).fetchall()
                assert len(rows_a) == 1
                assert rows_a[0][0] == "page_viewed"
            finally:
                conn.close()
        finally:
            await client_b.aclose()

    async def test_metadata_optional(self, client, storage, test_user):
        """metadata 可选（不传 / null）"""
        # 不传 metadata
        resp = await client.post("/analytics/event", json={"event_type": "entry_viewed"})
        assert resp.status_code == 200

        # metadata 为 null
        resp2 = await client.post("/analytics/event", json={
            "event_type": "chat_message_sent",
            "metadata": None,
        })
        assert resp2.status_code == 200

        # 验证 metadata 列都是 NULL
        conn = storage.sqlite.get_connection()
        try:
            rows = conn.execute(
                "SELECT metadata FROM analytics_events WHERE user_id = ?",
                (test_user.id,),
            ).fetchall()
            assert len(rows) == 2
            assert rows[0][0] is None
            assert rows[1][0] is None
        finally:
            conn.close()

    async def test_unauthenticated_returns_401(self, storage):
        """无认证返回 401"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as anon:
            resp = await anon.post("/analytics/event", json={"event_type": "page_viewed"})
            assert resp.status_code == 401

    async def test_write_failure_still_returns_200(self, client, storage, test_user):
        """写入失败不影响业务（返回 200）"""
        with patch("app.services.analytics_service.AnalyticsService.record_event", side_effect=Exception("DB down")):
            resp = await client.post("/analytics/event", json={"event_type": "page_viewed"})
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

    async def test_table_auto_created(self, temp_data_dir):
        """表自动创建"""
        from app.services.analytics_service import AnalyticsService
        from app.infrastructure.storage.sqlite import SQLiteStorage

        sqlite_storage = SQLiteStorage(db_path=f"{temp_data_dir}/analytics_test.db")
        svc = AnalyticsService(sqlite_storage=sqlite_storage)
        svc.ensure_table()

        conn = sqlite_storage.get_connection()
        try:
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='analytics_events'"
            ).fetchone()
            assert result is not None
        finally:
            conn.close()

    async def test_invalid_event_type_returns_422(self, client):
        """无效 event_type 返回 422"""
        resp = await client.post("/analytics/event", json={
            "event_type": "invalid_event",
        })
        assert resp.status_code == 422

    async def test_metadata_non_object_returns_422(self, client):
        """metadata 非对象返回 422"""
        resp = await client.post("/analytics/event", json={
            "event_type": "page_viewed",
            "metadata": "not_a_dict",
        })
        assert resp.status_code == 422
