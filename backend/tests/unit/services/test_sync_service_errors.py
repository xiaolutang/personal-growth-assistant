"""SyncService 错误处理测试 - Mock 外部依赖"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority
from app.services.sync_service import SyncService
from app.infrastructure.storage.markdown import MarkdownStorage


class TestSyncServiceErrors:
    """SyncService 错误处理测试"""

    @pytest.fixture
    def sample_entry(self):
        """创建测试用条目"""
        return Task(
            id="test-entry-1",
            title="测试任务",
            content="这是一个测试任务的内容 #测试标签",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/test-entry-1.md",
        )

    @pytest.fixture
    def mock_markdown_storage(self, temp_data_dir):
        """Mock Markdown 存储"""
        storage = MarkdownStorage(data_dir=temp_data_dir)
        return storage

    @pytest.fixture
    def mock_sqlite_storage(self):
        """Mock SQLite 存储"""
        storage = MagicMock()
        storage.upsert_entry = MagicMock(return_value=True)
        storage.delete_entry = MagicMock(return_value=True)
        return storage

    @pytest.fixture
    def mock_neo4j_available(self):
        """Mock Neo4j 可用"""
        client = AsyncMock()
        client.driver = AsyncMock()  # driver 存在表示已连接
        client.create_entry = AsyncMock(return_value=True)
        client.delete_entry = AsyncMock(return_value=True)
        client.create_concept = AsyncMock(return_value=True)
        client.create_entry_mentions = AsyncMock(return_value=True)
        client.create_concept_relation = AsyncMock(return_value=True)
        return client

    @pytest.fixture
    def mock_neo4j_unavailable(self):
        """Mock Neo4j 不可用"""
        client = MagicMock()
        client.driver = None  # driver 为 None 表示未连接
        return client

    @pytest.fixture
    def mock_qdrant_available(self):
        """Mock Qdrant 可用"""
        client = AsyncMock()
        client.upsert_entry = AsyncMock(return_value=True)
        client.delete_entry = AsyncMock(return_value=True)
        client.search = AsyncMock(return_value=[
            {"id": "entry-1", "score": 0.9, "payload": {"title": "测试"}}
        ])
        return client

    @pytest.fixture
    def mock_qdrant_unavailable(self):
        """Mock Qdrant 不可用"""
        client = MagicMock()
        client.upsert_entry = AsyncMock(side_effect=ConnectionError("Qdrant not available"))
        client.delete_entry = AsyncMock(side_effect=ConnectionError("Qdrant not available"))
        return client

    @pytest.fixture
    def mock_llm_caller(self):
        """Mock LLM Caller"""
        caller = AsyncMock()
        caller.call = AsyncMock(return_value='{"tags": ["测试"], "concepts": [], "relations": []}')
        return caller

    async def test_sync_to_qdrant_failure_graceful(
        self, mock_markdown_storage, mock_sqlite_storage, mock_neo4j_unavailable,
        mock_qdrant_unavailable, sample_entry
    ):
        """Qdrant 同步失败时优雅降级"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_unavailable,
            qdrant_client=mock_qdrant_unavailable,
            llm_caller=None,  # 不使用 LLM，使用规则提取
        )

        # 同步应该不会抛出异常
        result = await sync_service.sync_entry(sample_entry)

        # 因为 Qdrant 抛出异常，返回 False
        assert result is False

    async def test_sync_to_neo4j_failure_graceful(
        self, mock_markdown_storage, mock_sqlite_storage, sample_entry
    ):
        """Neo4j 同步失败时优雅降级"""
        # Neo4j 抛出异常
        mock_neo4j = AsyncMock()
        mock_neo4j.driver = AsyncMock()
        mock_neo4j.create_entry = AsyncMock(side_effect=Exception("Neo4j error"))

        mock_qdrant = AsyncMock()
        mock_qdrant.upsert_entry = AsyncMock(return_value=True)

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j,
            qdrant_client=mock_qdrant,
            llm_caller=None,
        )

        result = await sync_service.sync_entry(sample_entry)

        # 因为 Neo4j 抛出异常，返回 False
        assert result is False

    async def test_sync_with_both_services_available(
        self, mock_markdown_storage, mock_sqlite_storage,
        mock_neo4j_available, mock_qdrant_available, sample_entry
    ):
        """所有服务可用时同步成功"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant_available,
            llm_caller=None,
        )

        result = await sync_service.sync_entry(sample_entry)

        assert result is True
        mock_sqlite_storage.upsert_entry.assert_called_once_with(sample_entry, user_id="_default")
        mock_neo4j_available.create_entry.assert_called_once()
        mock_qdrant_available.upsert_entry.assert_called_once()

    async def test_sync_without_external_services(
        self, mock_markdown_storage, mock_sqlite_storage, sample_entry
    ):
        """没有外部服务时同步仍然成功（仅 SQLite）"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=None,
            qdrant_client=None,
            llm_caller=None,
        )

        result = await sync_service.sync_entry(sample_entry)

        assert result is True
        mock_sqlite_storage.upsert_entry.assert_called_once_with(sample_entry, user_id="_default")

    async def test_delete_entry_partial_failure(
        self, mock_markdown_storage, mock_sqlite_storage,
        mock_neo4j_available, mock_qdrant_unavailable, sample_entry
    ):
        """删除时部分失败不影响其他操作"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant_unavailable,
            llm_caller=None,
        )

        # 删除应该仍然成功（记录错误但不抛出异常）
        result = await sync_service.delete_entry("test-entry-1")

        # SQLite 和 Markdown 删除应该成功
        mock_sqlite_storage.delete_entry.assert_called_once_with("test-entry-1", user_id="_default")
        # 返回 True 因为主要操作完成了
        assert result is True

    async def test_sync_to_graph_and_vector_success(
        self, mock_markdown_storage, mock_sqlite_storage,
        mock_neo4j_available, mock_qdrant_available, sample_entry
    ):
        """后台同步到图谱和向量库成功"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant_available,
            llm_caller=None,
        )

        result = await sync_service.sync_to_graph_and_vector(sample_entry)

        assert result is True
        mock_neo4j_available.create_entry.assert_called_once()
        mock_qdrant_available.upsert_entry.assert_called_once()

    async def test_sync_to_graph_and_vector_qdrant_failure(
        self, mock_markdown_storage, mock_sqlite_storage,
        mock_neo4j_available, sample_entry
    ):
        """Qdrant 同步失败时后台同步仍然返回 True（记录错误）"""
        mock_qdrant = AsyncMock()
        mock_qdrant.upsert_entry = AsyncMock(side_effect=Exception("Qdrant error"))

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant,
            llm_caller=None,
        )

        # 不应该抛出异常
        result = await sync_service.sync_to_graph_and_vector(sample_entry)

        # 返回 True 因为 gather 使用 return_exceptions=True
        assert result is True

    async def test_sync_with_llm_extraction(
        self, mock_markdown_storage, mock_sqlite_storage,
        mock_neo4j_available, mock_qdrant_available, mock_llm_caller, sample_entry
    ):
        """使用 LLM 提取知识的同步"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant_available,
            llm_caller=mock_llm_caller,
        )

        result = await sync_service.sync_entry(sample_entry)

        assert result is True
        mock_llm_caller.call.assert_called_once()

    async def test_sync_llm_fallback_to_rules(
        self, mock_markdown_storage, mock_sqlite_storage,
        mock_neo4j_available, mock_qdrant_available, sample_entry
    ):
        """LLM 失败时回退到规则提取"""
        mock_llm = AsyncMock()
        mock_llm.call = AsyncMock(side_effect=Exception("LLM error"))

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant_available,
            llm_caller=mock_llm,
        )

        result = await sync_service.sync_entry(sample_entry)

        # 应该回退到规则提取并成功
        assert result is True

    async def test_extract_knowledge_with_rules(self, mock_markdown_storage, sample_entry):
        """使用规则提取知识"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=None,
            neo4j_client=None,
            qdrant_client=None,
            llm_caller=None,
        )

        knowledge = sync_service._knowledge_service._extract_with_rules(sample_entry)

        # 应该从内容中提取 #测试标签
        assert "测试标签" in knowledge.tags

    async def test_resync_entry_not_found(self, mock_markdown_storage):
        """重新同步不存在的条目"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=None,
            neo4j_client=None,
            qdrant_client=None,
            llm_caller=None,
        )

        # read_entry 返回 None
        with patch.object(mock_markdown_storage, 'read_entry', return_value=None):
            result = await sync_service.resync_entry("non-existent")

        assert result is False

    async def test_resync_entry_success(
        self, mock_markdown_storage, mock_sqlite_storage, sample_entry
    ):
        """重新同步存在的条目"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=None,
            qdrant_client=None,
            llm_caller=None,
        )

        with patch.object(mock_markdown_storage, 'read_entry', return_value=sample_entry):
            result = await sync_service.resync_entry("test-entry-1")

        assert result is True

    async def test_sync_all_mixed_results(
        self, mock_markdown_storage, mock_sqlite_storage,
        mock_neo4j_available, mock_qdrant_available
    ):
        """批量同步部分成功部分失败"""
        entry1 = Task(
            id="entry-1",
            title="成功条目",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/entry-1.md",
        )
        entry2 = Task(
            id="entry-2",
            title="失败条目",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/entry-2.md",
        )

        # Qdrant 第二次调用失败
        mock_qdrant_available.upsert_entry = AsyncMock(
            side_effect=[True, Exception("Qdrant error")]
        )

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant_available,
            llm_caller=None,
        )

        with patch.object(mock_markdown_storage, 'scan_all', return_value=[entry1, entry2]):
            result = await sync_service.sync_all()

        # 一个成功一个失败
        assert result["success"] == 1
        assert result["failed"] == 1
