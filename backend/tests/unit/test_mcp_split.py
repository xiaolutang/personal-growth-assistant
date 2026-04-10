"""TD04: MCP Server 拆分后结构和导入验证"""
import pytest

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
)


class TestToolsModule:
    def test_tools_count(self):
        """TOOL 列表包含 9 个工具"""
        assert len(TOOLS) == 9

    def test_tool_names(self):
        """所有 tool name 可枚举"""
        names = {t.name for t in TOOLS}
        expected = {
            "list_entries", "get_entry", "create_entry", "update_entry",
            "delete_entry", "search_entries", "get_knowledge_graph",
            "get_related_concepts", "get_project_progress",
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
        ]
        for h in handlers:
            assert callable(h)


class TestServerRouting:
    def test_tool_handlers_map_completeness(self):
        """TOOL_HANDLERS 映射覆盖所有 tool name"""
        from app.mcp.server import TOOL_HANDLERS
        assert len(TOOL_HANDLERS) == 9
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
