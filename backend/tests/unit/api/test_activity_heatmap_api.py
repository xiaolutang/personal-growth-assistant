"""活动热力图 API 单元测试"""
import pytest
from datetime import datetime, timedelta

from app.infrastructure.storage.sqlite import SQLiteStorage
from app.services.review_service import ReviewService
from app.models.task import Task
from app.models.enums import Category, TaskStatus, Priority


def _make_task(task_id, title, user_id, created_at=None):
    return Task(
        id=task_id,
        category=Category.NOTE,
        title=title,
        status=TaskStatus.DOING,
        created_at=created_at or datetime.now(),
        updated_at=datetime.now(),
        file_path=f"notes/{task_id}.md",
    )


@pytest.fixture
def sqlite_storage(tmp_path):
    return SQLiteStorage(str(tmp_path / "test.db"))


@pytest.fixture
def review_service(sqlite_storage):
    return ReviewService(sqlite_storage=sqlite_storage)


@pytest.fixture
def user_with_entries(sqlite_storage):
    user_id = "heatmap_user"
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)
    five_days_ago = today - timedelta(days=5)

    sqlite_storage.upsert_entry(_make_task("e1", "Today entry", user_id), user_id=user_id)
    sqlite_storage.upsert_entry(_make_task("e2", "Today entry 2", user_id), user_id=user_id)
    sqlite_storage.upsert_entry(_make_task("e3", "3 days ago", user_id, created_at=three_days_ago), user_id=user_id)
    sqlite_storage.upsert_entry(_make_task("e4", "5 days ago", user_id, created_at=five_days_ago), user_id=user_id)

    return user_id


class TestActivityHeatmap:
    def test_returns_full_year(self, review_service, user_with_entries):
        year = datetime.now().year
        result = review_service.get_activity_heatmap(year, user_with_entries)
        assert result.year == year
        # 365 or 366 days
        assert len(result.items) >= 365

    def test_counts_correct(self, review_service, user_with_entries):
        year = datetime.now().year
        result = review_service.get_activity_heatmap(year, user_with_entries)
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_item = next(i for i in result.items if i.date == today_str)
        assert today_item.count == 2

    def test_empty_year(self, review_service):
        result = review_service.get_activity_heatmap(2020, "nobody")
        assert result.year == 2020
        assert all(i.count == 0 for i in result.items)

    def test_user_isolation(self, review_service, sqlite_storage):
        user_a = "user_a"
        sqlite_storage.upsert_entry(_make_task("ea", "A entry", user_a), user_id=user_a)

        result_a = review_service.get_activity_heatmap(datetime.now().year, user_a)
        result_b = review_service.get_activity_heatmap(datetime.now().year, "user_b")

        today_str = datetime.now().strftime("%Y-%m-%d")
        count_a = next(i for i in result_a.items if i.date == today_str).count
        count_b = next(i for i in result_b.items if i.date == today_str).count
        assert count_a >= 1
        assert count_b == 0
