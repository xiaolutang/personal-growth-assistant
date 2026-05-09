"""B10: Neo4j 降级模式统一 + goal_service JSON 去重

测试场景:
1. KnowledgeService — get_learning_path 使用 _with_neo4j_fallback 统一降级
   - Neo4j 可用时返回图谱数据
   - Neo4j 不可用时降级到 SQLite 数据
   - Neo4j 运行时异常时降级
2. KnowledgeService — get_entry_knowledge_context / get_knowledge_map 降级回归
3. goal_service — _parse_json_fields 提取后响应解析回归
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

import pytest

from app.services.knowledge_service import KnowledgeService
from app.services.goal_service import GoalService, _calculate_progress
from app.models.knowledge import (
    LearningPathResponse,
    KnowledgeMapResponse,
    ConceptNode,
)


# ==================== Helper ====================


def _make_goal_row(
    goal_id="g1",
    user_id="user1",
    metric_type="count",
    target_value=10,
    auto_tags=None,
    checklist_items=None,
    start_date=None,
    end_date=None,
    status="active",
):
    return {
        "id": goal_id,
        "user_id": user_id,
        "title": f"Goal {goal_id}",
        "description": None,
        "metric_type": metric_type,
        "target_value": target_value,
        "current_value": 0,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "auto_tags": auto_tags,
        "checklist_items": checklist_items,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== get_learning_path Neo4j fallback ====================


class TestLearningPathNeo4jFallback:
    """get_learning_path 使用 _with_neo4j_fallback 统一降级"""

    async def test_neo4j_available_returns_prerequisites(self):
        """Neo4j 可用时 get_learning_path 返回前置知识"""
        neo4j_client = MagicMock()
        neo4j_client.is_connected = True
        neo4j_client.get_knowledge_graph = AsyncMock(return_value={
            "center": {"name": "Python", "category": "技术"},
            "connections": [
                {"node": {"name": "Programming", "category": "技术"}, "relationship": "PREREQUISITE_OF"},
            ],
        })

        mock_sqlite = MagicMock()
        mock_sqlite.search = MagicMock(return_value=[])
        mock_sqlite.search_tags_by_keyword = MagicMock(return_value=[])

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=mock_sqlite)

        result = await service.get_learning_path("Python", user_id="test")

        assert isinstance(result, LearningPathResponse)
        assert result.concept == "Python"
        assert len(result.prerequisites) == 1
        assert result.prerequisites[0].name == "Programming"

    async def test_neo4j_unavailable_degrades_to_sqlite(self):
        """Neo4j 不可用时 get_learning_path 降级到 SQLite 数据"""
        mock_sqlite = MagicMock()
        mock_sqlite.search = MagicMock(return_value=[
            {"type": "note", "status": "", "title": "Python笔记1"},
        ])
        mock_sqlite.search_tags_by_keyword = MagicMock(return_value=[
            {"name": "FastAPI", "entry_count": 3},
        ])

        service = KnowledgeService(neo4j_client=None, sqlite_storage=mock_sqlite)

        result = await service.get_learning_path("Python", user_id="test")

        assert isinstance(result, LearningPathResponse)
        assert result.concept == "Python"
        assert result.current_level == "beginner"

    async def test_neo4j_connection_error_degrades(self):
        """Neo4j 抛 ConnectionError 时 get_learning_path 降级"""
        neo4j_client = MagicMock()
        neo4j_client.is_connected = True
        neo4j_client.get_knowledge_graph = AsyncMock(
            side_effect=ConnectionError("Neo4j 连接断开")
        )

        mock_sqlite = MagicMock()
        mock_sqlite.search = MagicMock(return_value=[])
        mock_sqlite.search_tags_by_keyword = MagicMock(return_value=[])

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=mock_sqlite)

        result = await service.get_learning_path("Python", user_id="test")

        assert isinstance(result, LearningPathResponse)
        # 降级成功，无前置知识（因为 Neo4j 失败）
        assert result.prerequisites == []

    async def test_neo4j_runtime_error_degrades(self):
        """Neo4j 抛 RuntimeError 时 get_learning_path 降级"""
        neo4j_client = MagicMock()
        neo4j_client.is_connected = True
        neo4j_client.get_knowledge_graph = AsyncMock(
            side_effect=RuntimeError("查询超时")
        )

        mock_sqlite = MagicMock()
        mock_sqlite.search = MagicMock(return_value=[])
        mock_sqlite.search_tags_by_keyword = MagicMock(return_value=[])

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=mock_sqlite)

        result = await service.get_learning_path("Python", user_id="test")

        assert isinstance(result, LearningPathResponse)
        assert result.prerequisites == []


# ==================== get_entry_knowledge_context Neo4j fallback ====================


class TestEntryKnowledgeContextFallback:
    """get_entry_knowledge_context 使用 _with_neo4j_fallback 统一降级"""

    async def test_no_tags_returns_empty_subgraph(self):
        """条目无 tags 时返回空子图"""
        mock_sqlite = MagicMock()
        mock_sqlite.get_entry = MagicMock(return_value={"tags": []})

        service = KnowledgeService(neo4j_client=None, sqlite_storage=mock_sqlite)

        result = await service.get_entry_knowledge_context("entry1", user_id="test")

        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["center_concepts"] == []

    async def test_neo4j_unavailable_sqlite_fallback(self):
        """Neo4j 不可用但有 SQLite 时使用 SQLite 降级"""
        mock_sqlite = MagicMock()
        mock_sqlite.get_entry = MagicMock(return_value={"tags": ["python"]})
        mock_sqlite.get_tag_stats_for_subgraph = MagicMock(return_value={
            "tags": [
                {"name": "python", "entry_count": 5, "recent_count": 2, "note_count": 3},
            ],
            "co_occurrence_pairs": [],
        })

        service = KnowledgeService(neo4j_client=None, sqlite_storage=mock_sqlite)

        result = await service.get_entry_knowledge_context("entry1", user_id="test")

        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == "python"
        assert result["center_concepts"] == ["python"]

    async def test_both_unavailable_returns_empty(self):
        """Neo4j 和 SQLite 都不可用时返回空"""
        service = KnowledgeService(neo4j_client=None, sqlite_storage=None)

        result = await service.get_entry_knowledge_context("entry1", user_id="test")

        assert result["nodes"] == []
        assert result["edges"] == []


# ==================== get_knowledge_map Neo4j fallback ====================


class TestKnowledgeMapFallback:
    """get_knowledge_map 使用 _with_neo4j_fallback 统一降级"""

    async def test_neo4j_unavailable_returns_empty_map(self):
        """Neo4j 不可用时 get_knowledge_map 返回空地图"""
        service = KnowledgeService(neo4j_client=None, sqlite_storage=None)

        result = await service.get_knowledge_map(depth=2, view="domain", user_id="test")

        assert isinstance(result, KnowledgeMapResponse)
        assert result.nodes == []
        assert result.edges == []

    async def test_neo4j_available_returns_map(self):
        """Neo4j 可用时 get_knowledge_map 正常返回"""
        neo4j_client = MagicMock()
        neo4j_client.is_connected = True
        neo4j_client.get_all_concepts_with_stats = AsyncMock(return_value=[
            {"name": "Python", "category": "技术", "entry_count": 5},
        ])
        neo4j_client.get_all_relationships = AsyncMock(return_value=[])

        service = KnowledgeService(neo4j_client=neo4j_client, sqlite_storage=None)

        result = await service.get_knowledge_map(depth=2, view="domain", user_id="test")

        assert isinstance(result, KnowledgeMapResponse)
        assert len(result.nodes) == 1
        assert result.nodes[0].name == "Python"


# ==================== goal_service _parse_json_fields ====================


class TestParseJsonFields:
    """_parse_json_fields 共享方法测试"""

    def test_parses_auto_tags_json_string(self):
        svc = GoalService(sqlite_storage=MagicMock())
        row = {"auto_tags": '["python","fastapi"]', "checklist_items": None}
        svc._parse_json_fields(row)
        assert row["auto_tags"] == ["python", "fastapi"]
        assert row["checklist_items"] is None

    def test_parses_checklist_items_json_string(self):
        svc = GoalService(sqlite_storage=MagicMock())
        items = [{"id": "i1", "title": "Step 1", "checked": True}]
        row = {"auto_tags": None, "checklist_items": json.dumps(items)}
        svc._parse_json_fields(row)
        assert row["checklist_items"][0]["checked"] is True
        assert row["auto_tags"] is None

    def test_auto_tags_already_list(self):
        """auto_tags 已经是 list 时不变"""
        svc = GoalService(sqlite_storage=MagicMock())
        row = {"auto_tags": ["python"], "checklist_items": None}
        svc._parse_json_fields(row)
        assert row["auto_tags"] == ["python"]

    def test_auto_tags_null_becomes_none(self):
        """auto_tags 为 None 或空时设为 None"""
        svc = GoalService(sqlite_storage=MagicMock())
        row = {"auto_tags": None, "checklist_items": None}
        svc._parse_json_fields(row)
        assert row["auto_tags"] is None

    def test_auto_tags_empty_string_becomes_none(self):
        """auto_tags 为空字符串时设为 None"""
        svc = GoalService(sqlite_storage=MagicMock())
        row = {"auto_tags": "", "checklist_items": None}
        svc._parse_json_fields(row)
        assert row["auto_tags"] is None

    def test_both_fields_parsed(self):
        """两个字段同时解析"""
        svc = GoalService(sqlite_storage=MagicMock())
        row = {
            "auto_tags": '["tag1"]',
            "checklist_items": json.dumps([{"id": "i1", "title": "A", "checked": False}]),
        }
        svc._parse_json_fields(row)
        assert row["auto_tags"] == ["tag1"]
        assert len(row["checklist_items"]) == 1


class TestRowToResponseRegression:
    """_row_to_response 回归测试（确保 _parse_json_fields 提取后行为不变）"""

    def test_count_metric(self):
        mock_sqlite = MagicMock()
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="count", target_value=10)
        result = svc._row_to_response(row, linked_entries_count=7)
        assert result["current_value"] == 7
        assert result["progress_percentage"] == 70.0
        assert result["linked_entries_count"] == 7

    def test_checklist_metric(self):
        mock_sqlite = MagicMock()
        items = json.dumps([
            {"id": "i1", "title": "A", "checked": True},
            {"id": "i2", "title": "B", "checked": False},
        ])
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="checklist", checklist_items=items, target_value=2)
        result = svc._row_to_response(row, linked_entries_count=0)
        assert result["current_value"] == 1
        assert result["progress_percentage"] == 50.0
        assert isinstance(result["checklist_items"], list)

    def test_tag_auto_metric(self):
        mock_sqlite = MagicMock()
        mock_sqlite.count_entries_by_tags.return_value = 2
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="tag_auto", auto_tags='["python"]')
        result = svc._row_to_response(row, linked_entries_count=0)
        assert result["current_value"] == 2
        assert result["auto_tags"] == ["python"]

    def test_milestone_metric(self):
        mock_sqlite = MagicMock()
        mock_sqlite.count_completed_milestones.return_value = 3
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="milestone", target_value=5)
        result = svc._row_to_response(row, linked_entries_count=0)
        assert result["current_value"] == 3


class TestRowToResponseWithCurrentRegression:
    """_row_to_response_with_current 回归测试"""

    def test_uses_provided_current_value(self):
        svc = GoalService(sqlite_storage=MagicMock())
        row = _make_goal_row(auto_tags='["python"]')
        result = svc._row_to_response_with_current(row, current_value=7, linked_entries_count=3)
        assert result["current_value"] == 7
        assert result["progress_percentage"] == 70.0
        assert result["linked_entries_count"] == 3
        assert result["auto_tags"] == ["python"]

    def test_auto_tags_null(self):
        svc = GoalService(sqlite_storage=MagicMock())
        row = _make_goal_row(auto_tags=None)
        result = svc._row_to_response_with_current(row, current_value=0)
        assert result["auto_tags"] is None

    def test_checklist_items_parsed(self):
        svc = GoalService(sqlite_storage=MagicMock())
        items = json.dumps([{"id": "i1", "title": "Step 1", "checked": True}])
        row = _make_goal_row(metric_type="checklist", checklist_items=items)
        result = svc._row_to_response_with_current(row, current_value=1)
        assert isinstance(result["checklist_items"], list)
        assert result["checklist_items"][0]["checked"] is True
