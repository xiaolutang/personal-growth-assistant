"""B52 趋势数据多维扩展 + 周环比对比 测试

测试覆盖:
- TrendPeriod 返回 task_count/inbox_count 字段（笔记数用已有的 notes_count）
- 各分类计数与实际条目数一致
- WeeklyReport vs_last_week delta 正确
- MonthlyReport vs_last_month delta 正确
- 空用户返回零值和 null delta
- 按用户隔离验证
"""
from datetime import datetime, date, timedelta

import pytest
from httpx import AsyncClient

from app.models import Task, Category, TaskStatus, Priority


def _make_test_user_id(client) -> str:
    """从 client 认证头中提取测试用户 ID"""
    from app.routers import deps
    user_storage = deps._user_storage
    user = user_storage.get_by_username("testuser")
    return user.id if user else "test-user"


class TestTrendCategoryCounts:
    """趋势 API 分类计数测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据：创建 task/note/inbox 各类条目"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()

        # 创建今天的 2 个 task
        for i in range(2):
            entry = Task(
                id=f"b52-task-{i}",
                title=f"任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["b52-test"],
                created_at=today,
                updated_at=today,
                file_path=f"tasks/b52-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 创建今天的 1 个 note
        note = Task(
            id="b52-note-0",
            title="笔记",
            content="",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["b52-test"],
            created_at=today,
            updated_at=today,
            file_path="notes/b52-note-0.md",
        )
        storage.sqlite.upsert_entry(note, user_id=user_id)

        # 创建今天的 3 个 inbox
        for i in range(3):
            inbox = Task(
                id=f"b52-inbox-{i}",
                title=f"灵感-{i}",
                content="",
                category=Category.INBOX,
                status=TaskStatus.WAIT_START,
                priority=Priority.MEDIUM,
                tags=["b52-test"],
                created_at=today,
                updated_at=today,
                file_path=f"inbox/b52-inbox-{i}.md",
            )
            storage.sqlite.upsert_entry(inbox, user_id=user_id)

    async def test_trend_has_category_counts(self, client: AsyncClient):
        """趋势 API 返回 task_count/inbox_count 字段（笔记数用已有的 notes_count）"""
        response = await client.get("/review/trend?period=daily&days=1")
        assert response.status_code == 200

        data = response.json()
        period = data["periods"][0]

        assert "task_count" in period
        assert "inbox_count" in period

    async def test_trend_category_counts_correct(self, client: AsyncClient):
        """各分类计数与实际条目数一致"""
        response = await client.get("/review/trend?period=daily&days=1")
        assert response.status_code == 200

        data = response.json()
        period = data["periods"][0]

        # 今天有 2 个 task, 1 个 note, 3 个 inbox
        assert period["task_count"] == 2
        assert period["notes_count"] == 1
        assert period["inbox_count"] == 3

    async def test_trend_weekly_category_counts(self, client: AsyncClient):
        """weekly 模式也返回分类计数"""
        response = await client.get("/review/trend?period=weekly&weeks=1")
        assert response.status_code == 200

        data = response.json()
        period = data["periods"][0]

        assert period["task_count"] == 2
        assert period["notes_count"] == 1
        assert period["inbox_count"] == 3

    async def test_trend_empty_data_category_counts_zero(self, storage, client: AsyncClient):
        """空数据时各分类计数字段为 0"""
        storage.sqlite.clear_all()

        response = await client.get("/review/trend?period=daily&days=1")
        assert response.status_code == 200

        data = response.json()
        period = data["periods"][0]

        assert period["task_count"] == 0
        assert period["inbox_count"] == 0

    async def test_trend_user_isolation_category_counts(self, storage, client: AsyncClient):
        """用户隔离：其他用户的条目不影响当前用户的分类计数"""
        other_user_id = "b52-other-user"
        today = datetime.now()

        # 其他用户创建条目
        for cat, prefix in [(Category.TASK, "task"), (Category.NOTE, "note"), (Category.INBOX, "inbox")]:
            entry = Task(
                id=f"b52-other-{prefix}-0",
                title=f"其他用户{prefix}",
                content="",
                category=cat,
                status=TaskStatus.DOING if cat != Category.INBOX else TaskStatus.WAIT_START,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=today,
                updated_at=today,
                file_path=f"{prefix}s/b52-other-{prefix}-0.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=other_user_id)

        # 当前用户查询趋势
        response = await client.get("/review/trend?period=daily&days=1")
        assert response.status_code == 200

        data = response.json()
        period = data["periods"][0]

        # 当前用户的数据不变
        assert period["task_count"] == 2
        assert period["notes_count"] == 1
        assert period["inbox_count"] == 3


class TestWeeklyVsLastWeek:
    """周报 vs_last_week 环比测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """创建本周和上周的数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = date.today()
        # 本周一
        week_start = today - timedelta(days=today.weekday())

        # 本周任务：3 个，其中 2 个完成
        for i in range(3):
            entry = Task(
                id=f"b52-w-task-{i}",
                title=f"本周任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i < 2 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["b52-weekly"],
                created_at=datetime.combine(week_start + timedelta(days=i), datetime.min.time()),
                updated_at=datetime.combine(week_start + timedelta(days=i), datetime.min.time()),
                file_path=f"tasks/b52-w-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 上周任务：5 个，其中 1 个完成
        last_week_start = week_start - timedelta(weeks=1)
        for i in range(5):
            entry = Task(
                id=f"b52-lw-task-{i}",
                title=f"上周任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["b52-weekly"],
                created_at=datetime.combine(last_week_start + timedelta(days=i), datetime.min.time()),
                updated_at=datetime.combine(last_week_start + timedelta(days=i), datetime.min.time()),
                file_path=f"tasks/b52-lw-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

    async def test_weekly_has_vs_last_week(self, client: AsyncClient):
        """周报返回 vs_last_week 字段"""
        response = await client.get("/review/weekly")
        assert response.status_code == 200

        data = response.json()
        assert "vs_last_week" in data
        assert data["vs_last_week"] is not None

    async def test_weekly_vs_last_week_delta_correct(self, client: AsyncClient):
        """周报 vs_last_week delta 正确"""
        response = await client.get("/review/weekly")
        assert response.status_code == 200

        data = response.json()
        vs = data["vs_last_week"]

        assert "delta_completion_rate" in vs
        assert "delta_total" in vs

        # 本周 task_stats.total 和 vs_last_week.delta_total 应该有合理的值
        # delta_total = current_total - last_total
        assert isinstance(vs["delta_total"], int)
        assert isinstance(vs["delta_completion_rate"], float)

        # 精确验证 delta 值
        # delta 应为负数（本周 3 任务 vs 上周 5 任务）
        assert vs["delta_total"] == -2
        # 本周完成率高于上周 → delta > 0
        assert vs["delta_completion_rate"] > 0

    async def test_weekly_empty_vs_last_week_null(self, storage, client: AsyncClient):
        """空数据时 vs_last_week delta 为 null"""
        storage.sqlite.clear_all()

        response = await client.get("/review/weekly")
        assert response.status_code == 200

        data = response.json()
        assert data["vs_last_week"] is not None
        assert data["vs_last_week"]["delta_completion_rate"] is None
        assert data["vs_last_week"]["delta_total"] is None


class TestMonthlyVsLastMonth:
    """月报 vs_last_month 环比测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """创建本月和上月的数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = date.today()
        month_start = date(today.year, today.month, 1)

        # 本月任务：4 个，其中 3 个完成
        for i in range(4):
            day = min(i + 1, 28)
            entry = Task(
                id=f"b52-m-task-{i}",
                title=f"本月任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i < 3 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["b52-monthly"],
                created_at=datetime.combine(month_start + timedelta(days=day), datetime.min.time()),
                updated_at=datetime.combine(month_start + timedelta(days=day), datetime.min.time()),
                file_path=f"tasks/b52-m-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 上月任务：2 个，其中 1 个完成
        if month_start.month == 1:
            last_month_start = date(month_start.year - 1, 12, 1)
        else:
            last_month_start = date(month_start.year, month_start.month - 1, 1)

        for i in range(2):
            day = min(i + 1, 28)
            entry = Task(
                id=f"b52-lm-task-{i}",
                title=f"上月任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["b52-monthly"],
                created_at=datetime.combine(last_month_start + timedelta(days=day), datetime.min.time()),
                updated_at=datetime.combine(last_month_start + timedelta(days=day), datetime.min.time()),
                file_path=f"tasks/b52-lm-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

    async def test_monthly_has_vs_last_month(self, client: AsyncClient):
        """月报返回 vs_last_month 字段"""
        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        assert "vs_last_month" in data
        assert data["vs_last_month"] is not None

    async def test_monthly_vs_last_month_delta_correct(self, client: AsyncClient):
        """月报 vs_last_month delta 正确"""
        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        vs = data["vs_last_month"]

        assert "delta_completion_rate" in vs
        assert "delta_total" in vs

        # 验证 delta 类型正确
        assert isinstance(vs["delta_total"], int)
        assert isinstance(vs["delta_completion_rate"], float)

        # 精确验证 delta 值
        # 本月 4 任务，上月 2 任务 → delta_total = 2
        assert vs["delta_total"] == 2
        # delta_completion_rate 应为浮点数
        assert isinstance(vs["delta_completion_rate"], float)

        # delta_total = current - last，验证上月至少有 2 个任务
        current_total = data["task_stats"]["total"]
        last_total = current_total - vs["delta_total"]
        assert last_total >= 2

    async def test_monthly_empty_vs_last_month_null(self, storage, client: AsyncClient):
        """空数据时 vs_last_month delta 为 null"""
        storage.sqlite.clear_all()

        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        assert data["vs_last_month"] is not None
        assert data["vs_last_month"]["delta_completion_rate"] is None
        assert data["vs_last_month"]["delta_total"] is None


class TestReportUserIsolation:
    """用户隔离验证"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """创建当前用户和其他用户的数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()
        today_date = date.today()
        week_start = today_date - timedelta(days=today_date.weekday())

        # 当前用户：本周 1 个完成 task
        entry = Task(
            id="b52-iso-task-0",
            title="当前用户任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["b52-iso"],
            created_at=today,
            updated_at=today,
            file_path="tasks/b52-iso-task-0.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 其他用户：上周 10 个完成 task
        other_user_id = "b52-isolation-other"
        last_week_start = week_start - timedelta(weeks=1)
        for i in range(10):
            entry = Task(
                id=f"b52-iso-other-{i}",
                title=f"其他用户任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=datetime.combine(last_week_start + timedelta(days=i % 7), datetime.min.time()),
                updated_at=datetime.combine(last_week_start + timedelta(days=i % 7), datetime.min.time()),
                file_path=f"tasks/b52-iso-other-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=other_user_id)

    async def test_weekly_user_isolation(self, client: AsyncClient):
        """周报 vs_last_week 不受其他用户数据影响"""
        response = await client.get("/review/weekly")
        assert response.status_code == 200

        data = response.json()

        # 当前用户本周只有 1 个 task
        assert data["task_stats"]["total"] == 1
        assert data["task_stats"]["completed"] == 1

        # 上周数据不应包含其他用户的 10 个 task
        vs = data["vs_last_week"]
        assert vs["delta_total"] == 1  # 1 - 0 = 1 (当前用户上周无数据)

    async def test_monthly_user_isolation(self, client: AsyncClient):
        """月报 vs_last_month 不受其他用户数据影响"""
        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()

        # 当前用户本月只有 1 个 task
        assert data["task_stats"]["total"] == 1
        assert data["task_stats"]["completed"] == 1

        # 上月数据不应包含其他用户的数据
        vs = data["vs_last_month"]
        assert vs["delta_total"] == 1  # 1 - 0 = 1
