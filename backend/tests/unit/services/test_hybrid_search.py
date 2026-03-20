"""测试 HybridSearchService 混合搜索服务"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.hybrid_search import HybridSearchService, HybridSearchResult
from app.api.schemas.entry import EntryResponse


class TestHybridSearchService:
    """HybridSearchService 测试"""

    @pytest.fixture
    def mock_storage(self):
        """创建 mock storage"""
        storage = MagicMock()
        storage.qdrant = MagicMock()
        storage.sqlite = MagicMock()
        storage.markdown = MagicMock()
        return storage

    @pytest.fixture
    def service(self, mock_storage):
        """创建服务实例"""
        return HybridSearchService(mock_storage)

    def test_normalize_scores_empty(self, service):
        """测试空分数列表归一化"""
        result = service._normalize_scores([])
        assert result == []

    def test_normalize_scores_all_zeros(self, service):
        """测试全零分数归一化"""
        result = service._normalize_scores([0, 0, 0])
        assert result == [0.0, 0.0, 0.0]

    def test_normalize_scores_single_value(self, service):
        """测试单个值归一化"""
        result = service._normalize_scores([0.5])
        assert result == [1.0]

    def test_normalize_scores_multiple_values(self, service):
        """测试多值归一化"""
        result = service._normalize_scores([0.2, 0.5, 1.0])
        assert result == [0.2, 0.5, 1.0]

        result = service._normalize_scores([2.0, 4.0, 6.0])
        assert result == pytest.approx([1/3, 2/3, 1.0])

    @pytest.mark.asyncio
    async def test_search_both_services_available(self, mock_storage):
        """测试向量搜索和全文搜索都可用"""
        # 配置 mock
        mock_storage.qdrant.search = AsyncMock(return_value=[
            {"id": "task-001", "score": 0.9},
            {"id": "task-002", "score": 0.7},
        ])
        mock_storage.sqlite.search.return_value = [
            {"id": "task-001", "title": "测试任务", "content": "内容"},
            {"id": "task-003", "title": "其他任务", "content": "内容"},
        ]
        mock_storage.markdown.read_entry.return_value = None

        service = HybridSearchService(mock_storage)
        results = await service.search("测试查询", limit=10)

        # 验证两个搜索都被调用
        mock_storage.qdrant.search.assert_called_once()
        mock_storage.sqlite.search.assert_called_once()

        # task-001 同时出现在两个搜索结果中，分数应该更高
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_vector_only(self, mock_storage):
        """测试仅向量搜索可用"""
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime

        # 配置 mock - 禁用 SQLite
        mock_storage.sqlite = None
        mock_storage.qdrant.search = AsyncMock(return_value=[
            {"id": "task-001", "score": 0.9, "payload": {"title": "测试"}},
        ])

        # 创建真实的 Task 对象
        mock_entry = Task(
            id="task-001",
            title="测试任务",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime(2026, 3, 20, 10, 0, 0),
            updated_at=datetime(2026, 3, 20, 10, 0, 0),
            file_path="tasks/task-001.md",
        )
        mock_storage.markdown.read_entry.return_value = mock_entry

        service = HybridSearchService(mock_storage)
        results = await service.search("测试查询", limit=10)

        mock_storage.qdrant.search.assert_called_once()
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_text_only(self, mock_storage):
        """测试仅全文搜索可用"""
        # 配置 mock - 禁用 Qdrant
        mock_storage.qdrant = None
        mock_storage.sqlite.search.return_value = [
            {"id": "task-001", "title": "测试任务", "content": "内容"},
        ]

        service = HybridSearchService(mock_storage)
        results = await service.search("测试查询", limit=10)

        mock_storage.sqlite.search.assert_called_once()
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_storage):
        """测试无搜索结果"""
        mock_storage.qdrant.search = AsyncMock(return_value=[])
        mock_storage.sqlite.search.return_value = []

        service = HybridSearchService(mock_storage)
        results = await service.search("不存在的查询", limit=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_vector_error_fallback(self, mock_storage):
        """测试向量搜索出错时回退"""
        mock_storage.qdrant.search = AsyncMock(side_effect=Exception("Qdrant error"))
        mock_storage.sqlite.search.return_value = [
            {"id": "task-001", "title": "测试任务", "content": "内容"},
        ]

        service = HybridSearchService(mock_storage)
        results = await service.search("测试查询", limit=10)

        # 应该能从全文搜索获得结果
        mock_storage.sqlite.search.assert_called_once()
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_text_error_fallback(self, mock_storage):
        """测试全文搜索出错时回退"""
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime

        mock_storage.qdrant.search = AsyncMock(return_value=[
            {"id": "task-001", "score": 0.9, "payload": {"title": "测试"}},
        ])
        mock_storage.sqlite.search.side_effect = Exception("SQLite error")

        # 创建真实的 Task 对象
        mock_entry = Task(
            id="task-001",
            title="测试任务",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime(2026, 3, 20, 10, 0, 0),
            updated_at=datetime(2026, 3, 20, 10, 0, 0),
            file_path="tasks/task-001.md",
        )
        mock_storage.markdown.read_entry.return_value = mock_entry

        service = HybridSearchService(mock_storage)
        results = await service.search("测试查询", limit=10)

        # 应该能从向量搜索获得结果
        mock_storage.qdrant.search.assert_called_once()
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_custom_weights(self, mock_storage):
        """测试自定义权重"""
        mock_storage.qdrant.search = AsyncMock(return_value=[
            {"id": "task-001", "score": 1.0},
        ])
        mock_storage.sqlite.search.return_value = [
            {"id": "task-001", "title": "测试任务", "content": "内容"},
        ]

        service = HybridSearchService(mock_storage)
        # 使用自定义权重：向量 0.3，全文 0.7
        results = await service.search(
            "测试查询",
            limit=10,
            vector_weight=0.3,
            text_weight=0.7,
        )

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_min_score_filter(self, mock_storage):
        """测试最低分数过滤"""
        mock_storage.qdrant.search = AsyncMock(return_value=[
            {"id": "task-001", "score": 0.1},  # 低分
        ])
        mock_storage.sqlite.search.return_value = []  # 无全文结果

        service = HybridSearchService(mock_storage)
        # 使用非常高的 min_score（几乎不可能达到）
        results = await service.search(
            "测试查询",
            limit=10,
            min_score=0.99,  # 极高阈值
        )

        # 低分结果应该被过滤掉
        assert results == []

    @pytest.mark.asyncio
    async def test_search_limit(self, mock_storage):
        """测试结果数量限制"""
        # 创建多个搜索结果 - 使用全文搜索数据
        mock_storage.qdrant.search = AsyncMock(return_value=[])
        mock_storage.sqlite.search.return_value = [
            {
                "id": f"task-{i:03d}",
                "title": f"任务{i}",
                "content": "内容",
                "type": "task",
                "status": "doing",
                "file_path": f"tasks/task-{i:03d}.md",
                "created_at": "2026-03-20T10:00:00",
                "updated_at": "2026-03-20T10:00:00",
                "priority": "medium",
                "tags": [],
            }
            for i in range(10)
        ]

        service = HybridSearchService(mock_storage)
        results = await service.search("测试查询", limit=3)

        # 应该只返回 3 个结果
        assert len(results) == 3


class TestHybridSearchResult:
    """HybridSearchResult 数据类测试"""

    def test_dataclass_creation(self):
        """测试数据类创建"""
        result = HybridSearchResult(
            entry_id="task-001",
            score=0.85,
            vector_score=0.9,
            text_score=1.0,
        )

        assert result.entry_id == "task-001"
        assert result.score == 0.85
        assert result.vector_score == 0.9
        assert result.text_score == 1.0
        assert result.entry_data is None

    def test_dataclass_with_entry_data(self):
        """测试带 entry_data 的数据类"""
        entry_data = {"id": "task-001", "title": "测试"}
        result = HybridSearchResult(
            entry_id="task-001",
            score=0.85,
            vector_score=0.9,
            text_score=1.0,
            entry_data=entry_data,
        )

        assert result.entry_data == entry_data
