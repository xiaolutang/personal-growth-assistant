"""测试 B19 条目关联 API — get_related_entries"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.entry_service import EntryService
from app.models import Task, Category, TaskStatus, Priority
from app.api.schemas import RelatedEntriesResponse
from datetime import datetime


def _make_task(entry_id: str, title: str = "", tags=None, parent_id=None, **kw) -> Task:
    return Task(
        id=entry_id,
        title=title or f"测试-{entry_id}",
        content=kw.get("content", ""),
        category=kw.get("category", Category.TASK),
        status=kw.get("status", TaskStatus.DOING),
        priority=kw.get("priority", Priority.MEDIUM),
        tags=tags or [],
        created_at=kw.get("created_at", datetime.now()),
        updated_at=kw.get("updated_at", datetime.now()),
        file_path=kw.get("file_path", f"tasks/{entry_id}.md"),
        parent_id=parent_id,
    )


class TestGetRelatedEntries:
    """EntryService.get_related_entries 测试"""

    @pytest.fixture
    def service(self, storage):
        return EntryService(storage=storage)

    @pytest.mark.asyncio
    async def test_returns_siblings_when_same_parent(self, service, storage):
        """同项目条目优先返回"""
        parent_id = "project-parent"
        entry = _make_task("task-1", "任务1", parent_id=parent_id)
        sibling = _make_task("task-2", "任务2", parent_id=parent_id)

        # Mock entry read
        md_storage = MagicMock()
        md_storage.read_entry = MagicMock(return_value=entry)
        storage.get_markdown_storage = MagicMock(return_value=md_storage)
        # Mock _verify_entry_owner
        service._verify_entry_owner = MagicMock(return_value=True)
        # Mock list_entries to return siblings
        mock_response = MagicMock()
        mock_response.entries = [entry, sibling]
        service.list_entries = AsyncMock(return_value=mock_response)
        # No tags, no sqlite
        storage.sqlite = None
        # Mock HybridSearchService to return empty
        with patch("app.services.entry_service.HybridSearchService") as MockSearch:
            MockSearch.return_value.search = AsyncMock(return_value=[])
            result = await service.get_related_entries("task-1", user_id="u1")

        assert result is not None
        assert len(result.related) >= 1
        assert result.related[0].relevance_reason == "同项目"
        assert result.related[0].id == "task-2"

    @pytest.mark.asyncio
    async def test_tag_overlap_fills_when_no_siblings(self, service, storage):
        """无同项目时，标签重叠补位"""
        entry = _make_task("task-1", "任务1", tags=["react", "hooks"])

        md_storage = MagicMock()
        md_storage.read_entry = MagicMock(return_value=entry)
        storage.get_markdown_storage = MagicMock(return_value=md_storage)
        service._verify_entry_owner = MagicMock(return_value=True)
        service.list_entries = AsyncMock(return_value=MagicMock(entries=[entry]))

        # Mock sqlite with tag overlap
        mock_sqlite = MagicMock()
        mock_sqlite.find_entries_by_tag_overlap = MagicMock(return_value=[
            {"id": "task-3", "title": "React Hooks 指南", "category": "note"},
        ])
        storage.sqlite = mock_sqlite

        with patch("app.services.entry_service.HybridSearchService") as MockSearch:
            MockSearch.return_value.search = AsyncMock(return_value=[])
            result = await service.get_related_entries("task-1", user_id="u1")

        assert result is not None
        assert len(result.related) == 1
        assert result.related[0].relevance_reason == "标签相关"

    @pytest.mark.asyncio
    async def test_vector_similarity_fallback(self, service, storage):
        """无同项目、无标签重叠时，混合搜索兜底"""
        entry = _make_task("task-1", "任务1", tags=[])

        md_storage = MagicMock()
        md_storage.read_entry = MagicMock(return_value=entry)
        storage.get_markdown_storage = MagicMock(return_value=md_storage)
        service._verify_entry_owner = MagicMock(return_value=True)
        service.list_entries = AsyncMock(return_value=MagicMock(entries=[entry]))
        storage.sqlite = None

        # Mock vector search results
        from app.api.schemas import EntryResponse
        mock_vr = EntryResponse(
            id="task-vec1", title="相似条目", category="note",
            status="doing", priority="medium", tags=[],
            content="相似内容", file_path="notes/task-vec1.md",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        with patch("app.services.entry_service.HybridSearchService") as MockSearch:
            MockSearch.return_value.search = AsyncMock(return_value=[mock_vr])
            result = await service.get_related_entries("task-1", user_id="u1")

        assert result is not None
        assert len(result.related) == 1
        assert result.related[0].relevance_reason == "搜索相关"

    @pytest.mark.asyncio
    async def test_max_5_results(self, service, storage):
        """最多返回 5 条"""
        parent_id = "project-parent"
        entry = _make_task("task-1", "任务1", parent_id=parent_id)
        siblings = [_make_task(f"task-s{i}", f"兄弟{i}", parent_id=parent_id) for i in range(8)]

        md_storage = MagicMock()
        md_storage.read_entry = MagicMock(return_value=entry)
        storage.get_markdown_storage = MagicMock(return_value=md_storage)
        service._verify_entry_owner = MagicMock(return_value=True)
        service.list_entries = AsyncMock(return_value=MagicMock(entries=[entry] + siblings))
        storage.sqlite = None

        with patch("app.services.entry_service.HybridSearchService") as MockSearch:
            MockSearch.return_value.search = AsyncMock(return_value=[])
            result = await service.get_related_entries("task-1", user_id="u1")

        assert result is not None
        assert len(result.related) == 5

    @pytest.mark.asyncio
    async def test_empty_when_no_relations(self, service, storage):
        """无关联时返回空数组"""
        entry = _make_task("task-1", "任务1", tags=[])

        md_storage = MagicMock()
        md_storage.read_entry = MagicMock(return_value=entry)
        storage.get_markdown_storage = MagicMock(return_value=md_storage)
        service._verify_entry_owner = MagicMock(return_value=True)
        service.list_entries = AsyncMock(return_value=MagicMock(entries=[entry]))
        storage.sqlite = None

        with patch("app.services.entry_service.HybridSearchService") as MockSearch:
            MockSearch.return_value.search = AsyncMock(return_value=[])
            result = await service.get_related_entries("task-1", user_id="u1")

        assert result is not None
        assert len(result.related) == 0

    @pytest.mark.asyncio
    async def test_returns_none_when_entry_not_found(self, service, storage):
        """目标条目不存在时返回 None"""
        md_storage = MagicMock()
        md_storage.read_entry = MagicMock(return_value=None)
        storage.get_markdown_storage = MagicMock(return_value=md_storage)
        service._verify_entry_owner = MagicMock(return_value=True)

        result = await service.get_related_entries("nonexistent", user_id="u1")
        assert result is None

    @pytest.mark.asyncio
    async def test_vector_failure_graceful(self, service, storage):
        """向量搜索失败时不报错，返回前两层结果"""
        entry = _make_task("task-1", "任务1", parent_id="project-p")
        sibling = _make_task("task-2", "兄弟", parent_id="project-p")

        md_storage = MagicMock()
        md_storage.read_entry = MagicMock(return_value=entry)
        storage.get_markdown_storage = MagicMock(return_value=md_storage)
        service._verify_entry_owner = MagicMock(return_value=True)
        service.list_entries = AsyncMock(return_value=MagicMock(entries=[entry, sibling]))
        storage.sqlite = None

        with patch("app.services.entry_service.HybridSearchService") as MockSearch:
            MockSearch.return_value.search = AsyncMock(side_effect=Exception("Qdrant down"))
            result = await service.get_related_entries("task-1", user_id="u1")

        assert result is not None
        assert len(result.related) == 1
        assert result.related[0].relevance_reason == "同项目"
