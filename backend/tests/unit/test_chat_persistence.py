"""测试聊天持久化和消息截断"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import HumanMessage, AIMessage

from app.graphs.task_parser_graph import (
    estimate_tokens,
    truncate_messages,
    MAX_MESSAGES,
    MAX_TOKENS,
)
from app.services.ai_chat_service import AIChatService, HistoryMessage


# ── Token 估算测试 ──


class TestEstimateTokens:
    """测试 token 估算函数"""

    def test_chinese_text(self):
        """中文文本：每个字符约 1.5 token"""
        text = "你好世界"  # 4 个中文字符
        tokens = estimate_tokens(text)
        assert tokens == 6  # 4 * 1.5 = 6

    def test_english_text(self):
        """英文文本：每个字符约 0.25 token"""
        text = "hello"  # 5 个英文字符
        tokens = estimate_tokens(text)
        assert tokens == 1  # int(5 * 0.25) = 1

    def test_mixed_text(self):
        """中英混合文本"""
        text = "你好hello"  # 2 中文 + 5 英文
        tokens = estimate_tokens(text)
        assert tokens == int(2 * 1.5 + 5 * 0.25)

    def test_empty_text(self):
        """空文本"""
        assert estimate_tokens("") == 0

    def test_cjk_punctuation(self):
        """CJK 标点符号按中文计算"""
        text = "，。！？"  # CJK 标点
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_fullwidth_chars(self):
        """全角字符按中文计算"""
        text = "ＡＢ"  # Fullwidth Latin
        tokens = estimate_tokens(text)
        assert tokens > 0


# ── 消息截断测试 ──


class TestTruncateMessages:
    """测试消息截断逻辑"""

    def _make_messages(self, count: int, prefix: str = "msg") -> list:
        """生成指定数量的消息列表"""
        msgs = []
        for i in range(count):
            if i % 2 == 0:
                msgs.append(HumanMessage(content=f"{prefix}_{i}"))
            else:
                msgs.append(AIMessage(content=f"{prefix}_{i}"))
        return msgs

    def test_no_truncation_needed(self):
        """消息数量未超限时不截断"""
        msgs = self._make_messages(10)
        result = truncate_messages(msgs)
        assert len(result) == 10

    def test_truncation_by_count(self):
        """超过 MAX_MESSAGES 条时截断到最近 N 条"""
        msgs = self._make_messages(30)
        result = truncate_messages(msgs, max_messages=20)
        assert len(result) == 20
        # 保留的是最近的 20 条
        assert result[0].content == "msg_10"
        assert result[-1].content == "msg_29"

    def test_truncation_by_tokens(self):
        """总 token 超限时按 token 截断"""
        # 创建少量但每条很长的消息
        long_content = "你好" * 1000  # 每条约 3000 token
        msgs = [
            HumanMessage(content=long_content),
            AIMessage(content=long_content),
            HumanMessage(content="short"),
        ]
        result = truncate_messages(msgs, max_messages=100, max_tokens=500)
        # 应该只剩下最后一条或两条
        assert len(result) < 3
        total_tokens = sum(estimate_tokens(m.content) for m in result)
        assert total_tokens <= 500

    def test_custom_parameters(self):
        """自定义截断参数"""
        msgs = self._make_messages(50)
        result = truncate_messages(msgs, max_messages=5, max_tokens=10000)
        assert len(result) == 5

    def test_single_message_preserved(self):
        """即使 token 超限，至少保留 1 条消息"""
        very_long = "你好" * 5000  # 约 15000 token
        msgs = [HumanMessage(content=very_long)]
        result = truncate_messages(msgs, max_messages=20, max_tokens=100)
        assert len(result) == 1

    def test_returns_new_list(self):
        """截断不修改原始列表"""
        msgs = self._make_messages(30)
        original_len = len(msgs)
        truncate_messages(msgs, max_messages=5, max_tokens=10000)
        assert len(msgs) == original_len


# ── 持久化测试 ──


class TestAIChatServicePersistence:
    """测试 AIChatService 的持久化功能"""

    def test_page_thread_id_format(self):
        """thread_id 格式验证"""
        from app.routers.ai_chat import _page_thread_id
        thread_id = _page_thread_id("home", "user123")
        assert thread_id == "page:home:user123"

    def test_page_thread_id_different_pages(self):
        """不同页面生成不同 thread_id"""
        from app.routers.ai_chat import _page_thread_id
        t1 = _page_thread_id("home", "user123")
        t2 = _page_thread_id("explore", "user123")
        t3 = _page_thread_id("home", "user456")
        assert t1 != t2  # 不同页面不同
        assert t1 != t3  # 不同用户不同

    @pytest.mark.asyncio
    async def test_load_history_no_checkpointer(self):
        """无 checkpointer 时返回空列表"""
        service = AIChatService()
        result = await service.load_history("page:home:user1")
        assert result == []

    @pytest.mark.asyncio
    async def test_load_history_with_checkpointer(self):
        """有 checkpointer 时加载历史消息"""
        mock_checkpointer = AsyncMock()
        mock_state = MagicMock()
        mock_state.checkpoint = {
            "channel_values": {
                "messages": [
                    HumanMessage(content="你好"),
                    AIMessage(content="你好！我是日知。"),
                    HumanMessage(content="记一个想法"),
                ]
            }
        }
        mock_checkpointer.aget_tuple.return_value = mock_state

        service = AIChatService(checkpointer=mock_checkpointer)
        result = await service.load_history("page:home:user1")

        assert len(result) == 3
        assert result[0].role == "user"
        assert result[0].content == "你好"
        assert result[1].role == "assistant"
        assert result[2].role == "user"

    @pytest.mark.asyncio
    async def test_load_history_with_limit(self):
        """limit 参数限制返回数量"""
        messages = [HumanMessage(content=f"msg_{i}") for i in range(30)]
        mock_checkpointer = AsyncMock()
        mock_state = MagicMock()
        mock_state.checkpoint = {"channel_values": {"messages": messages}}
        mock_checkpointer.aget_tuple.return_value = mock_state

        service = AIChatService(checkpointer=mock_checkpointer)
        result = await service.load_history("page:home:user1", limit=20)
        assert len(result) == 20

    @pytest.mark.asyncio
    async def test_load_history_empty_state(self):
        """无历史记录时返回空列表"""
        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple.return_value = None

        service = AIChatService(checkpointer=mock_checkpointer)
        result = await service.load_history("page:home:user1")
        assert result == []

    @pytest.mark.asyncio
    async def test_load_history_exception(self):
        """异常时返回空列表（优雅降级）"""
        mock_checkpointer = AsyncMock()
        mock_checkpointer.aget_tuple.side_effect = Exception("DB error")

        service = AIChatService(checkpointer=mock_checkpointer)
        result = await service.load_history("page:home:user1")
        assert result == []

    @pytest.mark.asyncio
    async def test_chat_stream_with_thread_id(self):
        """持久化模式下 chat_stream 使用 checkpointer 历史"""
        mock_checkpointer = AsyncMock()
        mock_state = MagicMock()
        mock_state.checkpoint = {
            "channel_values": {
                "messages": [
                    HumanMessage(content="之前的问题"),
                    AIMessage(content="之前的回答"),
                ]
            }
        }
        mock_checkpointer.aget_tuple.return_value = mock_state

        mock_caller = MagicMock()
        mock_caller.stream = _mock_stream(["回答"])

        service = AIChatService(llm_caller=mock_caller, checkpointer=mock_checkpointer)

        chunks = []
        async for token in service.chat_stream(
            message="新问题",
            user_id="user1",
            thread_id="page:home:user1",
        ):
            chunks.append(token)

        # 验证历史消息被注入
        assert len(mock_caller.stream.calls) == 1
        call_args = mock_caller.stream.calls[0][0][0]
        # 应该包含 system + 2 条历史 + 1 条新消息 = 4 条
        assert len(call_args) == 4
        assert call_args[0]["role"] == "system"
        assert call_args[1]["content"] == "之前的问题"
        assert call_args[2]["content"] == "之前的回答"
        assert call_args[3]["content"] == "新问题"

    @pytest.mark.asyncio
    async def test_chat_stream_without_thread_id(self):
        """无 thread_id 时向后兼容（使用 context.messages）"""
        mock_caller = MagicMock()
        mock_caller.stream = _mock_stream(["回答"])

        service = AIChatService(llm_caller=mock_caller)

        context = {
            "messages": [
                {"role": "user", "content": "历史问题"},
                {"role": "assistant", "content": "历史回答"},
            ]
        }

        chunks = []
        async for token in service.chat_stream(
            message="新问题",
            context=context,
            user_id="user1",
        ):
            chunks.append(token)

        assert len(mock_caller.stream.calls) == 1
        call_args = mock_caller.stream.calls[0][0][0]
        assert len(call_args) == 4  # system + 2 history + 1 new


class AsyncIterator:
    """辅助类：模拟异步迭代器"""
    def __init__(self, items):
        self._items = list(items)

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._idx]
        self._idx += 1
        return item


def _mock_stream(tokens):
    """创建一个正确支持 async for 且可追踪调用参数的 mock stream"""
    calls = []

    async def _stream(*args, **kwargs):
        calls.append((args, kwargs))
        for token in tokens:
            yield token

    _stream.calls = calls
    return _stream


# ── 集成测试：截断 + 持久化 ──


class TestTruncationIntegration:
    """截断与持久化集成测试"""

    @pytest.mark.asyncio
    async def test_long_history_truncated_in_chat_stream(self):
        """长历史在 chat_stream 中被截断"""
        # 创建 30 条历史消息（超过 MAX_MESSAGES=20）
        messages = []
        for i in range(30):
            messages.append(HumanMessage(content=f"问题_{i}"))
            messages.append(AIMessage(content=f"回答_{i}"))

        mock_checkpointer = AsyncMock()
        mock_state = MagicMock()
        mock_state.checkpoint = {"channel_values": {"messages": messages}}
        mock_checkpointer.aget_tuple.return_value = mock_state

        mock_caller = MagicMock()
        mock_caller.stream = _mock_stream(["回答"])

        service = AIChatService(llm_caller=mock_caller, checkpointer=mock_checkpointer)

        async for _ in service.chat_stream(
            message="新问题",
            user_id="user1",
            thread_id="page:home:user1",
        ):
            pass

        assert len(mock_caller.stream.calls) == 1
        call_args = mock_caller.stream.calls[0][0][0]
        # system + MAX_MESSAGES(20) 历史 + 1 新 = 22
        assert len(call_args) == 22
