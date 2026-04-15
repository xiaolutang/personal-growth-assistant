"""B33: POST /chat API 级路由测试 — 验证 user_id 从 JWT 透传到 ChatService

使用 conftest.py 的 client fixture（真实 FastAPI app + JWT token），
通过 patch app.routers.parse._chat_service 来验证路由层透传。
"""
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


def _make_process_intent_mock():
    """创建一个行为类似 async generator 函数的 mock"""
    async def fake_gen(*args, **kwargs):
        yield 'event: done\ndata: {"message": "ok"}\n\n'
    return MagicMock(side_effect=fake_gen)


def _make_chat_service_mock():
    """创建完整的 mock _chat_service"""
    mock_svc = MagicMock()
    mock_svc.detect_intent = AsyncMock(return_value={
        "intent": "read",
        "confidence": 0.9,
        "query": "查看任务",
        "entities": {},
    })
    return mock_svc


class TestChatAPIUserIdThreading:
    """POST /chat 路由级测试 — 验证 user.id 从 JWT 正确透传"""

    @pytest.mark.asyncio
    async def test_chat_passes_user_id_to_process_intent(self, client):
        """/chat 路由将认证用户的 user.id 传递给 process_intent"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc):
            response = await client.post(
                "/chat",
                json={"text": "查看任务", "session_id": "sess-1"},
            )

        assert response.status_code == 200
        assert mock_process.called
        call_kwargs = mock_process.call_args.kwargs
        assert call_kwargs["user_id"] is not None
        assert call_kwargs["user_id"] != "_default"

    @pytest.mark.asyncio
    async def test_chat_namespaces_session_id(self, client):
        """/chat 路由将 session_id 命名空间化为 {user_id}:{session_id}"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc):
            response = await client.post(
                "/chat",
                json={"text": "查看任务", "session_id": "my-sess"},
            )

        assert response.status_code == 200
        call_kwargs = mock_process.call_args.kwargs
        session_id = call_kwargs["session_id"]
        assert ":" in session_id
        assert session_id.endswith(":my-sess")
        user_id_part = session_id.rsplit(":", 1)[0]
        assert user_id_part != "_default"

    @pytest.mark.asyncio
    async def test_chat_with_confirm_passes_user_id(self, client):
        """带 confirm 的 /chat 调用也传递 user_id"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.detect_intent = AsyncMock(return_value={
            "intent": "delete",
            "confidence": 0.9,
            "query": "删除",
            "entities": {},
        })
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc):
            response = await client.post(
                "/chat",
                json={
                    "text": "确认删除",
                    "session_id": "sess-2",
                    "confirm": {"action": "delete", "item_id": "e1"},
                },
            )

        assert response.status_code == 200
        call_kwargs = mock_process.call_args.kwargs
        assert call_kwargs["user_id"] is not None
        assert call_kwargs["user_id"] != "_default"
        assert call_kwargs["confirm"]["item_id"] == "e1"

    @pytest.mark.asyncio
    async def test_chat_skip_intent_still_passes_user_id(self, client):
        """skip_intent=true 时仍传递 user_id"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc):
            response = await client.post(
                "/chat",
                json={"text": "记个任务", "session_id": "sess-3", "skip_intent": True},
            )

        assert response.status_code == 200
        call_kwargs = mock_process.call_args.kwargs
        assert call_kwargs["user_id"] is not None
        assert call_kwargs["user_id"] != "_default"
