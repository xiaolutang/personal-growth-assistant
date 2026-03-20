"""Qdrant 客户端单元测试 - Mock 模式"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority
from app.storage.qdrant_client import QdrantClient, str_to_uuid


class TestQdrantClient:
    """Qdrant 客户端测试 - Mock 模式"""

    @pytest.fixture
    def sample_entry(self):
        """创建测试用条目"""
        return Task(
            id="test-entry-1",
            title="测试任务",
            content="这是一个测试任务的内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["test", "qdrant"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/test-entry-1.md",
        )

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock Embedding 服务"""
        service = AsyncMock()
        service.get_embedding = AsyncMock(return_value=[0.1] * 1024)
        return service

    def test_str_to_uuid_deterministic(self):
        """测试 UUID 转换是确定性的"""
        uuid1 = str_to_uuid("test-id-1")
        uuid2 = str_to_uuid("test-id-1")
        assert uuid1 == uuid2

    def test_str_to_uuid_different_inputs(self):
        """测试不同输入产生不同 UUID"""
        uuid1 = str_to_uuid("test-id-1")
        uuid2 = str_to_uuid("test-id-2")
        assert uuid1 != uuid2

    async def test_init_with_default_url(self):
        """测试默认 URL 初始化"""
        client = QdrantClient()
        assert client.url == "http://localhost:6333"
        assert client._client is None

    async def test_init_with_custom_url(self):
        """测试自定义 URL 初始化"""
        client = QdrantClient(url="http://custom:6333")
        assert client.url == "http://custom:6333"

    async def test_connect_success(self, mock_qdrant_available):
        """测试连接成功"""
        client = QdrantClient(url="http://test:6333")
        await client.connect()

        # 验证 client 已初始化
        assert client._client is not None

    async def test_upsert_entry_success(self, mock_qdrant_available, sample_entry, mock_embedding_service):
        """测试正常插入向量"""
        client = QdrantClient(url="http://test:6333", embedding_service=mock_embedding_service)
        await client.connect()

        result = await client.upsert_entry(sample_entry)

        assert result is True
        mock_qdrant_available.upsert.assert_called_once()
        mock_embedding_service.get_embedding.assert_called_once()

    async def test_search_vectors_success(self, mock_qdrant_available, mock_embedding_service):
        """测试正常搜索向量"""
        client = QdrantClient(url="http://test:6333", embedding_service=mock_embedding_service)
        await client.connect()

        results = await client.search("测试查询", limit=5)

        assert len(results) == 1
        assert results[0]["id"] == "task-1"
        assert results[0]["score"] == 0.9

    async def test_search_with_filter(self, mock_qdrant_available, mock_embedding_service):
        """测试带过滤条件的搜索"""
        client = QdrantClient(url="http://test:6333", embedding_service=mock_embedding_service)
        await client.connect()

        await client.search("测试查询", filter_type="task", filter_status="doing")

        # 验证调用了 query_points
        mock_qdrant_available.query_points.assert_called_once()
        call_kwargs = mock_qdrant_available.query_points.call_args[1]
        assert call_kwargs["query_filter"] is not None

    async def test_delete_entry_success(self, mock_qdrant_available):
        """测试正常删除向量"""
        client = QdrantClient(url="http://test:6333")
        await client.connect()

        result = await client.delete_entry("test-entry-1")

        assert result is True
        mock_qdrant_available.delete.assert_called_once()

    async def test_get_entry_found(self, mock_qdrant_available):
        """测试获取存在的条目"""
        # Mock 返回数据
        mock_point = MagicMock()
        mock_point.id = "test-uuid"
        mock_point.vector = [0.1] * 1024
        mock_point.payload = {"original_id": "test-entry-1", "title": "测试"}
        mock_qdrant_available.retrieve = AsyncMock(return_value=[mock_point])

        client = QdrantClient(url="http://test:6333")
        await client.connect()

        result = await client.get_entry("test-entry-1")

        assert result is not None
        assert result["id"] == "test-entry-1"

    async def test_get_entry_not_found(self, mock_qdrant_available):
        """测试获取不存在的条目"""
        mock_qdrant_available.retrieve = AsyncMock(return_value=[])

        client = QdrantClient(url="http://test:6333")
        await client.connect()

        result = await client.get_entry("non-existent")

        assert result is None

    async def test_batch_upsert_success(self, mock_qdrant_available, sample_entry, mock_embedding_service):
        """测试批量插入向量"""
        entries = [sample_entry]
        client = QdrantClient(url="http://test:6333", embedding_service=mock_embedding_service)
        await client.connect()

        count = await client.batch_upsert(entries)

        assert count == 1
        mock_qdrant_available.upsert.assert_called_once()

    async def test_batch_delete_success(self, mock_qdrant_available):
        """测试批量删除向量"""
        client = QdrantClient(url="http://test:6333")
        await client.connect()

        count = await client.batch_delete(["entry-1", "entry-2"])

        assert count == 2
        mock_qdrant_available.delete.assert_called_once()

    async def test_get_stats(self, mock_qdrant_available):
        """测试获取统计信息"""
        mock_collection_info = MagicMock()
        mock_collection_info.points_count = 100
        mock_collection_info.vectors_count = 100
        mock_collection_info.status = MagicMock(value="green")
        mock_qdrant_available.get_collection = AsyncMock(return_value=mock_collection_info)

        client = QdrantClient(url="http://test:6333")
        await client.connect()

        stats = await client.get_stats()

        assert stats["points_count"] == 100
        assert stats["status"] == "green"

    async def test_close(self, mock_qdrant_available):
        """测试关闭连接"""
        client = QdrantClient(url="http://test:6333")
        await client.connect()
        await client.close()

        mock_qdrant_available.close.assert_called_once()
        assert client._client is None

    async def test_embedding_not_configured_error(self, mock_qdrant_available, sample_entry):
        """测试 Embedding 服务未配置时抛出异常"""
        client = QdrantClient(url="http://test:6333")  # 没有 embedding_service
        await client.connect()

        with pytest.raises(NotImplementedError, match="Embedding service not configured"):
            await client.upsert_entry(sample_entry)


class TestQdrantClientUnavailable:
    """Qdrant 不可用时的优雅降级测试"""

    async def test_init_connection_error_handled(self, mock_qdrant_unavailable):
        """测试连接错误被捕获（不抛出异常）"""
        # QdrantClient 的 __init__ 不应该抛出异常
        client = QdrantClient(url="http://invalid:6333")
        assert client is not None
        assert client._client is None


class TestQdrantDimensionMismatch:
    """Qdrant 维度不匹配处理测试"""

    async def test_dimension_mismatch_recreates_collection(self):
        """测试维度不匹配时自动重建 collection"""
        # Mock collection info with wrong dimension
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1536  # 旧维度

        # Mock client
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock(return_value=mock_collection_info)
        mock_client.delete_collection = AsyncMock()
        mock_client.create_collection = AsyncMock()

        with patch('app.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(url="http://test:6333", vector_size=1024)
            await client.connect()

            # 应该检测到维度不匹配并重建
            mock_client.get_collection.assert_called_once()
            mock_client.delete_collection.assert_called_once()
            mock_client.create_collection.assert_called_once()

    async def test_dimension_match_skips_recreate(self):
        """测试维度匹配时不重建 collection"""
        # Mock collection info with matching dimension
        mock_collection_info = MagicMock()
        mock_collection_info.config.params.vectors.size = 1024  # 匹配

        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock(return_value=mock_collection_info)
        mock_client.delete_collection = AsyncMock()
        mock_client.create_collection = AsyncMock()

        with patch('app.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(url="http://test:6333", vector_size=1024)
            await client.connect()

            # 不应该删除或创建
            mock_client.get_collection.assert_called_once()
            mock_client.delete_collection.assert_not_called()
            mock_client.create_collection.assert_not_called()
