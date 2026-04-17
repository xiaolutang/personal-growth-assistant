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
    async def test_chat_passes_user_id_to_process_intent(self, client, test_user):
        """/chat 路由将认证用户的 user.id 精确传递给 process_intent"""
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
        assert call_kwargs["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_chat_namespaces_session_id(self, client, test_user):
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
        assert session_id == f"{test_user.id}:my-sess"

    @pytest.mark.asyncio
    async def test_chat_with_confirm_passes_user_id(self, client, test_user):
        """带 confirm 的 /chat 调用也传递精确 user_id"""
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
        assert call_kwargs["user_id"] == test_user.id
        assert call_kwargs["confirm"]["item_id"] == "e1"

    @pytest.mark.asyncio
    async def test_chat_skip_intent_still_passes_user_id(self, client, test_user):
        """skip_intent=true 时仍传递精确 user_id"""
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
        assert call_kwargs["user_id"] == test_user.id


class TestChatAPIPageContext:
    """POST /chat 路由级测试 — 验证 page_context 和 user_id 透传到 detect_intent"""

    @pytest.mark.asyncio
    async def test_chat_passes_page_context_to_detect_intent(self, client, test_user):
        """/chat 路由将 page_context 正确传递给 detect_intent"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc):
            response = await client.post(
                "/chat",
                json={
                    "text": "帮我补充内容",
                    "session_id": "sess-ctx-1",
                    "page_context": {
                        "page_type": "entry",
                        "entry_id": "entry-123",
                        "extra": {"tab": "detail"},
                    },
                },
            )

        assert response.status_code == 200
        # 验证 detect_intent 收到 page_context 和 user_id
        detect_call = mock_svc.detect_intent.call_args
        assert detect_call.kwargs["user_id"] == test_user.id
        pc = detect_call.kwargs["page_context"]
        assert pc.page_type == "entry"
        assert pc.entry_id == "entry-123"
        assert pc.extra == {"tab": "detail"}

    @pytest.mark.asyncio
    async def test_chat_passes_page_context_to_process_intent(self, client, test_user):
        """/chat 路由将 page_context 正确传递给 process_intent"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.detect_intent = AsyncMock(return_value={
            "intent": "update",
            "confidence": 0.9,
            "query": "补充",
            "entities": {"field": "content", "value": "新内容"},
        })
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc):
            response = await client.post(
                "/chat",
                json={
                    "text": "补充内容",
                    "session_id": "sess-ctx-2",
                    "page_context": {
                        "page_type": "entry",
                        "entry_id": "entry-456",
                    },
                },
            )

        assert response.status_code == 200
        call_kwargs = mock_process.call_args.kwargs
        assert call_kwargs["user_id"] == test_user.id
        pc = call_kwargs["page_context"]
        assert pc.page_type == "entry"
        assert pc.entry_id == "entry-456"

    @pytest.mark.asyncio
    async def test_chat_without_page_context(self, client, test_user):
        """/chat 路由不传 page_context 时服务层收到 None"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc):
            response = await client.post(
                "/chat",
                json={"text": "看看", "session_id": "sess-no-ctx"},
            )

        assert response.status_code == 200
        detect_call = mock_svc.detect_intent.call_args
        assert detect_call.kwargs["page_context"] is None


class TestForceIntentSecurityGate:
    """force_intent 仅在 DEBUG 模式允许"""

    @pytest.mark.asyncio
    async def test_force_intent_allowed_in_debug(self, client, test_user):
        """DEBUG=true 时 force_intent 正常工作，process_intent 被调用"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc), \
             patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.DEBUG = True
            response = await client.post(
                "/chat",
                json={"text": "搜索", "session_id": "s1", "force_intent": "read"},
            )

        assert response.status_code == 200
        assert "error" not in response.text
        # process_intent 必须被调用（证明 force_intent 路径走通了）
        assert mock_process.called
        # detect_intent 不应该被调用（force_intent 跳过意图检测）
        assert not mock_svc.detect_intent.called

    @pytest.mark.asyncio
    async def test_force_intent_blocked_in_production(self, client, test_user):
        """DEBUG=false 时 force_intent 返回 error 事件，process_intent 不被调用"""
        mock_process = _make_process_intent_mock()
        mock_svc = _make_chat_service_mock()
        mock_svc.process_intent = mock_process

        with patch("app.routers.parse._chat_service", mock_svc), \
             patch("app.core.config.get_settings") as mock_settings:
            mock_settings.return_value.DEBUG = False
            response = await client.post(
                "/chat",
                json={"text": "搜索", "session_id": "s1", "force_intent": "read"},
            )

        assert response.status_code == 200
        body = response.text
        assert "error" in body
        assert "force_intent 仅在 DEBUG 模式下可用" in body
        # process_intent 不应该被调用（门控拦截了）
        assert not mock_process.called
        # detect_intent 也不应该被调用（门控在意图检测之前）
        assert not mock_svc.detect_intent.called
