"""成长回顾 API 测试

测试覆盖:
- 日报 API
- 周报 API
- 月报 API
- 趋势 API
"""
from datetime import datetime, date, timedelta

import pytest
from httpx import AsyncClient

from app.models import Task, Category, TaskStatus, Priority


def _make_test_user_id(client) -> str:
    """从 client 认证头中提取测试用户 ID"""
    # conftest.py 的 client fixture 创建了 testuser，其 ID 通过 token 关联
    # 我们需要通过 deps 获取用户 ID
    from app.routers import deps
    user_storage = deps._user_storage
    user = user_storage.get_by_username("testuser")
    return user.id if user else "test-user"


class TestReviewAPI:
    """回顾 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()

        # 创建今天的任务（带 user_id）
        for i in range(3):
            entry = Task(
                id=f"review-today-{i}",
                title=f"今日任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["review-test"],
                created_at=today,
                updated_at=today,
                file_path=f"tasks/review-today-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 创建今天的笔记
        note = Task(
            id="review-note-today",
            title="今日笔记",
            content="学习内容测试",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["review-test"],
            created_at=today,
            updated_at=today,
            file_path="notes/review-note-today.md",
        )
        storage.sqlite.upsert_entry(note, user_id=user_id)

        # 创建昨天的任务
        yesterday = today - timedelta(days=1)
        entry_yesterday = Task(
            id="review-yesterday-1",
            title="昨日任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["review-test"],
            created_at=yesterday,
            updated_at=yesterday,
            file_path="tasks/review-yesterday-1.md",
        )
        storage.sqlite.upsert_entry(entry_yesterday, user_id=user_id)

    async def test_get_daily_report(self, client: AsyncClient):
        """测试获取日报"""
        response = await client.get("/review/daily")
        assert response.status_code == 200

        data = response.json()
        assert "date" in data
        assert "task_stats" in data
        assert "note_stats" in data

        task_stats = data["task_stats"]
        assert task_stats["total"] >= 3
        assert task_stats["completed"] >= 1

        note_stats = data["note_stats"]
        assert note_stats["total"] >= 1

    async def test_get_daily_report_with_date(self, client: AsyncClient):
        """测试指定日期的日报"""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        response = await client.get(f"/review/daily?date={yesterday}")
        assert response.status_code == 200

        data = response.json()
        assert data["date"] == yesterday

    async def test_get_daily_report_invalid_date(self, client: AsyncClient):
        """测试无效日期格式"""
        response = await client.get("/review/daily?date=invalid-date")
        assert response.status_code == 400

    async def test_get_weekly_report(self, client: AsyncClient):
        """测试获取周报"""
        response = await client.get("/review/weekly")
        assert response.status_code == 200

        data = response.json()
        assert "start_date" in data
        assert "end_date" in data
        assert "task_stats" in data
        assert "note_stats" in data
        assert "daily_breakdown" in data

        daily_breakdown = data["daily_breakdown"]
        assert len(daily_breakdown) == 7

        for day in daily_breakdown:
            assert "date" in day
            assert "total" in day
            assert "completed" in day

    async def test_get_monthly_report(self, client: AsyncClient):
        """测试获取月报"""
        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        assert "month" in data
        assert "task_stats" in data
        assert "note_stats" in data
        assert "weekly_breakdown" in data

        weekly_breakdown = data["weekly_breakdown"]
        assert len(weekly_breakdown) >= 4
        assert len(weekly_breakdown) <= 5

        for week in weekly_breakdown:
            assert "week" in week
            assert "start_date" in week
            assert "end_date" in week
            assert "total" in week
            assert "completed" in week

    async def test_monthly_report_with_month_param(self, client: AsyncClient):
        """测试指定月份的月报"""
        this_month = date.today().strftime("%Y-%m")
        response = await client.get(f"/review/monthly?month={this_month}")
        assert response.status_code == 200

        data = response.json()
        assert data["month"] == this_month

    async def test_monthly_report_invalid_month(self, client: AsyncClient):
        """测试无效月份格式"""
        response = await client.get("/review/monthly?month=invalid")
        assert response.status_code == 400

    async def test_task_stats_calculation(self, client: AsyncClient):
        """测试任务统计计算"""
        response = await client.get("/review/daily")
        data = response.json()

        task_stats = data["task_stats"]

        assert "total" in task_stats
        assert "completed" in task_stats
        assert "doing" in task_stats
        assert "wait_start" in task_stats
        assert "completion_rate" in task_stats

        if task_stats["total"] > 0:
            expected_rate = round(task_stats["completed"] / task_stats["total"] * 100, 1)
            assert task_stats["completion_rate"] == expected_rate

    async def test_completed_tasks_list(self, client: AsyncClient):
        """测试已完成任务列表"""
        response = await client.get("/review/daily")
        data = response.json()

        completed_tasks = data.get("completed_tasks", [])
        assert isinstance(completed_tasks, list)

        if completed_tasks:
            task = completed_tasks[0]
            assert "id" in task
            assert "title" in task
            assert "status" in task
            assert task["status"] == "complete"


class TestTrendAPI:
    """趋势 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """准备测试数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()

        # 创建近 3 天的任务
        for day_offset in range(3):
            day = today - timedelta(days=day_offset)
            for i in range(2):
                entry = Task(
                    id=f"trend-day{day_offset}-{i}",
                    title=f"趋势任务-day{day_offset}-{i}",
                    content="",
                    category=Category.TASK,
                    status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                    priority=Priority.MEDIUM,
                    tags=["trend-test"],
                    created_at=day,
                    updated_at=day,
                    file_path=f"tasks/trend-day{day_offset}-{i}.md",
                )
                storage.sqlite.upsert_entry(entry, user_id=user_id)

            note = Task(
                id=f"trend-note-day{day_offset}",
                title=f"趋势笔记-day{day_offset}",
                content="",
                category=Category.NOTE,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["trend-test"],
                created_at=day,
                updated_at=day,
                file_path=f"notes/trend-note-day{day_offset}.md",
            )
            storage.sqlite.upsert_entry(note, user_id=user_id)

    async def test_trend_daily_default(self, client: AsyncClient):
        """测试默认 daily 趋势"""
        response = await client.get("/review/trend")
        assert response.status_code == 200

        data = response.json()
        assert "periods" in data
        assert isinstance(data["periods"], list)
        assert len(data["periods"]) == 7  # 默认 7 天

        # 检查结构
        period = data["periods"][0]
        assert "date" in period
        assert "total" in period
        assert "completed" in period
        assert "completion_rate" in period
        assert "notes_count" in period

    async def test_trend_daily_custom_days(self, client: AsyncClient):
        """测试自定义天数的 daily 趋势"""
        response = await client.get("/review/trend?period=daily&days=3")
        assert response.status_code == 200

        data = response.json()
        assert len(data["periods"]) == 3

        # 验证有数据的日期
        today_periods = [p for p in data["periods"] if p["total"] > 0]
        assert len(today_periods) >= 1

    async def test_trend_weekly(self, client: AsyncClient):
        """测试 weekly 趋势"""
        response = await client.get("/review/trend?period=weekly&weeks=4")
        assert response.status_code == 200

        data = response.json()
        assert len(data["periods"]) == 4

    async def test_trend_empty_data(self, storage, client: AsyncClient):
        """测试空数据返回空数组"""
        storage.sqlite.clear_all()

        response = await client.get("/review/trend")
        assert response.status_code == 200

        data = response.json()
        for period in data["periods"]:
            assert period["total"] == 0
            assert period["completed"] == 0
            assert period["completion_rate"] == 0.0
            assert period["notes_count"] == 0

    async def test_trend_invalid_period(self, client: AsyncClient):
        """测试无效 period 参数"""
        response = await client.get("/review/trend?period=monthly")
        assert response.status_code == 422

    async def test_trend_no_auth(self, storage):
        """测试无 token 返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.routers import deps

        deps.storage = storage
        deps.reset_all_services()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/review/trend")
            assert response.status_code == 401

    async def test_trend_user_isolation(self, storage, client: AsyncClient):
        """测试用户隔离"""
        # 创建另一个用户的数据
        other_user_id = "other-user-isolation-test"
        entry = Task(
            id="trend-other-user-1",
            title="其他用户任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/trend-other-user-1.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=other_user_id)

        # 当前用户不应看到 other_user 的数据
        response = await client.get("/review/trend?period=daily&days=1")
        assert response.status_code == 200

        # 确保不包含 other_user 的任务
        for period in response.json()["periods"]:
            # 如果今天有数据，验证是当前用户的
            if period["total"] > 0:
                assert period["total"] <= 2  # 当前用户只有 2 个今日任务

    async def test_trend_days_boundary(self, client: AsyncClient):
        """测试 days 参数边界"""
        response = await client.get("/review/trend?period=daily&days=1")
        assert response.status_code == 200
        assert len(response.json()["periods"]) == 1

    async def test_trend_weeks_boundary(self, client: AsyncClient):
        """测试 weeks 参数边界"""
        response = await client.get("/review/trend?period=weekly&weeks=1")
        assert response.status_code == 200
        assert len(response.json()["periods"]) == 1
