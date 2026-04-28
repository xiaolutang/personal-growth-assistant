"""Agent Tools 单元测试

覆盖 7 个 tool 的正常参数、边界条件、异常处理和空数据库场景。
所有 service 调用使用 AsyncMock 模拟，不依赖真实存储。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from app.agent.schemas import (
    CreateEntryInput,
    UpdateEntryInput,
    DeleteEntryInput,
    SearchEntriesInput,
    GetEntryInput,
    GetReviewSummaryInput,
    AskUserInput,
    ToolResult,
)
from app.agent.tools import (
    ToolDependencies,
    _create_entry,
    _update_entry,
    _delete_entry,
    _search_entries,
    _get_entry,
    _get_review_summary,
    _ask_user,
    AGENT_TOOLS,
    AGENT_TOOL_NAMES,
)


# === Fixtures ===

def _make_entry_response(**overrides):
    """构造模拟的 EntryResponse 对象"""
    defaults = {
        "id": "note-abc12345",
        "title": "测试条目",
        "content": "测试内容",
        "category": "note",
        "status": "doing",
        "priority": "medium",
        "tags": ["test"],
        "created_at": "2026-04-28T10:00:00",
        "updated_at": "2026-04-28T10:00:00",
        "planned_date": None,
        "completed_at": None,
        "time_spent": None,
        "parent_id": None,
        "file_path": "notes/note-abc12345.md",
    }
    defaults.update(overrides)
    resp = MagicMock()
    for k, v in defaults.items():
        setattr(resp, k, v)
    resp.model_dump = lambda: dict(defaults)
    return resp


def _make_task_stats():
    """构造模拟的 TaskStats"""
    stats = MagicMock()
    stats.total = 5
    stats.completed = 2
    stats.doing = 2
    stats.wait_start = 1
    stats.completion_rate = 40.0
    return stats


def _make_note_stats():
    """构造模拟的 NoteStats"""
    stats = MagicMock()
    stats.total = 3
    return stats


def _make_daily_report():
    """构造模拟的 DailyReport"""
    report = MagicMock()
    report.date = "2026-04-28"
    report.task_stats = _make_task_stats()
    report.note_stats = _make_note_stats()
    report.ai_summary = "今日完成 2 个任务"
    report.completed_tasks = []
    return report


def _make_weekly_report():
    """构造模拟的 WeeklyReport"""
    report = MagicMock()
    report.start_date = "2026-04-27"
    report.end_date = "2026-05-03"
    report.task_stats = _make_task_stats()
    report.note_stats = _make_note_stats()
    report.ai_summary = "本周完成 2 个任务"
    report.completed_tasks = []
    report.daily_breakdown = []
    return report


@pytest.fixture
def mock_entry_service():
    """模拟 EntryService"""
    service = AsyncMock()
    service.create_entry = AsyncMock(return_value=_make_entry_response())
    service.update_entry = AsyncMock(return_value=(True, "已更新条目: note-abc12345"))
    service.delete_entry = AsyncMock(return_value=(True, "已删除条目: note-abc12345"))
    service.search_entries = AsyncMock(return_value=None)  # 需要单独设置
    service.get_entry = AsyncMock(return_value=_make_entry_response())
    return service


@pytest.fixture
def mock_review_service():
    """模拟 ReviewService"""
    service = AsyncMock()
    service.get_daily_report = AsyncMock(return_value=_make_daily_report())
    service.get_weekly_report = AsyncMock(return_value=_make_weekly_report())
    return service


@pytest.fixture
def deps(mock_entry_service, mock_review_service):
    """构造注入好依赖的 ToolDependencies"""
    d = ToolDependencies()
    d.set_entry_service(mock_entry_service)
    d.set_review_service(mock_review_service)
    return d


# === 正常参数测试 ===


class TestCreateEntry:
    """create_entry tool 测试"""

    @pytest.mark.asyncio
    async def test_normal_create(self, deps, mock_entry_service):
        """正常参数：创建条目"""
        result = await _create_entry(
            category="note",
            title="测试笔记",
            content="这是一条测试笔记",
            tags=["test"],
            dependencies=deps,
            user_id="user-1",
        )

        assert result["success"] is True
        assert result["data"]["id"] == "note-abc12345"
        assert result["data"]["title"] == "测试条目"  # mock 返回固定值
        assert result["data"]["category"] == "note"
        mock_entry_service.create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_minimal_params(self, deps, mock_entry_service):
        """最小参数：仅必填字段"""
        result = await _create_entry(
            category="task",
            title="任务标题",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["category"] == "note"  # mock 返回值
        mock_entry_service.create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_params(self, deps, mock_entry_service):
        """完整参数：所有字段"""
        result = await _create_entry(
            category="task",
            title="完整任务",
            content="任务内容",
            tags=["tag1", "tag2"],
            parent_id="project-xxx",
            status="doing",
            priority="high",
            planned_date="2026-05-01",
            time_spent=30,
            dependencies=deps,
            user_id="user-1",
        )

        assert result["success"] is True
        mock_entry_service.create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_returns_none(self, deps, mock_entry_service):
        """边界条件：service 返回 None"""
        mock_entry_service.create_entry = AsyncMock(return_value=None)

        result = await _create_entry(
            category="note",
            title="测试",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "None" in result["error"]

    @pytest.mark.asyncio
    async def test_service_exception(self, deps, mock_entry_service):
        """异常处理：service 抛出异常"""
        mock_entry_service.create_entry = AsyncMock(side_effect=RuntimeError("存储异常"))

        result = await _create_entry(
            category="note",
            title="测试",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "存储异常" in result["error"]

    @pytest.mark.asyncio
    async def test_no_entry_service(self):
        """异常处理：EntryService 未初始化"""
        d = ToolDependencies()
        result = await _create_entry(
            category="note",
            title="测试",
            dependencies=d,
        )

        assert result["success"] is False
        assert "EntryService" in result["error"]


class TestUpdateEntry:
    """update_entry tool 测试"""

    @pytest.mark.asyncio
    async def test_update_title(self, deps, mock_entry_service):
        """正常参数：更新标题"""
        result = await _update_entry(
            entry_id="note-abc12345",
            title="新标题",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["entry_id"] == "note-abc12345"
        mock_entry_service.update_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_all_fields(self, deps, mock_entry_service):
        """完整参数：更新所有字段"""
        result = await _update_entry(
            entry_id="note-abc12345",
            title="新标题",
            content="新内容",
            status="complete",
            priority="high",
            tags=["new-tag"],
            dependencies=deps,
        )

        assert result["success"] is True
        mock_entry_service.update_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, deps, mock_entry_service):
        """边界条件：条目不存在"""
        mock_entry_service.update_entry = AsyncMock(
            return_value=(False, "条目不存在: note-abc12345")
        )

        result = await _update_entry(
            entry_id="note-abc12345",
            title="新标题",
            dependencies=deps,
        )

        assert result["success"] is False
        assert result["data"]["message"] == "条目不存在: note-abc12345"

    @pytest.mark.asyncio
    async def test_service_exception(self, deps, mock_entry_service):
        """异常处理：service 抛出异常"""
        mock_entry_service.update_entry = AsyncMock(side_effect=ValueError("无效参数"))

        result = await _update_entry(
            entry_id="note-abc12345",
            title="新标题",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "无效参数" in result["error"]


class TestDeleteEntry:
    """delete_entry tool 测试"""

    @pytest.mark.asyncio
    async def test_normal_delete(self, deps, mock_entry_service):
        """正常参数：删除条目"""
        result = await _delete_entry(
            entry_id="note-abc12345",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["entry_id"] == "note-abc12345"
        mock_entry_service.delete_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, deps, mock_entry_service):
        """边界条件：条目不存在"""
        mock_entry_service.delete_entry = AsyncMock(
            return_value=(False, "条目不存在: note-abc12345")
        )

        result = await _delete_entry(
            entry_id="note-abc12345",
            dependencies=deps,
        )

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_service_exception(self, deps, mock_entry_service):
        """异常处理：service 抛出异常"""
        mock_entry_service.delete_entry = AsyncMock(side_effect=RuntimeError("删除异常"))

        result = await _delete_entry(
            entry_id="note-abc12345",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "删除异常" in result["error"]


class TestSearchEntries:
    """search_entries tool 测试"""

    @pytest.mark.asyncio
    async def test_normal_search(self, deps, mock_entry_service):
        """正常参数：搜索条目"""
        mock_result = MagicMock()
        mock_entry = _make_entry_response()
        mock_result.entries = [mock_entry]
        mock_result.query = "测试"
        mock_entry_service.search_entries = AsyncMock(return_value=mock_result)

        result = await _search_entries(
            query="测试",
            limit=5,
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["query"] == "测试"
        assert result["data"]["total"] == 1
        mock_entry_service.search_entries.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_no_results(self, deps, mock_entry_service):
        """边界条件：搜索无结果"""
        mock_result = MagicMock()
        mock_result.entries = []
        mock_result.query = "不存在的关键词"
        mock_entry_service.search_entries = AsyncMock(return_value=mock_result)

        result = await _search_entries(
            query="不存在的关键词",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert result["data"]["entries"] == []

    @pytest.mark.asyncio
    async def test_service_exception(self, deps, mock_entry_service):
        """异常处理：service 抛出异常"""
        mock_entry_service.search_entries = AsyncMock(
            side_effect=RuntimeError("没有可用的搜索服务")
        )

        result = await _search_entries(
            query="测试",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "搜索服务" in result["error"]


class TestGetEntry:
    """get_entry tool 测试"""

    @pytest.mark.asyncio
    async def test_normal_get(self, deps, mock_entry_service):
        """正常参数：获取条目"""
        result = await _get_entry(
            entry_id="note-abc12345",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["id"] == "note-abc12345"
        assert result["data"]["title"] == "测试条目"
        mock_entry_service.get_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_entry_not_found(self, deps, mock_entry_service):
        """边界条件：条目不存在"""
        mock_entry_service.get_entry = AsyncMock(return_value=None)

        result = await _get_entry(
            entry_id="note-nonexist",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_service_exception(self, deps, mock_entry_service):
        """异常处理：service 抛出异常"""
        mock_entry_service.get_entry = AsyncMock(side_effect=RuntimeError("读取异常"))

        result = await _get_entry(
            entry_id="note-abc12345",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "读取异常" in result["error"]


class TestGetReviewSummary:
    """get_review_summary tool 测试"""

    @pytest.mark.asyncio
    async def test_daily_report(self, deps, mock_review_service):
        """正常参数：获取日报"""
        result = await _get_review_summary(
            period="daily",
            target_date="2026-04-28",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["period"] == "daily"
        assert result["data"]["date_range"] == "2026-04-28"
        assert result["data"]["task_stats"]["total"] == 5
        mock_review_service.get_daily_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_weekly_report(self, deps, mock_review_service):
        """正常参数：获取周报"""
        result = await _get_review_summary(
            period="weekly",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["period"] == "weekly"
        assert "2026-04-27" in result["data"]["date_range"]
        mock_review_service.get_weekly_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_period(self, deps, mock_review_service):
        """默认参数：period 默认 daily"""
        result = await _get_review_summary(
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["period"] == "daily"

    @pytest.mark.asyncio
    async def test_no_review_service(self):
        """异常处理：ReviewService 未初始化"""
        d = ToolDependencies()
        d.set_entry_service(AsyncMock())

        result = await _get_review_summary(
            dependencies=d,
        )

        assert result["success"] is False
        assert "ReviewService" in result["error"]

    @pytest.mark.asyncio
    async def test_service_exception(self, deps, mock_review_service):
        """异常处理：service 抛出异常"""
        mock_review_service.get_daily_report = AsyncMock(
            side_effect=RuntimeError("SQLite 不可用")
        )

        result = await _get_review_summary(
            period="daily",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "SQLite" in result["error"]


class TestAskUser:
    """ask_user tool 测试"""

    @pytest.mark.asyncio
    async def test_normal_ask(self, deps):
        """正常参数：向用户提问"""
        result = await _ask_user(
            question="请问您想创建什么类型的条目？",
            dependencies=deps,
        )

        # ask_user 返回 AskUserOutput 结构，不经过 ToolResult 包装
        assert result["type"] == "ask"
        assert result["question"] == "请问您想创建什么类型的条目？"

    @pytest.mark.asyncio
    async def test_ask_with_long_question(self, deps):
        """边界条件：长问题"""
        long_question = "这是一个很长的问题？" * 50
        result = await _ask_user(
            question=long_question,
            dependencies=deps,
        )

        assert result["type"] == "ask"
        assert result["question"] == long_question


class TestPydanticSchemas:
    """Pydantic schema 参数校验测试"""

    def test_create_entry_input_valid(self):
        """CreateEntryInput 合法参数"""
        inp = CreateEntryInput(category="note", title="测试")
        assert inp.category == "note"
        assert inp.title == "测试"
        assert inp.content == ""
        assert inp.tags == []

    def test_create_entry_input_missing_required(self):
        """CreateEntryInput 缺少必填字段"""
        with pytest.raises(Exception):
            CreateEntryInput(title="测试")  # 缺少 category

        with pytest.raises(Exception):
            CreateEntryInput(category="note")  # 缺少 title

    def test_update_entry_input_only_id(self):
        """UpdateEntryInput 仅 entry_id"""
        inp = UpdateEntryInput(entry_id="note-abc12345")
        assert inp.entry_id == "note-abc12345"
        assert inp.title is None

    def test_search_entries_input_defaults(self):
        """SearchEntriesInput 默认值"""
        inp = SearchEntriesInput(query="测试")
        assert inp.limit == 10

    def test_get_entry_input_valid(self):
        """GetEntryInput 合法参数"""
        inp = GetEntryInput(entry_id="note-abc12345")
        assert inp.entry_id == "note-abc12345"

    def test_get_review_summary_input_defaults(self):
        """GetReviewSummaryInput 默认值"""
        inp = GetReviewSummaryInput()
        assert inp.period == "daily"
        assert inp.target_date is None

    def test_ask_user_input_valid(self):
        """AskUserInput 合法参数"""
        inp = AskUserInput(question="测试问题？")
        assert inp.question == "测试问题？"

    def test_ask_user_input_empty_question(self):
        """AskUserInput 空 question"""
        with pytest.raises(Exception):
            AskUserInput(question="")

    def test_search_entries_input_empty_query(self):
        """SearchEntriesInput 空 query"""
        with pytest.raises(Exception):
            SearchEntriesInput(query="")

    def test_tool_result_success(self):
        """ToolResult 成功"""
        result = ToolResult(success=True, data={"id": "123"})
        assert result.success is True
        assert result.data == {"id": "123"}
        assert result.error is None

    def test_tool_result_failure(self):
        """ToolResult 失败"""
        result = ToolResult(success=False, error="出错了")
        assert result.success is False
        assert result.error == "出错了"
        assert result.data is None


class TestToolRegistration:
    """Tool 注册表测试"""

    def test_all_tools_registered(self):
        """所有 7 个 tools 都已注册"""
        assert len(AGENT_TOOLS) == 7
        expected_names = {
            "create_entry",
            "update_entry",
            "delete_entry",
            "search_entries",
            "get_entry",
            "get_review_summary",
            "ask_user",
        }
        assert AGENT_TOOL_NAMES == expected_names

    def test_tools_have_description(self):
        """所有 tools 都有描述"""
        for tool in AGENT_TOOLS:
            assert tool.description is not None
            assert len(tool.description) > 0

    def test_tools_have_args_schema(self):
        """所有 tools 都有 args_schema"""
        for tool in AGENT_TOOLS:
            assert tool.args_schema is not None


class TestToolDependencies:
    """ToolDependencies 测试"""

    def test_initial_state(self):
        """初始状态：所有 service 为 None"""
        d = ToolDependencies()
        assert d.entry_service is None
        assert d.review_service is None

    def test_set_entry_service(self):
        """注入 EntryService"""
        d = ToolDependencies()
        mock_svc = MagicMock()
        d.set_entry_service(mock_svc)
        assert d.entry_service is mock_svc

    def test_set_review_service(self):
        """注入 ReviewService"""
        d = ToolDependencies()
        mock_svc = MagicMock()
        d.set_review_service(mock_svc)
        assert d.review_service is mock_svc


class TestEmptyDatabase:
    """空数据库状态下的 tools 行为"""

    @pytest.mark.asyncio
    async def test_search_empty_db(self, deps, mock_entry_service):
        """空数据库：搜索返回空列表"""
        mock_result = MagicMock()
        mock_result.entries = []
        mock_result.query = "任何关键词"
        mock_entry_service.search_entries = AsyncMock(return_value=mock_result)

        result = await _search_entries(
            query="任何关键词",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["entries"] == []
        assert result["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_get_entry_empty_db(self, deps, mock_entry_service):
        """空数据库：获取条目返回不存在"""
        mock_entry_service.get_entry = AsyncMock(return_value=None)

        result = await _get_entry(
            entry_id="note-nonexist",
            dependencies=deps,
        )

        assert result["success"] is False
        assert "不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_create_still_works(self, deps, mock_entry_service):
        """空数据库：创建仍可正常工作"""
        result = await _create_entry(
            category="note",
            title="第一条笔记",
            content="这是第一条",
            dependencies=deps,
        )

        assert result["success"] is True
        mock_entry_service.create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_daily_empty_db(self, deps, mock_review_service):
        """空数据库：日报仍可生成（统计数据为 0）"""
        empty_stats = MagicMock()
        empty_stats.total = 0
        empty_stats.completed = 0
        empty_stats.doing = 0
        empty_stats.wait_start = 0
        empty_stats.completion_rate = 0.0

        empty_note_stats = MagicMock()
        empty_note_stats.total = 0

        empty_report = MagicMock()
        empty_report.date = "2026-04-28"
        empty_report.task_stats = empty_stats
        empty_report.note_stats = empty_note_stats
        empty_report.ai_summary = None
        empty_report.completed_tasks = []

        mock_review_service.get_daily_report = AsyncMock(return_value=empty_report)

        result = await _get_review_summary(
            period="daily",
            dependencies=deps,
        )

        assert result["success"] is True
        assert result["data"]["task_stats"]["total"] == 0
