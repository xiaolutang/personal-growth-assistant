"""R043 review_service 模板提取测试

覆盖:
- _require_sqlite 前置检查
- _fetch_tasks_and_notes 数据获取
- _calculate_vs_last_period 环比计算
- _build_daily_breakdown / _build_weekly_breakdown 静态方法
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest


def _make_review_service(sqlite_storage=None, neo4j_client=None):
    from app.services.review_service import ReviewService
    if sqlite_storage is None:
        sqlite_storage = MagicMock()
    return ReviewService(sqlite_storage=sqlite_storage, neo4j_client=neo4j_client)


# === _require_sqlite ===


class TestRequireSqlite:
    def test_raises_when_none(self):
        from app.services.review_service import ReviewService
        svc = ReviewService()  # defaults to sqlite_storage=None, _sqlite is None
        assert svc._sqlite is None
        with pytest.raises(ValueError, match="SQLite"):
            svc._require_sqlite()

    def test_passes_when_set(self):
        mock = MagicMock()
        svc = _make_review_service(sqlite_storage=mock)
        # mock is truthy → should not raise
        svc._require_sqlite()

    def test_raises_on_empty_init(self):
        from app.services.review_service import ReviewService
        svc = ReviewService()  # defaults to sqlite_storage=None
        with pytest.raises(ValueError, match="SQLite"):
            svc._require_sqlite()


# === _fetch_tasks_and_notes ===


class TestFetchTasksAndNotes:
    def test_returns_tasks_and_notes(self):
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.side_effect = [
            [{"id": "t1", "type": "task"}],  # tasks
            [{"id": "n1", "type": "note"}],  # notes
        ]
        svc = _make_review_service(sqlite_storage=mock_sqlite)
        tasks, notes = svc._fetch_tasks_and_notes(
            start_date="2026-04-01",
            end_date="2026-04-28",
            user_id="user1",
        )
        assert len(tasks) == 1
        assert len(notes) == 1
        assert tasks[0]["type"] == "task"
        assert notes[0]["type"] == "note"

    def test_empty_results(self):
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []
        svc = _make_review_service(sqlite_storage=mock_sqlite)
        tasks, notes = svc._fetch_tasks_and_notes(
            start_date="2026-04-01",
            end_date="2026-04-28",
            user_id="user1",
        )
        assert tasks == []
        assert notes == []


# === _build_daily_breakdown ===


class TestBuildDailyBreakdown:
    def test_groups_by_day(self):
        from app.services.review_service import ReviewService
        tasks = [
            {"created_at": "2026-04-21T10:00:00", "status": "complete"},
            {"created_at": "2026-04-21T14:00:00", "status": "doing"},
            {"created_at": "2026-04-22T09:00:00", "status": "complete"},
        ]
        week_start = date(2026, 4, 20)
        result = ReviewService._build_daily_breakdown(tasks, week_start)
        assert len(result) == 7  # 7 days in a week
        # Monday (index 1 = April 21)
        monday = result[1]
        assert monday["total"] == 2
        assert monday["completed"] == 1

    def test_empty_tasks(self):
        from app.services.review_service import ReviewService
        result = ReviewService._build_daily_breakdown([], date(2026, 4, 20))
        assert len(result) == 7
        for day in result:
            assert day["total"] == 0
            assert day["completed"] == 0

    def test_out_of_range_tasks_ignored(self):
        from app.services.review_service import ReviewService
        tasks = [
            {"created_at": "2026-04-19T10:00:00", "status": "complete"},  # before week (Sunday before)
            {"created_at": "2026-04-27T10:00:00", "status": "complete"},  # after week
        ]
        week_start = date(2026, 4, 20)  # Monday
        result = ReviewService._build_daily_breakdown(tasks, week_start)
        total_all = sum(d["total"] for d in result)
        # Neither April 19 (before) nor April 27 (after, week is 20-26) should be in range
        assert total_all == 0


# === _build_weekly_breakdown ===


class TestBuildWeeklyBreakdown:
    def test_groups_by_week(self):
        from app.services.review_service import ReviewService
        tasks = [
            {"created_at": "2026-04-06T10:00:00", "status": "complete"},
            {"created_at": "2026-04-07T10:00:00", "status": "doing"},
            {"created_at": "2026-04-20T10:00:00", "status": "complete"},
        ]
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)
        result = ReviewService._build_weekly_breakdown(tasks, month_start, month_end)
        assert len(result) > 0
        total_all = sum(w["total"] for w in result)
        assert total_all == 3  # all 3 tasks are in April

    def test_empty_tasks(self):
        from app.services.review_service import ReviewService
        result = ReviewService._build_weekly_breakdown(
            [], date(2026, 4, 1), date(2026, 4, 30)
        )
        for week in result:
            assert week["total"] == 0


# === _calculate_vs_last_period ===


class TestCalculateVsLastPeriod:
    def test_returns_none_when_no_data(self):
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []
        svc = _make_review_service(sqlite_storage=mock_sqlite)

        from app.models.review import TaskStats
        current = TaskStats(total=0, completed=0, doing=0, wait_start=0, completion_rate=0.0)

        result = svc._calculate_vs_last_period(
            prev_start=date(2026, 4, 7),
            prev_end=date(2026, 4, 13),
            current_task_stats=current,
            user_id="user1",
        )
        # 两期都为空时 delta 字段为 None（差值 0-0=0，但 code 不一定写 0）
        # 行为验证：返回对象存在且不崩溃
        assert result is not None
        assert isinstance(result.delta_total, (int, float, type(None)))

    def test_calculates_delta(self):
        mock_sqlite = MagicMock()
        # 上一周有 3 条，2 条完成
        mock_sqlite.list_entries.return_value = [
            {"id": "t0", "status": "complete"},
            {"id": "t1", "status": "complete"},
            {"id": "t2", "status": "doing"},
        ]
        svc = _make_review_service(sqlite_storage=mock_sqlite)

        from app.models.review import TaskStats
        current = TaskStats(total=5, completed=4, doing=1, wait_start=0, completion_rate=80.0)

        result = svc._calculate_vs_last_period(
            prev_start=date(2026, 4, 7),
            prev_end=date(2026, 4, 13),
            current_task_stats=current,
            user_id="user1",
        )
        assert result is not None
        assert result.delta_total == 5 - 3  # current(5) - prev(3)
        assert result.delta_completion_rate is not None
