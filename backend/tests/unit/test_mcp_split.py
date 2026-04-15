"""TD04: MCP Server 拆分后结构和导入验证"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.mcp.tools import TOOLS
from app.mcp.handlers import (
    ENTRY_ID_LENGTH,
    MAX_CHILD_TASKS,
    MAX_DISPLAY_TASKS,
    parse_iso_date,
    handle_list_entries,
    handle_get_entry,
    handle_create_entry,
    handle_update_entry,
    handle_delete_entry,
    handle_search_entries,
    handle_get_knowledge_graph,
    handle_get_related_concepts,
    handle_get_project_progress,
    handle_get_review_summary,
    handle_get_knowledge_stats,
)


class TestToolsModule:
    def test_tools_count(self):
        """TOOL 列表包含 11 个工具"""
        assert len(TOOLS) == 11
        assert isinstance(TOOLS, tuple)

    def test_tool_names(self):
        """所有 tool name 可枚举"""
        names = {t.name for t in TOOLS}
        expected = {
            "list_entries", "get_entry", "create_entry", "update_entry",
            "delete_entry", "search_entries", "get_knowledge_graph",
            "get_related_concepts", "get_project_progress",
            "get_review_summary", "get_knowledge_stats",
        }
        assert names == expected


class TestHandlersModule:
    def test_all_handler_functions_importable(self):
        """所有 handler 函数可正常导入"""
        handlers = [
            handle_list_entries, handle_get_entry, handle_create_entry,
            handle_update_entry, handle_delete_entry, handle_search_entries,
            handle_get_knowledge_graph, handle_get_related_concepts,
            handle_get_project_progress,
            handle_get_review_summary, handle_get_knowledge_stats,
        ]
        for h in handlers:
            assert callable(h)


class TestServerRouting:
    def test_tool_handlers_map_completeness(self):
        """TOOL_HANDLERS 映射覆盖所有 tool name"""
        from app.mcp.server import TOOL_HANDLERS
        assert len(TOOL_HANDLERS) == 11
        for tool in TOOLS:
            assert tool.name in TOOL_HANDLERS, f"Missing handler for: {tool.name}"
            assert callable(TOOL_HANDLERS[tool.name])

    def test_tool_handlers_map_values_are_handlers(self):
        """TOOL_HANDLERS 的值是 handlers 模块中的函数"""
        from app.mcp.server import TOOL_HANDLERS
        handler_ids = {id(v) for v in TOOL_HANDLERS.values()}
        expected_ids = {
            id(handle_list_entries), id(handle_get_entry), id(handle_create_entry),
            id(handle_update_entry), id(handle_delete_entry), id(handle_search_entries),
            id(handle_get_knowledge_graph), id(handle_get_related_concepts),
            id(handle_get_project_progress),
            id(handle_get_review_summary), id(handle_get_knowledge_stats),
        }
        assert handler_ids == expected_ids


class TestHelpers:
    def test_parse_iso_date_valid(self):
        from app.mcp.handlers import parse_iso_date
        result = parse_iso_date("2026-04-10")
        assert result is not None
        assert result.year == 2026

    def test_parse_iso_date_none(self):
        from app.mcp.handlers import parse_iso_date
        assert parse_iso_date(None) is None
        assert parse_iso_date("") is None

    def test_constants(self):
        assert ENTRY_ID_LENGTH == 8
        assert MAX_CHILD_TASKS == 1000
        assert MAX_DISPLAY_TASKS == 10


class TestCallToolDispatch:
    """验证 call_tool 路由分发到正确的 handler"""

    @pytest.mark.asyncio
    async def test_call_tool_dispatches_to_handler(self):
        """call_tool 正确分发到对应 handler"""
        from app.mcp.server import call_tool

        mock_storage = MagicMock()
        mock_handler = AsyncMock(return_value=[])

        with patch("app.mcp.server.storage", mock_storage), \
             patch("app.mcp.server.authenticated_user_id", "user-123"), \
             patch("app.mcp.server.TOOL_HANDLERS", {"list_entries": mock_handler}):
            result = await call_tool("list_entries", {"limit": 10})
            mock_handler.assert_called_once_with(mock_storage, {"limit": 10}, "user-123")

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """未知工具名返回错误消息"""
        from app.mcp.server import call_tool

        with patch("app.mcp.server.storage", MagicMock()), \
             patch("app.mcp.server.authenticated_user_id", "user-123"):
            result = await call_tool("nonexistent_tool", {})
            assert len(result) == 1
            assert "未知工具" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_handler_exception(self):
        """handler 抛异常时返回错误消息"""
        from app.mcp.server import call_tool

        mock_handler = AsyncMock(side_effect=ValueError("test error"))
        with patch("app.mcp.server.storage", MagicMock()), \
             patch("app.mcp.server.authenticated_user_id", "user-123"), \
             patch("app.mcp.server.TOOL_HANDLERS", {"list_entries": mock_handler}):
            result = await call_tool("list_entries", {})
            assert len(result) == 1
            assert "错误" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_auto_init_when_no_storage(self):
        """storage 为 None 时自动初始化"""
        from app.mcp.server import call_tool

        mock_handler = AsyncMock(return_value=[])

        with patch("app.mcp.server.storage", None), \
             patch("app.mcp.server.authenticated_user_id", "user-123"), \
             patch("app.mcp.server.init", new_callable=AsyncMock) as mock_init, \
             patch("app.mcp.server.TOOL_HANDLERS", {"list_entries": mock_handler}):
            result = await call_tool("list_entries", {})
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_all_11_tools_routable(self):
        """所有 11 个 tool name 都能找到对应 handler"""
        from app.mcp.server import TOOL_HANDLERS

        for tool in TOOLS:
            assert tool.name in TOOL_HANDLERS, f"Tool {tool.name} not in TOOL_HANDLERS"

    def test_main_entry_point_exists(self):
        """main 函数存在且可调用"""
        from app.mcp.server import main
        assert callable(main)
