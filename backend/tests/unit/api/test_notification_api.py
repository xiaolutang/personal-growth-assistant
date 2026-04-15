"""通知服务单元测试"""
import pytest
from datetime import datetime, timedelta

from app.infrastructure.storage.sqlite import SQLiteStorage
from app.services.notification_service import NotificationService, NotificationPreferences
from app.models.task import Task
from app.models.enums import Category, TaskStatus, Priority


def _make_task(task_id, category, title, status=TaskStatus.DOING, user_id="test_user",
               planned_date=None, created_at=None):
    return Task(
        id=task_id,
        category=category,
        title=title,
        status=status,
        priority=Priority.MEDIUM,
        created_at=created_at or datetime.now(),
        updated_at=datetime.now(),
        planned_date=planned_date,
        file_path=f"{category.value}/{task_id}.md",
        user_id=user_id,
    )


@pytest.fixture
def sqlite_storage(tmp_path):
    db_path = str(tmp_path / "test.db")
    return SQLiteStorage(db_path)


@pytest.fixture
def notification_service(sqlite_storage):
    return NotificationService(sqlite_storage)


@pytest.fixture
def user_with_entries(sqlite_storage):
    user_id = "test_user_1"
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    four_days_ago = today - timedelta(days=4)

    # 逾期任务
    sqlite_storage.upsert_entry(
        _make_task("task-overdue-1", Category.TASK, "逾期任务1",
                    status=TaskStatus.DOING, user_id=user_id, planned_date=yesterday),
        user_id=user_id,
    )

    # 未转化灵感（4天前）
    sqlite_storage.upsert_entry(
        _make_task("inbox-stale-1", Category.INBOX, "旧灵感1",
                    status=TaskStatus.WAIT_START, user_id=user_id, created_at=four_days_ago),
        user_id=user_id,
    )

    # 已完成任务（不应出现）
    sqlite_storage.upsert_entry(
        _make_task("task-done-1", Category.TASK, "已完成任务",
                    status=TaskStatus.COMPLETE, user_id=user_id, planned_date=yesterday),
        user_id=user_id,
    )

    return user_id


class TestNotificationGeneration:
    def test_overdue_task_notification(self, notification_service, user_with_entries):
        result = notification_service.get_notifications(user_with_entries)
        overdue = [n for n in result.items if n.type == "overdue_task"]
        assert len(overdue) == 1
        assert overdue[0].ref_id == "task-overdue-1"
        assert "逾期任务1" in overdue[0].message

    def test_stale_inbox_notification(self, notification_service, user_with_entries):
        result = notification_service.get_notifications(user_with_entries)
        stale = [n for n in result.items if n.type == "stale_inbox"]
        assert len(stale) == 1
        assert stale[0].ref_id == "inbox-stale-1"
        assert "旧灵感1" in stale[0].message

    def test_review_prompt_when_no_recent_activity(self, notification_service):
        result = notification_service.get_notifications("inactive_user")
        prompts = [n for n in result.items if n.type == "review_prompt"]
        assert len(prompts) == 1

    def test_no_overdue_when_all_complete(self, notification_service, sqlite_storage):
        user_id = "user_all_done"
        yesterday = datetime.now() - timedelta(days=1)
        sqlite_storage.upsert_entry(
            _make_task("task-done", Category.TASK, "Done",
                        status=TaskStatus.COMPLETE, user_id=user_id, planned_date=yesterday),
            user_id=user_id,
        )
        result = notification_service.get_notifications(user_id)
        overdue = [n for n in result.items if n.type == "overdue_task"]
        assert len(overdue) == 0

    def test_empty_for_user_with_no_data(self, notification_service):
        result = notification_service.get_notifications("empty_user")
        assert len([n for n in result.items if n.type != "review_prompt"]) == 0


class TestNotificationDismiss:
    def test_dismiss_marks_as_read(self, notification_service, user_with_entries):
        result = notification_service.get_notifications(user_with_entries)
        nid = [n for n in result.items if n.type == "overdue_task"][0].id
        notification_service.dismiss_notification(nid, user_with_entries)

        result2 = notification_service.get_notifications(user_with_entries)
        dismissed = [n for n in result2.items if n.id == nid]
        assert len(dismissed) == 1
        assert dismissed[0].dismissed is True

    def test_unread_count_decreases_after_dismiss(self, notification_service, user_with_entries):
        result1 = notification_service.get_notifications(user_with_entries)
        count1 = result1.unread_count
        assert count1 > 0

        nid = result1.items[0].id
        notification_service.dismiss_notification(nid, user_with_entries)

        result2 = notification_service.get_notifications(user_with_entries)
        assert result2.unread_count == count1 - 1


class TestNotificationPreferences:
    def test_default_preferences(self, notification_service):
        prefs = notification_service.get_preferences("new_user")
        assert prefs.overdue_task_enabled is True
        assert prefs.stale_inbox_enabled is True
        assert prefs.review_prompt_enabled is True

    def test_update_preferences(self, notification_service):
        notification_service.update_preferences("user1", NotificationPreferences(
            overdue_task_enabled=False,
            stale_inbox_enabled=True,
            review_prompt_enabled=False,
        ))
        prefs = notification_service.get_preferences("user1")
        assert prefs.overdue_task_enabled is False
        assert prefs.stale_inbox_enabled is True
        assert prefs.review_prompt_enabled is False

    def test_disabled_type_not_generated(self, notification_service, user_with_entries):
        notification_service.update_preferences(user_with_entries, NotificationPreferences(
            overdue_task_enabled=False, stale_inbox_enabled=False, review_prompt_enabled=False,
        ))
        result = notification_service.get_notifications(user_with_entries)
        assert len(result.items) == 0
        assert result.unread_count == 0


class TestUserIsolation:
    def test_only_sees_own_notifications(self, notification_service, sqlite_storage):
        user_a = "user_a"
        user_b = "user_b"
        yesterday = datetime.now() - timedelta(days=1)

        sqlite_storage.upsert_entry(
            _make_task("task-a", Category.TASK, "A's task",
                        status=TaskStatus.DOING, user_id=user_a, planned_date=yesterday),
            user_id=user_a,
        )

        result_a = notification_service.get_notifications(user_a)
        result_b = notification_service.get_notifications(user_b)

        overdue_a = [n for n in result_a.items if n.type == "overdue_task"]
        overdue_b = [n for n in result_b.items if n.type == "overdue_task"]
        assert len(overdue_a) == 1
        assert len(overdue_b) == 0
