"""B44: 增强 AI 晨报 — 学习连续天数 + 每日聚焦 + 模式洞察 测试"""
import pytest
from datetime import date, timedelta

from httpx import AsyncClient, ASGITransport


def _insert_entry(conn, entry_id, user_id, title, entry_type, status, created_at,
                  priority=None, planned_date=None):
    """辅助函数：插入条目到 SQLite"""
    conn.execute(
        "INSERT INTO entries (id, user_id, title, type, status, created_at, file_path, priority, planned_date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (entry_id, user_id, title, entry_type, status, created_at,
         f"notes/{entry_id}.md", priority, planned_date),
    )


@pytest.mark.asyncio
async def test_learning_streak_consecutive(client, test_user, storage):
    """连续 5 天有记录返回 streak=5"""
    today = date.today()
    conn = storage.sqlite._get_conn()
    for i in range(5):
        day = today - timedelta(days=i)
        _insert_entry(conn, f"streak-b44-{i}", test_user.id, f"Day {i}", "note", "complete", day.isoformat())
    conn.commit()

    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    assert resp.json()["learning_streak"] == 5


@pytest.mark.asyncio
async def test_learning_streak_broken(client, test_user, storage):
    """中断记录后 streak 从 1 重新计算"""
    today = date.today()
    conn = storage.sqlite._get_conn()
    for offset in [0, 3, 4]:
        day = today - timedelta(days=offset)
        _insert_entry(conn, f"broken-b44-{offset}", test_user.id, f"Day {offset}", "note", "complete", day.isoformat())
    conn.commit()

    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    assert resp.json()["learning_streak"] == 1


@pytest.mark.asyncio
async def test_learning_streak_no_records(client, test_user):
    """新用户无记录返回 streak=0"""
    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    assert resp.json()["learning_streak"] == 0


@pytest.mark.asyncio
async def test_daily_focus_overdue_template(client, test_user, storage):
    """LLM 不可用时 daily_focus 降级为逾期任务模板"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    conn = storage.sqlite._get_conn()
    _insert_entry(conn, "overdue-b44-1", test_user.id, "逾期任务", "task", "doing",
                  today.isoformat(), priority="high", planned_date=yesterday.isoformat())
    conn.commit()

    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_focus"] is not None
    assert "title" in data["daily_focus"]
    assert "description" in data["daily_focus"]
    assert data["daily_focus"]["target_entry_id"] == "overdue-b44-1"


@pytest.mark.asyncio
async def test_daily_focus_no_data(client, test_user):
    """无数据时 daily_focus 为 null"""
    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    assert resp.json()["daily_focus"] is None


@pytest.mark.asyncio
async def test_pattern_insights_inbox_heavy(client, test_user, storage):
    """灵感占比高时生成洞察"""
    today = date.today()
    conn = storage.sqlite._get_conn()
    for i in range(5):
        day = today - timedelta(days=i)
        _insert_entry(conn, f"inbox-b44-{i}", test_user.id, f"灵感 {i}", "inbox", "pending", day.isoformat())
    conn.commit()

    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["pattern_insights"], list)
    assert len(data["pattern_insights"]) <= 3
    has_inbox_insight = any("灵感" in i for i in data["pattern_insights"])
    assert has_inbox_insight


@pytest.mark.asyncio
async def test_pattern_insights_empty(client, test_user):
    """无数据时 pattern_insights 为空数组"""
    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    assert resp.json()["pattern_insights"] == []


@pytest.mark.asyncio
async def test_backward_compatibility(client, test_user):
    """新字段有默认值，不破坏旧客户端"""
    resp = await client.get("/review/morning-digest")
    assert resp.status_code == 200
    data = resp.json()
    # 旧字段仍在
    assert "date" in data
    assert "ai_suggestion" in data
    assert "todos" in data
    assert "overdue" in data
    assert "stale_inbox" in data
    assert "weekly_summary" in data
    # 新字段有默认值
    assert "learning_streak" in data
    assert data["learning_streak"] == 0
    assert "daily_focus" in data
    assert data["daily_focus"] is None
    assert "pattern_insights" in data
    assert data["pattern_insights"] == []
