"""B99: tag_stats SQL 聚合测试 — _compute_30d_tag_stats 使用 get_tag_stats_in_range"""
import pytest
from unittest.mock import MagicMock

from app.services.review_service import ReviewService


@pytest.fixture
def mock_sqlite():
    return MagicMock()


@pytest.fixture
def service(mock_sqlite):
    return ReviewService(sqlite_storage=mock_sqlite)


class TestTagStatsSqlAggregation:

    def test_with_entries_freq_sorted(self, service, mock_sqlite):
        """有 entries 时 tag 频次按降序排列"""
        mock_sqlite.get_tag_stats_in_range.return_value = [
            ("python", 15),
            ("rust", 8),
            ("ml", 3),
        ]

        result = service._compute_30d_tag_stats("user1")

        assert len(result) == 3
        assert result[0] == ("python", 15)
        assert result[1] == ("rust", 8)
        assert result[2] == ("ml", 3)
        mock_sqlite.list_entries.assert_not_called()

    def test_no_entries_empty_list(self, service, mock_sqlite):
        """无 entries 时返回空列表"""
        mock_sqlite.get_tag_stats_in_range.return_value = []

        result = service._compute_30d_tag_stats("user1")

        assert result == []

    def test_top_n_limit(self, service, mock_sqlite):
        """top_n 参数限制返回数量"""
        mock_sqlite.get_tag_stats_in_range.return_value = [
            ("a", 5), ("b", 3),
        ]

        result = service._compute_30d_tag_stats("user1", top_n=2)

        assert len(result) == 2
        mock_sqlite.get_tag_stats_in_range.assert_called_once_with(
            user_id="user1",
            start_date=mock_sqlite.get_tag_stats_in_range.call_args[1]["start_date"],
            end_date=mock_sqlite.get_tag_stats_in_range.call_args[1]["end_date"],
            top_n=2,
        )

    def test_freq_consistent(self, service, mock_sqlite):
        """频次与 SQL 聚合一致"""
        mock_sqlite.get_tag_stats_in_range.return_value = [("test", 42)]

        result = service._compute_30d_tag_stats("user1")

        assert result[0][1] == 42

    def test_user_id_isolation(self, service, mock_sqlite):
        """user_id 正确传递到 SQL 查询"""
        mock_sqlite.get_tag_stats_in_range.return_value = []

        service._compute_30d_tag_stats("special-user")

        call_args = mock_sqlite.get_tag_stats_in_range.call_args
        assert call_args[1]["user_id"] == "special-user"

    def test_regression_no_list_entries(self, service, mock_sqlite):
        """回归：不再调用 list_entries"""
        mock_sqlite.get_tag_stats_in_range.return_value = [("t", 1)]

        service._compute_30d_tag_stats("user1")

        mock_sqlite.list_entries.assert_not_called()
