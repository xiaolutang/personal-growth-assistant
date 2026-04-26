"""知识推荐引擎测试 (B115)

测试覆盖:
- 知识缺口检测 (knowledge_gaps)
- 复习推荐 (review_suggestions)
- 共现推荐 (related_concepts)
- Neo4j 不可用时降级到 SQLite
- GET /knowledge/recommendations API 端点
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.models import Task, Category, TaskStatus, Priority
from app.services.recommendation_service import (
    RecommendationService,
    RecommendationResponse,
    KnowledgeGapItem,
    ReviewSuggestionItem,
    RelatedConceptItem,
)


def _make_entry(entry_id: str, tags: list, days_ago: int = 0, **kwargs):
    """快速创建测试条目"""
    now = datetime.now() - timedelta(days=days_ago)
    return Task(
        id=entry_id,
        title=kwargs.get("title", f"测试-{entry_id}"),
        content=kwargs.get("content", ""),
        category=kwargs.get("category", Category.TASK),
        status=kwargs.get("status", TaskStatus.DOING),
        priority=kwargs.get("priority", Priority.MEDIUM),
        tags=tags,
        created_at=now,
        updated_at=now,
        file_path=f"tasks/{entry_id}.md",
    )


class TestKnowledgeGaps:
    """知识缺口检测测试"""

    @pytest.mark.asyncio
    async def test_knowledge_gaps_with_neo4j(self):
        """Neo4j 可用时返回缺口数据"""
        neo4j_mock = MagicMock()
        neo4j_mock.is_connected = True
        neo4j_mock.find_prerequisite_gaps = AsyncMock(return_value=[
            {"concept": "React", "missing_prerequisites": ["JavaScript", "HTML"]},
            {"concept": "TypeScript", "missing_prerequisites": ["JavaScript"]},
        ])

        svc = RecommendationService(neo4j_client=neo4j_mock)
        gaps = await svc.knowledge_gaps(user_id="u1")

        assert len(gaps) == 2
        assert gaps[0].concept == "React"
        assert "JavaScript" in gaps[0].missing_prerequisites
        neo4j_mock.find_prerequisite_gaps.assert_awaited_once_with(user_id="u1")

    @pytest.mark.asyncio
    async def test_knowledge_gaps_neo4j_unavailable(self):
        """Neo4j 不可用时返回空列表"""
        svc = RecommendationService(neo4j_client=None)
        gaps = await svc.knowledge_gaps()
        assert gaps == []

    @pytest.mark.asyncio
    async def test_knowledge_gaps_neo4j_error(self):
        """Neo4j 查询异常时返回空列表"""
        neo4j_mock = MagicMock()
        neo4j_mock.is_connected = True
        neo4j_mock.find_prerequisite_gaps = AsyncMock(side_effect=Exception("连接超时"))

        svc = RecommendationService(neo4j_client=neo4j_mock)
        gaps = await svc.knowledge_gaps()
        assert gaps == []

    @pytest.mark.asyncio
    async def test_knowledge_gaps_empty_result(self):
        """Neo4j 返回空结果"""
        neo4j_mock = MagicMock()
        neo4j_mock.is_connected = True
        neo4j_mock.find_prerequisite_gaps = AsyncMock(return_value=[])

        svc = RecommendationService(neo4j_client=neo4j_mock)
        gaps = await svc.knowledge_gaps()
        assert gaps == []


class TestReviewSuggestions:
    """复习推荐测试"""

    @pytest.mark.asyncio
    async def test_review_suggestions_finds_stale_tags(self, sqlite_storage):
        """找出超过阈值未出现的标签"""
        user_id = "_default"
        # 创建近期条目 (Python)
        sqlite_storage.upsert_entry(
            _make_entry("recent-1", ["Python"], days_ago=1),
            user_id=user_id,
        )
        # 创建旧条目 (Rust)
        sqlite_storage.upsert_entry(
            _make_entry("old-1", ["Rust"], days_ago=30),
            user_id=user_id,
        )

        svc = RecommendationService(sqlite_storage=sqlite_storage)
        suggestions = await svc.review_suggestions(
            user_id=user_id, days_threshold=14, limit=10,
        )

        # Rust 应该在复习推荐中，Python 不应该
        concept_names = [s.concept for s in suggestions]
        assert "Rust" in concept_names
        assert "Python" not in concept_names

    @pytest.mark.asyncio
    async def test_review_suggestions_no_sqlite(self):
        """SQLite 不可用时返回空列表"""
        svc = RecommendationService(sqlite_storage=None)
        suggestions = await svc.review_suggestions()
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_review_suggestions_sorted_by_staleness(self, sqlite_storage):
        """结果按距离上次出现的天数降序排列"""
        user_id = "_default"
        # 更早出现的标签排前面
        sqlite_storage.upsert_entry(
            _make_entry("very-old", ["OldTech"], days_ago=60),
            user_id=user_id,
        )
        sqlite_storage.upsert_entry(
            _make_entry("somewhat-old", ["MidTech"], days_ago=20),
            user_id=user_id,
        )

        svc = RecommendationService(sqlite_storage=sqlite_storage)
        suggestions = await svc.review_suggestions(
            user_id=user_id, days_threshold=14, limit=10,
        )

        if len(suggestions) >= 2:
            # 最久未出现的应该排在前面
            assert suggestions[0].last_seen_days_ago >= suggestions[1].last_seen_days_ago

    @pytest.mark.asyncio
    async def test_review_suggestions_empty_db(self, sqlite_storage):
        """空数据库返回空列表"""
        svc = RecommendationService(sqlite_storage=sqlite_storage)
        suggestions = await svc.review_suggestions(user_id="empty-user")
        assert suggestions == []


class TestRelatedConcepts:
    """共现推荐测试"""

    @pytest.mark.asyncio
    async def test_related_concepts_with_neo4j(self):
        """Neo4j 可用时使用概念中心度"""
        neo4j_mock = MagicMock()
        neo4j_mock.is_connected = True
        neo4j_mock.get_concept_centrality = AsyncMock(return_value=[
            {"name": "Python", "centrality": 15, "category": "技术"},
            {"name": "FastAPI", "centrality": 8, "category": "技术"},
        ])

        svc = RecommendationService(neo4j_client=neo4j_mock)
        related = await svc.related_concepts(user_id="u1")

        assert len(related) == 2
        assert related[0].concept == "Python"
        assert related[0].score == 15.0
        assert related[0].source == "neo4j"

    @pytest.mark.asyncio
    async def test_related_concepts_neo4j_fallback_to_sqlite(self, sqlite_storage):
        """Neo4j 不可用时降级到 SQLite 标签频次"""
        user_id = "_default"
        sqlite_storage.upsert_entry(
            _make_entry("e1", ["Python", "编程"], days_ago=1),
            user_id=user_id,
        )
        sqlite_storage.upsert_entry(
            _make_entry("e2", ["Python"], days_ago=5),
            user_id=user_id,
        )

        svc = RecommendationService(
            neo4j_client=None,
            sqlite_storage=sqlite_storage,
        )
        related = await svc.related_concepts(user_id=user_id, limit=5)

        assert len(related) > 0
        assert all(r.source == "tag" for r in related)
        # Python 出现最多，score 应为 1.0
        python_items = [r for r in related if r.concept == "Python"]
        assert len(python_items) == 1
        assert python_items[0].score == 1.0

    @pytest.mark.asyncio
    async def test_related_concepts_neo4j_error_fallback(self, sqlite_storage):
        """Neo4j 查询出错时降级到 SQLite"""
        neo4j_mock = MagicMock()
        neo4j_mock.is_connected = True
        neo4j_mock.get_concept_centrality = AsyncMock(side_effect=Exception("查询超时"))

        user_id = "_default"
        sqlite_storage.upsert_entry(
            _make_entry("e1", ["Test"], days_ago=1),
            user_id=user_id,
        )

        svc = RecommendationService(
            neo4j_client=neo4j_mock,
            sqlite_storage=sqlite_storage,
        )
        related = await svc.related_concepts(user_id=user_id)

        assert len(related) > 0
        assert all(r.source == "tag" for r in related)

    @pytest.mark.asyncio
    async def test_related_concepts_no_data(self):
        """无数据时返回空列表"""
        svc = RecommendationService(
            neo4j_client=None,
            sqlite_storage=None,
        )
        related = await svc.related_concepts()
        assert related == []


class TestGetRecommendations:
    """聚合推荐测试"""

    @pytest.mark.asyncio
    async def test_get_recommendations_aggregates_all(self, sqlite_storage):
        """聚合三类推荐"""
        user_id = "_default"
        # 创建一些数据
        sqlite_storage.upsert_entry(
            _make_entry("e1", ["Python"], days_ago=20),
            user_id=user_id,
        )

        svc = RecommendationService(
            neo4j_client=None,
            sqlite_storage=sqlite_storage,
        )
        result = await svc.get_recommendations(user_id=user_id)

        assert isinstance(result, RecommendationResponse)
        assert result.source == "sqlite"
        assert isinstance(result.knowledge_gaps, list)
        assert isinstance(result.review_suggestions, list)
        assert isinstance(result.related_concepts, list)

    @pytest.mark.asyncio
    async def test_get_recommendations_with_neo4j(self):
        """Neo4j 可用时 source 为 neo4j"""
        neo4j_mock = MagicMock()
        neo4j_mock.is_connected = True
        neo4j_mock.find_prerequisite_gaps = AsyncMock(return_value=[
            {"concept": "React", "missing_prerequisites": ["JS"]},
        ])
        neo4j_mock.get_concept_centrality = AsyncMock(return_value=[
            {"name": "Python", "centrality": 5, "category": "技术"},
        ])

        svc = RecommendationService(neo4j_client=neo4j_mock)
        result = await svc.get_recommendations()

        assert result.source == "neo4j"
        assert len(result.knowledge_gaps) == 1
        assert len(result.related_concepts) == 1


class TestRecommendationAPI:
    """GET /knowledge/recommendations API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """准备测试数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = "_default"
        from app.routers import deps
        user = deps._user_storage.get_by_username("testuser")
        if user:
            user_id = user.id

        now = datetime.now()

        # 创建近期的带标签条目
        storage.sqlite.upsert_entry(
            _make_entry("rec-1", ["Python", "编程"], days_ago=1),
            user_id=user_id,
        )
        storage.sqlite.upsert_entry(
            _make_entry("rec-2", ["Rust"], days_ago=30),
            user_id=user_id,
        )
        storage.sqlite.upsert_entry(
            _make_entry("rec-3", ["Python"], days_ago=5),
            user_id=user_id,
        )

    @pytest.mark.asyncio
    async def test_recommendations_api_returns_200(self, client):
        """API 返回 200 + 推荐数据"""
        resp = await client.get("/knowledge/recommendations")
        assert resp.status_code == 200

        data = resp.json()
        assert "knowledge_gaps" in data
        assert "review_suggestions" in data
        assert "related_concepts" in data
        assert "source" in data
        assert data["source"] == "sqlite"  # 测试环境无 Neo4j

    @pytest.mark.asyncio
    async def test_recommendations_api_structure(self, client):
        """API 返回数据结构正确"""
        resp = await client.get("/knowledge/recommendations")
        data = resp.json()

        # knowledge_gaps 应为空列表（无 Neo4j）
        assert isinstance(data["knowledge_gaps"], list)

        # review_suggestions 应有数据
        assert isinstance(data["review_suggestions"], list)
        for item in data["review_suggestions"]:
            assert "concept" in item
            assert "last_seen_days_ago" in item
            assert "entry_count" in item

        # related_concepts 应有数据
        assert isinstance(data["related_concepts"], list)
        for item in data["related_concepts"]:
            assert "concept" in item
            assert "score" in item
            assert "source" in item
