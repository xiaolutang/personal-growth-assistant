"""时间筛选功能测试

测试覆盖:
- SQLite 时间范围筛选
- API 时间参数传递
"""
from datetime import datetime, timedelta

import pytest

from app.models import Task, Category, TaskStatus, Priority


class TestDateFilter:
    """时间筛选测试"""

    def test_filter_by_start_date(self, sqlite_storage):
        """测试按开始日期筛选"""
        # 创建不同日期的条目
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        # 今天的任务
        entry_today = Task(
            id="date-today",
            title="今天的任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=today,
            updated_at=today,
            file_path="tasks/date-today.md",
        )
        sqlite_storage.upsert_entry(entry_today)

        # 昨天的任务
        entry_yesterday = Task(
            id="date-yesterday",
            title="昨天的任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=yesterday,
            updated_at=yesterday,
            file_path="tasks/date-yesterday.md",
        )
        sqlite_storage.upsert_entry(entry_yesterday)

        # 一周前的任务
        entry_week_ago = Task(
            id="date-week-ago",
            title="一周前的任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=week_ago,
            updated_at=week_ago,
            file_path="tasks/date-week-ago.md",
        )
        sqlite_storage.upsert_entry(entry_week_ago)

        # 筛选：从昨天开始
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        results = sqlite_storage.list_entries(
            type="task",
            start_date=yesterday_str,
            limit=100,
        )

        # 应该包含昨天和今天的任务，不包含一周前的
        ids = [r["id"] for r in results]
        assert "date-today" in ids
        assert "date-yesterday" in ids
        assert "date-week-ago" not in ids

    def test_filter_by_end_date(self, sqlite_storage):
        """测试按结束日期筛选"""
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # 创建不同日期的任务
        for dt, id_suffix in [(yesterday, "yesterday"), (today, "today"), (tomorrow, "tomorrow")]:
            entry = Task(
                id=f"enddate-{id_suffix}",
                title=f"任务-{id_suffix}",
                content="",
                category=Category.TASK,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=dt,
                updated_at=dt,
                file_path=f"tasks/enddate-{id_suffix}.md",
            )
            sqlite_storage.upsert_entry(entry)

        # 筛选：到今天为止
        today_str = today.strftime("%Y-%m-%d")
        results = sqlite_storage.list_entries(
            type="task",
            end_date=today_str,
            limit=100,
        )

        ids = [r["id"] for r in results]
        assert "enddate-yesterday" in ids
        assert "enddate-today" in ids
        assert "enddate-tomorrow" not in ids

    def test_filter_by_date_range(self, sqlite_storage):
        """测试按日期范围筛选"""
        # 清空现有数据
        sqlite_storage.clear_all()

        # 创建一周内每天的任务
        today = datetime.now()
        for i in range(7):
            dt = today - timedelta(days=i)
            entry = Task(
                id=f"range-day-{i}",
                title=f"任务-{i}天前",
                content="",
                category=Category.TASK,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=dt,
                updated_at=dt,
                file_path=f"tasks/range-day-{i}.md",
            )
            sqlite_storage.upsert_entry(entry)

        # 筛选最近3天
        start_str = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")

        results = sqlite_storage.list_entries(
            type="task",
            start_date=start_str,
            end_date=end_str,
            limit=100,
        )

        # 应该只有3个任务
        assert len(results) == 3

    def test_count_with_date_filter(self, sqlite_storage):
        """测试带日期筛选的统计"""
        sqlite_storage.clear_all()

        today = datetime.now()
        week_ago = today - timedelta(days=7)

        # 创建不同日期的任务
        for i, dt in enumerate([today, today - timedelta(days=1), week_ago]):
            entry = Task(
                id=f"count-date-{i}",
                title=f"统计任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=dt,
                updated_at=dt,
                file_path=f"tasks/count-date-{i}.md",
            )
            sqlite_storage.upsert_entry(entry)

        # 统计最近3天的任务数
        start_str = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        count = sqlite_storage.count_entries(
            type="task",
            start_date=start_str,
        )

        assert count == 2

    def test_filter_combined_with_status(self, sqlite_storage):
        """测试日期+状态组合筛选"""
        sqlite_storage.clear_all()

        today = datetime.now()
        yesterday = today - timedelta(days=1)

        # 创建不同日期和状态的任务
        entries = [
            ("combined-1", today, TaskStatus.COMPLETE),
            ("combined-2", today, TaskStatus.DOING),
            ("combined-3", yesterday, TaskStatus.COMPLETE),
        ]

        for id_suffix, dt, status in entries:
            entry = Task(
                id=id_suffix,
                title=f"组合测试-{id_suffix}",
                content="",
                category=Category.TASK,
                status=status,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=dt,
                updated_at=dt,
                file_path=f"tasks/{id_suffix}.md",
            )
            sqlite_storage.upsert_entry(entry)

        # 筛选：今天 + 已完成
        today_str = today.strftime("%Y-%m-%d")
        results = sqlite_storage.list_entries(
            type="task",
            status="complete",
            start_date=today_str,
            end_date=today_str,
            limit=100,
        )

        assert len(results) == 1
        assert results[0]["id"] == "combined-1"
