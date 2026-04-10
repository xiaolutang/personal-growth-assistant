"""TD10: GET /entries 503 集成测试 — 验证 storage 未初始化时返回 503"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.routers import deps


@pytest.fixture(autouse=True)
def _reset_deps():
    """确保测试后恢复 deps 状态"""
    original_storage = deps.storage
    deps.reset_all_services()
    yield
    deps.storage = original_storage
    deps.reset_all_services()


@pytest.mark.asyncio
async def test_get_entries_returns_503_when_storage_not_initialized():
    """storage=None 时 GET /entries 返回 503 且 body 含 '存储服务未初始化'"""
    deps.storage = None
    deps.reset_all_services()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/entries")

    assert response.status_code == 503
    assert "存储服务未初始化" in response.json()["detail"]
