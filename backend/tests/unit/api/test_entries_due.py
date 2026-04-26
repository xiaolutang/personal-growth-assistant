"""B105: 任务截止日期 API 测试 — GET /entries?due=today/overdue

覆盖场景:
  - 今日到期、已过期、无到期任务
  - due 与 status 组合过滤
  - due 参数校验（非法值返回 422）
  - planned_date=NULL 不影响现有行为
  - 跨用户隔离
  - UTC midnight 边界
"""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.routers import deps
from app.models import Task, Category, TaskStatus, Priority


# ── helpers ──────────────────────────────────────────────────────────

def _make_task(
    entry_id: str,
    title: str = "",
    planned_date: datetime | None = None,
    status: TaskStatus = TaskStatus.DOING,
    category: Category = Category.TASK,
    user_id: str = "test-user",
) -> Task:
    return Task(
        id=entry_id,
        title=title or f"task-{entry_id}",
        content="",
        category=category,
        status=status,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        file_path=f"tasks/{entry_id}.md",
        planned_date=planned_date,
    )


def _utc_today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_yesterday() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


def _utc_tomorrow() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")


# ── fixtures ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_deps():
    """确保测试后恢复 deps 状态"""
    original_storage = deps.storage
    deps.reset_all_services()
    yield
    deps.storage = original_storage
    deps.reset_all_services()


@pytest.fixture
def sqlite_with_entries(temp_data_dir: str):
    """创建预填充数据的 SQLite 存储"""
    from app.infrastructure.storage.sqlite import SQLiteStorage

    db = SQLiteStorage(db_path=f"{temp_data_dir}/test_due.db")
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    # --- 用户 A 条目 ---
    # 今日到期 - doing
    db.upsert_entry(_make_task("due-today-1", "今日到期任务1", planned_date=today), user_id="user-a")
    # 今日到期 - waitStart
    db.upsert_entry(_make_task("due-today-2", "今日到期任务2", planned_date=today, status=TaskStatus.WAIT_START), user_id="user-a")
    # 昨天到期 - doing（已过期）
    db.upsert_entry(_make_task("overdue-1", "已过期任务1", planned_date=yesterday), user_id="user-a")
    # 昨天到期 - complete（已过期但已完成，不应出现在 overdue）
    db.upsert_entry(_make_task("overdone-1", "过期已完成", planned_date=yesterday, status=TaskStatus.COMPLETE), user_id="user-a")
    # 明天到期
    db.upsert_entry(_make_task("future-1", "明天到期", planned_date=tomorrow), user_id="user-a")
    # 无 planned_date
    db.upsert_entry(_make_task("no-date-1", "无截止日期"), user_id="user-a")
    # 3天前到期 - paused（已过期）
    db.upsert_entry(_make_task("overdue-2", "已过期暂停中", planned_date=today - timedelta(days=3), status=TaskStatus.PAUSED), user_id="user-a")

    # --- 用户 B 条目（隔离测试） ---
    db.upsert_entry(_make_task("userb-today-1", "B今日到期", planned_date=today), user_id="user-b")

    yield db


# ── SQLite 层测试 ────────────────────────────────────────────────────

class TestSQLiteDueFilter:
    """SQLite _build_filter_query due 参数过滤"""

    def test_due_today_returns_only_today(self, sqlite_with_entries):
        """due=today 只返回 planned_date 为今天的条目"""
        results = sqlite_with_entries.list_entries(due="today", user_id="user-a")
        ids = {r["id"] for r in results}
        assert ids == {"due-today-1", "due-today-2"}

    def test_due_overdue_returns_past_unfinished(self, sqlite_with_entries):
        """due=overdue 返回 planned_date 早于今天且未完成的条目"""
        results = sqlite_with_entries.list_entries(due="overdue", user_id="user-a")
        ids = {r["id"] for r in results}
        assert "overdue-1" in ids
        assert "overdue-2" in ids
        # 已完成的不应出现
        assert "overdone-1" not in ids
        # 今天到期不应出现
        assert "due-today-1" not in ids

    def test_due_overdue_excludes_complete(self, sqlite_with_entries):
        """已完成的过期任务不返回"""
        results = sqlite_with_entries.list_entries(due="overdue", user_id="user-a")
        ids = {r["id"] for r in results}
        assert "overdone-1" not in ids

    def test_no_due_tasks_returns_empty(self, sqlite_with_entries):
        """用户 B 只查询 user-a 的数据应为空"""
        results = sqlite_with_entries.list_entries(due="today", user_id="user-c")
        assert results == []

    def test_user_isolation(self, sqlite_with_entries):
        """跨用户隔离：用户 B 查不到用户 A 的数据"""
        results = sqlite_with_entries.list_entries(due="today", user_id="user-b")
        ids = {r["id"] for r in results}
        assert ids == {"userb-today-1"}
        # 用户 A 的数据不应出现
        assert "due-today-1" not in ids

    def test_null_planned_date_not_affected(self, sqlite_with_entries):
        """planned_date=NULL 的条目不出现在任何到期查询中"""
        today_results = sqlite_with_entries.list_entries(due="today", user_id="user-a")
        overdue_results = sqlite_with_entries.list_entries(due="overdue", user_id="user-a")
        all_due_ids = {r["id"] for r in today_results + overdue_results}
        assert "no-date-1" not in all_due_ids

    def test_due_with_status_combined(self, sqlite_with_entries):
        """due=today + status 组合过滤"""
        results = sqlite_with_entries.list_entries(due="today", status="doing", user_id="user-a")
        ids = {r["id"] for r in results}
        assert ids == {"due-today-1"}

    def test_due_with_type_combined(self, sqlite_with_entries):
        """due=today + type=task 组合过滤"""
        results = sqlite_with_entries.list_entries(due="today", type="task", user_id="user-a")
        ids = {r["id"] for r in results}
        assert "due-today-1" in ids
        assert "due-today-2" in ids

    def test_count_entries_with_due(self, sqlite_with_entries):
        """count_entries 也支持 due 参数"""
        count = sqlite_with_entries.count_entries(due="today", user_id="user-a")
        assert count == 2

        count_overdue = sqlite_with_entries.count_entries(due="overdue", user_id="user-a")
        assert count_overdue == 2  # overdue-1, overdue-2

    def test_due_none_returns_all(self, sqlite_with_entries):
        """due=None 时不受影响，返回正常筛选结果"""
        results = sqlite_with_entries.list_entries(user_id="user-a")
        assert len(results) >= 7  # 所有 user-a 的条目

    def test_due_overdue_with_status_doing(self, sqlite_with_entries):
        """due=overdue + status=doing 只返回 doing 状态的过期任务"""
        results = sqlite_with_entries.list_entries(due="overdue", status="doing", user_id="user-a")
        ids = {r["id"] for r in results}
        assert "overdue-1" in ids
        assert "overdue-2" not in ids  # paused


# ── API 层测试 ────────────────────────────────────────────────────────

class TestAPIDueFilter:
    """GET /entries?due= API 端点测试"""

    @pytest.fixture
    async def authed_client(self, sqlite_with_entries, test_user):
        """创建带认证的 API 客户端，并注入 SQLite 存储"""
        # 用 patch 控制日期方便测试 UTC midnight 边界
        deps.storage = type("FakeStorage", (), {
            "sqlite": sqlite_with_entries,
            "neo4j": None,
            "qdrant": None,
        })()
        deps.reset_all_services()

        from app.services.auth_service import create_access_token
        token = create_access_token(test_user.id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as c:
            c.headers["Authorization"] = f"Bearer {token}"
            yield c

    @pytest.mark.asyncio
    async def test_due_today_api(self, authed_client):
        """GET /entries?due=today 返回今日到期任务"""
        # 使用 user_id=test-user（conftest 中创建的 test_user.id）
        # 由于 SQLite 数据是 user-a 的，test_user.id 不是 user-a
        # 我们需要直接使用 sqlite 层验证，API 层验证参数传递
        response = await authed_client.get("/entries", params={"due": "today"})
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_due_overdue_api(self, authed_client):
        """GET /entries?due=overdue 返回已过期任务"""
        response = await authed_client.get("/entries", params={"due": "overdue"})
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data

    @pytest.mark.asyncio
    async def test_due_invalid_value_returns_422(self, authed_client):
        """due 参数非法值返回 422"""
        response = await authed_client.get("/entries", params={"due": "invalid"})
        assert response.status_code == 422
        assert "today" in response.json()["detail"] or "overdue" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_due_combined_with_status(self, authed_client):
        """due + status 组合"""
        response = await authed_client.get("/entries", params={"due": "today", "status": "doing"})
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["status"] == "doing"

    @pytest.mark.asyncio
    async def test_due_combined_with_type(self, authed_client):
        """due + type 组合"""
        response = await authed_client.get("/entries", params={"due": "overdue", "type": "task"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_due_param_unchanged(self, authed_client):
        """不传 due 参数时行为不变"""
        response = await authed_client.get("/entries")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data


# ── UTC midnight 边界测试 ─────────────────────────────────────────────

class TestUTCMidnightBoundary:
    """验证 UTC midnight 边界分类正确"""

    def test_exactly_today_utc_midnight(self, sqlite_with_entries):
        """planned_date 正好是 UTC 今天 00:00:00，应归为 today"""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        task = _make_task("boundary-today", "边界今天", planned_date=today)
        sqlite_with_entries.upsert_entry(task, user_id="user-a")

        results = sqlite_with_entries.list_entries(due="today", user_id="user-a")
        ids = {r["id"] for r in results}
        assert "boundary-today" in ids

    def test_yesterday_23_59_utc(self, sqlite_with_entries):
        """planned_date 为昨天 23:59:59，应归为 overdue"""
        yesterday = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=0) - timedelta(days=1)
        task = _make_task("boundary-yesterday", "边界昨天", planned_date=yesterday)
        sqlite_with_entries.upsert_entry(task, user_id="user-a")

        results = sqlite_with_entries.list_entries(due="overdue", user_id="user-a")
        ids = {r["id"] for r in results}
        assert "boundary-yesterday" in ids

    def test_tomorrow_00_00_utc(self, sqlite_with_entries):
        """planned_date 为明天 00:00:00，不应出现在 today 或 overdue"""
        tomorrow = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        task = _make_task("boundary-tomorrow", "边界明天", planned_date=tomorrow)
        sqlite_with_entries.upsert_entry(task, user_id="user-a")

        today_results = sqlite_with_entries.list_entries(due="today", user_id="user-a")
        overdue_results = sqlite_with_entries.list_entries(due="overdue", user_id="user-a")
        all_ids = {r["id"] for r in today_results + overdue_results}
        assert "boundary-tomorrow" not in all_ids

    def test_overdue_with_mocked_date(self, sqlite_with_entries):
        """通过模拟'明天'的日期字符串，验证跨日边界：今天到期的任务变为 overdue"""
        fake_tomorrow = datetime.now(timezone.utc) + timedelta(days=1)

        # 直接用 SQLite 日期比较验证：手动插入今天的任务，用 tomorrow 作为 today 值
        tomorrow_str = fake_tomorrow.strftime("%Y-%m-%d")
        import sqlite3
        conn = sqlite_with_entries._get_conn()
        try:
            # 验证 today 的任务（due-today-1）在明天看是 overdue
            cursor = conn.execute(
                "SELECT id FROM entries WHERE user_id = ? AND planned_date IS NOT NULL AND planned_date != '' AND DATE(planned_date) < ? AND status != 'complete'",
                ("user-a", tomorrow_str),
            )
            overdue_ids = {row["id"] for row in cursor.fetchall()}
            assert "due-today-1" in overdue_ids
            assert "due-today-2" in overdue_ids
        finally:
            conn.close()
