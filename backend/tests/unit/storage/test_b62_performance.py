"""B62: StorageFactory LRU 淘汰 + 趋势聚合测试"""
import pytest

from app.infrastructure.storage.storage_factory import StorageFactory, _MAX_CACHE_SIZE
from app.infrastructure.storage.sqlite import SQLiteStorage
from app.models import Task, Category, TaskStatus, Priority
from datetime import date, datetime, timezone


class TestStorageFactoryLRU:
    """StorageFactory LRU 缓存淘汰"""

    def test_lru_evicts_oldest_when_over_capacity(self, tmp_path):
        """超过 maxsize 时淘汰最早创建的实例"""
        factory = StorageFactory(str(tmp_path))

        # 创建 maxsize 个实例
        first = factory.get_markdown_storage("user_001")
        for i in range(2, _MAX_CACHE_SIZE + 1):
            factory.get_markdown_storage(f"user_{i:03d}")

        assert "user_001" in factory._cache

        # 多一个触发淘汰
        factory.get_markdown_storage("user_extra")

        assert "user_001" not in factory._cache
        assert len(factory._cache) == _MAX_CACHE_SIZE

    def test_lru_access_renews_position(self, tmp_path):
        """访问已缓存的实例会刷新 LRU 位置"""
        factory = StorageFactory(str(tmp_path))

        first = factory.get_markdown_storage("user_001")
        for i in range(2, _MAX_CACHE_SIZE + 1):
            factory.get_markdown_storage(f"user_{i:03d}")

        # 访问 user_001 刷新位置
        factory.get_markdown_storage("user_001")

        # 加一个触发淘汰 — user_002 应该被淘汰而非 user_001
        factory.get_markdown_storage("user_extra")

        assert "user_001" in factory._cache
        assert "user_002" not in factory._cache

    def test_cache_hit_returns_same_instance(self, tmp_path):
        """缓存命中返回同一实例"""
        factory = StorageFactory(str(tmp_path))
        s1 = factory.get_markdown_storage("user_x")
        s2 = factory.get_markdown_storage("user_x")
        assert s1 is s2


class TestTrendAggregation:
    """get_trend_aggregation 单次聚合替代 N+1"""

    @pytest.fixture
    def sqlite(self, tmp_path):
        db = SQLiteStorage(str(tmp_path / "test.db"))
        return db

    def _make_task(self, task_id, cat, status, created_at, user_id="u1"):
        return Task(
            id=task_id,
            title=f"test-{task_id}",
            category=cat,
            status=status,
            priority=Priority.MEDIUM,
            file_path=f"{cat.value}/{task_id}.md",
            created_at=created_at,
            updated_at=created_at,
            user_id=user_id,
        )

    def test_aggregation_groups_by_date_type_status(self, sqlite, tmp_path):
        """聚合 SQL 按 date+type+status 正确分组"""
        now = datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone.utc)

        tasks = [
            self._make_task("t1", Category.TASK, TaskStatus.DOING, now),
            self._make_task("t2", Category.TASK, TaskStatus.COMPLETE, now),
            self._make_task("t3", Category.TASK, TaskStatus.COMPLETE, now),
            self._make_task("n1", Category.NOTE, TaskStatus.DOING, now),
            self._make_task("i1", Category.INBOX, TaskStatus.WAIT_START, now),
        ]
        for t in tasks:
            sqlite.upsert_entry(t, user_id="u1")

        rows = sqlite.get_trend_aggregation("u1", "2026-04-19", "2026-04-20")

        # 应该有 4 组：(task, doing=1), (task, complete=2), (note, doing=1), (inbox, pending=1)
        assert len(rows) == 4

        task_doing = next(r for r in rows if r["category"] == "task" and r["status"] == "doing")
        assert task_doing["cnt"] == 1

        task_complete = next(r for r in rows if r["category"] == "task" and r["status"] == "complete")
        assert task_complete["cnt"] == 2

    def test_aggregation_empty_range(self, sqlite, tmp_path):
        """空日期范围返回空列表"""
        rows = sqlite.get_trend_aggregation("u1", "2026-01-01", "2026-01-02")
        assert rows == []

    def test_aggregation_date_range_exclusive_end(self, sqlite, tmp_path):
        """end_date 是不含的（<）"""
        now = datetime(2026, 4, 19, 10, 0, 0, tzinfo=timezone.utc)
        sqlite.upsert_entry(
            self._make_task("t1", Category.TASK, TaskStatus.DOING, now), user_id="u1"
        )

        # end_date = 2026-04-19 不包含 4/19 的数据
        rows = sqlite.get_trend_aggregation("u1", "2026-04-19", "2026-04-19")
        assert len(rows) == 0

        # end_date = 2026-04-20 包含 4/19 的数据
        rows = sqlite.get_trend_aggregation("u1", "2026-04-19", "2026-04-20")
        assert len(rows) == 1
