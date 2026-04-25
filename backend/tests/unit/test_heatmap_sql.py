"""B98: heatmap SQL 聚合测试 — _get_heatmap_from_sqlite 使用 get_tag_stats_for_knowledge_map"""
import pytest
from unittest.mock import MagicMock

from app.services.review_service import ReviewService
from app.models.review import HeatmapResponse


@pytest.fixture
def mock_sqlite():
    storage = MagicMock()
    return storage


@pytest.fixture
def service(mock_sqlite):
    return ReviewService(sqlite_storage=mock_sqlite)


class TestHeatmapSqlAggregation:

    def test_with_entries_correct_tag_stats(self, service, mock_sqlite):
        """有 entries 时 heatmap 使用 SQL 聚合返回正确的 tag 统计"""
        mock_sqlite.get_tag_stats_for_knowledge_map.return_value = {
            "tags": [
                {"name": "python", "entry_count": 10, "note_count": 5, "recent_count": 3},
                {"name": "rust", "entry_count": 2, "note_count": 0, "recent_count": 0},
            ],
            "co_occurrence_pairs": [],
        }

        result = service._get_heatmap_from_sqlite("user1")

        assert isinstance(result, HeatmapResponse)
        assert len(result.items) == 2
        # python: 10 entries + 5 notes → advanced
        python_item = next(i for i in result.items if i.concept == "python")
        assert python_item.mastery == "advanced"
        assert python_item.entry_count == 10
        # rust: 2 entries → beginner
        rust_item = next(i for i in result.items if i.concept == "rust")
        assert rust_item.mastery == "beginner"
        assert rust_item.entry_count == 2
        # 验证不再调用 list_entries
        mock_sqlite.list_entries.assert_not_called()

    def test_no_entries_empty_list(self, service, mock_sqlite):
        """无 entries 时 heatmap 返回空列表"""
        mock_sqlite.get_tag_stats_for_knowledge_map.return_value = {
            "tags": [],
            "co_occurrence_pairs": [],
        }

        result = service._get_heatmap_from_sqlite("user1")

        assert isinstance(result, HeatmapResponse)
        assert len(result.items) == 0

    def test_counts_match_sql_stats(self, service, mock_sqlite):
        """计数与 SQL 聚合结果一致"""
        mock_sqlite.get_tag_stats_for_knowledge_map.return_value = {
            "tags": [
                {"name": "ml", "entry_count": 4, "note_count": 2, "recent_count": 1},
            ],
            "co_occurrence_pairs": [],
        }

        result = service._get_heatmap_from_sqlite("user1")

        assert len(result.items) == 1
        item = result.items[0]
        assert item.entry_count == 4
        assert item.concept == "ml"

    def test_mastery_correct_from_sql_stats(self, service, mock_sqlite):
        """掌握度从 SQL 聚合统计正确计算"""
        mock_sqlite.get_tag_stats_for_knowledge_map.return_value = {
            "tags": [
                {"name": "a", "entry_count": 3, "note_count": 0, "recent_count": 1},
                {"name": "b", "entry_count": 0, "note_count": 0, "recent_count": 0},
            ],
            "co_occurrence_pairs": [],
        }

        result = service._get_heatmap_from_sqlite("user1")

        items_by_name = {i.concept: i for i in result.items}
        assert items_by_name["a"].mastery == "intermediate"
        assert items_by_name["b"].mastery == "new"

    def test_regression_sorted_by_mastery(self, service, mock_sqlite):
        """回归：items 按 mastery 排序"""
        mock_sqlite.get_tag_stats_for_knowledge_map.return_value = {
            "tags": [
                {"name": "beginner_tag", "entry_count": 1, "note_count": 0, "recent_count": 0},
                {"name": "advanced_tag", "entry_count": 10, "note_count": 5, "recent_count": 1},
            ],
            "co_occurrence_pairs": [],
        }

        result = service._get_heatmap_from_sqlite("user1")

        # 排序后 advanced 在前面（mastery_order: advanced=0, beginner=2）
        assert result.items[0].mastery == "advanced"
        assert result.items[1].mastery == "beginner"
