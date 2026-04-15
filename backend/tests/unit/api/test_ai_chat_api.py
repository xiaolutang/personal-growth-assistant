"""AI 对话 API 测试"""
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "ai_chat.py"
SPEC = importlib.util.spec_from_file_location("ai_chat_router_module", MODULE_PATH)
ai_chat_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(ai_chat_module)
router = ai_chat_module.router

# Mock user for auth bypass
_mock_user = MagicMock()
_mock_user.id = "test-user"


@pytest.fixture
async def client():
    """创建带 mock auth 的测试客户端"""
    app = FastAPI()

    # Override auth
    from app.routers.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: _mock_user

    app.include_router(router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """兼容 fixture — auth 已在 client 中 override，返回空 dict"""
    return {}


class TestAIChatAPI:
    """POST /ai/chat 测试"""

    async def test_chat_no_auth(self):
        """无认证返回 401/403"""
        app = FastAPI()
        app.include_router(router)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as unauth_client:
            response = await unauth_client.post("/ai/chat", json={"message": "hello"})
        assert response.status_code in (401, 403)

    async def test_chat_empty_message(self, client):
        """空消息返回 422"""
        response = await client.post("/ai/chat", json={"message": ""})
        assert response.status_code == 422

    async def test_chat_with_context(self, client):
        """带 context 的请求"""
        with patch("app.services.ai_chat_service.AIChatService.chat_stream") as mock_stream:
            async def fake_stream(*args, **kwargs):
                yield "你好"
            mock_stream.return_value = fake_stream()

            response = await client.post(
                "/ai/chat",
                json={
                    "message": "帮我看看今天有什么任务",
                    "context": {"page": "home", "filters": {"status": "doing"}},
                },
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

    async def test_chat_without_context(self, client):
        """无 context 降级为通用对话"""
        with patch("app.services.ai_chat_service.AIChatService.chat_stream") as mock_stream:
            async def fake_stream(*args, **kwargs):
                yield "通用回复"
            mock_stream.return_value = fake_stream()

            response = await client.post(
                "/ai/chat",
                json={"message": "你好"},
            )
            assert response.status_code == 200

    async def test_chat_llm_unavailable(self, client):
        """LLM 不可用时返回降级消息"""
        with patch("app.services.ai_chat_service.AIChatService.chat_stream") as mock_stream:
            async def fake_stream(*args, **kwargs):
                yield "AI 助手暂不可用，请稍后再试。"
            mock_stream.return_value = fake_stream()

            response = await client.post(
                "/ai/chat",
                json={"message": "hello"},
            )
            assert response.status_code == 200

    async def test_chat_sse_format(self, client):
        """SSE 格式验证"""
        with patch("app.services.ai_chat_service.AIChatService.chat_stream") as mock_stream:
            async def fake_stream(*args, **kwargs):
                yield "你好"
                yield "世界"
            mock_stream.return_value = fake_stream()

            response = await client.post(
                "/ai/chat",
                json={"message": "hello"},
            )
            assert response.status_code == 200
            content = response.text
            assert "data:" in content
            assert "[DONE]" in content
