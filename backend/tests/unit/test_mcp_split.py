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
    handle_batch_create_entries,
    handle_batch_update_status,
    handle_get_learning_path,
)


class TestToolsModule:
    def test_tools_count(self):
        """TOOL 列表包含 14 个工具"""
        assert len(TOOLS) == 14
        assert isinstance(TOOLS, tuple)

    def test_tool_names(self):
        """所有 tool name 可枚举"""
        names = {t.name for t in TOOLS}
        expected = {
            "list_entries", "get_entry", "create_entry", "update_entry",
            "delete_entry", "search_entries", "get_knowledge_graph",
            "get_related_concepts", "get_project_progress",
            "get_review_summary", "get_knowledge_stats",
            "batch_create_entries", "batch_update_status", "get_learning_path",
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
            handle_batch_create_entries, handle_batch_update_status,
            handle_get_learning_path,
        ]
        for h in handlers:
            assert callable(h)


class TestServerRouting:
    def test_tool_handlers_map_completeness(self):
        """TOOL_HANDLERS 映射覆盖所有 tool name"""
        from app.mcp.server import TOOL_HANDLERS
        assert len(TOOL_HANDLERS) == 14
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
            id(handle_batch_create_entries), id(handle_batch_update_status),
            id(handle_get_learning_path),
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

        with patch("app.routers.deps.storage", mock_storage), \
             patch("app.mcp.server.authenticated_user_id", "user-123"), \
             patch("app.mcp.server.TOOL_HANDLERS", {"list_entries": mock_handler}):
            result = await call_tool("list_entries", {"limit": 10})
            mock_handler.assert_called_once_with(mock_storage, {"limit": 10}, "user-123")

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """未知工具名返回错误消息"""
        from app.mcp.server import call_tool

        with patch("app.routers.deps.storage", MagicMock()), \
             patch("app.mcp.server.authenticated_user_id", "user-123"):
            result = await call_tool("nonexistent_tool", {})
            assert len(result) == 1
            assert "未知工具" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_handler_exception(self):
        """handler 抛异常时返回错误消息"""
        from app.mcp.server import call_tool

        mock_handler = AsyncMock(side_effect=ValueError("test error"))
        with patch("app.routers.deps.storage", MagicMock()), \
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

        with patch("app.routers.deps.storage", None), \
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


class TestB58EntryBelongsToUserFallback:
    """B58: _entry_belongs_to_user 回退策略为 return False"""

    def test_entry_belongs_to_user_returns_false_on_unknown_object(self):
        """无法判断归属的对象（无 user_id 属性）应返回 False"""
        from app.mcp.handlers import _entry_belongs_to_user

        # 普通对象没有 user_id 属性，也不是 dict
        class FakeEntry:
            pass

        result = _entry_belongs_to_user(FakeEntry(), "usr_alice")
        assert result is False

    def test_entry_belongs_to_user_task_object_no_user_id_field(self):
        """Task 对象没有 user_id 字段，走不到 hasattr 分支，返回 False"""
        from app.mcp.handlers import _entry_belongs_to_user
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime

        entry = Task(
            id="test-1", title="t", content="",
            category=Category.TASK, status=TaskStatus.DOING,
            priority=Priority.MEDIUM, tags=[],
            created_at=datetime.now(), updated_at=datetime.now(),
            file_path="tasks/test-1.md",
        )

        # Task 没有 user_id 属性，无法判断归属 → 返回 False
        assert _entry_belongs_to_user(entry, "usr_alice") is False

    def test_entry_belongs_to_user_object_with_user_id_attr(self):
        """带 user_id 属性的自定义对象应正确判断"""
        from app.mcp.handlers import _entry_belongs_to_user

        class EntryWithUser:
            def __init__(self, uid):
                self.user_id = uid

        entry = EntryWithUser("usr_alice")
        assert _entry_belongs_to_user(entry, "usr_alice") is True
        assert _entry_belongs_to_user(entry, "usr_bob") is False

    def test_entry_belongs_to_user_dict_match(self):
        """dict 格式条目 user_id 匹配时返回 True"""
        from app.mcp.handlers import _entry_belongs_to_user

        entry = {"id": "test-1", "user_id": "usr_alice"}
        assert _entry_belongs_to_user(entry, "usr_alice") is True
        assert _entry_belongs_to_user(entry, "usr_bob") is False

    def test_entry_belongs_to_user_dict_no_user_id_key(self):
        """dict 没有 user_id 键时返回 False（安全优先）"""
        from app.mcp.handlers import _entry_belongs_to_user

        entry = {"id": "test-1", "title": "no user"}
        assert _entry_belongs_to_user(entry, "usr_alice") is False


class TestB58McpHandlerUserIsolation:
    """B58: MCP handler 传递 user_id 后隔离生效"""

    @pytest.mark.asyncio
    async def test_get_entry_passes_user_id_to_sqlite(self):
        """handle_get_entry 应将 user_id 传递给 sqlite.get_entry"""
        mock_storage = MagicMock()
        mock_storage.sqlite = MagicMock()
        mock_storage.sqlite.get_entry = MagicMock(return_value={"id": "task-1", "user_id": "usr_alice"})

        mock_md = MagicMock()
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime
        mock_md.read_entry = MagicMock(return_value=Task(
            id="task-1", title="测试", content="内容",
            category=Category.TASK, status=TaskStatus.DOING,
            priority=Priority.MEDIUM, tags=[],
            created_at=datetime.now(), updated_at=datetime.now(),
            file_path="tasks/task-1.md",
        ))
        mock_storage.get_markdown_storage = MagicMock(return_value=mock_md)

        result = await handle_get_entry(mock_storage, {"id": "task-1"}, "usr_alice")

        # 验证 get_entry 被调用时传递了 user_id
        mock_storage.sqlite.get_entry.assert_called_once_with("task-1", user_id="usr_alice")

    @pytest.mark.asyncio
    async def test_update_entry_passes_user_id_to_sqlite(self):
        """handle_update_entry 应将 user_id 传递给 sqlite.get_entry"""
        mock_storage = MagicMock()
        mock_storage.sqlite = MagicMock()
        mock_storage.sqlite.get_entry = MagicMock(return_value={"id": "task-1", "user_id": "usr_alice"})

        mock_md = MagicMock()
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime
        mock_md.read_entry = MagicMock(return_value=Task(
            id="task-1", title="测试", content="内容",
            category=Category.TASK, status=TaskStatus.DOING,
            priority=Priority.MEDIUM, tags=[],
            created_at=datetime.now(), updated_at=datetime.now(),
            file_path="tasks/task-1.md",
        ))
        mock_storage.get_markdown_storage = MagicMock(return_value=mock_md)
        mock_storage.sync_entry = AsyncMock()

        result = await handle_update_entry(mock_storage, {"id": "task-1", "title": "新标题"}, "usr_alice")

        mock_storage.sqlite.get_entry.assert_called_once_with("task-1", user_id="usr_alice")

    @pytest.mark.asyncio
    async def test_delete_entry_passes_user_id_to_sqlite(self):
        """handle_delete_entry 应将 user_id 传递给 sqlite.get_entry"""
        mock_storage = MagicMock()
        mock_storage.sqlite = MagicMock()
        mock_storage.sqlite.get_entry = MagicMock(return_value={"id": "task-1", "user_id": "usr_alice"})
        mock_storage.delete_entry = AsyncMock(return_value=True)

        result = await handle_delete_entry(mock_storage, {"id": "task-1"}, "usr_alice")

        mock_storage.sqlite.get_entry.assert_called_once_with("task-1", user_id="usr_alice")

    @pytest.mark.asyncio
    async def test_get_project_progress_passes_user_id_to_sqlite(self):
        """handle_get_project_progress 应将 user_id 传递给 sqlite.get_entry"""
        mock_storage = MagicMock()
        mock_storage.sqlite = MagicMock()
        mock_storage.sqlite.get_entry = MagicMock(return_value={"id": "project-1", "user_id": "usr_alice"})
        mock_storage.sqlite.list_entries = MagicMock(return_value=[])

        mock_md = MagicMock()
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime
        mock_md.read_entry = MagicMock(return_value=Task(
            id="project-1", title="项目", content="",
            category=Category.PROJECT, status=TaskStatus.DOING,
            priority=Priority.MEDIUM, tags=[],
            created_at=datetime.now(), updated_at=datetime.now(),
            file_path="projects/project-1.md",
        ))
        mock_storage.get_markdown_storage = MagicMock(return_value=mock_md)

        result = await handle_get_project_progress(mock_storage, {"project_id": "project-1"}, "usr_alice")

        mock_storage.sqlite.get_entry.assert_called_once_with("project-1", user_id="usr_alice")

    @pytest.mark.asyncio
    async def test_batch_update_status_passes_user_id_to_sqlite(self):
        """handle_batch_update_status 应将 user_id 传递给 sqlite.get_entry"""
        mock_storage = MagicMock()
        mock_storage.sqlite = MagicMock()
        mock_storage.sqlite.get_entry = MagicMock(return_value={"id": "task-1", "user_id": "usr_alice"})

        mock_md = MagicMock()
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime
        mock_md.read_entry = MagicMock(return_value=Task(
            id="task-1", title="测试", content="内容",
            category=Category.TASK, status=TaskStatus.DOING,
            priority=Priority.MEDIUM, tags=[],
            created_at=datetime.now(), updated_at=datetime.now(),
            file_path="tasks/task-1.md",
        ))
        mock_storage.get_markdown_storage = MagicMock(return_value=mock_md)
        mock_storage.sync_entry = AsyncMock()

        result = await handle_batch_update_status(
            mock_storage, {"ids": ["task-1"], "status": "complete"}, "usr_alice"
        )

        mock_storage.sqlite.get_entry.assert_called_once_with("task-1", user_id="usr_alice")
