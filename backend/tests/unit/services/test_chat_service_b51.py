"""B51: LLM 页面感知系统提示词 — stream_parse page_context_hint + intent_service extra_system_hint

测试：
1. stream_parse 传入 page_context_hint → 系统提示词包含页面信息
2. stream_parse 不传 page_context_hint → 系统提示词不变
3. _handle_create 正确传递 context hint 到 graph（非拼接到用户文本）
4. detect_intent 传入 page_context → extra_system_hint 包含页面指导
"""
import importlib.util
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# 通过 spec_from_file_location 直接加载 chat_service.py，避免循环导入
_CHAT_SERVICE_PATH = Path(__file__).resolve().parents[3] / "app" / "services" / "chat_service.py"
_SPEC = importlib.util.spec_from_file_location("chat_service_module", _CHAT_SERVICE_PATH)
_chat_svc_module = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader

import sys
_prev = {}
for key in ("app.routers", "app.routers.intent", "app.routers.deps"):
    _prev[key] = sys.modules.get(key)
    sys.modules[key] = MagicMock()

try:
    _SPEC.loader.exec_module(_chat_svc_module)
finally:
    for key, val in _prev.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val

ChatService = _chat_svc_module.ChatService

from app.api.schemas import EntryResponse, EntryListResponse, SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry_response(entry_id="e1", title="测试", category="task", tags=None, content="", status="pending"):
    return EntryResponse(
        id=entry_id, title=title, content=content, type="task", status=status,
        category=category, tags=tags or [], created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00", file_path="",
    )


def _make_entry_list_response(entries=None, total=0):
    return EntryListResponse(entries=entries or [], total=total if total else len(entries) if entries else 0)


def _make_search_result(entries=None):
    return SearchResult(entries=entries or [], query="test", total=len(entries) if entries else 0)


def _make_page_context(page_type, entry_id=None, extra=None):
    ctx = MagicMock()
    ctx.page_type = page_type
    ctx.entry_id = entry_id
    ctx.extra = extra
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_entry_service():
    svc = AsyncMock()
    svc.create_entry = AsyncMock(return_value=_make_entry_response())
    svc.update_entry = AsyncMock(return_value=(True, "已更新"))
    svc.search_entries = AsyncMock(return_value=_make_search_result())
    svc.get_entry = AsyncMock(return_value=None)
    svc.list_entries = AsyncMock(return_value=_make_entry_list_response())
    return svc


@pytest.fixture
def mock_graph():
    return MagicMock()


@pytest.fixture
def mock_intent_service():
    svc = MagicMock()
    svc.detect = AsyncMock()
    return svc


@pytest.fixture
def chat_service(mock_graph, mock_entry_service, mock_intent_service):
    return ChatService(graph=mock_graph, entry_service=mock_entry_service, intent_service=mock_intent_service)


# ===========================================================================
# Test 1: stream_parse 传入 page_context_hint → 系统提示词包含页面信息
# ===========================================================================

class TestStreamParsePageContextHint:
    """TaskParserGraph._parse_node page_context_hint 测试"""

    @pytest.mark.asyncio
    async def test_page_context_hint_appended_to_system_prompt(self):
        """page_context_hint 通过 config 传递到 _parse_node，追加到系统提示词"""
        from app.graphs.task_parser_graph import TaskParserGraph, SYSTEM_PROMPT_TEMPLATE
        from langchain_core.runnables import RunnableConfig

        captured_messages = []
        mock_caller = AsyncMock()

        async def capture_call(messages, response_format):
            captured_messages.extend(messages)
            return json.dumps({"tasks": [], "response": "ok"})

        mock_caller.call = capture_call

        # 使用 MemorySaver 代替 mock
        from langgraph.checkpoint.memory import MemorySaver
        graph = TaskParserGraph(caller=mock_caller, checkpointer=MemorySaver())

        hint = "[页面上下文] 用户当前在「条目详情页」\n条目标题: 学习 Rust"
        async for chunk in graph.stream_parse("记个笔记", thread_id="test-hint", page_context_hint=hint):
            pass

        assert len(captured_messages) > 0
        system_msg = captured_messages[0]
        assert system_msg["role"] == "system"
        assert "学习 Rust" in system_msg["content"]
        assert "当前页面上下文" in system_msg["content"]
        user_msg = captured_messages[1]
        assert user_msg["content"] == "记个笔记"

    @pytest.mark.asyncio
    async def test_no_page_context_hint_system_prompt_unchanged(self):
        """不传 page_context_hint 时系统提示词不变"""
        from app.graphs.task_parser_graph import TaskParserGraph
        from langgraph.checkpoint.memory import MemorySaver

        captured_messages = []
        mock_caller = AsyncMock()

        async def capture_call(messages, response_format):
            captured_messages.extend(messages)
            return json.dumps({"tasks": [], "response": "ok"})

        mock_caller.call = capture_call
        graph = TaskParserGraph(caller=mock_caller, checkpointer=MemorySaver())

        async for chunk in graph.stream_parse("记个笔记", thread_id="test-no-hint"):
            pass

        system_msg = captured_messages[0]
        assert "当前页面上下文" not in system_msg["content"]
        assert system_msg["content"].startswith("你是一个任务解析助手")

    @pytest.mark.asyncio
    async def test_empty_page_context_hint_system_prompt_unchanged(self):
        """空字符串 page_context_hint 时系统提示词不变"""
        from app.graphs.task_parser_graph import TaskParserGraph
        from langgraph.checkpoint.memory import MemorySaver

        captured_messages = []
        mock_caller = AsyncMock()

        async def capture_call(messages, response_format):
            captured_messages.extend(messages)
            return json.dumps({"tasks": [], "response": "ok"})

        mock_caller.call = capture_call
        graph = TaskParserGraph(caller=mock_caller, checkpointer=MemorySaver())

        async for chunk in graph.stream_parse("记个笔记", thread_id="test-empty", page_context_hint=""):
            pass

        system_msg = captured_messages[0]
        assert "当前页面上下文" not in system_msg["content"]


# ===========================================================================
# Test 3: _handle_create 正确传递 context hint 到 graph
# ===========================================================================

class TestHandleCreateContextHint:
    """_handle_create 通过参数传递 context hint 到 graph"""

    @pytest.mark.asyncio
    async def test_handle_create_passes_context_hint_as_param(self, chat_service, mock_entry_service, mock_graph):
        """_handle_create 将 context_hint 作为参数传给 stream_parse，不拼接到用户文本"""

        # 让 get_entry 返回有效条目
        mock_entry_service.get_entry = AsyncMock(return_value=_make_entry_response(
            entry_id="e123", title="学习 Rust", tags=["rust"], content="系统编程"
        ))

        # mock stream_parse 捕获调用参数
        fake_response = json.dumps({"tasks": [], "response": "ok"})

        async def fake_stream_parse(text, thread_id, page_context_hint=""):
            yield f'data: {json.dumps({"content": fake_response})}\n\n'
            yield "data: [DONE]\n\n"

        mock_graph.stream_parse = MagicMock(side_effect=fake_stream_parse)

        ctx = _make_page_context("entry", entry_id="e123")
        events = []
        async for e in chat_service._handle_create("补充内容", "sess-1", "user-a", page_context=ctx):
            events.append(e)

        # 验证 stream_parse 被调用时参数正确
        call_args = mock_graph.stream_parse.call_args
        # 用户文本不含 context hint
        assert call_args.args[0] == "补充内容"
        # page_context_hint 通过命名参数传递
        assert "学习 Rust" in call_args.kwargs["page_context_hint"]
        assert "条目详情页" in call_args.kwargs["page_context_hint"]

    @pytest.mark.asyncio
    async def test_handle_create_no_context_no_hint(self, chat_service, mock_entry_service, mock_graph):
        """_handle_create 无 page_context 时不传 hint"""
        fake_response = json.dumps({"tasks": [], "response": "ok"})

        async def fake_stream_parse(text, thread_id, page_context_hint=""):
            yield f'data: {json.dumps({"content": fake_response})}\n\n'
            yield "data: [DONE]\n\n"

        mock_graph.stream_parse = MagicMock(side_effect=fake_stream_parse)

        events = []
        async for e in chat_service._handle_create("记个任务", "sess-2", "user-a"):
            events.append(e)

        call_args = mock_graph.stream_parse.call_args
        assert call_args.kwargs.get("page_context_hint", "") == ""


# ===========================================================================
# Test 4: detect_intent page_context → extra_system_hint 包含页面指导
# ===========================================================================

class TestDetectIntentPageContextHint:
    """detect_intent 传入 page_context → extra_system_hint 包含页面上下文"""

    @pytest.mark.asyncio
    async def test_detect_intent_entry_page_hint(self, chat_service, mock_entry_service):
        """条目页 detect_intent → extra_system_hint 包含条目信息"""
        mock_entry_service.get_entry = AsyncMock(return_value=_make_entry_response(
            entry_id="e1", title="学习 Rust", tags=["rust"]
        ))

        mock_intent_resp = MagicMock()
        mock_intent_resp.intent = "create"
        mock_intent_resp.confidence = 0.9
        mock_intent_resp.query = "补充"
        mock_intent_resp.entities = {}

        captured_hint = []

        async def capture_detect(text, extra_system_hint=""):
            captured_hint.append(extra_system_hint)
            return mock_intent_resp

        mock_intent_svc = MagicMock()
        mock_intent_svc.detect = capture_detect
        chat_service._intent_service = mock_intent_svc

        ctx = _make_page_context("entry", entry_id="e1")
        await chat_service.detect_intent("补充一些内容", page_context=ctx, user_id="user-a")

        # extra_system_hint 应包含条目信息
        assert len(captured_hint) == 1
        assert "学习 Rust" in captured_hint[0]
        assert "条目详情页" in captured_hint[0]

    @pytest.mark.asyncio
    async def test_detect_intent_home_page_hint(self, chat_service, mock_entry_service):
        """首页 detect_intent → extra_system_hint 包含统计"""
        mock_entry_service.list_entries = AsyncMock(return_value=_make_entry_list_response(total=3))

        mock_intent_resp = MagicMock()
        mock_intent_resp.intent = "create"
        mock_intent_resp.confidence = 0.9
        mock_intent_resp.query = "记个想法"
        mock_intent_resp.entities = {}

        captured_hint = []

        async def capture_detect(text, extra_system_hint=""):
            captured_hint.append(extra_system_hint)
            return mock_intent_resp

        mock_intent_svc = MagicMock()
        mock_intent_svc.detect = capture_detect
        chat_service._intent_service = mock_intent_svc

        ctx = _make_page_context("home")
        await chat_service.detect_intent("记个想法", page_context=ctx, user_id="user-a")

        assert "首页" in captured_hint[0]
        assert "今日条目数" in captured_hint[0]
