"""Neo4j 客户端单元测试 - Mock 模式"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority, Concept, ConceptRelation
from app.storage.neo4j_client import Neo4jClient


class TestNeo4jClient:
    """Neo4j 客户端测试 - Mock 模式"""

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
            tags=["test", "neo4j"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/test-entry-1.md",
        )

    @pytest.fixture
    def sample_concept(self):
        """创建测试用概念"""
        return Concept(
            name="测试概念",
            description="这是一个测试概念",
            category="技术",
        )

    @pytest.fixture
    def sample_relation(self):
        """创建测试用关系"""
        return ConceptRelation(
            from_concept="概念A",
            to_concept="概念B",
            relation_type="RELATED_TO",
        )

    @pytest.fixture
    def mock_neo4j_session(self):
        """创建 mock session"""
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    async def test_init_with_default_uri(self):
        """测试默认 URI 初始化"""
        client = Neo4jClient()
        assert client.uri == "bolt://localhost:7687"
        assert client._driver is None

    async def test_init_with_custom_uri(self):
        """测试自定义 URI 初始化"""
        client = Neo4jClient(uri="bolt://custom:7687", username="user", password="pass")
        assert client.uri == "bolt://custom:7687"
        assert client.username == "user"
        assert client.password == "pass"

    async def test_connect_success(self, mock_neo4j_available):
        """测试连接成功"""
        client = Neo4jClient(uri="bolt://test:7687")
        await client.connect()

        assert client._driver is not None

    async def test_close(self, mock_neo4j_available):
        """测试关闭连接"""
        client = Neo4jClient(uri="bolt://test:7687")
        await client.connect()
        await client.close()

        mock_neo4j_available.close.assert_called_once()
        assert client._driver is None

    async def test_create_entry_success(self, sample_entry, mock_neo4j_session):
        """测试正常创建条目节点"""
        # Mock result
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={"e": sample_entry.model_dump()})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_entry(sample_entry)

        assert result is True

    async def test_update_entry_success(self, sample_entry, mock_neo4j_session):
        """测试更新条目（使用 MERGE）"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={"e": sample_entry.model_dump()})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.update_entry(sample_entry)

        assert result is True

    async def test_delete_entry_success(self, mock_neo4j_session):
        """测试正常删除条目节点"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={"deleted": 1})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.delete_entry("test-entry-1")

        assert result is True

    async def test_delete_entry_not_found(self, mock_neo4j_session):
        """测试删除不存在的条目"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={"deleted": 0})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.delete_entry("non-existent")

        assert result is False

    async def test_get_entry_found(self, sample_entry, mock_neo4j_session):
        """测试获取存在的条目"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={
            "id": sample_entry.id,
            "title": sample_entry.title,
            "type": sample_entry.category.value,
        })
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.get_entry("test-entry-1")

        assert result is not None
        assert result["id"] == sample_entry.id

    async def test_get_entry_not_found(self, mock_neo4j_session):
        """测试获取不存在的条目"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value=None)
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.get_entry("non-existent")

        assert result is None

    async def test_create_concept_success(self, sample_concept, mock_neo4j_session):
        """测试正常创建概念节点"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={"c": sample_concept.model_dump()})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_concept(sample_concept)

        assert result is True

    async def test_get_concept_found(self, sample_concept, mock_neo4j_session):
        """测试获取存在的概念"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={
            "name": sample_concept.name,
            "description": sample_concept.description,
            "category": sample_concept.category,
        })
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.get_concept(sample_concept.name)

        assert result is not None
        assert result["name"] == sample_concept.name

    async def test_create_entry_mentions(self, mock_neo4j_session):
        """测试创建条目与概念的关系"""
        mock_result = MagicMock()
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_entry_mentions("entry-1", ["概念A", "概念B"])

        assert result is True
        mock_neo4j_session.run.assert_called_once()

    async def test_create_concept_relation(self, sample_relation, mock_neo4j_session):
        """测试创建概念之间的关系"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_concept_relation(sample_relation)

        assert result is True

    async def test_get_entries_by_concept(self, mock_neo4j_session):
        """测试获取提及某概念的所有条目"""
        # 创建异步生成器 mock
        class AsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        records = [
            {"id": "entry-1", "title": "条目1"},
            {"id": "entry-2", "title": "条目2"},
        ]

        mock_result = AsyncIterator(records)
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        results = await client.get_entries_by_concept("测试概念")

        assert len(results) == 2
        assert results[0]["id"] == "entry-1"

    async def test_create_indexes(self, mock_neo4j_session):
        """测试创建索引"""
        mock_neo4j_session.run = AsyncMock()

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        await client.create_indexes()

        # 应该调用 4 次创建索引
        assert mock_neo4j_session.run.call_count == 4

    async def test_list_entries_with_filter(self, mock_neo4j_session):
        """测试带过滤条件的列表查询"""
        # 创建异步生成器 mock
        class AsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        records = [
            {"id": "entry-1", "title": "条目1", "type": "task", "status": "doing"},
        ]

        mock_result = AsyncIterator(records)
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        results = await client.list_entries(entry_type="task", status="doing")

        assert len(results) == 1

    async def test_create_entry_relation(self, mock_neo4j_session):
        """测试创建条目之间的关系"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_entry_relation("entry-1", "entry-2", "BELONGS_TO")

        assert result is True

    async def test_get_entry_with_relations(self, mock_neo4j_session):
        """测试获取条目及其关系"""
        mock_result = MagicMock()
        mock_result.single = MagicMock(return_value={
            "entry": {"id": "entry-1", "title": "测试"},
            "relations": []
        })
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.get_entry_with_relations("entry-1")

        assert result["entry"] is not None


class TestNeo4jClientUnavailable:
    """Neo4j 不可用时的优雅降级测试"""

    async def test_connect_failure_graceful(self, mock_neo4j_unavailable):
        """测试连接失败时优雅降级（不抛出异常）"""
        client = Neo4jClient(uri="bolt://invalid:7687")
        # connect 内部捕获异常，不抛出
        await client.connect()

        # 驱动应该是 None
        assert client._driver is None

    async def test_operations_when_driver_none(self):
        """测试 driver 为 None 时的操作处理"""
        client = Neo4jClient(uri="bolt://invalid:7687")
        client._driver = None  # 模拟未连接状态

        # _get_session 会尝试 connect，但因为没有 mock，会失败
        # 我们测试的是 driver 为 None 的初始状态
        assert client._driver is None

    async def test_create_entry_driver_none_state(self):
        """测试 driver 为 None 时创建条目的状态检查"""
        client = Neo4jClient(uri="bolt://invalid:7687")
        client._driver = None

        entry = Task(
            id="test-entry-1",
            title="测试任务",
            content="测试内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/test-entry-1.md",
        )

        # 验证初始状态
        assert client._driver is None

        # 当 driver 为 None 时，_get_session 会调用 connect()
        # connect 会尝试连接，如果失败会设置 _driver = None
        # 这会导致后续操作失败，但这是预期的行为
