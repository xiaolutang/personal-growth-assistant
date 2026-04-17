"""B50: ChatService 页面上下文数据注入 + 更新路径打通测试

使用 importlib.util.spec_from_file_location 直接加载 chat_service.py，
完全绕过循环导入（chat_service.py → app.routers.intent → __init__ → parse → chat_service）。
"""
import importlib.util
import json
from datetime import date
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# 通过 spec_from_file_location 直接加载 chat_service.py，避免循环导入
# ---------------------------------------------------------------------------
_CHAT_SERVICE_PATH = Path(__file__).resolve().parents[3] / "app" / "services" / "chat_service.py"
_SPEC = importlib.util.spec_from_file_location("chat_service_module", _CHAT_SERVICE_PATH)
_chat_svc_module = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader

# mock 掉循环依赖的模块
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
sse_event = _chat_svc_module.sse_event

from app.api.schemas import EntryCreate, EntryUpdate, EntryResponse, EntryListResponse, SearchResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_page_context(page_type: str, entry_id: str = None, extra: dict = None):
    """构建 PageContext mock 对象"""
    ctx = MagicMock()
    ctx.page_type = page_type
    ctx.entry_id = entry_id
    ctx.extra = extra
    return ctx


def _make_entry_response(
    entry_id: str = "e1",
    title: str = "测试条目",
    category: str = "task",
    tags: list = None,
    content: str = "",
    status: str = "pending",
) -> EntryResponse:
    return EntryResponse(
        id=entry_id,
        title=title,
        content=content,
        type="task",
        status=status,
        category=category,
        tags=tags or [],
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        file_path="",
    )


def _make_entry_list_response(entries=None, total: int = 0) -> EntryListResponse:
    return EntryListResponse(
        entries=entries or [],
        total=total if total else len(entries) if entries else 0,
    )


def _make_search_result(entries=None) -> SearchResult:
    return SearchResult(
        entries=entries or [],
        query="test",
        total=len(entries) if entries else 0,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_entry_service():
    svc = AsyncMock()
    svc.create_entry = AsyncMock(return_value=_make_entry_response())
    svc.update_entry = AsyncMock(return_value=(True, "已更新"))
    svc.delete_entry = AsyncMock(return_value=(True, "已删除"))
    svc.search_entries = AsyncMock(return_value=_make_search_result())
    svc.get_entry = AsyncMock(return_value=None)
    svc.list_entries = AsyncMock(return_value=_make_entry_list_response())
    return svc


@pytest.fixture
def mock_graph():
    return MagicMock()


@pytest.fixture
def chat_service(mock_graph, mock_entry_service):
    return ChatService(graph=mock_graph, entry_service=mock_entry_service)


# ===========================================================================
# _build_page_context_hint — Entry page 数据注入
# ===========================================================================

class TestBuildPageContextHintEntry:
    """Entry page 上下文数据注入"""

    @pytest.mark.asyncio
    async def test_entry_page_valid_entry_id(self, chat_service, mock_entry_service):
        """Entry page 有效 entry_id → context 含标题/分类/标签"""
        mock_entry_service.get_entry = AsyncMock(return_value=_make_entry_response(
            entry_id="e123",
            title="学习 Rust",
            category="task",
            tags=["rust", "编程"],
            content="Rust 是一门系统编程语言...",
        ))
        ctx = _make_page_context("entry", entry_id="e123")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "条目标题: 学习 Rust" in hint
        assert "分类: task" in hint
        assert "标签: rust, 编程" in hint
        assert "内容摘要: Rust 是一门系统编程语言..." in hint
        mock_entry_service.get_entry.assert_called_once_with("e123", "user-a")

    @pytest.mark.asyncio
    async def test_entry_page_invalid_entry_id(self, chat_service, mock_entry_service):
        """Entry page 无效 entry_id → context 降级为基础信息"""
        mock_entry_service.get_entry = AsyncMock(return_value=None)
        ctx = _make_page_context("entry", entry_id="nonexistent")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "条目详情页" in hint
        assert "正在查看条目 ID: nonexistent" in hint
        # 不应该有标题等详情
        assert "条目标题:" not in hint

    @pytest.mark.asyncio
    async def test_entry_page_other_users_entry(self, chat_service, mock_entry_service):
        """Entry page entry_id 属于其他用户 → 降级（隔离验证）"""
        # get_entry 对其他用户返回 None
        mock_entry_service.get_entry = AsyncMock(return_value=None)
        ctx = _make_page_context("entry", entry_id="e-other-user")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "条目详情页" in hint
        assert "正在查看条目 ID: e-other-user" in hint
        assert "条目标题:" not in hint

    @pytest.mark.asyncio
    async def test_entry_page_no_content(self, chat_service, mock_entry_service):
        """Entry page 条目无内容 → 不输出内容摘要"""
        mock_entry_service.get_entry = AsyncMock(return_value=_make_entry_response(
            entry_id="e1", title="空条目", content=""
        ))
        ctx = _make_page_context("entry", entry_id="e1")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "条目标题: 空条目" in hint
        assert "内容摘要:" not in hint

    @pytest.mark.asyncio
    async def test_entry_page_long_content_truncated(self, chat_service, mock_entry_service):
        """Entry page 内容超过300字 → 截断到300字"""
        long_content = "x" * 500
        mock_entry_service.get_entry = AsyncMock(return_value=_make_entry_response(
            entry_id="e1", title="长文", content=long_content
        ))
        ctx = _make_page_context("entry", entry_id="e1")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        # 摘要应该是 300 字
        for line in hint.split("\n"):
            if line.startswith("内容摘要:"):
                assert len(line) == len("内容摘要: ") + 300


# ===========================================================================
# _build_page_context_hint — Home page 数据注入
# ===========================================================================

class TestBuildPageContextHintHome:
    """Home page 上下文数据注入"""

    @pytest.mark.asyncio
    async def test_home_page_today_stats(self, chat_service, mock_entry_service):
        """Home page → context 含今日统计 + 进行中数"""
        mock_entry_service.list_entries = AsyncMock(
            return_value=_make_entry_list_response(total=5)
        )
        ctx = _make_page_context("home")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "首页" in hint
        assert "今日条目数: 5" in hint
        assert "进行中条目数: 5" in hint
        # 验证两次调用：一次带日期过滤，一次带 status 过滤
        assert mock_entry_service.list_entries.call_count == 2
        calls = mock_entry_service.list_entries.call_args_list
        today = date.today().isoformat()
        first_kwargs = calls[0].kwargs
        assert first_kwargs.get("start_date") == today
        assert first_kwargs.get("end_date") == today
        second_kwargs = calls[1].kwargs
        assert second_kwargs.get("status") == "doing"

    @pytest.mark.asyncio
    async def test_home_page_list_failure_graceful(self, chat_service, mock_entry_service):
        """Home page list_entries 异常 → 优雅降级不阻塞"""
        mock_entry_service.list_entries = AsyncMock(side_effect=RuntimeError("DB error"))
        ctx = _make_page_context("home")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "首页" in hint
        assert "今日条目数:" not in hint


# ===========================================================================
# _build_page_context_hint — 其他页面类型
# ===========================================================================

class TestBuildPageContextHintOtherPages:
    """Explore/Review/Graph page → context 含基本页面标识"""

    @pytest.mark.asyncio
    async def test_explore_page(self, chat_service):
        ctx = _make_page_context("explore")
        hint = await chat_service._build_page_context_hint(ctx, "user-a")
        assert "探索页" in hint

    @pytest.mark.asyncio
    async def test_review_page(self, chat_service):
        ctx = _make_page_context("review")
        hint = await chat_service._build_page_context_hint(ctx, "user-a")
        assert "回顾页" in hint

    @pytest.mark.asyncio
    async def test_graph_page(self, chat_service):
        ctx = _make_page_context("graph")
        hint = await chat_service._build_page_context_hint(ctx, "user-a")
        assert "知识图谱页" in hint


# ===========================================================================
# _build_page_context_hint — 边界场景
# ===========================================================================

class TestBuildPageContextHintEdgeCases:

    @pytest.mark.asyncio
    async def test_none_page_context(self, chat_service):
        """page_context 为 None → 返回空字符串"""
        hint = await chat_service._build_page_context_hint(None, "user-a")
        assert hint == ""

    @pytest.mark.asyncio
    async def test_extra_fields_passthrough(self, chat_service):
        """extra 字段透传到 context hint"""
        ctx = _make_page_context("home", extra={"current_tag": "rust", "view_mode": "list"})

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "current_tag: rust" in hint
        assert "view_mode: list" in hint

    @pytest.mark.asyncio
    async def test_get_entry_exception_graceful(self, chat_service, mock_entry_service):
        """EntryService.get_entry 异常 → 优雅降级不阻塞"""
        mock_entry_service.get_entry = AsyncMock(side_effect=RuntimeError("DB down"))
        ctx = _make_page_context("entry", entry_id="e1")

        hint = await chat_service._build_page_context_hint(ctx, "user-a")

        assert "条目详情页" in hint
        assert "正在查看条目 ID: e1" in hint


# ===========================================================================
# _handle_update — 条目页 entry_id fallback
# ===========================================================================

class TestHandleUpdateWithContext:
    """_handle_update 的 page_context fallback 测试"""

    @pytest.mark.asyncio
    async def test_entry_page_search_no_result_fallback_to_entry_id(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 条目页 entry_id → 搜索无结果时直接更新"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([])  # 搜索无结果
        )
        ctx = _make_page_context("entry", entry_id="ctx-entry-123")

        events = []
        async for e in chat_service._handle_update(
            "标记完成", {"field": "status", "value": "complete"}, None, "user-a",
            page_context=ctx,
        ):
            events.append(e)

        # 应该直接用 ctx-entry-123 更新
        mock_entry_service.update_entry.assert_called_once()
        call_kwargs = mock_entry_service.update_entry.call_args
        assert call_kwargs[0][0] == "ctx-entry-123" or call_kwargs.kwargs.get("entry_id") == "ctx-entry-123" or "ctx-entry-123" in str(call_kwargs)
        # 验证 user_id 传递
        assert call_kwargs.kwargs["user_id"] == "user-a"

        # 检查事件
        updated_events = [e for e in events if "event: updated" in e]
        assert len(updated_events) == 1
        assert "ctx-entry-123" in updated_events[0]

    @pytest.mark.asyncio
    async def test_entry_page_search_single_result_takes_priority(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 条目页 entry_id + 精确搜索匹配 → 搜索结果优先"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([
                _make_entry_response("search-result-1", "买菜任务")
            ])
        )
        ctx = _make_page_context("entry", entry_id="ctx-entry-456")

        events = []
        async for e in chat_service._handle_update(
            "买菜", {"field": "status", "value": "complete"}, None, "user-a",
            page_context=ctx,
        ):
            events.append(e)

        # 应该用搜索结果 search-result-1，不是 ctx-entry-456
        call_kwargs = mock_entry_service.update_entry.call_args
        # update_entry(entry_id, EntryUpdate(...), user_id=user_id)
        assert call_kwargs[0][0] == "search-result-1"
        assert call_kwargs.kwargs["user_id"] == "user-a"

    @pytest.mark.asyncio
    async def test_entry_page_search_multiple_results_fallback_to_entry_id(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 条目页 entry_id + 多个搜索结果 → fallback 到 entry_id"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([
                _make_entry_response("r1", "买菜1"),
                _make_entry_response("r2", "买菜2"),
            ])
        )
        ctx = _make_page_context("entry", entry_id="ctx-entry-789")

        events = []
        async for e in chat_service._handle_update(
            "买菜", {"field": "status", "value": "complete"}, None, "user-a",
            page_context=ctx,
        ):
            events.append(e)

        # 多个结果，fallback 到 ctx_entry_id
        call_kwargs = mock_entry_service.update_entry.call_args
        assert call_kwargs[0][0] == "ctx-entry-789"
        assert call_kwargs.kwargs["user_id"] == "user-a"

    @pytest.mark.asyncio
    async def test_entry_page_search_multiple_results_exact_match_takes_priority(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 条目页 多个搜索结果中有精确匹配 → 使用精确匹配而非 entry_id"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([
                _make_entry_response("r1", "买菜1"),
                _make_entry_response("r2", "买菜"),  # 精确匹配 query
                _make_entry_response("r3", "买菜2"),
            ])
        )
        ctx = _make_page_context("entry", entry_id="ctx-entry-999")

        events = []
        async for e in chat_service._handle_update(
            "买菜", {"field": "status", "value": "complete"}, None, "user-a",
            page_context=ctx,
        ):
            events.append(e)

        # 应该用精确匹配的 r2，不是 fallback 的 ctx-entry-999
        call_kwargs = mock_entry_service.update_entry.call_args
        assert call_kwargs[0][0] == "r2"
        assert call_kwargs.kwargs["user_id"] == "user-a"

    @pytest.mark.asyncio
    async def test_non_entry_page_behavior_unchanged(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 非条目页 → 行为不变"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([])  # 无结果
        )
        # home page context（不是 entry page）
        ctx = _make_page_context("home")

        events = []
        async for e in chat_service._handle_update(
            "买菜", {"field": "status", "value": "complete"}, None, "user-a",
            page_context=ctx,
        ):
            events.append(e)

        # 无结果且无 fallback → 只返回 done 事件
        mock_entry_service.update_entry.assert_not_called()
        done_events = [e for e in events if "event: done" in e]
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_no_page_context_behavior_unchanged(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 无 page_context → 行为不变"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([])
        )

        events = []
        async for e in chat_service._handle_update(
            "买菜", {"field": "status", "value": "complete"}, None, "user-a",
            page_context=None,
        ):
            events.append(e)

        mock_entry_service.update_entry.assert_not_called()
        done_events = [e for e in events if "event: done" in e]
        assert len(done_events) == 1

    @pytest.mark.asyncio
    async def test_entry_page_no_field_value_no_fallback(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 条目页但 entities 无 field/value → 不执行 fallback 更新"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([])
        )
        ctx = _make_page_context("entry", entry_id="ctx-entry-abc")

        events = []
        async for e in chat_service._handle_update(
            "看看这个条目", {}, None, "user-a",
            page_context=ctx,
        ):
            events.append(e)

        # 无 field/value → 不更新
        mock_entry_service.update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_entry_page_search_no_result_no_field(
        self, chat_service, mock_entry_service
    ):
        """_handle_update 条目页搜索无结果且无 field → fallback 但不更新"""
        mock_entry_service.search_entries = AsyncMock(
            return_value=_make_search_result([])
        )
        ctx = _make_page_context("entry", entry_id="ctx-entry-xyz")

        events = []
        async for e in chat_service._handle_update(
            "查看详情", {}, None, "user-a",
            page_context=ctx,
        ):
            events.append(e)

        mock_entry_service.update_entry.assert_not_called()


# ===========================================================================
# detect_intent — user_id 透传到 _build_page_context_hint
# ===========================================================================

class TestDetectIntentUserId:
    """detect_intent 将 user_id 传递给 _build_page_context_hint"""

    @pytest.mark.asyncio
    async def test_detect_intent_passes_user_id_to_context_hint(
        self, chat_service, mock_entry_service
    ):
        """detect_intent 传入 user_id → _build_page_context_hint 收到 user_id"""
        mock_entry_service.get_entry = AsyncMock(return_value=_make_entry_response(
            entry_id="e1", title="测试条目"
        ))

        mock_intent_svc = MagicMock()
        mock_intent_resp = MagicMock()
        mock_intent_resp.intent = "read"
        mock_intent_resp.confidence = 0.9
        mock_intent_resp.query = "查看"
        mock_intent_resp.entities = {}
        mock_intent_svc.detect = AsyncMock(return_value=mock_intent_resp)
        chat_service._intent_service = mock_intent_svc

        ctx = _make_page_context("entry", entry_id="e1")
        result = await chat_service.detect_intent("查看这个条目", page_context=ctx, user_id="user-xyz")

        # get_entry 应该以 user-xyz 调用
        mock_entry_service.get_entry.assert_called_once_with("e1", "user-xyz")
        assert result["intent"] == "read"
