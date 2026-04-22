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


class TestReviewKnowledgeAPI:
    """知识热力图 + 成长曲线 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()

        # 创建带标签的任务（多个概念）
        for i in range(3):
            entry = Task(
                id=f"heatmap-task-{i}",
                title=f"热力图任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["python", "fastapi"] if i < 2 else ["python"],
                created_at=today,
                updated_at=today,
                file_path=f"tasks/heatmap-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 创建带标签的笔记
        note = Task(
            id="heatmap-note-1",
            title="热力图笔记",
            content="学习 python 和 fastapi",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["python", "fastapi", "学习笔记"],
            created_at=today,
            updated_at=today,
            file_path="notes/heatmap-note-1.md",
        )
        storage.sqlite.upsert_entry(note, user_id=user_id)

    async def test_knowledge_heatmap_with_data(self, client: AsyncClient):
        """测试知识热力图正常返回"""
        response = await client.get("/review/knowledge-heatmap")
        assert response.status_code == 200

        data = response.json()
        assert "items" in data
        items = data["items"]
        assert len(items) > 0

        # 验证 item 结构
        for item in items:
            assert "concept" in item
            assert "mastery" in item
            assert "entry_count" in item
            assert item["mastery"] in ("new", "beginner", "intermediate", "advanced")

        # python 标签应该最多条目
        python_items = [i for i in items if i["concept"] == "python"]
        assert len(python_items) == 1
        assert python_items[0]["entry_count"] >= 3

    async def test_knowledge_heatmap_empty(self, storage, client: AsyncClient):
        """测试空数据返回空列表"""
        storage.sqlite.clear_all()

        response = await client.get("/review/knowledge-heatmap")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []

    async def test_growth_curve_with_data(self, client: AsyncClient):
        """测试成长曲线正常返回"""
        response = await client.get("/review/growth-curve?weeks=4")
        assert response.status_code == 200

        data = response.json()
        assert "points" in data
        points = data["points"]
        assert len(points) == 4

        for point in points:
            assert "week" in point
            assert "total_concepts" in point
            assert "advanced_count" in point
            assert "intermediate_count" in point
            assert "beginner_count" in point
            # week 格式应为 YYYY-WXX
            assert "W" in point["week"]

    async def test_growth_curve_default_weeks(self, client: AsyncClient):
        """测试成长曲线默认 8 周"""
        response = await client.get("/review/growth-curve")
        assert response.status_code == 200

        data = response.json()
        assert len(data["points"]) == 8

    async def test_growth_curve_user_isolation(self, storage, client: AsyncClient):
        """测试成长曲线用户隔离"""
        other_user_id = "other-growth-user"
        entry = Task(
            id="growth-other-1",
            title="其他用户任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["unique-other-tag"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/growth-other-1.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=other_user_id)

        response = await client.get("/review/growth-curve?weeks=1")
        assert response.status_code == 200

        # 本周数据不应包含 other_user 的 tag
        for point in response.json()["points"]:
            # 当前用户的 total_concepts 不应因 other_user 而改变
            assert "unique-other-tag" not in str(point)


class TestReviewAISummary:
    """AI 总结测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()

        for i in range(2):
            entry = Task(
                id=f"ai-summary-task-{i}",
                title=f"AI总结任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["ai-test"],
                created_at=today,
                updated_at=today,
                file_path=f"tasks/ai-summary-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

    async def test_daily_report_with_ai_summary(self, storage, client: AsyncClient):
        """测试 LLM 可用时日报包含 AI 总结"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        # 设置 Mock LLM caller
        mock_llm = MockCaller(response="今天完成了1个任务，继续加油！建议保持当前节奏。")
        deps._review_service = None  # 重置以触发重新创建
        # 直接给 review_service 设置 llm_caller
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/daily")
        assert response.status_code == 200

        data = response.json()
        assert "ai_summary" in data
        assert data["ai_summary"] is not None
        assert len(data["ai_summary"]) > 0

        # 清理
        review_svc.set_llm_caller(None)

    async def test_daily_report_without_llm(self, storage, client: AsyncClient):
        """测试 LLM 不可用时 ai_summary 为 None"""
        from app.routers import deps

        # 确保 review_service 没有 llm_caller
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(None)

        response = await client.get("/review/daily")
        assert response.status_code == 200

        data = response.json()
        assert data["ai_summary"] is None

    async def test_weekly_report_with_ai_summary(self, storage, client: AsyncClient):
        """测试周报包含 AI 总结"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        mock_llm = MockCaller(response="本周完成率50%，表现不错。可以适当增加任务量。")
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/weekly")
        assert response.status_code == 200

        data = response.json()
        assert data["ai_summary"] is not None
        assert len(data["ai_summary"]) > 0

        # 清理
        review_svc.set_llm_caller(None)

    async def test_ai_summary_llm_failure_graceful(self, storage, client: AsyncClient):
        """测试 LLM 失败时降级"""
        from app.routers import deps
        from unittest.mock import AsyncMock

        # 创建会抛出异常的 mock caller
        mock_llm = AsyncMock()
        mock_llm.call = AsyncMock(side_effect=Exception("LLM 服务不可用"))

        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/daily")
        assert response.status_code == 200

        data = response.json()
        # LLM 失败时 ai_summary 应为空字符串 ""
        assert data["ai_summary"] == ""

        # 清理
        review_svc.set_llm_caller(None)

    async def test_monthly_report_with_ai_summary(self, storage, client: AsyncClient):
        """测试月报包含 AI 总结"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        mock_llm = MockCaller(response="本月完成任务数显著提升，学习节奏稳定。建议下月增加项目实践。")
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        assert data["ai_summary"] is not None
        assert len(data["ai_summary"]) > 0

        # 清理
        review_svc.set_llm_caller(None)

    async def test_monthly_report_without_llm(self, storage, client: AsyncClient):
        """测试 LLM 不可用时月报 ai_summary 为 None"""
        from app.routers import deps

        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(None)

        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        assert data["ai_summary"] is None

    async def test_monthly_report_llm_failure_graceful(self, storage, client: AsyncClient):
        """测试 LLM 失败时月报其他字段正常"""
        from app.routers import deps
        from unittest.mock import AsyncMock

        mock_llm = AsyncMock()
        mock_llm.call = AsyncMock(side_effect=Exception("LLM 服务不可用"))

        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        # LLM 失败时 ai_summary 为空字符串
        assert data["ai_summary"] == ""
        # 其他字段正常返回
        assert "month" in data
        assert "task_stats" in data
        assert "note_stats" in data
        assert "weekly_breakdown" in data

        # 清理
        review_svc.set_llm_caller(None)

    async def test_monthly_report_llm_timeout(self, storage, client: AsyncClient):
        """测试 LLM 超时时月报 ai_summary 为空"""
        from app.routers import deps
        import asyncio
        from unittest.mock import AsyncMock

        async def slow_call(messages):
            await asyncio.sleep(20)  # 超过 10 秒超时
            return "不应返回"

        mock_llm = AsyncMock()
        mock_llm.call = slow_call

        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        assert data["ai_summary"] == ""

        # 清理
        review_svc.set_llm_caller(None)

    async def test_monthly_report_empty_data_ai_summary(self, storage, client: AsyncClient):
        """测试无数据月份的 AI 总结"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        storage.sqlite.clear_all()

        mock_llm = MockCaller(response="本月暂无记录，建议开始记录学习历程。")
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/monthly")
        assert response.status_code == 200

        data = response.json()
        assert data["ai_summary"] is not None
        assert data["task_stats"]["total"] == 0

        # 清理
        review_svc.set_llm_caller(None)


class TestMorningDigestAPI:
    """AI 晨报 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()
        today_date = date.today()

        # 今日待办（waitStart + planned_date=today）
        for i in range(3):
            entry = Task(
                id=f"digest-todo-{i}",
                title=f"晨报待办-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.WAIT_START if i == 0 else TaskStatus.DOING,
                priority=Priority.HIGH if i == 0 else Priority.MEDIUM,
                tags=["digest-test"],
                planned_date=today,
                created_at=today,
                updated_at=today,
                file_path=f"tasks/digest-todo-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 逾期任务（planned_date=昨天，status=doing）
        overdue_entry = Task(
            id="digest-overdue-1",
            title="逾期任务-1",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=["digest-test"],
            planned_date=today - timedelta(days=1),
            created_at=today - timedelta(days=2),
            updated_at=today - timedelta(days=1),
            file_path="tasks/digest-overdue-1.md",
        )
        storage.sqlite.upsert_entry(overdue_entry, user_id=user_id)

        # 已完成的任务（不应出现在 todos/overdue）
        complete_entry = Task(
            id="digest-complete-1",
            title="已完成任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=["digest-test"],
            planned_date=today,
            created_at=today,
            updated_at=today,
            file_path="tasks/digest-complete-1.md",
        )
        storage.sqlite.upsert_entry(complete_entry, user_id=user_id)

        # 未跟进灵感（>3天）
        old_inbox = Task(
            id="digest-inbox-old",
            title="旧灵感-未跟进",
            content="",
            category=Category.INBOX,
            status=TaskStatus.WAIT_START,
            priority=Priority.MEDIUM,
            tags=["old-idea"],
            created_at=today - timedelta(days=5),
            updated_at=today - timedelta(days=5),
            file_path="inbox/digest-inbox-old.md",
        )
        storage.sqlite.upsert_entry(old_inbox, user_id=user_id)

        # 最近的灵感（不应出现在 stale）
        new_inbox = Task(
            id="digest-inbox-new",
            title="新灵感",
            content="",
            category=Category.INBOX,
            status=TaskStatus.WAIT_START,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=today,
            updated_at=today,
            file_path="inbox/digest-inbox-new.md",
        )
        storage.sqlite.upsert_entry(new_inbox, user_id=user_id)

    async def test_morning_digest_basic(self, client: AsyncClient):
        """测试晨报基本结构"""
        response = await client.get("/review/morning-digest")
        assert response.status_code == 200

        data = response.json()
        assert "date" in data
        assert "ai_suggestion" in data
        assert "todos" in data
        assert "overdue" in data
        assert "stale_inbox" in data
        assert "weekly_summary" in data

        assert data["date"] == date.today().isoformat()
        assert isinstance(data["ai_suggestion"], str)
        assert len(data["ai_suggestion"]) > 0

    async def test_morning_digest_todos(self, client: AsyncClient):
        """测试晨报待办列表"""
        response = await client.get("/review/morning-digest")
        data = response.json()

        todos = data["todos"]
        assert len(todos) == 3

        # 第一个应为高优先级
        assert todos[0]["priority"] == "high"

        for todo in todos:
            assert "id" in todo
            assert "title" in todo
            assert "priority" in todo

    async def test_morning_digest_overdue(self, client: AsyncClient):
        """测试晨报逾期列表"""
        response = await client.get("/review/morning-digest")
        data = response.json()

        overdue = data["overdue"]
        assert len(overdue) == 1
        assert overdue[0]["title"] == "逾期任务-1"

    async def test_morning_digest_stale_inbox(self, client: AsyncClient):
        """测试晨报未跟进灵感"""
        response = await client.get("/review/morning-digest")
        data = response.json()

        stale = data["stale_inbox"]
        assert len(stale) == 1
        assert stale[0]["title"] == "旧灵感-未跟进"

    async def test_morning_digest_weekly_summary(self, client: AsyncClient):
        """测试晨报本周摘要"""
        response = await client.get("/review/morning-digest")
        data = response.json()

        summary = data["weekly_summary"]
        assert "new_concepts" in summary
        assert "entries_count" in summary
        assert summary["entries_count"] > 0

    async def test_morning_digest_no_auth(self, storage):
        """测试无 token 返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.routers import deps

        deps.storage = storage
        deps.reset_all_services()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/review/morning-digest")
            assert response.status_code == 401

    async def test_morning_digest_user_isolation(self, storage, client: AsyncClient):
        """测试用户隔离"""
        other_user_id = "other-digest-user"

        other_entry = Task(
            id="digest-other-overdue",
            title="其他用户逾期任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=[],
            planned_date=datetime.now() - timedelta(days=2),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/digest-other-overdue.md",
        )
        storage.sqlite.upsert_entry(other_entry, user_id=other_user_id)

        response = await client.get("/review/morning-digest")
        assert response.status_code == 200

        data = response.json()
        overdue_ids = [o["id"] for o in data["overdue"]]
        assert "digest-other-overdue" not in overdue_ids

    async def test_morning_digest_empty_data(self, storage, client: AsyncClient):
        """测试空数据场景"""
        storage.sqlite.clear_all()

        response = await client.get("/review/morning-digest")
        assert response.status_code == 200

        data = response.json()
        assert data["todos"] == []
        assert data["overdue"] == []
        assert data["stale_inbox"] == []
        assert data["weekly_summary"]["entries_count"] == 0
        assert "没有待办任务" in data["ai_suggestion"]

    async def test_morning_digest_llm_degradation(self, storage, client: AsyncClient):
        """测试 LLM 不可用时降级为模板文本"""
        from app.routers import deps

        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(None)

        response = await client.get("/review/morning-digest")
        assert response.status_code == 200

        data = response.json()
        assert len(data["ai_suggestion"]) > 0

    async def test_morning_digest_with_llm(self, storage, client: AsyncClient):
        """测试 LLM 生成 AI 建议"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        mock_llm = MockCaller(response="今天有3个任务待完成，建议先做晨报待办-0...")
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/morning-digest")
        assert response.status_code == 200

        data = response.json()
        assert "晨报待办" in data["ai_suggestion"]

        # 清理
        review_svc.set_llm_caller(None)


class TestInsightsAPI:
    """S15 AI 深度洞察 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        today = datetime.now()

        # 创建本周任务（足够多以触发行为模式分析）
        for i in range(5):
            entry = Task(
                id=f"insight-task-{i}",
                title=f"洞察任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i < 3 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["python", "fastapi"] if i < 3 else ["python"],
                created_at=today,
                updated_at=today,
                file_path=f"tasks/insight-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 创建笔记
        note = Task(
            id="insight-note-1",
            title="洞察笔记",
            content="学习 python",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["python", "学习笔记"],
            created_at=today,
            updated_at=today,
            file_path="notes/insight-note-1.md",
        )
        storage.sqlite.upsert_entry(note, user_id=user_id)

        # 创建上周期数据（用于对比）
        prev_week = today - timedelta(days=10)
        for i in range(3):
            entry = Task(
                id=f"insight-prev-task-{i}",
                title=f"上周任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["python"],
                created_at=prev_week,
                updated_at=prev_week,
                file_path=f"tasks/insight-prev-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

    async def test_insights_weekly_normal(self, client: AsyncClient):
        """测试正常 weekly 洞察返回"""
        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200

        data = response.json()
        assert data["period"] == "weekly"
        assert "start_date" in data
        assert "end_date" in data
        assert "insights" in data
        assert "source" in data

        insights = data["insights"]
        assert "behavior_patterns" in insights
        assert "growth_suggestions" in insights
        assert "capability_changes" in insights

        # 验证结构
        for bp in insights["behavior_patterns"]:
            assert "pattern" in bp
            assert "frequency" in bp
            assert "trend" in bp
            assert bp["trend"] in ("improving", "stable", "declining")

        for gs in insights["growth_suggestions"]:
            assert "suggestion" in gs
            assert "priority" in gs
            assert "related_area" in gs
            assert gs["priority"] in ("high", "medium", "low")

        for cc in insights["capability_changes"]:
            assert "capability" in cc
            assert "previous_level" in cc
            assert "current_level" in cc
            assert "change" in cc

    async def test_insights_monthly_normal(self, client: AsyncClient):
        """测试 monthly 洞察返回"""
        response = await client.get("/review/insights?period=monthly")
        assert response.status_code == 200

        data = response.json()
        assert data["period"] == "monthly"
        assert "start_date" in data
        assert "end_date" in data

    async def test_insights_empty_data(self, storage, client: AsyncClient):
        """测试空数据时返回降级洞察"""
        storage.sqlite.clear_all()

        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200

        data = response.json()
        assert data["source"] == "rule_based"
        insights = data["insights"]
        assert isinstance(insights["behavior_patterns"], list)
        assert isinstance(insights["growth_suggestions"], list)
        assert isinstance(insights["capability_changes"], list)

    async def test_insights_invalid_period(self, client: AsyncClient):
        """测试非法 period 参数返回 422"""
        response = await client.get("/review/insights?period=daily")
        assert response.status_code == 422

        response = await client.get("/review/insights?period=yearly")
        assert response.status_code == 422

    async def test_insights_missing_period(self, client: AsyncClient):
        """测试缺少 period 参数"""
        response = await client.get("/review/insights")
        # FastAPI 对必填 Query 参数缺失返回 422
        assert response.status_code == 422

    async def test_insights_llm_degradation(self, storage, client: AsyncClient):
        """测试 LLM 不可用时走规则分析"""
        from app.routers import deps
        from unittest.mock import AsyncMock

        # 创建会抛出异常的 mock caller
        mock_llm = AsyncMock()
        mock_llm.call = AsyncMock(side_effect=Exception("LLM 服务不可用"))

        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200

        data = response.json()
        assert data["source"] == "rule_based"
        assert len(data["insights"]["behavior_patterns"]) >= 0

        # 清理
        review_svc.set_llm_caller(None)

    async def test_insights_llm_success(self, storage, client: AsyncClient):
        """测试 LLM 可用时返回 llm 来源洞察"""
        import json
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        llm_response = json.dumps({
            "behavior_patterns": [
                {"pattern": "本周集中学习 python", "frequency": 5, "trend": "improving"}
            ],
            "growth_suggestions": [
                {"suggestion": "继续深入学习 fastapi", "priority": "high", "related_area": "技术"}
            ],
            "capability_changes": [
                {"capability": "python", "previous_level": 0.4, "current_level": 0.8, "change": 0.4}
            ],
        })
        mock_llm = MockCaller(response=llm_response)
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200

        data = response.json()
        assert data["source"] == "llm"
        assert len(data["insights"]["behavior_patterns"]) == 1
        assert data["insights"]["behavior_patterns"][0]["pattern"] == "本周集中学习 python"
        assert len(data["insights"]["growth_suggestions"]) == 1
        assert len(data["insights"]["capability_changes"]) == 1

        # 清理
        review_svc.set_llm_caller(None)

    async def test_insights_user_isolation(self, storage, client: AsyncClient):
        """测试不同 user_id 返回不同洞察"""
        other_user_id = "other-insight-user"
        today = datetime.now()

        # 创建大量其他用户的任务（会触发行为模式）
        for i in range(10):
            entry = Task(
                id=f"insight-other-{i}",
                title=f"其他用户洞察任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE,
                priority=Priority.HIGH,
                tags=["unique-other-tag-xyz"],
                created_at=today,
                updated_at=today,
                file_path=f"tasks/insight-other-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=other_user_id)

        # 当前用户请求洞察
        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200

        data = response.json()
        # 确保能力变化中不包含其他用户的标签
        for cc in data["insights"]["capability_changes"]:
            assert cc["capability"] != "unique-other-tag-xyz"

    async def test_insights_no_auth(self, storage):
        """测试无 token 返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.routers import deps

        deps.storage = storage
        deps.reset_all_services()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/review/insights?period=weekly")
            assert response.status_code == 401

    async def test_insights_llm_timeout(self, storage, client: AsyncClient):
        """测试 LLM 超时时降级为规则分析"""
        from app.routers import deps
        from unittest.mock import AsyncMock
        import asyncio

        mock_llm = AsyncMock()
        mock_llm.call = AsyncMock(side_effect=asyncio.TimeoutError())

        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "rule_based"

        review_svc.set_llm_caller(None)

    async def test_insights_llm_invalid_json(self, storage, client: AsyncClient):
        """测试 LLM 返回无效 JSON 时降级"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        mock_llm = MockCaller(response="这不是 JSON 内容 <<>>")
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "rule_based"

        review_svc.set_llm_caller(None)

    async def test_insights_llm_overlong_arrays(self, storage, client: AsyncClient):
        """测试 LLM 返回超长数组时截断为 3"""
        import json
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        # 生成超过 3 项的数组
        overlong_patterns = [
            {"pattern": f"模式{i}", "frequency": i, "trend": "stable"}
            for i in range(10)
        ]
        overlong_suggestions = [
            {"suggestion": f"建议{i}", "priority": "medium", "related_area": "测试"}
            for i in range(10)
        ]
        overlong_changes = [
            {"capability": f"能力{i}", "previous_level": 0.1, "current_level": 0.2, "change": 0.1}
            for i in range(10)
        ]

        llm_response = json.dumps({
            "behavior_patterns": overlong_patterns,
            "growth_suggestions": overlong_suggestions,
            "capability_changes": overlong_changes,
        })
        mock_llm = MockCaller(response=llm_response)
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200

        data = response.json()
        assert data["source"] == "llm"
        assert len(data["insights"]["behavior_patterns"]) <= 3
        assert len(data["insights"]["growth_suggestions"]) <= 3
        assert len(data["insights"]["capability_changes"]) <= 3

        review_svc.set_llm_caller(None)

    async def test_insights_llm_invalid_schema_fields(self, storage, client: AsyncClient):
        """测试 LLM 返回 JSON 有效但 schema 字段无效时降级"""
        import json
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        # trend 使用无效值 "super" — Literal 校验会失败
        llm_response = json.dumps({
            "behavior_patterns": [
                {"pattern": "测试", "frequency": 1, "trend": "super"}
            ],
            "growth_suggestions": [],
            "capability_changes": [],
        })
        mock_llm = MockCaller(response=llm_response)
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200
        data = response.json()
        # 无效 trend 导致 Pydantic 校验失败，降级为 rule_based
        assert data["source"] == "rule_based"

        review_svc.set_llm_caller(None)

    async def test_insights_user_isolation_all_sections(self, storage, client: AsyncClient):
        """测试用户隔离覆盖所有洞察维度"""
        other_user_id = "isolation-check-user"
        today = datetime.now()

        # 其他用户创建大量特定标签条目
        for i in range(10):
            entry = Task(
                id=f"iso-other-{i}",
                title=f"隔离用户任务-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.COMPLETE,
                priority=Priority.HIGH,
                tags=["iso-exclusive-tag"],
                created_at=today,
                updated_at=today,
                file_path=f"tasks/iso-other-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=other_user_id)

        # 当前用户请求洞察
        response = await client.get("/review/insights?period=weekly")
        assert response.status_code == 200

        data = response.json()
        # 检查所有维度不包含其他用户数据
        for bp in data["insights"]["behavior_patterns"]:
            assert "iso-exclusive-tag" not in bp.get("pattern", "")
        for gs in data["insights"]["growth_suggestions"]:
            assert "iso-exclusive-tag" not in gs.get("suggestion", "")
        for cc in data["insights"]["capability_changes"]:
            assert cc["capability"] != "iso-exclusive-tag"

    async def test_insights_monthly_degradation(self, storage, client: AsyncClient):
        """测试 monthly 降级时内容语义正确（不包含'本周'文案）"""
        from app.routers import deps
        from unittest.mock import AsyncMock

        # 强制走降级
        mock_llm = AsyncMock()
        mock_llm.call = AsyncMock(side_effect=Exception("LLM down"))
        review_svc = deps.get_review_service()
        review_svc.set_llm_caller(mock_llm)

        response = await client.get("/review/insights?period=monthly")
        assert response.status_code == 200

        data = response.json()
        assert data["source"] == "rule_based"
        # 降级内容不应包含"本周"文案
        for bp in data["insights"]["behavior_patterns"]:
            assert "本周" not in bp.get("pattern", "")
        for gs in data["insights"]["growth_suggestions"]:
            assert "本周" not in gs.get("suggestion", "")

        review_svc.set_llm_caller(None)
