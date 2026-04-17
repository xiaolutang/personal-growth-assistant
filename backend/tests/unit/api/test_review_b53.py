"""B53 知识热力图 Neo4j 数据源升级 测试

测试覆盖:
- ReviewService 构造函数接受 neo4j_client 参数
- get_knowledge_heatmap 优先使用 Neo4j 数据
- Neo4j 不可用时降级到 SQLite
- 掌握度算法增强：relationship_count 参与计算
- HeatmapItem 包含 category 和 mention_count 字段
- 返回数据按 mastery 分组排序
- 用户隔离验证
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models import Task, Category, TaskStatus, Priority
from app.services.review_service import ReviewService, HeatmapItem, HeatmapResponse


def _make_test_user_id(client) -> str:
    """从 client 认证头中提取测试用户 ID"""
    from app.routers import deps
    user_storage = deps._user_storage
    user = user_storage.get_by_username("testuser")
    return user.id if user else "test-user"


# ==================== ReviewService 构造函数测试 ====================


class TestReviewServiceInit:
    """ReviewService 初始化测试"""

    def test_init_without_neo4j(self):
        """不带 neo4j_client 初始化"""
        svc = ReviewService(sqlite_storage=MagicMock())
        assert svc._neo4j_client is None

    def test_init_with_neo4j(self):
        """带 neo4j_client 初始化"""
        mock_neo4j = MagicMock()
        svc = ReviewService(sqlite_storage=MagicMock(), neo4j_client=mock_neo4j)
        assert svc._neo4j_client is mock_neo4j


# ==================== 掌握度算法增强测试 ====================


class TestCalculateMasteryEnhanced:
    """_calculate_mastery_from_stats 增强算法测试"""

    def test_new_zero_everything(self):
        """entry_count=0, relationship_count=0 → new"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=0, relationship_count=0
        ) == "new"

    def test_beginner_entry_count_1(self):
        """entry_count=1 → score=2 → beginner"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=1, recent_count=0, note_count=0, relationship_count=0
        ) == "beginner"

    def test_beginner_only_relationship(self):
        """entry_count=0 但 relationship_count=1 → score=1 → new (不够 beginner)"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=0, recent_count=0, note_count=0, relationship_count=1
        ) == "new"

    def test_beginner_relationship_boost(self):
        """entry_count=0, relationship_count=2 → score=2 → beginner"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=0, recent_count=0, note_count=0, relationship_count=2
        ) == "beginner"

    def test_intermediate_entry_count_2_recent_1(self):
        """entry_count=2, recent_count=1 → score=7 → intermediate"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=2, recent_count=1, note_count=0, relationship_count=0
        ) == "intermediate"

    def test_intermediate_with_relationship(self):
        """entry_count=1, relationship_count=3 → score=5 → intermediate"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=1, recent_count=0, note_count=0, relationship_count=3
        ) == "intermediate"

    def test_advanced_entry_count_5_recent_1(self):
        """entry_count=5, recent_count=1 → score=13 → advanced"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=5, recent_count=1, note_count=0, relationship_count=0
        ) == "advanced"

    def test_advanced_with_notes_and_relationships(self):
        """entry_count=3, note_count=2, relationship_count=2 → score=12 → advanced"""
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=3, recent_count=0, note_count=2, relationship_count=2
        ) == "advanced"

    def test_score_formula(self):
        """验证公式: entry_count*2 + recent_count*3 + note_count*2 + relationship_count*1"""
        # entry=2, recent=1, note=1, rel=1 → 4+3+2+1 = 10 → advanced
        assert ReviewService._calculate_mastery_from_stats(
            entry_count=2, recent_count=1, note_count=1, relationship_count=1
        ) == "advanced"


# ==================== HeatmapItem 模型测试 ====================


class TestHeatmapItemModel:
    """HeatmapItem 模型字段测试"""

    def test_heatmap_item_has_category(self):
        """HeatmapItem 包含 category 字段"""
        item = HeatmapItem(concept="Python", mastery="intermediate", entry_count=5, category="技术")
        assert item.category == "技术"

    def test_heatmap_item_category_default_none(self):
        """category 默认为 None"""
        item = HeatmapItem(concept="Python", mastery="intermediate", entry_count=5)
        assert item.category is None

    def test_heatmap_item_has_mention_count(self):
        """HeatmapItem 包含 mention_count 字段"""
        item = HeatmapItem(
            concept="Python", mastery="intermediate",
            entry_count=5, mention_count=10
        )
        assert item.mention_count == 10

    def test_heatmap_item_mention_count_default_zero(self):
        """mention_count 默认为 0"""
        item = HeatmapItem(concept="Python", mastery="intermediate", entry_count=5)
        assert item.mention_count == 0


# ==================== Neo4j 路径测试 ====================


class TestNeo4jPath:
    """Neo4j 数据路径测试"""

    @pytest.fixture
    def mock_neo4j(self):
        """创建 mock Neo4j client"""
        neo4j = AsyncMock()
        neo4j.get_all_concepts_with_stats = AsyncMock(return_value=[
            {"name": "Python", "category": "技术", "entry_count": 5, "mention_count": 8},
            {"name": "FastAPI", "category": "技术", "entry_count": 3, "mention_count": 4},
            {"name": "React", "category": "前端", "entry_count": 1, "mention_count": 2},
        ])
        neo4j.get_all_relationships = AsyncMock(return_value=[
            {"source": "Python", "target": "FastAPI", "type": "RELATED_TO"},
        ])
        return neo4j

    def test_neo4j_path_returns_data(self, mock_neo4j):
        """Neo4j 路径返回正确的热力图数据"""
        svc = ReviewService(sqlite_storage=MagicMock(), neo4j_client=mock_neo4j)
        result = svc.get_knowledge_heatmap(user_id="user1")

        assert isinstance(result, HeatmapResponse)
        assert len(result.items) == 3

    def test_neo4j_concept_fields(self, mock_neo4j):
        """Neo4j 数据包含 category 和 mention_count"""
        svc = ReviewService(sqlite_storage=MagicMock(), neo4j_client=mock_neo4j)
        result = svc.get_knowledge_heatmap(user_id="user1")

        python_item = next(i for i in result.items if i.concept == "Python")
        assert python_item.category == "技术"
        assert python_item.mention_count == 8
        assert python_item.entry_count == 5

    def test_neo4j_relationship_contribution(self, mock_neo4j):
        """关系数量影响掌握度计算"""
        svc = ReviewService(sqlite_storage=MagicMock(), neo4j_client=mock_neo4j)
        result = svc.get_knowledge_heatmap(user_id="user1")

        # Python: entry=5, rel=1 → score=5*2+1=11 → advanced
        python_item = next(i for i in result.items if i.concept == "Python")
        assert python_item.mastery == "advanced"

        # FastAPI: entry=3, rel=1 → score=3*2+1=7 → intermediate
        fastapi_item = next(i for i in result.items if i.concept == "FastAPI")
        assert fastapi_item.mastery == "intermediate"

        # React: entry=1, rel=0 → score=1*2=2 → beginner
        react_item = next(i for i in result.items if i.concept == "React")
        assert react_item.mastery == "beginner"

    def test_neo4j_sorted_by_mastery(self, mock_neo4j):
        """结果按 mastery 排序（advanced 在前）"""
        svc = ReviewService(sqlite_storage=MagicMock(), neo4j_client=mock_neo4j)
        result = svc.get_knowledge_heatmap(user_id="user1")

        masteries = [item.mastery for item in result.items]
        # advanced < intermediate < beginner < new
        for i in range(len(masteries) - 1):
            assert ReviewService._mastery_order(masteries[i]) <= ReviewService._mastery_order(masteries[i + 1])

    def test_neo4j_empty_concepts_falls_back(self, mock_neo4j):
        """Neo4j 返回空列表时降级到 SQLite"""
        mock_neo4j.get_all_concepts_with_stats = AsyncMock(return_value=[])

        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []

        svc = ReviewService(sqlite_storage=mock_sqlite, neo4j_client=mock_neo4j)
        result = svc.get_knowledge_heatmap(user_id="user1")

        # 应该调用 SQLite 降级路径
        mock_sqlite.list_entries.assert_called_once()


# ==================== Neo4j 降级测试 ====================


class TestNeo4jDegradation:
    """Neo4j 降级测试"""

    def test_neo4j_exception_falls_back_to_sqlite(self):
        """Neo4j 抛出异常时降级到 SQLite"""
        mock_neo4j = AsyncMock()
        mock_neo4j.get_all_concepts_with_stats = AsyncMock(
            side_effect=Exception("Neo4j connection lost")
        )

        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []

        svc = ReviewService(sqlite_storage=mock_sqlite, neo4j_client=mock_neo4j)
        result = svc.get_knowledge_heatmap(user_id="user1")

        # 不抛异常，返回降级结果
        assert isinstance(result, HeatmapResponse)
        mock_sqlite.list_entries.assert_called_once()

    def test_no_neo4j_uses_sqlite(self):
        """没有 Neo4j client 时直接使用 SQLite"""
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []

        svc = ReviewService(sqlite_storage=mock_sqlite, neo4j_client=None)
        result = svc.get_knowledge_heatmap(user_id="user1")

        assert isinstance(result, HeatmapResponse)
        mock_sqlite.list_entries.assert_called_once()

    def test_sqlite_fallback_data_format(self):
        """SQLite 降级路径返回格式一致（包含 category 和 mention_count）"""
        mock_sqlite = MagicMock()
        now = datetime.now().isoformat()
        mock_sqlite.list_entries.return_value = [
            {
                "id": "e1", "title": "test", "type": "task",
                "tags": ["Python", "AI"],
                "status": "doing",
                "updated_at": now,
            },
            {
                "id": "e2", "title": "note", "type": "note",
                "tags": ["Python"],
                "status": "doing",
                "updated_at": now,
            },
        ]

        svc = ReviewService(sqlite_storage=mock_sqlite, neo4j_client=None)
        result = svc.get_knowledge_heatmap(user_id="user1")

        assert len(result.items) == 2
        python_item = next(i for i in result.items if i.concept == "Python")
        assert python_item.entry_count == 2
        assert python_item.category == "tag"
        assert python_item.mention_count == 0  # SQLite 路径不含 mention_count


# ==================== 关系计数测试 ====================


class TestCountRelationships:
    """_count_relationships_per_concept 测试"""

    def test_count_basic(self):
        """基础关系计数"""
        rels = [
            {"source": "A", "target": "B", "type": "RELATED_TO"},
            {"source": "B", "target": "C", "type": "PREREQUISITE"},
        ]
        result = ReviewService._count_relationships_per_concept(rels)
        assert result == {"A": 1, "B": 2, "C": 1}

    def test_count_empty(self):
        """空关系列表"""
        result = ReviewService._count_relationships_per_concept([])
        assert result == {}


# ==================== API 集成测试 ====================


class TestHeatmapAPI:
    """热力图 API 集成测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """准备测试数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        now = datetime.now()

        # 创建带 tags 的条目
        for i in range(3):
            entry = Task(
                id=f"b53-task-{i}",
                title=f"测试任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i < 2 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["Python", "AI"],
                created_at=now,
                updated_at=now,
                file_path=f"tasks/b53-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 创建笔记条目
        note = Task(
            id="b53-note-0",
            title="Python学习笔记",
            content="",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["Python"],
            created_at=now,
            updated_at=now,
            file_path="notes/b53-note-0.md",
        )
        storage.sqlite.upsert_entry(note, user_id=user_id)

    async def test_heatmap_api_returns_200(self, client: AsyncClient):
        """热力图 API 返回 200"""
        response = await client.get("/review/knowledge-heatmap")
        assert response.status_code == 200

    async def test_heatmap_api_has_items(self, client: AsyncClient):
        """热力图 API 返回 items"""
        response = await client.get("/review/knowledge-heatmap")
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

    async def test_heatmap_item_fields(self, client: AsyncClient):
        """热力图项包含新字段 category 和 mention_count"""
        response = await client.get("/review/knowledge-heatmap")
        data = response.json()

        for item in data["items"]:
            assert "concept" in item
            assert "mastery" in item
            assert "entry_count" in item
            assert "category" in item
            assert "mention_count" in item

    async def test_heatmap_sorted_by_mastery(self, client: AsyncClient):
        """热力图按 mastery 排序"""
        response = await client.get("/review/knowledge-heatmap")
        data = response.json()

        if len(data["items"]) > 1:
            masteries = [item["mastery"] for item in data["items"]]
            order = {"advanced": 0, "intermediate": 1, "beginner": 2, "new": 3}
            for i in range(len(masteries) - 1):
                assert order.get(masteries[i], 99) <= order.get(masteries[i + 1], 99)

    async def test_heatmap_sqlite_category_is_tag(self, client: AsyncClient):
        """SQLite 路径下 category 为 'tag'"""
        response = await client.get("/review/knowledge-heatmap")
        data = response.json()

        for item in data["items"]:
            assert item["category"] == "tag"

    async def test_heatmap_python_entry_count(self, client: AsyncClient):
        """验证 Python 概念的 entry_count"""
        response = await client.get("/review/knowledge-heatmap")
        data = response.json()

        python_items = [i for i in data["items"] if i["concept"] == "Python"]
        assert len(python_items) == 1
        # 3 task + 1 note = 4 entries
        assert python_items[0]["entry_count"] == 4


# ==================== 用户隔离测试 ====================


class TestHeatmapUserIsolation:
    """热力图用户隔离测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """创建当前用户和其他用户的数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        now = datetime.now()

        # 当前用户：带 Python tag
        entry = Task(
            id="b53-iso-task-0",
            title="当前用户任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["Python"],
            created_at=now,
            updated_at=now,
            file_path="tasks/b53-iso-task-0.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 其他用户：带 Java tag
        other_user_id = "b53-isolation-other"
        other_entry = Task(
            id="b53-iso-other-0",
            title="其他用户任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["Java"],
            created_at=now,
            updated_at=now,
            file_path="tasks/b53-iso-other-0.md",
        )
        storage.sqlite.upsert_entry(other_entry, user_id=other_user_id)

    async def test_heatmap_user_isolation(self, client: AsyncClient):
        """热力图不包含其他用户的数据"""
        response = await client.get("/review/knowledge-heatmap")
        assert response.status_code == 200

        data = response.json()
        concepts = [item["concept"] for item in data["items"]]

        # 当前用户只有 Python
        assert "Python" in concepts
        # 不应包含其他用户的 Java
        assert "Java" not in concepts
