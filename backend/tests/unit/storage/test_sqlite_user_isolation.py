"""SQLite 用户数据隔离测试

测试 user_id 过滤在 entries 表各操作中的正确性。
"""

import pytest

from app.models import Category
from tests.conftest import _make_entry


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

    def test_claim_default_entries(self, sqlite_storage):
        """可将 `_default` 条目认领到真实用户"""
        sqlite_storage.upsert_entry(_make_entry("legacy-1"), user_id="_default")
        sqlite_storage.upsert_entry(_make_entry("legacy-2"), user_id="_default")

        claimed = sqlite_storage.claim_default_entries("usr_alice")

        assert claimed == 2
        assert sqlite_storage.count_entries(user_id="_default") == 0
        assert sqlite_storage.count_entries(user_id="usr_alice") == 2

    def test_sync_from_markdown_default_does_not_override_claimed_owner(self, sqlite_storage, tmp_path):
        """_default 启动同步不应覆盖已认领到真实用户的数据"""
        from app.infrastructure.storage.markdown import MarkdownStorage

        md = MarkdownStorage(str(tmp_path))
        entry = _make_entry("claimed-entry")
        md.write_entry(entry)
        sqlite_storage.upsert_entry(entry, user_id="usr_alice")

        count = sqlite_storage.sync_from_markdown(md, user_id="_default")

        assert count == 0
        assert sqlite_storage.get_entry_owner("claimed-entry") == "usr_alice"


class TestUpdateGoalFieldWhitelist:
    """update_goal 字段名白名单校验测试"""

    def _create_goal(self, sqlite_storage, user_id="usr_test"):
        """辅助：创建一个目标"""
        return sqlite_storage.create_goal(
            goal_id="goal-whitelist-1",
            user_id=user_id,
            title="白名单测试目标",
            metric_type="count",
            target_value=10,
        )

    def test_update_goal_accepts_allowed_field(self, sqlite_storage):
        """合法字段名正常更新"""
        self._create_goal(sqlite_storage)
        result = sqlite_storage.update_goal(
            "goal-whitelist-1", "usr_test", title="新标题"
        )
        assert result is not None
        assert result["title"] == "新标题"

    def test_update_goal_rejects_invalid_field(self, sqlite_storage):
        """非法字段名抛出 ValueError"""
        self._create_goal(sqlite_storage)
        with pytest.raises(ValueError, match="非法字段名"):
            sqlite_storage.update_goal(
                "goal-whitelist-1", "usr_test", evil_column="hack"
            )

    def test_update_goal_rejects_mixed_fields(self, sqlite_storage):
        """混合合法与非法字段时，整体拒绝"""
        self._create_goal(sqlite_storage)
        with pytest.raises(ValueError, match="非法字段名"):
            sqlite_storage.update_goal(
                "goal-whitelist-1", "usr_test",
                title="合法", evil_col="非法",
            )

    def test_update_goal_accepts_all_allowed_fields(self, sqlite_storage):
        """所有白名单中存在于表中的字段均可正常更新"""
        self._create_goal(sqlite_storage)
        result = sqlite_storage.update_goal(
            "goal-whitelist-1", "usr_test",
            title="t", description="d", status="completed",
            target_value=99, metric_type="percent",
            start_date="2026-01-01", end_date="2026-12-31",
            auto_tags="tag1,tag2",
        )
        assert result is not None
        assert result["title"] == "t"
        assert result["status"] == "completed"

    def test_update_goal_none_values_are_skipped(self, sqlite_storage):
        """None 值被跳过，不触发白名单校验"""
        self._create_goal(sqlite_storage)
        result = sqlite_storage.update_goal(
            "goal-whitelist-1", "usr_test",
            title="新标题", description=None,
        )
        assert result is not None
        assert result["title"] == "新标题"

    def test_update_goal_error_message_lists_invalid(self, sqlite_storage):
        """错误消息包含非法字段名和合法值列表"""
        self._create_goal(sqlite_storage)
        with pytest.raises(ValueError) as exc_info:
            sqlite_storage.update_goal(
                "goal-whitelist-1", "usr_test",
                bad_field="x", another_bad="y",
            )
        msg = str(exc_info.value)
        assert "another_bad" in msg
        assert "bad_field" in msg
        assert "title" in msg  # 合法值列表中包含 title
