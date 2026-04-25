"""B101: get_growth_curve SQL 聚合测试"""
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.infrastructure.storage.sqlite import SQLiteStorage
from app.models import Task, Category, TaskStatus, Priority
from app.services.review_service import ReviewService


# === SQLiteStorage.get_growth_curve_tag_stats 测试 ===


class TestGrowthCurveTagStatsSql:
    """测试 SQLiteStorage.get_growth_curve_tag_stats SQL 聚合"""

    def test_with_entries_returns_correct_stats(self, sqlite_storage):
        """有 entries 时 SQL 聚合返回正确的按周 tag 统计"""
        now = datetime.now()
        # 创建 2 个带 tag 的 entries，在当前周
        for i, tag in enumerate(["python", "rust"]):
            entry = Task(
                id=f"gc-test-{i}",
                title=f"成长曲线测试-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=[tag],
                created_at=now,
                updated_at=now,
                file_path=f"tasks/gc-test-{i}.md",
            )
            sqlite_storage.upsert_entry(entry)

        today = now.strftime("%Y-%m-%d")
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date=start, end_date=today
        )

        # 应该有 2 行，每行一个 tag
        assert len(result) == 2
        tag_names = {r["tag_name"] for r in result}
        assert "python" in tag_names
        assert "rust" in tag_names
        for r in result:
            assert r["entry_count"] == 1
            assert r["note_count"] == 0
            assert r["recent_count"] == 1  # 刚创建，在 30 天内

    def test_no_entries_returns_empty(self, sqlite_storage):
        """无 entries 时返回空结果"""
        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date="2020-01-01", end_date="2020-12-31"
        )
        assert result == []

    def test_week_boundary_grouping(self, sqlite_storage):
        """不同周的 entries 正确分组到不同 year_week"""
        now = datetime.now()
        # 当前周
        entry_this_week = Task(
            id="gc-week-this",
            title="本周条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["tag_a"],
            created_at=now,
            updated_at=now,
            file_path="tasks/gc-week-this.md",
        )
        sqlite_storage.upsert_entry(entry_this_week)

        # 4 周前
        four_weeks_ago = now - timedelta(weeks=4)
        entry_past = Task(
            id="gc-week-past",
            title="过去条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["tag_a"],
            created_at=four_weeks_ago,
            updated_at=four_weeks_ago,
            file_path="tasks/gc-week-past.md",
        )
        sqlite_storage.upsert_entry(entry_past)

        start = (now - timedelta(weeks=5)).strftime("%Y-%m-%d")
        today = now.strftime("%Y-%m-%d")

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date=start, end_date=today
        )

        # 两个条目在不同周，应该有 2 行
        assert len(result) == 2
        year_weeks = {r["year_week"] for r in result}
        assert len(year_weeks) == 2  # 两个不同的周

    def test_note_count_correct(self, sqlite_storage):
        """note 类型条目正确计数"""
        now = datetime.now()
        # 创建 note 类型
        entry = Task(
            id="gc-note",
            title="笔记条目",
            content="",
            category=Category.NOTE,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["ml"],
            created_at=now,
            updated_at=now,
            file_path="notes/gc-note.md",
        )
        sqlite_storage.upsert_entry(entry)

        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        today = now.strftime("%Y-%m-%d")

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date=start, end_date=today
        )

        assert len(result) == 1
        assert result[0]["note_count"] == 1
        assert result[0]["entry_count"] == 1

    def test_user_id_isolation(self, sqlite_storage):
        """user_id 隔离验证"""
        now = datetime.now()
        # 创建 user1 的条目（user_id 通过 upsert_entry 参数传入）
        entry = Task(
            id="gc-user1",
            title="用户1条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["secret"],
            created_at=now,
            updated_at=now,
            file_path="tasks/gc-user1.md",
        )
        sqlite_storage.upsert_entry(entry, user_id="user1")

        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        today = now.strftime("%Y-%m-%d")

        # 查询另一个用户，应该为空
        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="user2", start_date=start, end_date=today
        )
        assert result == []

        # 查询正确用户，应该有数据
        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="user1", start_date=start, end_date=today
        )
        assert len(result) == 1
        assert result[0]["tag_name"] == "secret"


# === ReviewService.get_growth_curve 测试 ===


@pytest.fixture
def mock_sqlite():
    return MagicMock()


@pytest.fixture
def service(mock_sqlite):
    return ReviewService(sqlite_storage=mock_sqlite)


class TestGrowthCurveReviewService:
    """测试 ReviewService.get_growth_curve 使用 SQL 聚合"""

    def test_with_entries_correct_mastery(self, service, mock_sqlite):
        """有 entries 时掌握度分布正确计算"""
        # 模拟 SQL 聚合返回
        # 当前周的 year_week 格式
        from datetime import date, timedelta

        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        year_week_key = current_week_start.strftime("%Y-%W")

        mock_sqlite.get_growth_curve_tag_stats.return_value = [
            {
                "year_week": year_week_key,
                "tag_name": "python",
                "entry_count": 10,
                "note_count": 5,
                "recent_count": 3,
            },
            {
                "year_week": year_week_key,
                "tag_name": "rust",
                "entry_count": 1,
                "note_count": 0,
                "recent_count": 0,
            },
        ]

        result = service.get_growth_curve(weeks=4, user_id="user1")

        assert len(result.points) == 4
        # 当前周（最后一项，因为是倒序）
        current_point = result.points[0]
        assert current_point.total_concepts == 2
        assert current_point.advanced_count >= 1  # python 应该是 advanced
        assert current_point.beginner_count >= 1  # rust 应该是 beginner

    def test_no_entries_empty_points(self, service, mock_sqlite):
        """无 entries 时所有周 total_concepts 为 0"""
        mock_sqlite.get_growth_curve_tag_stats.return_value = []

        result = service.get_growth_curve(weeks=4, user_id="user1")

        assert len(result.points) == 4
        for point in result.points:
            assert point.total_concepts == 0
            assert point.advanced_count == 0
            assert point.intermediate_count == 0
            assert point.beginner_count == 0

    def test_regression_no_list_entries(self, service, mock_sqlite):
        """回归：不再调用 list_entries"""
        mock_sqlite.get_growth_curve_tag_stats.return_value = []

        service.get_growth_curve(weeks=4, user_id="user1")

        mock_sqlite.list_entries.assert_not_called()

    def test_mastery_consistent_with_sql_stats(self, service, mock_sqlite):
        """掌握度计算结果与之前内存过滤一致"""
        from datetime import date, timedelta

        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        year_week_key = current_week_start.strftime("%Y-%W")

        # 3 entry_count, 1 recent → intermediate
        mock_sqlite.get_growth_curve_tag_stats.return_value = [
            {
                "year_week": year_week_key,
                "tag_name": "ml",
                "entry_count": 3,
                "note_count": 0,
                "recent_count": 1,
            },
        ]

        result = service.get_growth_curve(weeks=2, user_id="user1")

        current_point = result.points[0]
        assert current_point.intermediate_count == 1
        assert current_point.total_concepts == 1

    def test_user_id_passed_to_sql(self, service, mock_sqlite):
        """user_id 正确传递到 SQL 查询"""
        mock_sqlite.get_growth_curve_tag_stats.return_value = []

        service.get_growth_curve(weeks=2, user_id="special-user")

        call_args = mock_sqlite.get_growth_curve_tag_stats.call_args
        assert call_args[1]["user_id"] == "special-user"

    def test_weeks_count_correct(self, service, mock_sqlite):
        """返回的 points 数量等于 weeks 参数"""
        mock_sqlite.get_growth_curve_tag_stats.return_value = []

        result = service.get_growth_curve(weeks=8, user_id="user1")
        assert len(result.points) == 8

        result = service.get_growth_curve(weeks=2, user_id="user1")
        assert len(result.points) == 2

    def test_multi_week_data(self, service, mock_sqlite):
        """多周数据正确分布到对应周"""
        from datetime import date, timedelta

        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())
        week0_key = current_week_start.strftime("%Y-%W")
        week2_start = current_week_start - timedelta(weeks=2)
        week2_key = week2_start.strftime("%Y-%W")

        mock_sqlite.get_growth_curve_tag_stats.return_value = [
            {
                "year_week": week0_key,
                "tag_name": "tag_a",
                "entry_count": 5,
                "note_count": 0,
                "recent_count": 1,
            },
            {
                "year_week": week2_key,
                "tag_name": "tag_b",
                "entry_count": 2,
                "note_count": 1,
                "recent_count": 0,
            },
        ]

        result = service.get_growth_curve(weeks=4, user_id="user1")

        assert len(result.points) == 4
        # 当前周有 tag_a
        assert result.points[0].total_concepts == 1
        # 第 1 周无数据
        assert result.points[1].total_concepts == 0
        # 第 2 周有 tag_b
        assert result.points[2].total_concepts == 1
        # 第 3 周无数据
        assert result.points[3].total_concepts == 0


# === B101: ISO week 一致性 — 年边界测试 ===


class TestYearBoundaryConsistency:
    """B101: 验证 SQL %Y-%W 与 Python strftime('%Y-%W') 在年边界时一致"""

    def test_sql_python_week_key_dec30(self, sqlite_storage):
        """2024-12-30 (周一) 的 SQL year_week 与 Python strftime('%Y-%W') 一致"""
        # 2024-12-30 是周一，属于 2024 年第 53 周（%W 编号）
        dec30 = datetime(2024, 12, 30, 12, 0, 0)
        entry = Task(
            id="gc-dec30",
            title="年末条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["year_boundary"],
            created_at=dec30,
            updated_at=dec30,
            file_path="tasks/gc-dec30.md",
        )
        sqlite_storage.upsert_entry(entry)

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date="2024-12-23", end_date="2025-01-05"
        )

        assert len(result) == 1
        sql_year_week = result[0]["year_week"]
        # Python strftime('%Y-%W') for 2024-12-30 should be "2024-53"
        python_year_week = dec30.strftime("%Y-%W")
        assert sql_year_week == python_year_week, (
            f"SQL year_week={sql_year_week} != Python year_week={python_year_week}"
        )

    def test_sql_python_week_key_jan6(self, sqlite_storage):
        """2025-01-06 (周一) 的 SQL year_week 与 Python strftime('%Y-%W') 一致"""
        # 2025-01-06 是周一
        jan6 = datetime(2025, 1, 6, 12, 0, 0)
        entry = Task(
            id="gc-jan6",
            title="新年条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["year_boundary"],
            created_at=jan6,
            updated_at=jan6,
            file_path="tasks/gc-jan6.md",
        )
        sqlite_storage.upsert_entry(entry)

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date="2025-01-01", end_date="2025-01-12"
        )

        assert len(result) == 1
        sql_year_week = result[0]["year_week"]
        python_year_week = jan6.strftime("%Y-%W")
        assert sql_year_week == python_year_week, (
            f"SQL year_week={sql_year_week} != Python year_week={python_year_week}"
        )

    def test_year_boundary_two_weeks_different_year(self, sqlite_storage):
        """年边界附近的两周分别属于不同年的周编号"""
        # 2024-12-30 周一 → %W = 2024-53
        dec30 = datetime(2024, 12, 30, 12, 0, 0)
        entry1 = Task(
            id="gc-yb1",
            title="2024年末",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["dec"],
            created_at=dec30,
            updated_at=dec30,
            file_path="tasks/gc-yb1.md",
        )
        sqlite_storage.upsert_entry(entry1)

        # 2025-01-06 周一 → %W = 2025-01
        jan6 = datetime(2025, 1, 6, 12, 0, 0)
        entry2 = Task(
            id="gc-yb2",
            title="2025年初",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["jan"],
            created_at=jan6,
            updated_at=jan6,
            file_path="tasks/gc-yb2.md",
        )
        sqlite_storage.upsert_entry(entry2)

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date="2024-12-23", end_date="2025-01-12"
        )

        assert len(result) == 2
        year_weeks = {r["year_week"] for r in result}
        # 两个条目必须分到不同的周
        assert len(year_weeks) == 2
        # 验证 Python 侧也能正确匹配
        assert dec30.strftime("%Y-%W") in year_weeks
        assert jan6.strftime("%Y-%W") in year_weeks

    def test_review_service_year_boundary_week_label(self, service, mock_sqlite):
        """B101: ReviewService 在年边界时 week label 与 SQL year_week 正确映射为 ISO"""
        from unittest.mock import patch

        # 固定 today=2024-12-31 (周二)，current_week_start=2024-12-30 (周一)
        fixed_today = date(2024, 12, 31)

        # 2024-12-30 周一的 strftime('%Y-%W') = "2024-53"
        week_start = fixed_today - timedelta(days=fixed_today.weekday())
        year_week_key = week_start.strftime("%Y-%W")
        assert year_week_key == "2024-53"

        # ISO label: 2024-12-30 的 isocalendar() = (2025, 1, 1) → "2025-W01"
        expected_iso = f"{week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d}"
        assert expected_iso == "2025-W01"

        mock_sqlite.get_growth_curve_tag_stats.return_value = [
            {
                "year_week": year_week_key,
                "tag_name": "python",
                "entry_count": 5,
                "note_count": 0,
                "recent_count": 1,
            },
        ]

        with patch("app.services.review_service.date") as mock_date:
            mock_date.today.return_value = fixed_today
            result = service.get_growth_curve(weeks=4, user_id="user1")

        # 当前周 (index 0) 一定有数据
        current_point = result.points[0]
        assert current_point.total_concepts == 1
        # 验证 week label 是 ISO 格式而非 %Y-%W
        assert current_point.week == expected_iso, (
            f"week label={current_point.week} != expected ISO={expected_iso}"
        )


class TestCrossWeekAttribution:
    """B101: created_at/updated_at 跨周归属回归测试"""

    def test_entry_counted_in_both_created_and_updated_weeks(self, sqlite_storage):
        """条目 created_at 在周 A、updated_at 在周 B → 两周都包含该条目"""
        now = datetime.now()
        # 本周一和上周一
        this_monday = now - timedelta(days=now.weekday())
        last_monday = this_monday - timedelta(weeks=1)

        # 创建条目：created_at 在上周，updated_at 在本周
        entry = Task(
            id="cross-week-1",
            title="跨周条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["python"],
            created_at=last_monday + timedelta(hours=12),
            updated_at=this_monday + timedelta(hours=12),
            file_path="tasks/cross-week-1.md",
        )
        sqlite_storage.upsert_entry(entry)

        start = last_monday.strftime("%Y-%m-%d")
        end = this_monday.strftime("%Y-%m-%d")

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date=start, end_date=end
        )

        # 应该有 2 行：上周和本周各一行
        tag_rows = [r for r in result if r["tag_name"] == "python"]
        assert len(tag_rows) == 2, f"Expected 2 rows for cross-week, got {len(tag_rows)}"
        # 每行 entry_count = 1
        for row in tag_rows:
            assert row["entry_count"] == 1

    def test_same_week_no_double_count(self, sqlite_storage):
        """created_at 和 updated_at 在同一周 → 只计一次"""
        now = datetime.now()
        this_monday = now - timedelta(days=now.weekday())

        # 两个时间都在同一周内
        entry = Task(
            id="same-week-1",
            title="同周条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["python"],
            created_at=this_monday + timedelta(hours=1),
            updated_at=this_monday + timedelta(hours=48),
            file_path="tasks/same-week-1.md",
        )
        sqlite_storage.upsert_entry(entry)

        start = (this_monday - timedelta(days=1)).strftime("%Y-%m-%d")
        end = (this_monday + timedelta(days=7)).strftime("%Y-%m-%d")

        result = sqlite_storage.get_growth_curve_tag_stats(
            user_id="_default", start_date=start, end_date=end
        )

        python_rows = [r for r in result if r["tag_name"] == "python"]
        assert len(python_rows) == 1, f"Expected 1 row (same week dedup), got {len(python_rows)}"
        assert python_rows[0]["entry_count"] == 1

    def test_iso_week_label_format(self, service, mock_sqlite):
        """B101: week label 必须精确匹配 ISO 格式 — 使用固定时钟验证年边界映射"""
        from unittest.mock import patch

        # 固定 today=2025-01-08 (周三)，current_week_start=2025-01-06 (周一)
        fixed_today = date(2025, 1, 8)
        week_start = fixed_today - timedelta(days=fixed_today.weekday())
        year_week_key = week_start.strftime("%Y-%W")
        assert year_week_key == "2025-01"

        # ISO label: 2025-01-06 的 isocalendar() = (2025, 2, 1) → "2025-W02"
        expected_iso = f"{week_start.isocalendar()[0]}-W{week_start.isocalendar()[1]:02d}"

        mock_sqlite.get_growth_curve_tag_stats.return_value = [
            {
                "year_week": year_week_key,
                "tag_name": "python",
                "entry_count": 3,
                "note_count": 1,
                "recent_count": 2,
            },
        ]

        with patch("app.services.review_service.date") as mock_date:
            mock_date.today.return_value = fixed_today
            result = service.get_growth_curve(weeks=4, user_id="user1")

        # 当前周一定有匹配
        current_point = result.points[0]
        assert current_point.total_concepts == 1, "Current week should have data"
        # 精确断言 ISO label，不只验正则
        assert current_point.week == expected_iso, (
            f"week label={current_point.week} != expected ISO={expected_iso}"
        )
        # 同时验证格式不是 %Y-%W（即 "2025-01"）
        assert current_point.week != year_week_key, (
            f"week label should be ISO format, not %Y-%W: got {current_point.week}"
        )
