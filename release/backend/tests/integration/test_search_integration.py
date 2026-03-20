"""Search API 集成测试 - 真实 Qdrant"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock
import httpx

from app.models import Task, Category, TaskStatus, Priority


@pytest.mark.integration
class TestSearchIntegration:
    """Search API 集成测试 - 真实 Qdrant"""

    @pytest.fixture
    def sample_entry(self):
        """创建测试用条目"""
        return Task(
            id="search-test-1",
            title="搜索测试任务",
            content="这是一个用于搜索测试的任务内容，包含关键词 Python 和 FastAPI",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["search", "test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/search-test-1.md",
        )

    async def test_upsert_and_search(self, qdrant_client_with_container, sample_entry):
        """测试插入和搜索"""
        client = qdrant_client_with_container

        # 插入
        result = await client.upsert_entry(sample_entry)
        assert result is True

        # 搜索（使用相同的向量，因为我们的 mock 返回固定向量）
        results = await client.search("搜索测试", limit=5)
        assert len(results) >= 1

        # 找到我们刚插入的条目
        found = any(r["id"] == sample_entry.id for r in results)
        assert found

    async def test_delete_entry(self, qdrant_client_with_container, sample_entry):
        """测试删除条目"""
        client = qdrant_client_with_container

        # 先插入
        await client.upsert_entry(sample_entry)

        # 删除
        result = await client.delete_entry(sample_entry.id)
        assert result is True

        # 搜索应该找不到
        results = await client.search("搜索测试", limit=10)
        found = any(r["id"] == sample_entry.id for r in results)
        assert not found

    async def test_get_entry(self, qdrant_client_with_container, sample_entry):
        """测试获取单个条目"""
        client = qdrant_client_with_container

        # 插入
        await client.upsert_entry(sample_entry)

        # 获取
        result = await client.get_entry(sample_entry.id)
        assert result is not None
        assert result["id"] == sample_entry.id

    async def test_batch_operations(self, qdrant_client_with_container):
        """测试批量操作"""
        client = qdrant_client_with_container

        # 创建多个条目
        entries = [
            Task(
                id=f"batch-test-{i}",
                title=f"批量测试任务 {i}",
                content=f"批量测试内容 {i}",
                category=Category.TASK,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["batch"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                file_path=f"tasks/batch-test-{i}.md",
            )
            for i in range(3)
        ]

        # 批量插入
        count = await client.batch_upsert(entries)
        assert count == 3

        # 搜索应该能找到
        results = await client.search("批量测试", limit=10)
        assert len(results) >= 3

        # 批量删除
        ids = [e.id for e in entries]
        deleted = await client.batch_delete(ids)
        assert deleted == 3

    async def test_search_with_filter(self, qdrant_client_with_container):
        """测试带过滤条件的搜索"""
        client = qdrant_client_with_container

        # 插入不同类型的条目
        task_entry = Task(
            id="filter-task",
            title="过滤测试任务",
            content="任务内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/filter-task.md",
        )

        project_entry = Task(
            id="filter-project",
            title="过滤测试项目",
            content="项目内容",
            category=Category.PROJECT,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="projects/filter-project.md",
        )

        await client.batch_upsert([task_entry, project_entry])

        # 搜索并过滤
        results = await client.search("过滤测试", filter_type="task", limit=10)

        # 只应该返回任务类型
        for r in results:
            if r.get("payload"):
                assert r["payload"].get("type") == "task"

        # 清理
        await client.batch_delete(["filter-task", "filter-project"])

    async def test_get_stats(self, qdrant_client_with_container, sample_entry):
        """测试获取统计信息"""
        client = qdrant_client_with_container

        # 插入
        await client.upsert_entry(sample_entry)

        # 获取统计
        stats = await client.get_stats()
        assert "points_count" in stats
        assert stats["points_count"] >= 1

        # 清理
        await client.delete_entry(sample_entry.id)


@pytest.mark.integration
class TestSearchByVector:
    """按向量搜索测试"""

    async def test_search_by_vector(self, qdrant_client_with_container):
        """测试按向量搜索"""
        client = qdrant_client_with_container

        # 使用固定向量搜索
        vector = [0.1] * 1024
        results = await client.search_by_vector(vector, limit=5)

        # 应该返回结果（可能为空，取决于是否有数据）
        assert isinstance(results, list)


@pytest.mark.integration
class TestDimensionMismatch:
    """维度不匹配时的处理测试"""

    async def test_dimension_mismatch_auto_recreate(self, qdrant_url):
        """测试维度不匹配时自动重建 collection"""
        from app.infrastructure.storage.qdrant_client import QdrantClient

        # 1. 先创建一个 512 维度的 collection
        class MockEmbedding512:
            async def get_embedding(self, text: str):
                return [0.1] * 512

        client_512 = QdrantClient(
            url=qdrant_url,
            embedding_service=MockEmbedding512(),
            vector_size=512,
        )
        await client_512.connect()
        await client_512.close()

        # 2. 现在用 1024 维度连接，应该自动重建
        class MockEmbedding1024:
            async def get_embedding(self, text: str):
                return [0.1] * 1024

        client_1024 = QdrantClient(
            url=qdrant_url,
            embedding_service=MockEmbedding1024(),
            vector_size=1024,
        )
        await client_1024.connect()

        # 3. 验证可以正常插入和搜索（1024 维度）
        entry = Task(
            id="dim-test-1",
            title="维度测试",
            content="测试维度不匹配重建",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/dim-test-1.md",
        )
        result = await client_1024.upsert_entry(entry)
        assert result is True

        # 清理
        await client_1024.delete_entry(entry.id)
        await client_1024.close()


@pytest.mark.integration
class TestSearchAPIE2E:
    """搜索 API 端到端测试"""

    @pytest.fixture
    def api_base_url(self):
        """API 基础 URL"""
        import os
        return os.getenv("API_BASE_URL", "http://localhost:8080/growth/api")

    async def test_search_api_returns_200(self, api_base_url):
        """测试搜索 API 返回 200"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_base_url}/search",
                json={"query": "测试查询", "limit": 5},
            )

            # 应该返回 200 或 503（如果 Qdrant 未配置）
            assert response.status_code in [200, 503]

            if response.status_code == 200:
                data = response.json()
                assert "results" in data
                assert isinstance(data["results"], list)

    async def test_search_api_empty_query_validation(self, api_base_url):
        """测试搜索 API 空查询验证"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_base_url}/search",
                json={"query": "", "limit": 5},
            )

            # 空查询应该返回 422 (Validation Error)
            assert response.status_code == 422

    async def test_search_api_limit_validation(self, api_base_url):
        """测试搜索 API limit 参数验证"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # limit 超过最大值
            response = await client.post(
                f"{api_base_url}/search",
                json={"query": "测试", "limit": 100},
            )

            # 应该返回 422 (Validation Error)
            assert response.status_code == 422
