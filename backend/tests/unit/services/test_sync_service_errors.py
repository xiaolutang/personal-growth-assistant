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
        """Qdrant 同步失败时优雅降级 — Markdown 和 SQLite 已成功，主流程返回 True"""
        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_unavailable,
            qdrant_client=mock_qdrant_unavailable,
            llm_caller=None,  # 不使用 LLM，使用规则提取
        )

        # 同步应该不会抛出异常
        result = await sync_service.sync_entry(sample_entry)

        # Markdown 已写入成功，索引层失败不影响主流程
        assert result is True

    async def test_sync_to_neo4j_failure_graceful(
        self, mock_markdown_storage, mock_sqlite_storage, sample_entry
    ):
        """Neo4j 同步失败时优雅降级 — Markdown 已写入，主流程返回 True"""
        # Neo4j 抛出异常
        mock_neo4j = AsyncMock()
        mock_neo4j._driver = AsyncMock()
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

        # Markdown 已写入成功，图谱/向量索引失败不影响主流程
        assert result is True

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
        # 先写入条目到 Markdown（使 delete_entry 返回 True）
        mock_markdown_storage.write_entry(sample_entry)

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j_available,
            qdrant_client=mock_qdrant_unavailable,
            llm_caller=None,
        )

        # 删除应该仍然成功（记录错误但不抛出异常）
        result = await sync_service.delete_entry("test-entry-1")

        # SQLite 和 Markdown 删除应该被调用
        mock_sqlite_storage.delete_entry.assert_called_once_with("test-entry-1", user_id="_default")
        # 返回 True 因为 Markdown 删除成功（索引层失败不阻塞）
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
        """批量同步 — 索引层失败不影响计数，sync_entry 始终返回 True"""
        entry1 = Task(
            id="entry-1",
            title="条目1",
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
            title="条目2",
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

        # Markdown 写入均成功，索引层失败不影响计数
        assert result["success"] == 2
        assert result["failed"] == 0


class TestSyncServiceWriteDeleteOrder:
    """B60: 写入/删除顺序与一致性测试"""

    @pytest.fixture
    def sample_entry(self):
        """创建测试用条目"""
        return Task(
            id="order-test-1",
            title="顺序测试",
            content="测试写入删除顺序",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/order-test-1.md",
        )

    @pytest.fixture
    def mock_markdown_storage(self, temp_data_dir):
        """真实 Markdown 存储（可验证文件存在）"""
        return MarkdownStorage(data_dir=temp_data_dir)

    @pytest.fixture
    def mock_sqlite_storage(self):
        """Mock SQLite 存储"""
        storage = MagicMock()
        storage.upsert_entry = MagicMock(return_value=True)
        storage.delete_entry = MagicMock(return_value=True)
        return storage

    async def test_sync_entry_sqlite_failure_markdown_preserved(
        self, mock_markdown_storage, sample_entry
    ):
        """sync_entry: SQLite 失败时 Markdown 数据保留"""
        # SQLite 模拟失败
        failing_sqlite = MagicMock()
        failing_sqlite.upsert_entry = MagicMock(side_effect=RuntimeError("SQLite disk error"))

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=failing_sqlite,
            neo4j_client=None,
            qdrant_client=None,
            llm_caller=None,
        )

        result = await sync_service.sync_entry(sample_entry)

        # 主流程应返回 True（Markdown 写入成功）
        assert result is True

        # 验证 Markdown 文件确实存在（数据未丢失）
        md_entry = mock_markdown_storage.read_entry("order-test-1")
        assert md_entry is not None
        assert md_entry.title == "顺序测试"

    async def test_sync_entry_markdown_failure_returns_false(
        self, mock_markdown_storage, mock_sqlite_storage, sample_entry
    ):
        """sync_entry: Markdown 写入失败时返回 False"""
        # 让 Markdown 写入抛异常
        mock_markdown_bad = MagicMock(spec=MarkdownStorage)
        mock_markdown_bad.write_entry = MagicMock(side_effect=OSError("disk full"))

        sync_service = SyncService(
            markdown_storage=mock_markdown_bad,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=None,
            qdrant_client=None,
            llm_caller=None,
        )

        result = await sync_service.sync_entry(sample_entry)

        # Markdown 失败应返回 False
        assert result is False
        # SQLite 不应被调用
        mock_sqlite_storage.upsert_entry.assert_not_called()

    async def test_delete_entry_markdown_first(
        self, mock_markdown_storage, mock_sqlite_storage, sample_entry
    ):
        """delete_entry: 先删 Markdown，索引删除失败不影响"""
        # 先写入一条数据
        mock_markdown_storage.write_entry(sample_entry)
        assert mock_markdown_storage.read_entry("order-test-1") is not None

        # 让 SQLite 删除失败
        failing_sqlite = MagicMock()
        failing_sqlite.delete_entry = MagicMock(side_effect=RuntimeError("SQLite busy"))

        # Neo4j 也模拟失败
        mock_neo4j = AsyncMock()
        mock_neo4j.delete_entry = AsyncMock(side_effect=Exception("Neo4j connection lost"))

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=failing_sqlite,
            neo4j_client=mock_neo4j,
            qdrant_client=None,
            llm_caller=None,
        )

        result = await sync_service.delete_entry("order-test-1")

        # Markdown 应已被删除
        assert mock_markdown_storage.read_entry("order-test-1") is None
        # 返回值反映 Markdown 删除成功
        assert result is True

    async def test_delete_entry_markdown_failure_returns_false(
        self, mock_sqlite_storage
    ):
        """delete_entry: Markdown 删除失败时返回 False"""
        mock_markdown_bad = MagicMock(spec=MarkdownStorage)
        mock_markdown_bad.delete_entry = MagicMock(side_effect=OSError("disk error"))

        sync_service = SyncService(
            markdown_storage=mock_markdown_bad,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=None,
            qdrant_client=None,
            llm_caller=None,
        )

        result = await sync_service.delete_entry("nonexistent")

        # Markdown 删除失败应返回 False
        assert result is False

    async def test_sync_entry_neo4j_qdrant_failure_not_blocking(
        self, mock_markdown_storage, mock_sqlite_storage, sample_entry
    ):
        """sync_entry: Neo4j 和 Qdrant 都失败时主流程仍返回 True"""
        mock_neo4j = AsyncMock()
        mock_neo4j._driver = AsyncMock()
        mock_neo4j.create_entry = AsyncMock(side_effect=Exception("Neo4j down"))

        mock_qdrant = AsyncMock()
        mock_qdrant.upsert_entry = AsyncMock(side_effect=Exception("Qdrant down"))

        sync_service = SyncService(
            markdown_storage=mock_markdown_storage,
            sqlite_storage=mock_sqlite_storage,
            neo4j_client=mock_neo4j,
            qdrant_client=mock_qdrant,
            llm_caller=None,
        )

        result = await sync_service.sync_entry(sample_entry)

        # Markdown 写入成功，索引层失败不阻塞
        assert result is True
        # 验证 Markdown 文件存在
        assert mock_markdown_storage.read_entry("order-test-1") is not None
        # SQLite 也应被成功调用
        mock_sqlite_storage.upsert_entry.assert_called_once()

    async def test_delete_entry_order_sqlite_after_markdown(
        self, mock_markdown_storage, sample_entry
    ):
        """delete_entry: 验证 SQLite 在 Markdown 之后被调用"""
        mock_markdown_storage.write_entry(sample_entry)

        call_order = []

        sqlite = MagicMock()
        original_sqlite_delete = sqlite.delete_entry

        def track_sqlite_delete(*args, **kwargs):
            call_order.append("sqlite")
            return True

        sqlite.delete_entry = MagicMock(side_effect=track_sqlite_delete)

        # 用 patch 追踪 Markdown 删除调用顺序
        original_md_delete = mock_markdown_storage.delete_entry

        def track_md_delete(*args, **kwargs):
            call_order.append("markdown")
            return original_md_delete(*args, **kwargs)

        with patch.object(type(mock_markdown_storage), 'delete_entry', track_md_delete):
            sync_service = SyncService(
                markdown_storage=mock_markdown_storage,
                sqlite_storage=sqlite,
                neo4j_client=None,
                qdrant_client=None,
                llm_caller=None,
            )

            await sync_service.delete_entry("order-test-1")

        # Markdown 应在 SQLite 之前被调用
        assert call_order[0] == "markdown"
        assert call_order[1] == "sqlite"
