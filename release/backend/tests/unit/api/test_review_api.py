"""成长回顾 API 测试

测试覆盖:
- 日报 API
- 周报 API
- 月报 API
"""
from datetime import datetime, date, timedelta

import pytest
from httpx import AsyncClient

from app.models import Task, Category, TaskStatus, Priority


class TestReviewAPI:
    """回顾 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage):
        """每个测试前准备数据"""
        # 清空现有数据
        if storage.sqlite:
            storage.sqlite.clear_all()

        today = datetime.now()

        # 创建今天的任务
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
            storage.sqlite.upsert_entry(entry)

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
        storage.sqlite.upsert_entry(note)

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
        storage.sqlite.upsert_entry(entry_yesterday)

    async def test_get_daily_report(self, client: AsyncClient):
        """测试获取日报"""
        response = await client.get("/review/daily")
        assert response.status_code == 200

        data = response.json()
        assert "date" in data
        assert "task_stats" in data
        assert "note_stats" in data

        # 验证任务统计
        task_stats = data["task_stats"]
        assert task_stats["total"] >= 3  # 至少有3个今日任务
        assert task_stats["completed"] >= 1  # 至少有1个已完成

        # 验证笔记统计
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

        # 验证每日分解数据
        daily_breakdown = data["daily_breakdown"]
        assert len(daily_breakdown) == 7  # 7天

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

        # 验证周分解数据
        weekly_breakdown = data["weekly_breakdown"]
        assert len(weekly_breakdown) >= 4  # 至少4周
        assert len(weekly_breakdown) <= 5  # 最多5周

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

        # 验证统计字段
        assert "total" in task_stats
        assert "completed" in task_stats
        assert "doing" in task_stats
        assert "wait_start" in task_stats
        assert "completion_rate" in task_stats

        # 验证完成率计算
        if task_stats["total"] > 0:
            expected_rate = round(task_stats["completed"] / task_stats["total"] * 100, 1)
            assert task_stats["completion_rate"] == expected_rate

    async def test_completed_tasks_list(self, client: AsyncClient):
        """测试已完成任务列表"""
        response = await client.get("/review/daily")
        data = response.json()

        completed_tasks = data.get("completed_tasks", [])
        assert isinstance(completed_tasks, list)

        # 如果有已完成任务，验证字段
        if completed_tasks:
            task = completed_tasks[0]
            assert "id" in task
            assert "title" in task
            assert "status" in task
            assert task["status"] == "complete"
