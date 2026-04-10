"""CORS 配置测试"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_preflight_allows_expected_methods(client: AsyncClient):
    """OPTIONS 预检请求返回正确的 Allow-Methods 和 Allow-Headers"""
    response = await client.options(
        "/entries",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,X-UID",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    allow_methods = response.headers.get("access-control-allow-methods", "")
    for method in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
        assert method in allow_methods, f"{method} not in allow_methods: {allow_methods}"
    allow_headers = response.headers.get("access-control-allow-headers", "")
    for header in ["Content-Type", "Authorization", "X-UID", "X-Request-ID"]:
        assert header.lower() in allow_headers.lower(), f"{header} not in allow_headers: {allow_headers}"


@pytest.mark.asyncio
async def test_cors_rejects_disallowed_origin(client: AsyncClient):
    """不允许的源被 CORS 拒绝"""
    response = await client.options(
        "/entries",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_rejects_disallowed_method(client: AsyncClient):
    """非允许方法（如 TRACE）预检返回 400"""
    response = await client.options(
        "/entries",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "TRACE",
        },
    )
    # CORSMiddleware 对不在 allow_methods 中的方法返回 400 Bad Request
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cors_get_request_with_allowed_origin(client: AsyncClient):
    """GET 请求带允许的 Origin 返回 CORS 头"""
    response = await client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
