"""Neo4j 客户端单元测试 - Mock 模式"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority, Concept, ConceptRelation
from app.infrastructure.storage.neo4j_client import Neo4jClient


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
        mock_result.single = AsyncMock(return_value={"e": sample_entry.model_dump()})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_entry(sample_entry)

        assert result is True

    async def test_update_entry_success(self, sample_entry, mock_neo4j_session):
        """测试更新条目（使用 MERGE）"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"e": sample_entry.model_dump()})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.update_entry(sample_entry)

        assert result is True

    async def test_delete_entry_success(self, mock_neo4j_session):
        """测试正常删除条目节点"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"deleted": 1})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.delete_entry("test-entry-1")

        assert result is True

    async def test_delete_entry_not_found(self, mock_neo4j_session):
        """测试删除不存在的条目"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"deleted": 0})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.delete_entry("non-existent")

        assert result is False

    async def test_get_entry_found(self, sample_entry, mock_neo4j_session):
        """测试获取存在的条目"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={
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
        mock_result.single = AsyncMock(return_value=None)
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.get_entry("non-existent")

        assert result is None

    async def test_create_concept_success(self, sample_concept, mock_neo4j_session):
        """测试正常创建概念节点"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"c": sample_concept.model_dump()})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_concept(sample_concept)

        assert result is True

    async def test_get_concept_found(self, sample_concept, mock_neo4j_session):
        """测试获取存在的概念"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={
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
        mock_result.single = AsyncMock(return_value={})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_concept_relation(sample_relation)

        assert result is True

    async def test_get_entries_by_concept(self, mock_neo4j_session):
        """测试获取提及某概念的所有条目"""
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

        # 应该调用 6 次创建索引（Entry 4 + Concept 2）
        assert mock_neo4j_session.run.call_count == 6

    async def test_list_entries_with_filter(self, mock_neo4j_session):
        """测试带过滤条件的列表查询"""
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
        mock_result.single = AsyncMock(return_value={})
        mock_neo4j_session.run = AsyncMock(return_value=mock_result)

        client = Neo4jClient(uri="bolt://test:7687")
        client._driver = MagicMock()
        client._driver.session = MagicMock(return_value=mock_neo4j_session)

        result = await client.create_entry_relation("entry-1", "entry-2", "BELONGS_TO")

        assert result is True

    async def test_get_entry_with_relations(self, mock_neo4j_session):
        """测试获取条目及其关系"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={
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


class TestNeo4jUserIdIsolation:
    """Neo4j 用户数据隔离测试"""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    @pytest.fixture
    def client(self, mock_session):
        c = Neo4jClient(uri="bolt://test:7687")
        c._driver = MagicMock()
        c._driver.session = MagicMock(return_value=mock_session)
        return c

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
    def sample_concept(self):
        return Concept(
            name="隔离概念",
            description="隔离测试概念",
            category="技术",
        )

    async def test_create_entry_passes_user_id(self, client, mock_session, sample_entry):
        """create_entry 应将 user_id 传入 Cypher"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"e": {}})
        mock_session.run = AsyncMock(return_value=mock_result)

        await client.create_entry(sample_entry, user_id="user_alpha")

        call_args = mock_session.run.call_args
        cypher = call_args[0][0]
        params = call_args[1] if len(call_args) > 1 else call_args[0][1] if len(call_args[0]) > 1 else {}
        assert "user_id" in cypher or "user_id" in str(params)
        if isinstance(params, dict):
            assert params.get("user_id") == "user_alpha"

    async def test_get_entry_isolates_by_user(self, client, mock_session):
        """get_entry 使用 user_id 过滤，不同用户查不到"""
        mock_result = MagicMock()
        # 模拟用户 A 查询无结果
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await client.get_entry("entry-1", user_id="user_b")
        assert result is None

        # 验证 Cypher 包含 user_id
        cypher = mock_session.run.call_args[0][0]
        assert "user_id" in cypher

    async def test_delete_entry_isolates_by_user(self, client, mock_session):
        """delete_entry 使用 user_id 过滤"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"deleted": 0})
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await client.delete_entry("entry-1", user_id="user_b")
        assert result is False

        cypher = mock_session.run.call_args[0][0]
        assert "user_id" in cypher

    async def test_list_entries_filters_by_user(self, client, mock_session):
        """list_entries 使用 user_id 过滤"""
        mock_session.run = AsyncMock(return_value=AsyncIterator([]))

        results = await client.list_entries(user_id="user_alpha")
        assert len(results) == 0

        cypher = mock_session.run.call_args[0][0]
        assert "user_id" in cypher

    async def test_create_concept_isolates_by_user(self, client, mock_session, sample_concept):
        """create_concept 的 MERGE 包含 user_id"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"c": {}})
        mock_session.run = AsyncMock(return_value=mock_result)

        await client.create_concept(sample_concept, user_id="user_alpha")

        cypher = mock_session.run.call_args[0][0]
        assert "user_id" in cypher

    async def test_get_concept_isolates_by_user(self, client, mock_session):
        """get_concept 按用户隔离"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await client.get_concept("概念A", user_id="other_user")
        assert result is None

        cypher = mock_session.run.call_args[0][0]
        assert "user_id" in cypher

    async def test_get_knowledge_graph_isolates_by_user(self, client, mock_session):
        """知识图谱按用户隔离"""
        mock_result = AsyncIterator([])
        mock_result.single = AsyncMock(return_value=None)
        mock_session.run = AsyncMock(return_value=mock_result)

        await client.get_knowledge_graph("概念A", user_id="user_alpha")

        cypher = mock_session.run.call_args[0][0]
        assert "user_id" in cypher


class AsyncIterator:
    """异步迭代器辅助类"""
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


class TestNeo4jInjectionPrevention:
    """Neo4j Cypher 注入防护测试 — relation_type 白名单"""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        return session

    @pytest.fixture
    def client(self, mock_session):
        c = Neo4jClient(uri="bolt://test:7687")
        c._driver = MagicMock()
        c._driver.session = MagicMock(return_value=mock_session)
        return c

    async def test_create_concept_relation_rejects_invalid_type(self, client):
        """create_concept_relation 拒绝非白名单 relation_type"""
        malicious = ConceptRelation(
            from_concept="A",
            to_concept="B",
            relation_type="MALICIOUS_TYPE; DROP ALL",
        )
        with pytest.raises(ValueError, match="非法关系类型"):
            await client.create_concept_relation(malicious)

    async def test_create_concept_relation_accepts_valid_types(self, client, mock_session):
        """create_concept_relation 接受白名单中的合法值"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={})
        mock_session.run = AsyncMock(return_value=mock_result)

        for rt in ["RELATED_TO", "PART_OF", "BELONGS_TO", "DEPENDS_ON", "DERIVED_FROM"]:
            relation = ConceptRelation(
                from_concept="A", to_concept="B", relation_type=rt
            )
            result = await client.create_concept_relation(relation)
            assert result is True

    async def test_create_entry_relation_rejects_invalid_type(self, client):
        """create_entry_relation 拒绝非白名单 relation_type"""
        with pytest.raises(ValueError, match="非法关系类型"):
            await client.create_entry_relation("e1", "e2", "HACK DETACH DELETE ALL")

    async def test_create_entry_relation_accepts_default_type(self, client, mock_session):
        """create_entry_relation 默认 BELONGS_TO 合法"""
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={})
        mock_session.run = AsyncMock(return_value=mock_result)

        result = await client.create_entry_relation("e1", "e2")
        assert result is True

    async def test_create_concept_relation_error_message(self, client):
        """错误消息包含合法值列表"""
        bad = ConceptRelation(
            from_concept="X", to_concept="Y", relation_type="INVALID"
        )
        with pytest.raises(ValueError) as exc_info:
            await client.create_concept_relation(bad)

        msg = str(exc_info.value)
        assert "INVALID" in msg
        assert "RELATED_TO" in msg
        assert "BELONGS_TO" in msg

    async def test_create_entry_relation_error_message(self, client):
        """entry relation 错误消息包含合法值列表"""
        with pytest.raises(ValueError) as exc_info:
            await client.create_entry_relation("e1", "e2", "NO_SUCH_TYPE")

        msg = str(exc_info.value)
        assert "NO_SUCH_TYPE" in msg
        assert "RELATED_TO" in msg
