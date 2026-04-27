"""R043 SQLite 层批量查询方法测试

覆盖:
- batch_entry_belongs_to_user / batch_get_entry_summaries (sqlite_entries)
- batch_count_goal_entries / batch_count_completed_milestones / batch_count_entries_by_tags (sqlite_goals)
- count_entries_by_tags 合并日期参数
- list_entries_by_tags 合并日期参数
- _conn() 上下文管理器异常回滚
"""
from datetime import datetime, timezone

import pytest

from app.infrastructure.storage.sqlite import SQLiteStorage
from app.models import Task, Category, TaskStatus, Priority


def _make_task(task_id, title, user_id="_default", tags=None, created_at=None):
    return Task(
        id=task_id,
        title=title,
        content=f"content for {title}",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=tags or [],
        created_at=created_at or datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        file_path=f"tasks/{task_id}.md",
    )


# === batch_entry_belongs_to_user ===


class TestBatchEntryBelongsToUser:
    def test_empty_list(self, sqlite_storage):
        result = sqlite_storage.batch_entry_belongs_to_user([], "user1")
        assert result == set()

    def test_all_match(self, sqlite_storage):
        uid = "user-a"
        sqlite_storage.upsert_entry(_make_task("e1", "t1", uid), user_id=uid)
        sqlite_storage.upsert_entry(_make_task("e2", "t2", uid), user_id=uid)
        result = sqlite_storage.batch_entry_belongs_to_user(["e1", "e2"], uid)
        assert result == {"e1", "e2"}

    def test_partial_match(self, sqlite_storage):
        uid = "user-b"
        sqlite_storage.upsert_entry(_make_task("e1", "t1", uid), user_id=uid)
        result = sqlite_storage.batch_entry_belongs_to_user(["e1", "e2", "e3"], uid)
        assert result == {"e1"}

    def test_different_user_no_match(self, sqlite_storage):
        sqlite_storage.upsert_entry(_make_task("e1", "t1", "user-x"), user_id="user-x")
        result = sqlite_storage.batch_entry_belongs_to_user(["e1"], "user-y")
        assert result == set()

    def test_consistency_with_single_check(self, sqlite_storage):
        uid = "user-c"
        sqlite_storage.upsert_entry(_make_task("e1", "t1", uid), user_id=uid)
        sqlite_storage.upsert_entry(_make_task("e2", "t2", uid), user_id=uid)
        ids = ["e1", "e2", "e3"]
        batch_result = sqlite_storage.batch_entry_belongs_to_user(ids, uid)
        for eid in ids:
            assert sqlite_storage.entry_belongs_to_user(eid, uid) == (eid in batch_result)


# === batch_get_entry_summaries ===


class TestBatchGetEntrySummaries:
    def test_empty_list(self, sqlite_storage):
        result = sqlite_storage.batch_get_entry_summaries([], "user1")
        assert result == {}

    def test_returns_id_title_type(self, sqlite_storage):
        uid = "user-d"
        sqlite_storage.upsert_entry(
            _make_task("e1", "My Task", uid, tags=["py"]),
            user_id=uid,
        )
        result = sqlite_storage.batch_get_entry_summaries(["e1"], uid)
        assert "e1" in result
        assert result["e1"]["title"] == "My Task"
        assert result["e1"]["type"] == "task"

    def test_partial_match_only_returns_existing(self, sqlite_storage):
        uid = "user-e"
        sqlite_storage.upsert_entry(_make_task("e1", "t1", uid), user_id=uid)
        result = sqlite_storage.batch_get_entry_summaries(["e1", "nonexistent"], uid)
        assert len(result) == 1
        assert "e1" in result
        assert "nonexistent" not in result


# === batch_count_goal_entries ===


class TestBatchCountGoalEntries:
    def test_empty_list(self, sqlite_storage):
        result = sqlite_storage.batch_count_goal_entries([], "user1")
        assert result == {}

    def test_zeros_for_goals_with_no_entries(self, sqlite_storage):
        uid = "user-f"
        sqlite_storage.create_goal("g1", uid, "Goal 1", "count", 10)
        sqlite_storage.create_goal("g2", uid, "Goal 2", "count", 5)
        result = sqlite_storage.batch_count_goal_entries(["g1", "g2"], uid)
        assert result == {"g1": 0, "g2": 0}

    def test_counts_linked_entries(self, sqlite_storage):
        uid = "user-g"
        sqlite_storage.create_goal("g1", uid, "Goal 1", "count", 10)
        sqlite_storage.create_goal("g2", uid, "Goal 2", "count", 5)
        sqlite_storage.upsert_entry(_make_task("e1", "t1", uid), user_id=uid)
        sqlite_storage.upsert_entry(_make_task("e2", "t2", uid), user_id=uid)
        sqlite_storage.create_goal_entry("g1", "e1", uid)
        sqlite_storage.create_goal_entry("g1", "e2", uid)
        result = sqlite_storage.batch_count_goal_entries(["g1", "g2"], uid)
        assert result == {"g1": 2, "g2": 0}

    def test_user_isolation(self, sqlite_storage):
        uid_a = "user-h"
        uid_b = "user-i"
        sqlite_storage.create_goal("ga", uid_a, "Goal A", "count", 10)
        sqlite_storage.create_goal("gb", uid_b, "Goal B", "count", 10)
        sqlite_storage.upsert_entry(_make_task("e1", "t1", uid_a), user_id=uid_a)
        sqlite_storage.create_goal_entry("ga", "e1", uid_a)
        result_a = sqlite_storage.batch_count_goal_entries(["ga"], uid_a)
        result_b = sqlite_storage.batch_count_goal_entries(["gb"], uid_b)
        assert result_a == {"ga": 1}
        assert result_b == {"gb": 0}


# === batch_count_completed_milestones ===


class TestBatchCountCompletedMilestones:
    def test_empty_list(self, sqlite_storage):
        result = sqlite_storage.batch_count_completed_milestones([], "user1")
        assert result == {}

    def test_counts_completed_only(self, sqlite_storage):
        uid = "user-j"
        sqlite_storage.create_goal("g1", uid, "Goal 1", "milestone", 3)
        sqlite_storage.create_milestone("m1", "g1", uid, "M1")
        sqlite_storage.create_milestone("m2", "g1", uid, "M2")
        sqlite_storage.create_milestone("m3", "g1", uid, "M3")
        # mark m1 and m3 as completed
        sqlite_storage.update_milestone("m1", uid, status="completed")
        sqlite_storage.update_milestone("m3", uid, status="completed")
        result = sqlite_storage.batch_count_completed_milestones(["g1"], uid)
        assert result == {"g1": 2}

    def test_zeros_for_no_milestones(self, sqlite_storage):
        uid = "user-k"
        sqlite_storage.create_goal("g1", uid, "Goal 1", "milestone", 3)
        result = sqlite_storage.batch_count_completed_milestones(["g1"], uid)
        assert result == {"g1": 0}

    def test_multiple_goals(self, sqlite_storage):
        uid = "user-l"
        sqlite_storage.create_goal("g1", uid, "Goal 1", "milestone", 2)
        sqlite_storage.create_goal("g2", uid, "Goal 2", "milestone", 1)
        sqlite_storage.create_milestone("m1", "g1", uid, "M1")
        sqlite_storage.create_milestone("m2", "g2", uid, "M2")
        sqlite_storage.update_milestone("m1", uid, status="completed")
        result = sqlite_storage.batch_count_completed_milestones(["g1", "g2"], uid)
        assert result == {"g1": 1, "g2": 0}


# === batch_count_entries_by_tags ===


class TestBatchCountEntriesByTags:
    def test_empty_list(self, sqlite_storage):
        result = sqlite_storage.batch_count_entries_by_tags([], "user1")
        assert result == []

    def test_empty_tags_returns_zero(self, sqlite_storage):
        result = sqlite_storage.batch_count_entries_by_tags(
            [([], "ignored", None, None)], "user1"
        )
        assert result == [0]

    def test_counts_matching_entries(self, sqlite_storage):
        uid = "user-m"
        sqlite_storage.upsert_entry(
            _make_task("e1", "t1", uid, tags=["python", "fastapi"]),
            user_id=uid,
        )
        sqlite_storage.upsert_entry(
            _make_task("e2", "t2", uid, tags=["python"]),
            user_id=uid,
        )
        sqlite_storage.upsert_entry(
            _make_task("e3", "t3", uid, tags=["rust"]),
            user_id=uid,
        )
        result = sqlite_storage.batch_count_entries_by_tags(
            [
                (["python"], "ignored", None, None),
                (["rust"], "ignored", None, None),
                (["python", "fastapi"], "ignored", None, None),
                (["go"], "ignored", None, None),
            ],
            uid,
        )
        # tags IN (...) is OR semantics, so ["python", "fastapi"] matches entries with EITHER tag → 2
        assert result == [2, 1, 2, 0]

    def test_with_date_range(self, sqlite_storage):
        uid = "user-n"
        old = datetime(2025, 1, 15, tzinfo=timezone.utc)
        recent = datetime(2026, 4, 20, tzinfo=timezone.utc)
        sqlite_storage.upsert_entry(
            _make_task("e1", "old", uid, tags=["python"], created_at=old),
            user_id=uid,
        )
        sqlite_storage.upsert_entry(
            _make_task("e2", "recent", uid, tags=["python"], created_at=recent),
            user_id=uid,
        )
        # 只查 2026 年
        result = sqlite_storage.batch_count_entries_by_tags(
            [ (["python"], "ignored", "2026-01-01", "2026-12-31") ],
            uid,
        )
        assert result == [1]


# === count_entries_by_tags 合并日期参数 ===


class TestCountEntriesByTagsMerged:
    def test_without_dates(self, sqlite_storage):
        uid = "user-o"
        sqlite_storage.upsert_entry(
            _make_task("e1", "t1", uid, tags=["python"]),
            user_id=uid,
        )
        assert sqlite_storage.count_entries_by_tags(["python"], uid) == 1
        assert sqlite_storage.count_entries_by_tags(["go"], uid) == 0

    def test_with_dates(self, sqlite_storage):
        uid = "user-p"
        old = datetime(2025, 6, 1, tzinfo=timezone.utc)
        recent = datetime(2026, 4, 1, tzinfo=timezone.utc)
        sqlite_storage.upsert_entry(
            _make_task("e1", "old", uid, tags=["python"], created_at=old),
            user_id=uid,
        )
        sqlite_storage.upsert_entry(
            _make_task("e2", "recent", uid, tags=["python"], created_at=recent),
            user_id=uid,
        )
        assert sqlite_storage.count_entries_by_tags(["python"], uid, "2026-01-01", "2027-01-01") == 1
        assert sqlite_storage.count_entries_by_tags(["python"], uid) == 2

    def test_empty_tags_returns_zero(self, sqlite_storage):
        assert sqlite_storage.count_entries_by_tags([], "user") == 0

    def test_in_range_alias(self, sqlite_storage):
        uid = "user-q"
        sqlite_storage.upsert_entry(
            _make_task("e1", "t1", uid, tags=["python"]),
            user_id=uid,
        )
        # alias 应该和带日期参数的原方法返回相同结果
        alias = sqlite_storage.count_entries_by_tags_in_range(
            ["python"], uid, "2000-01-01", "2099-12-31"
        )
        direct = sqlite_storage.count_entries_by_tags(
            ["python"], uid, "2000-01-01", "2099-12-31"
        )
        assert alias == direct


# === list_entries_by_tags 合并日期参数 ===


class TestListEntriesByTagsMerged:
    def test_without_dates(self, sqlite_storage):
        uid = "user-r"
        sqlite_storage.upsert_entry(
            _make_task("e1", "t1", uid, tags=["python"]),
            user_id=uid,
        )
        rows = sqlite_storage.list_entries_by_tags(["python"], uid)
        assert len(rows) == 1
        assert rows[0]["id"] == "e1"

    def test_with_dates(self, sqlite_storage):
        uid = "user-s"
        old = datetime(2025, 1, 1, tzinfo=timezone.utc)
        recent = datetime(2026, 4, 1, tzinfo=timezone.utc)
        sqlite_storage.upsert_entry(
            _make_task("e1", "old", uid, tags=["python"], created_at=old),
            user_id=uid,
        )
        sqlite_storage.upsert_entry(
            _make_task("e2", "recent", uid, tags=["python"], created_at=recent),
            user_id=uid,
        )
        rows = sqlite_storage.list_entries_by_tags(["python"], uid, start_date="2026-01-01", end_date="2027-01-01")
        assert len(rows) == 1
        assert rows[0]["id"] == "e2"

    def test_in_range_alias(self, sqlite_storage):
        uid = "user-t"
        sqlite_storage.upsert_entry(
            _make_task("e1", "t1", uid, tags=["python"]),
            user_id=uid,
        )
        alias = sqlite_storage.list_entries_by_tags_in_range(
            ["python"], uid, "2000-01-01", "2099-12-31"
        )
        direct = sqlite_storage.list_entries_by_tags(
            ["python"], uid, start_date="2000-01-01", end_date="2099-12-31"
        )
        assert len(alias) == len(direct)


# === _conn() 上下文管理器回滚 ===


class TestConnContextManager:
    def test_rollback_on_exception(self, sqlite_storage):
        """异常退出时应该回滚，不应写入脏数据"""
        uid = "user-conn"
        sqlite_storage.upsert_entry(_make_task("e1", "before", uid), user_id=uid)
        try:
            with sqlite_storage._conn() as conn:
                conn.execute(
                    "UPDATE entries SET title = 'dirty' WHERE id = ?",
                    ("e1",),
                )
                raise RuntimeError("simulate failure")
        except RuntimeError:
            pass
        # 回滚后标题应保持原值
        entry = sqlite_storage.get_entry("e1", uid)
        assert entry["title"] == "before"

    def test_commit_on_success(self, sqlite_storage):
        """正常退出时应该 commit"""
        uid = "user-conn2"
        sqlite_storage.upsert_entry(_make_task("e1", "before", uid), user_id=uid)
        with sqlite_storage._conn() as conn:
            conn.execute(
                "UPDATE entries SET title = 'after' WHERE id = ?",
                ("e1",),
            )
        entry = sqlite_storage.get_entry("e1", uid)
        assert entry["title"] == "after"
