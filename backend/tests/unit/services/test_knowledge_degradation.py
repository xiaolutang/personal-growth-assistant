"""B92: Neo4j 客户端降级 + 知识图谱路由层完善

测试场景:
- _get_session ConnectionError 时 _with_neo4j_fallback 返回空结构
- knowledge-map Neo4j 不可用时返回 200
- knowledge-stats Neo4j 不可用时返回 200
- knowledge-graph 503 保留
- 回归：正常路径不受影响
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.storage.neo4j_client import Neo4jClient
from app.services.knowledge_service import (
    KnowledgeService,
    KnowledgeMapResponse,
    ConceptStatsResponse,
    KnowledgeGraphResponse,
)


# ==================== Neo4j 客户端 _get_session 测试 ====================


class TestNeo4jGetSessionConnectionError:
    """_get_session 在 _driver=None 时应抛 ConnectionError"""

    async def test_get_session_raises_connection_error_when_driver_none(self):
        """_driver 为 None 且 connect() 无法建立连接时抛 ConnectionError"""
        client = Neo4jClient(uri="bolt://invalid:7687")
        # 不调用 connect()，_driver 为 None

        with pytest.raises(ConnectionError, match="Neo4j 驱动未初始化或连接失败"):
            await client._get_session()

    async def test_get_session_raises_connection_error_after_failed_connect(self):
        """connect() 失败后 _driver 仍为 None 时抛 ConnectionError"""
        client = Neo4jClient(uri="bolt://invalid:7687")

        with patch('app.infrastructure.storage.neo4j_client.AsyncGraphDatabase') as mock_db:
            mock_db.driver.side_effect = Exception("Connection refused")
            await client.connect()
            # connect 内部捕获异常，_driver 仍为 None
            assert client._driver is None

        with pytest.raises(ConnectionError, match="Neo4j 驱动未初始化或连接失败"):
            await client._get_session()

    async def test_get_session_returns_session_when_driver_available(self, mock_neo4j_available):
        """driver 可用时 _get_session 正常返回 session"""
        client = Neo4jClient(uri="bolt://test:7687")
        await client.connect()

        session = await client._get_session()
        assert session is not None


# ==================== _with_neo4j_fallback 降级测试 ====================


class TestNeo4jFallback:
    """_with_neo4j_fallback 降级模式测试"""

    def _make_service(self, neo4j_available=False, sqlite_available=False):
        """创建 KnowledgeService 实例"""
        neo4j_client = None
        if neo4j_available:
            neo4j_client = MagicMock()
            neo4j_client._driver = MagicMock()  # 模拟 driver 存在

        sqlite_storage = MagicMock() if sqlite_available else None

        return KnowledgeService(
            neo4j_client=neo4j_client,
            sqlite_storage=sqlite_storage,
        )

    async def test_neo4j_connection_error_falls_back_to_sqlite(self):
        """Neo4j 抛 ConnectionError 时降级到 SQLite"""
        service = self._make_service(neo4j_available=True, sqlite_available=True)

        # Neo4j 操作抛 ConnectionError
        async def neo4j_fn():
            raise ConnectionError("Neo4j 驱动未初始化或连接失败")

        # SQLite 降级返回数据
        sqlite_result = {"data": "from_sqlite"}
        service._sqlite = MagicMock()
        service._sqlite.get_data = MagicMock(return_value=sqlite_result)

        result = await service._with_neo4j_fallback(
            neo4j_fn,
            lambda: service._sqlite.get_data(),
        )

        assert result == sqlite_result

    async def test_neo4j_other_error_falls_back_to_sqlite(self):
        """Neo4j 抛其他异常时也降级到 SQLite"""
        service = self._make_service(neo4j_available=True, sqlite_available=True)

        async def neo4j_fn():
            raise RuntimeError("Query failed")

        sqlite_result = {"data": "from_sqlite"}
        service._sqlite = MagicMock()
        service._sqlite.get_data = MagicMock(return_value=sqlite_result)

        result = await service._with_neo4j_fallback(
            neo4j_fn,
            lambda: service._sqlite.get_data(),
        )

        assert result == sqlite_result

    async def test_both_unavailable_returns_none(self):
        """Neo4j 和 SQLite 都不可用时返回 None"""
        service = self._make_service(neo4j_available=False, sqlite_available=False)

        result = await service._with_neo4j_fallback(
            lambda: None,
            lambda: None,
        )

        assert result is None

    async def test_neo4j_available_success(self):
        """Neo4j 可用且成功时直接返回结果"""
        service = self._make_service(neo4j_available=True, sqlite_available=True)

        async def neo4j_fn():
            return {"data": "from_neo4j"}

        result = await service._with_neo4j_fallback(
            neo4j_fn,
            lambda: {"data": "from_sqlite"},
        )

        assert result == {"data": "from_neo4j"}

    async def test_sqlite_only_returns_sqlite_result(self):
        """Neo4j 不可用、SQLite 可用时返回 SQLite 结果"""
        service = self._make_service(neo4j_available=False, sqlite_available=True)

        sqlite_result = {"data": "from_sqlite"}
        service._sqlite = MagicMock()
        service._sqlite.get_data = MagicMock(return_value=sqlite_result)

        result = await service._with_neo4j_fallback(
            lambda: None,
            lambda: service._sqlite.get_data(),
        )

        assert result == sqlite_result


# ==================== get_knowledge_map 降级测试 ====================


class TestKnowledgeMapDegradation:
    """get_knowledge_map 降级测试"""

    async def test_neo4j_unavailable_returns_empty_map(self):
        """Neo4j 不可用时 get_knowledge_map 返回空 KnowledgeMapResponse"""
        service = KnowledgeService(neo4j_client=None, sqlite_storage=None)

        result = await service.get_knowledge_map(depth=2, view="domain", user_id="test")

        assert isinstance(result, KnowledgeMapResponse)
        assert result.nodes == []
        assert result.edges == []

    async def test_neo4j_connection_error_returns_empty_map(self):
        """Neo4j 抛 ConnectionError 时返回空 KnowledgeMapResponse"""
        neo4j_client = MagicMock()
        neo4j_client._driver = MagicMock()  # is_neo4j_available 返回 True

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        # 让 Neo4j 操作抛 ConnectionError
        neo4j_client.get_all_concepts_with_stats = AsyncMock(
            side_effect=ConnectionError("Neo4j 驱动未初始化或连接失败")
        )

        result = await service.get_knowledge_map(depth=2, view="domain", user_id="test")

        assert isinstance(result, KnowledgeMapResponse)
        assert result.nodes == []
        assert result.edges == []

    async def test_neo4j_unavailable_sqlite_fallback(self):
        """Neo4j 不可用但有 SQLite 时，使用 SQLite 降级"""
        service = KnowledgeService(neo4j_client=None, sqlite_storage=None)

        mock_sqlite = MagicMock()
        mock_sqlite.get_tag_stats_for_knowledge_map = MagicMock(return_value={
            "tags": [
                {"name": "Python", "entry_count": 3, "recent_count": 1, "note_count": 2, "category": "tag"},
            ],
            "co_occurrence_pairs": [],
        })
        service._sqlite = mock_sqlite

        result = await service.get_knowledge_map(depth=2, view="domain", user_id="test")

        assert isinstance(result, KnowledgeMapResponse)
        assert len(result.nodes) == 1
        assert result.nodes[0].name == "Python"


# ==================== get_knowledge_stats 降级测试 ====================


class TestKnowledgeStatsDegradation:
    """get_knowledge_stats 降级测试"""

    async def test_neo4j_unavailable_returns_empty_stats(self):
        """Neo4j 不可用时 get_knowledge_stats 返回空 ConceptStatsResponse"""
        service = KnowledgeService(neo4j_client=None, sqlite_storage=None)

        result = await service.get_knowledge_stats(user_id="test")

        assert isinstance(result, ConceptStatsResponse)
        assert result.concept_count == 0
        assert result.relation_count == 0
        assert result.category_distribution == {}
        assert result.top_concepts == []

    async def test_neo4j_connection_error_returns_empty_stats(self):
        """Neo4j 抛 ConnectionError 时返回空 ConceptStatsResponse"""
        neo4j_client = MagicMock()
        neo4j_client._driver = MagicMock()

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        neo4j_client.get_all_concepts_with_stats = AsyncMock(
            side_effect=ConnectionError("Neo4j 驱动未初始化或连接失败")
        )

        result = await service.get_knowledge_stats(user_id="test")

        assert isinstance(result, ConceptStatsResponse)
        assert result.concept_count == 0
        assert result.relation_count == 0

    async def test_neo4j_unavailable_sqlite_fallback(self):
        """Neo4j 不可用但有 SQLite 时，使用 SQLite 降级"""
        service = KnowledgeService(neo4j_client=None, sqlite_storage=None)

        mock_sqlite = MagicMock()
        mock_sqlite.get_tag_stats_for_concept_stats = MagicMock(return_value={
            "tags": [
                {"name": "Python", "entry_count": 3, "category": "tag"},
            ],
            "concept_count": 1,
            "edge_count": 0,
        })
        service._sqlite = mock_sqlite

        result = await service.get_knowledge_stats(user_id="test")

        assert isinstance(result, ConceptStatsResponse)
        assert result.concept_count == 1
        assert result.relation_count == 0


# ==================== get_knowledge_graph 保留 503 行为 ====================


class TestKnowledgeGraphNoDegradation:
    """get_knowledge_graph 应保留 503 行为（不降级）"""

    async def test_neo4j_unavailable_raises_value_error(self):
        """Neo4j 不可用时 get_knowledge_graph 抛 ValueError"""
        service = KnowledgeService(neo4j_client=None, sqlite_storage=None)

        with pytest.raises(ValueError, match="知识图谱服务未配置"):
            await service.get_knowledge_graph("Python", depth=2, user_id="test")

    async def test_neo4j_driver_none_raises_value_error(self):
        """Neo4j driver 为 None 时 get_knowledge_graph 抛 ValueError"""
        neo4j_client = MagicMock()
        neo4j_client._driver = None

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        with pytest.raises(ValueError, match="知识图谱服务未配置"):
            await service.get_knowledge_graph("Python", depth=2, user_id="test")


# ==================== 正常路径回归测试 ====================


class TestNormalPathRegression:
    """正常路径不受降级改动影响"""

    async def test_get_knowledge_map_neo4j_success(self):
        """Neo4j 可用时 get_knowledge_map 正常返回"""
        neo4j_client = MagicMock()
        neo4j_client._driver = MagicMock()  # is_neo4j_available -> True
        neo4j_client.get_all_concepts_with_stats = AsyncMock(return_value=[
            {"name": "Python", "category": "技术", "entry_count": 5, "mention_count": 3},
        ])
        neo4j_client.get_all_relationships = AsyncMock(return_value=[
            {"source": "Python", "target": "AI", "type": "RELATED_TO"},
        ])

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        result = await service.get_knowledge_map(depth=2, view="domain", user_id="test")

        assert isinstance(result, KnowledgeMapResponse)
        assert len(result.nodes) == 1
        assert result.nodes[0].name == "Python"
        assert len(result.edges) == 1
        assert result.edges[0].source == "Python"
        assert result.edges[0].target == "AI"

    async def test_get_knowledge_stats_neo4j_success(self):
        """Neo4j 可用时 get_knowledge_stats 正常返回"""
        neo4j_client = MagicMock()
        neo4j_client._driver = MagicMock()
        neo4j_client.get_all_concepts_with_stats = AsyncMock(return_value=[
            {"name": "Python", "category": "技术", "entry_count": 5},
            {"name": "AI", "category": "技术", "entry_count": 3},
        ])
        neo4j_client.get_all_relationships = AsyncMock(return_value=[
            {"source": "Python", "target": "AI", "type": "RELATED_TO"},
        ])

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        result = await service.get_knowledge_stats(user_id="test")

        assert isinstance(result, ConceptStatsResponse)
        assert result.concept_count == 2
        assert result.relation_count == 1

    async def test_get_knowledge_graph_neo4j_success(self):
        """Neo4j 可用时 get_knowledge_graph 正常返回"""
        neo4j_client = MagicMock()
        neo4j_client._driver = MagicMock()
        neo4j_client.get_knowledge_graph = AsyncMock(return_value={
            "center": {"name": "Python", "category": "技术", "description": "编程语言"},
            "connections": [
                {"node": {"name": "AI", "category": "技术"}, "relationship": "RELATED_TO"},
            ],
        })

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        result = await service.get_knowledge_graph("Python", depth=2, user_id="test")

        assert isinstance(result, KnowledgeGraphResponse)
        assert result.center is not None
        assert result.center.name == "Python"
        assert len(result.connections) == 1


# ==================== ConnectionError → 503 路由层测试 ====================


class TestConnectionError503Mapping:
    """ConnectionError 在路由层映射为 503（运行时断连场景）"""

    async def test_knowledge_graph_connection_error_returns_503(self):
        """get_knowledge_graph 在 Neo4j 运行时断连时抛 ConnectionError"""
        neo4j_client = MagicMock()
        neo4j_client._driver = MagicMock()  # is_neo4j_available -> True
        neo4j_client.get_knowledge_graph = AsyncMock(side_effect=ConnectionError("连接断开"))

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        with pytest.raises(ConnectionError, match="连接断开"):
            await service.get_knowledge_graph("Python", depth=2, user_id="test")

    async def test_get_related_concepts_connection_error(self):
        """get_related_concepts 在 Neo4j 运行时断连时抛 ConnectionError"""
        neo4j_client = MagicMock()
        neo4j_client._driver = MagicMock()
        neo4j_client.get_related_concepts = AsyncMock(side_effect=ConnectionError("连接断开"))

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        with pytest.raises(ConnectionError, match="连接断开"):
            await service.get_related_concepts("Python", user_id="test")
