"""B99: get_tag_stats_in_range 真实 SQL 测试

验证 storage 层 SQL 聚合的正确性、日期边界、用户隔离和排序稳定性。
"""
from datetime import datetime, timedelta

import pytest

from app.models import Task, Category, TaskStatus, Priority


def _make_entry(entry_id, tags, created_at, user_id="u1"):
    """快速创建测试条目"""
    return Task(
        id=entry_id,
        title=f"test-{entry_id}",
        content="",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=tags,
        created_at=created_at,
        updated_at=created_at,
        file_path=f"tasks/{entry_id}.md",
        user_id=user_id,
    )


class TestGetTagStatsInRange:
    """get_tag_stats_in_range 真实 SQLite 测试"""

    def test_basic_freq_count(self, sqlite_storage):
        """基本频次计数正确"""
        now = datetime.now()
        sqlite_storage.upsert_entry(_make_entry("e1", ["Python", "Rust"], now), user_id="u1")
        sqlite_storage.upsert_entry(_make_entry("e2", ["Python"], now), user_id="u1")
        sqlite_storage.upsert_entry(_make_entry("e3", ["Rust", "Go"], now), user_id="u1")

        today = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        result = sqlite_storage.get_tag_stats_in_range("u1", start, today)

        tags = {r[0]: r[1] for r in result}
        assert tags["Python"] == 2
        assert tags["Rust"] == 2
        assert tags["Go"] == 1

    def test_deterministic_tie_break(self, sqlite_storage):
        """等频次标签按名称升序排列（确定性排序）"""
        now = datetime.now()
        sqlite_storage.upsert_entry(_make_entry("e1", ["Zebra", "Alpha"], now), user_id="u1")
        sqlite_storage.upsert_entry(_make_entry("e2", ["Zebra", "Alpha"], now), user_id="u1")

        today = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        result = sqlite_storage.get_tag_stats_in_range("u1", start, today)

        assert len(result) == 2
        assert result[0][0] == "Alpha"  # 字母序在前
        assert result[1][0] == "Zebra"

    def test_date_range_inclusive_start(self, sqlite_storage):
        """start_date 包含当天"""
        now = datetime.now()
        start_date = now.strftime("%Y-%m-%d")

        sqlite_storage.upsert_entry(_make_entry("e1", ["Python"], now), user_id="u1")

        result = sqlite_storage.get_tag_stats_in_range("u1", start_date, "2099-12-31")
        assert len(result) == 1
        assert result[0][0] == "Python"

    def test_date_range_excludes_after_end(self, sqlite_storage):
        """end_date 之后的条目不包含"""
        yesterday = datetime.now() - timedelta(days=1)
        long_ago = datetime(2020, 1, 1)

        sqlite_storage.upsert_entry(_make_entry("old", ["Old"], long_ago), user_id="u1")
        sqlite_storage.upsert_entry(_make_entry("recent", ["Recent"], yesterday), user_id="u1")

        # 查询 2020-01-01 到 2020-01-02 的数据
        result = sqlite_storage.get_tag_stats_in_range("u1", "2020-01-01", "2020-01-02")
        assert len(result) == 1
        assert result[0][0] == "Old"

    def test_empty_range_returns_empty(self, sqlite_storage):
        """无匹配数据返回空列表"""
        result = sqlite_storage.get_tag_stats_in_range(
            "nonexistent_user", "2020-01-01", "2020-12-31",
        )
        assert result == []

    def test_top_n_limit(self, sqlite_storage):
        """top_n 限制返回数量"""
        now = datetime.now()
        for i in range(10):
            sqlite_storage.upsert_entry(
                _make_entry(f"e{i}", [f"tag{i}"], now), user_id="u1",
            )

        today = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        result = sqlite_storage.get_tag_stats_in_range("u1", start, today, top_n=3)
        assert len(result) == 3

    def test_user_isolation(self, sqlite_storage):
        """不同用户数据隔离"""
        now = datetime.now()
        sqlite_storage.upsert_entry(_make_entry("u1-e1", ["Python"], now), user_id="u1")
        sqlite_storage.upsert_entry(_make_entry("u2-e1", ["Java"], now), user_id="u2")

        today = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        u1_result = sqlite_storage.get_tag_stats_in_range("u1", start, today)
        u2_result = sqlite_storage.get_tag_stats_in_range("u2", start, today)

        u1_tags = {r[0] for r in u1_result}
        u2_tags = {r[0] for r in u2_result}
        assert "Python" in u1_tags
        assert "Java" not in u1_tags
        assert "Java" in u2_tags
        assert "Python" not in u2_tags

    def test_duplicate_entry_counted_once(self, sqlite_storage):
        """同一 entry 内重复 tag 只计一次（DISTINCT e.id）"""
        now = datetime.now()
        entry = Task(
            id="dup-e1",
            title="dup tags",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["Python", "Python", "Python"],  # 重复 tag
            created_at=now,
            updated_at=now,
            file_path="tasks/dup-e1.md",
        )
        sqlite_storage.upsert_entry(entry, user_id="u1")

        today = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        result = sqlite_storage.get_tag_stats_in_range("u1", start, today)

        # SQLite 的 entry_tags 表会去重，Python 只关联一次
        assert len(result) == 1
        assert result[0][0] == "Python"
