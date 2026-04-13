"""TD10: GET /entries 认证拦截测试 — 验证未认证请求被拦截"""
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
async def test_get_entries_returns_auth_error_when_not_authenticated():
    """无 token 时 GET /entries 返回 401 或 403（认证拦截）"""
    deps.storage = None
    deps.reset_all_services()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/entries")

    assert response.status_code in (401, 403)
