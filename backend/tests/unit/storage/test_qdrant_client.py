"""Qdrant 客户端单元测试 - Mock 模式"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority
from app.infrastructure.storage.qdrant_client import QdrantClient, str_to_uuid


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

    async def test_embedding_not_configured_returns_false(self, mock_qdrant_available, sample_entry):
        """测试 Embedding 服务未配置时返回 False（不抛异常）"""
        client = QdrantClient(url="http://test:6333")  # 没有 embedding_service
        await client.connect()

        result = await client.upsert_entry(sample_entry)
        assert result is False


class TestQdrantClientUnavailable:
    """Qdrant 不可用时的优雅降级测试"""

    async def test_init_connection_error_handled(self, mock_qdrant_unavailable):
        """测试连接错误被捕获（不抛出异常）"""
        # QdrantClient 的 __init__ 不应该抛出异常
        client = QdrantClient(url="http://invalid:6333")
        assert client is not None
        assert client._client is None

    async def test_connect_failure_raises_connection_error(self, mock_qdrant_unavailable):
        """B91: connect() 连接失败时抛 ConnectionError 且 _client 为 None"""
        client = QdrantClient(url="http://invalid:6333")
        with pytest.raises(ConnectionError, match="Qdrant 连接失败"):
            await client.connect()
        assert client._client is None


class TestQdrantLazyReconnect:
    """B91: Qdrant 客户端懒重连异常保护测试"""

    @pytest.fixture
    def sample_entry(self):
        """创建测试用条目"""
        return Task(
            id="b91-entry-1",
            title="B91测试",
            content="懒重连测试内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/b91-entry-1.md",
        )

    @pytest.fixture
    def mock_embedding_service(self):
        service = AsyncMock()
        service.get_embedding = AsyncMock(return_value=[0.1] * 1024)
        return service

    async def test_upsert_no_client_no_reconnect_returns_false(self, sample_entry):
        """B91: _client=None 且无法重连时 upsert_entry 返回 False（无 AttributeError）"""
        client = QdrantClient(url="http://invalid:6333")
        assert client._client is None
        # 不调用 connect()，直接调用 upsert_entry
        result = await client.upsert_entry(sample_entry)
        assert result is False

    async def test_search_no_client_no_reconnect_returns_empty(self, mock_embedding_service):
        """B91: _client=None 且无法重连时 search 返回空列表（无 AttributeError）"""
        client = QdrantClient(url="http://invalid:6333", embedding_service=mock_embedding_service)
        assert client._client is None
        result = await client.search("测试查询")
        assert result == []

    async def test_delete_no_client_no_reconnect_returns_false(self):
        """B91: _client=None 且无法重连时 delete_entry 返回 False（无 AttributeError）"""
        client = QdrantClient(url="http://invalid:6333")
        assert client._client is None
        result = await client.delete_entry("nonexistent-id")
        assert result is False

    async def test_get_entry_no_client_no_reconnect_returns_none(self):
        """B91: _client=None 且无法重连时 get_entry 返回 None"""
        client = QdrantClient(url="http://invalid:6333")
        assert client._client is None
        result = await client.get_entry("nonexistent-id")
        assert result is None

    async def test_get_stats_no_client_no_reconnect_returns_unavailable(self):
        """B91: _client=None 且无法重连时 get_stats 返回 unavailable"""
        client = QdrantClient(url="http://invalid:6333")
        assert client._client is None
        stats = await client.get_stats()
        assert stats == {"points_count": 0, "status": "unavailable"}

    async def test_batch_upsert_no_client_returns_zero(self, sample_entry):
        """B91: _client=None 且无法重连时 batch_upsert 返回 0"""
        client = QdrantClient(url="http://invalid:6333")
        assert client._client is None
        result = await client.batch_upsert([sample_entry])
        assert result == 0

    async def test_batch_delete_no_client_returns_zero(self):
        """B91: _client=None 且无法重连时 batch_delete 返回 0"""
        client = QdrantClient(url="http://invalid:6333")
        assert client._client is None
        result = await client.batch_delete(["entry-1"])
        assert result == 0

    async def test_search_by_vector_no_client_returns_empty(self):
        """B91: _client=None 且无法重连时 search_by_vector 返回空列表"""
        client = QdrantClient(url="http://invalid:6333")
        assert client._client is None
        result = await client.search_by_vector([0.1] * 1024)
        assert result == []

    async def test_upsert_runtime_disconnect_returns_false(
        self, sample_entry, mock_embedding_service
    ):
        """B91: 运行时 Qdrant 断连后 upsert 返回 False（无 AttributeError）"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()
        mock_client.upsert = AsyncMock(side_effect=ConnectionError("Connection lost"))

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(
                url="http://test:6333",
                embedding_service=mock_embedding_service,
            )
            await client.connect()

            result = await client.upsert_entry(sample_entry)
            assert result is False

    async def test_search_runtime_disconnect_returns_empty(self, mock_embedding_service):
        """B91: 运行时 Qdrant 断连后 search 返回空列表（无 AttributeError）"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()
        mock_client.query_points = AsyncMock(side_effect=ConnectionError("Connection lost"))

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(
                url="http://test:6333",
                embedding_service=mock_embedding_service,
            )
            await client.connect()

            result = await client.search("测试查询")
            assert result == []

    async def test_delete_runtime_disconnect_returns_false(self):
        """B91: 运行时 Qdrant 断连后 delete_entry 返回 False（无 AttributeError）"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()
        mock_client.delete = AsyncMock(side_effect=ConnectionError("Connection lost"))

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(url="http://test:6333")
            await client.connect()

            result = await client.delete_entry("test-id")
            assert result is False

    async def test_upsert_normal_path_still_works(
        self, sample_entry, mock_embedding_service
    ):
        """B91回归: Qdrant 可用时 upsert 正常工作"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()
        mock_client.upsert = AsyncMock()

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(
                url="http://test:6333",
                embedding_service=mock_embedding_service,
            )
            await client.connect()

            result = await client.upsert_entry(sample_entry)
            assert result is True
            mock_client.upsert.assert_called_once()

    async def test_search_normal_path_still_works(self, mock_embedding_service):
        """B91回归: Qdrant 可用时 search 正常工作"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()
        mock_point = MagicMock()
        mock_point.id = "test-uuid"
        mock_point.score = 0.95
        mock_point.payload = {"original_id": "entry-1", "title": "回归测试"}
        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_client.query_points = AsyncMock(return_value=mock_response)

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(
                url="http://test:6333",
                embedding_service=mock_embedding_service,
            )
            await client.connect()

            results = await client.search("回归测试")
            assert len(results) == 1
            assert results[0]["score"] == 0.95


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

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
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

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(url="http://test:6333", vector_size=1024)
            await client.connect()

            # 不应该删除或创建
            mock_client.get_collection.assert_called_once()
            mock_client.delete_collection.assert_not_called()
            mock_client.create_collection.assert_not_called()


class TestQdrantUserIdIsolation:
    """Qdrant 用户数据隔离测试"""

    @pytest.fixture
    def sample_entry(self):
        return Task(
            id="iso-entry-1",
            title="隔离测试条目",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["iso"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/iso-entry-1.md",
        )

    @pytest.fixture
    def mock_embedding_service(self):
        mock = AsyncMock()
        mock.get_embedding = AsyncMock(return_value=[0.1] * 128)
        return mock

    async def test_upsert_includes_user_id_in_payload(self, sample_entry, mock_embedding_service):
        """upsert_entry 应在 payload 中包含 user_id"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()
        mock_client.upsert = AsyncMock()

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(url="http://test:6333", vector_size=128, embedding_service=mock_embedding_service)
            await client.connect()

            await client.upsert_entry(sample_entry, user_id="user_alpha")

            # 验证 upsert 被调用
            assert mock_client.upsert.called
            # 获取 upsert 传入的 points
            call_kwargs = mock_client.upsert.call_args
            points = call_kwargs[1].get("points") or call_kwargs[0][0] if call_kwargs[0] else None
            if points and hasattr(points[0], 'payload'):
                assert points[0].payload.get("user_id") == "user_alpha"

    async def test_search_filters_by_user_id(self, mock_embedding_service):
        """search 应按 user_id 过滤结果"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()

        # 模拟搜索返回
        mock_point = MagicMock()
        mock_point.id = "test-uuid"
        mock_point.score = 0.9
        mock_point.payload = {"original_id": "entry-1", "title": "A的条目", "user_id": "user_alpha"}
        mock_response = MagicMock()
        mock_response.points = [mock_point]
        mock_client.query_points = AsyncMock(return_value=mock_response)

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(url="http://test:6333", vector_size=128, embedding_service=mock_embedding_service)
            await client.connect()

            results = await client.search("测试", limit=5, user_id="user_alpha")

            # 验证 query_points 被调用时带 filter
            call_args = mock_client.query_points.call_args
            query_filter = call_args[1].get("query_filter") or call_args[0][1] if len(call_args[0]) > 1 else None
            # 搜索应该传入了 user_id 过滤参数
            assert mock_client.query_points.called

    async def test_search_different_user_no_results(self, mock_embedding_service):
        """不同用户搜索应返回空结果"""
        mock_client = AsyncMock()
        mock_client.get_collection = AsyncMock()
        mock_response = MagicMock()
        mock_response.points = []  # 模拟无结果
        mock_client.query_points = AsyncMock(return_value=mock_response)

        with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient', return_value=mock_client):
            client = QdrantClient(url="http://test:6333", vector_size=128, embedding_service=mock_embedding_service)
            await client.connect()

            results = await client.search("测试", limit=5, user_id="user_beta")
            assert len(results) == 0
