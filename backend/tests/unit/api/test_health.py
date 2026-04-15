"""B34: Health check 增强 — 依赖连接检查测试"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from httpx import AsyncClient, ASGITransport

from app.main import app, _check_services


@pytest.fixture
def mock_storage():
    """创建 mock SyncService"""
    storage = MagicMock()

    # SQLite
    sqlite = MagicMock()
    conn = MagicMock()
    conn.execute = MagicMock(return_value=None)
    sqlite._get_conn = MagicMock(return_value=conn)
    storage.sqlite = sqlite

    # Neo4j
    neo4j = MagicMock()
    neo4j._driver = MagicMock()  # 非空 = 已连接
    storage.neo4j = neo4j

    # Qdrant
    qdrant = MagicMock()
    qdrant._client = MagicMock()  # 非空 = 已连接
    storage.qdrant = qdrant

    return storage


# ===========================================================================
# _check_services 单元测试
# ===========================================================================

class TestCheckServices:
    """_check_services 函数逻辑"""

    def test_all_ok(self, mock_storage):
        """全部服务正常"""
        result = _check_services(mock_storage)
        assert result == {"sqlite": "ok", "neo4j": "ok", "qdrant": "ok"}

    def test_sqlite_none(self, mock_storage):
        """SQLite 为 None → error"""
        mock_storage.sqlite = None
        result = _check_services(mock_storage)
        assert result["sqlite"] == "error"
        assert result["neo4j"] == "ok"
        assert result["qdrant"] == "ok"

    def test_sqlite_query_fails(self, mock_storage):
        """SQLite 查询失败 → error"""
        mock_storage.sqlite._get_conn.return_value.execute.side_effect = Exception("db error")
        result = _check_services(mock_storage)
        assert result["sqlite"] == "error"

    def test_neo4j_unavailable(self, mock_storage):
        """Neo4j driver 为 None → unavailable"""
        mock_storage.neo4j._driver = None
        result = _check_services(mock_storage)
        assert result["neo4j"] == "unavailable"
        assert result["sqlite"] == "ok"
        assert result["qdrant"] == "ok"

    def test_neo4j_none(self, mock_storage):
        """Neo4j 客户端为 None → unavailable"""
        mock_storage.neo4j = None
        result = _check_services(mock_storage)
        assert result["neo4j"] == "unavailable"

    def test_qdrant_unavailable(self, mock_storage):
        """Qdrant client 为 None → unavailable"""
        mock_storage.qdrant._client = None
        result = _check_services(mock_storage)
        assert result["qdrant"] == "unavailable"
        assert result["sqlite"] == "ok"

    def test_qdrant_none(self, mock_storage):
        """Qdrant 客户端为 None → unavailable"""
        mock_storage.qdrant = None
        result = _check_services(mock_storage)
        assert result["qdrant"] == "unavailable"

    def test_both_non_core_unavailable(self, mock_storage):
        """Neo4j + Qdrant 同时不可达 → 都标记 unavailable"""
        mock_storage.neo4j._driver = None
        mock_storage.qdrant._client = None
        result = _check_services(mock_storage)
        assert result == {
            "sqlite": "ok",
            "neo4j": "unavailable",
            "qdrant": "unavailable",
        }

    def test_storage_none(self):
        """storage 为 None → SQLite error, 其余 unavailable"""
        result = _check_services(None)
        assert result["sqlite"] == "error"
        assert result["neo4j"] == "unavailable"
        assert result["qdrant"] == "unavailable"


# ===========================================================================
# API 端点测试
# ===========================================================================

class TestHealthEndpoint:
    """/health API 端点"""

    @pytest.mark.asyncio
    async def test_all_healthy(self, mock_storage):
        """全部正常 → 200 + status: ok"""
        with patch("app.main.deps") as mock_deps:
            mock_deps.storage = mock_storage
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["services"]["sqlite"] == "ok"
        assert data["services"]["neo4j"] == "ok"
        assert data["services"]["qdrant"] == "ok"

    @pytest.mark.asyncio
    async def test_sqlite_down_returns_503(self, mock_storage):
        """SQLite 不可达 → 503 + status: degraded"""
        mock_storage.sqlite = None
        with patch("app.main.deps") as mock_deps:
            mock_deps.storage = mock_storage
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health")

        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["services"]["sqlite"] == "error"

    @pytest.mark.asyncio
    async def test_neo4j_down_returns_200_degraded(self, mock_storage):
        """Neo4j 不可达 → 200 + status: degraded"""
        mock_storage.neo4j._driver = None
        with patch("app.main.deps") as mock_deps:
            mock_deps.storage = mock_storage
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["services"]["neo4j"] == "unavailable"
        assert data["services"]["sqlite"] == "ok"

    @pytest.mark.asyncio
    async def test_qdrant_down_returns_200_degraded(self, mock_storage):
        """Qdrant 不可达 → 200 + status: degraded"""
        mock_storage.qdrant._client = None
        with patch("app.main.deps") as mock_deps:
            mock_deps.storage = mock_storage
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["services"]["qdrant"] == "unavailable"
        assert data["services"]["sqlite"] == "ok"

    @pytest.mark.asyncio
    async def test_both_non_core_down_returns_200_degraded(self, mock_storage):
        """Neo4j + Qdrant 同时不可达 → 200 + status: degraded"""
        mock_storage.neo4j._driver = None
        mock_storage.qdrant._client = None
        with patch("app.main.deps") as mock_deps:
            mock_deps.storage = mock_storage
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                resp = await c.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["services"]["neo4j"] == "unavailable"
        assert data["services"]["qdrant"] == "unavailable"
        assert data["services"]["sqlite"] == "ok"
