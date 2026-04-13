"""SQLite 用户数据隔离测试

测试 user_id 过滤在 entries 表各操作中的正确性。
"""
from datetime import datetime

import pytest

from app.models import Task, Category, TaskStatus, Priority


def _make_entry(entry_id: str, title: str = "测试条目", **kwargs) -> Task:
    """快速创建测试用 Task"""
    return Task(
        id=entry_id,
        title=title,
        content=kwargs.get("content", ""),
        category=kwargs.get("category", Category.TASK),
        status=kwargs.get("status", TaskStatus.DOING),
        priority=kwargs.get("priority", Priority.MEDIUM),
        tags=kwargs.get("tags", []),
        created_at=kwargs.get("created_at", datetime.now()),
        updated_at=kwargs.get("updated_at", datetime.now()),
        file_path=f"tasks/{entry_id}.md",
    )


class TestUserIsolation:
    """用户数据隔离"""

    def test_upsert_entry_with_user_id(self, sqlite_storage):
        """创建条目时带上 user_id"""
        entry = _make_entry("user-entry-1")
        sqlite_storage.upsert_entry(entry, user_id="usr_abc123")

        # 通过 get_entry 带 user_id 查询
        result = sqlite_storage.get_entry("user-entry-1", user_id="usr_abc123")
        assert result is not None
        assert result["id"] == "user-entry-1"
        assert result["user_id"] == "usr_abc123"

    def test_get_entry_user_mismatch(self, sqlite_storage):
        """不同 user_id 查不到对方的条目"""
        entry = _make_entry("user-entry-2")
        sqlite_storage.upsert_entry(entry, user_id="usr_alice")

        # user_id 不匹配返回 None
        result = sqlite_storage.get_entry("user-entry-2", user_id="usr_bob")
        assert result is None

    def test_list_entries_filters_by_user(self, sqlite_storage):
        """list_entries 只返回当前用户数据"""
        # 用户 A 创建 2 个条目
        sqlite_storage.upsert_entry(_make_entry("alice-1"), user_id="usr_alice")
        sqlite_storage.upsert_entry(_make_entry("alice-2"), user_id="usr_alice")

        # 用户 B 创建 1 个条目
        sqlite_storage.upsert_entry(_make_entry("bob-1"), user_id="usr_bob")

        # 用户 A 只看到 2 个
        alice_entries = sqlite_storage.list_entries(user_id="usr_alice")
        assert len(alice_entries) == 2

        # 用户 B 只看到 1 个
        bob_entries = sqlite_storage.list_entries(user_id="usr_bob")
        assert len(bob_entries) == 1
        assert bob_entries[0]["id"] == "bob-1"

    def test_count_entries_filters_by_user(self, sqlite_storage):
        """count_entries 只统计当前用户数据"""
        sqlite_storage.upsert_entry(_make_entry("count-a1"), user_id="usr_alice")
        sqlite_storage.upsert_entry(_make_entry("count-a2"), user_id="usr_alice")
        sqlite_storage.upsert_entry(_make_entry("count-b1"), user_id="usr_bob")

        assert sqlite_storage.count_entries(user_id="usr_alice") == 2
        assert sqlite_storage.count_entries(user_id="usr_bob") == 1

    def test_delete_entry_user_mismatch(self, sqlite_storage):
        """不同用户无法删除他人的条目"""
        sqlite_storage.upsert_entry(_make_entry("delete-test"), user_id="usr_alice")

        # 用户 B 尝试删除用户 A 的条目
        result = sqlite_storage.delete_entry("delete-test", user_id="usr_bob")
        assert result is True  # SQL 执行成功但影响 0 行

        # 用户 A 的条目仍然存在
        result = sqlite_storage.get_entry("delete-test", user_id="usr_alice")
        assert result is not None

    def test_search_filters_by_user(self, sqlite_storage):
        """全文搜索只返回当前用户数据"""
        sqlite_storage.upsert_entry(
            _make_entry("search-alice", title="Alice Report", content="unique keyword xyz"),
            user_id="usr_alice",
        )
        sqlite_storage.upsert_entry(
            _make_entry("search-bob", title="Bob Report", content="unique keyword xyz"),
            user_id="usr_bob",
        )

        # 每个用户只搜到自己的
        alice_results = sqlite_storage.search("xyz", user_id="usr_alice")
        assert len(alice_results) == 1
        assert alice_results[0]["id"] == "search-alice"

        bob_results = sqlite_storage.search("xyz", user_id="usr_bob")
        assert len(bob_results) == 1
        assert bob_results[0]["id"] == "search-bob"

    def test_default_user_id(self, sqlite_storage):
        """不传 user_id 时默认使用 _default"""
        entry = _make_entry("default-user-entry")
        sqlite_storage.upsert_entry(entry)  # 不传 user_id

        # 用 _default 查询能找到
        result = sqlite_storage.get_entry("default-user-entry", user_id="_default")
        assert result is not None
        assert result["user_id"] == "_default"

    def test_migration_assigns_default(self, sqlite_storage):
        """已有数据的 user_id 应为 _default"""
        # 通过 upsert 不传 user_id 创建
        sqlite_storage.upsert_entry(_make_entry("migrate-test"))

        # 验证 user_id = _default
        conn = sqlite_storage._get_conn()
        try:
            row = conn.execute(
                "SELECT user_id FROM entries WHERE id = ?", ("migrate-test",)
            ).fetchone()
            assert row["user_id"] == "_default"
        finally:
            conn.close()

    def test_list_entries_with_type_and_user(self, sqlite_storage):
        """type + user_id 组合筛选"""
        sqlite_storage.upsert_entry(
            _make_entry("alice-task", category=Category.TASK), user_id="usr_alice"
        )
        sqlite_storage.upsert_entry(
            _make_entry("alice-project", category=Category.PROJECT), user_id="usr_alice"
        )
        sqlite_storage.upsert_entry(
            _make_entry("bob-task", category=Category.TASK), user_id="usr_bob"
        )

        alice_tasks = sqlite_storage.list_entries(type="task", user_id="usr_alice")
        assert len(alice_tasks) == 1
        assert alice_tasks[0]["id"] == "alice-task"
