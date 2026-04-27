"""R043 goal_service 批量查询 + JSON 解析测试

覆盖:
- _row_to_response_with_current 预计算 current_value
- _row_to_response auto_tags JSON 解析（字符串/list/null/double-encoded）
- list_goals 批量模式（3 种 metric_type）
- _get_prev_period_end 周期计算
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.services.goal_service import GoalService, _calculate_progress


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
    row = {
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
    return row


class TestCalculateProgress:
    def test_normal(self):
        assert _calculate_progress(5, 10) == 50.0

    def test_over_100_capped(self):
        assert _calculate_progress(15, 10) == 100.0

    def test_zero_target(self):
        assert _calculate_progress(5, 0) == 0.0

    def test_zero_current(self):
        assert _calculate_progress(0, 10) == 0.0


class TestRowToResponseWithCurrent:
    def test_uses_provided_current_value(self):
        svc = GoalService(sqlite_storage=MagicMock())
        row = _make_goal_row(auto_tags='["python"]')
        result = svc._row_to_response_with_current(row, current_value=7, linked_entries_count=3)
        assert result["current_value"] == 7
        assert result["progress_percentage"] == 70.0
        assert result["linked_entries_count"] == 3

    def test_parses_auto_tags_json_string(self):
        svc = GoalService(sqlite_storage=MagicMock())
        row = _make_goal_row(auto_tags='["python","fastapi"]')
        result = svc._row_to_response_with_current(row, current_value=0)
        assert result["auto_tags"] == ["python", "fastapi"]

    def test_auto_tags_none_stays_none(self):
        svc = GoalService(sqlite_storage=MagicMock())
        row = _make_goal_row(auto_tags=None)
        result = svc._row_to_response_with_current(row, current_value=0)
        assert result["auto_tags"] is None

    def test_checklist_items_parsed(self):
        svc = GoalService(sqlite_storage=MagicMock())
        items = json.dumps([{"id": "i1", "title": "Step 1", "checked": True}])
        row = _make_goal_row(metric_type="checklist", checklist_items=items)
        result = svc._row_to_response_with_current(row, current_value=1)
        assert len(result["checklist_items"]) == 1
        assert result["checklist_items"][0]["checked"] is True


class TestRowToResponseMetricTypes:
    def test_checklist_metric(self):
        mock_sqlite = MagicMock()
        items = json.dumps([
            {"id": "i1", "title": "A", "checked": True},
            {"id": "i2", "title": "B", "checked": False},
        ])
        mock_sqlite.count_goal_entries.return_value = 0
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="checklist", checklist_items=items, target_value=2)
        result = svc._row_to_response(row, linked_entries_count=0)
        assert result["current_value"] == 1  # only 1 checked
        assert result["progress_percentage"] == 50.0

    def test_milestone_metric(self):
        mock_sqlite = MagicMock()
        mock_sqlite.count_completed_milestones.return_value = 3
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="milestone", target_value=5)
        result = svc._row_to_response(row, linked_entries_count=0)
        assert result["current_value"] == 3
        mock_sqlite.count_completed_milestones.assert_called_once_with("g1", "user1")

    def test_tag_auto_metric_with_date_range(self):
        mock_sqlite = MagicMock()
        mock_sqlite.count_entries_by_tags_in_range.return_value = 4
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(
            metric_type="tag_auto",
            auto_tags='["python"]',
            start_date="2026-01-01",
            end_date="2026-06-01",
        )
        result = svc._row_to_response(row, linked_entries_count=0)
        assert result["current_value"] == 4
        mock_sqlite.count_entries_by_tags_in_range.assert_called_once_with(
            ["python"], "user1", "2026-01-01", "2026-06-01"
        )

    def test_tag_auto_metric_without_date_range(self):
        mock_sqlite = MagicMock()
        mock_sqlite.count_entries_by_tags.return_value = 2
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="tag_auto", auto_tags='["python"]')
        result = svc._row_to_response(row, linked_entries_count=0)
        assert result["current_value"] == 2
        mock_sqlite.count_entries_by_tags.assert_called_once_with(["python"], "user1")

    def test_count_metric_uses_linked_entries_count(self):
        mock_sqlite = MagicMock()
        svc = GoalService(sqlite_storage=mock_sqlite)
        row = _make_goal_row(metric_type="count", target_value=10)
        result = svc._row_to_response(row, linked_entries_count=7)
        assert result["current_value"] == 7
        assert result["progress_percentage"] == 70.0


class TestGetPrevPeriodEnd:
    def test_weekly_returns_monday(self):
        svc = GoalService(sqlite_storage=MagicMock())
        result = svc._get_prev_period_end("weekly")
        # 应该是 YYYY-MM-DDT00:00:00 格式
        assert result.endswith("T00:00:00")
        # 解析日期部分应该是周一（或今天就是周一）
        from datetime import datetime
        date_part = result.split("T")[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        assert dt.weekday() == 0  # Monday

    def test_monthly_returns_first_of_month(self):
        svc = GoalService(sqlite_storage=MagicMock())
        result = svc._get_prev_period_end("monthly")
        assert result.endswith("T00:00:00")
        date_part = result.split("T")[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        assert dt.day == 1


class TestListGoalsBatch:
    @pytest.mark.asyncio
    async def test_empty_returns_empty(self):
        mock_sqlite = MagicMock()
        mock_sqlite.list_goals.return_value = []
        svc = GoalService(sqlite_storage=mock_sqlite)
        result, code, _ = await svc.list_goals("user1")
        assert result == []
        assert code == 200

    @pytest.mark.asyncio
    async def test_count_type_uses_batch(self):
        """count 类型目标应该使用 batch_count_goal_entries 获取 linked_count"""
        mock_sqlite = MagicMock()
        row = _make_goal_row(goal_id="g1", metric_type="count", target_value=10)
        mock_sqlite.list_goals.return_value = [row]
        mock_sqlite.batch_count_goal_entries.return_value = {"g1": 5}
        mock_sqlite.batch_count_completed_milestones.return_value = {}
        svc = GoalService(sqlite_storage=mock_sqlite)
        result, _, _ = await svc.list_goals("user1")
        assert len(result) == 1
        assert result[0]["current_value"] == 5  # count uses linked_entries_count
        assert result[0]["progress_percentage"] == 50.0
        mock_sqlite.batch_count_goal_entries.assert_called_once_with(["g1"], "user1")

    @pytest.mark.asyncio
    async def test_milestone_type_uses_batch(self):
        mock_sqlite = MagicMock()
        row = _make_goal_row(goal_id="g1", metric_type="milestone", target_value=3)
        mock_sqlite.list_goals.return_value = [row]
        mock_sqlite.batch_count_goal_entries.return_value = {"g1": 0}
        mock_sqlite.batch_count_completed_milestones.return_value = {"g1": 2}
        svc = GoalService(sqlite_storage=mock_sqlite)
        result, _, _ = await svc.list_goals("user1")
        assert result[0]["current_value"] == 2
        assert result[0]["progress_percentage"] == 66.7

    @pytest.mark.asyncio
    async def test_tag_auto_uses_batch(self):
        mock_sqlite = MagicMock()
        row = _make_goal_row(
            goal_id="g1",
            metric_type="tag_auto",
            auto_tags='["python"]',
            target_value=10,
        )
        mock_sqlite.list_goals.return_value = [row]
        mock_sqlite.batch_count_goal_entries.return_value = {"g1": 0}
        mock_sqlite.batch_count_entries_by_tags.return_value = [3]
        svc = GoalService(sqlite_storage=mock_sqlite)
        result, _, _ = await svc.list_goals("user1")
        assert result[0]["current_value"] == 3
        mock_sqlite.batch_count_entries_by_tags.assert_called_once()
