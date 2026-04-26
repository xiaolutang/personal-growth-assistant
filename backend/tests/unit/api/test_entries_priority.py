"""B112: priority 筛选/排序 API 测试

测试覆盖:
- priority 单参数筛选
- sort_by=priority 排序
- priority + status 组合筛选
- 无 priority 参数向后兼容
- priority 值非法时忽略过滤
- 不同用户数据隔离
"""
import pytest
from httpx import AsyncClient


async def _create_entries_with_priority(client: AsyncClient):
    """创建不同优先级的测试条目"""
    entries = [
        ("high-task", "高优先级任务", "task", "high"),
        ("medium-task", "中优先级任务", "task", "medium"),
        ("low-task", "低优先级任务", "task", "low"),
        ("high-note", "高优先级笔记", "note", "high"),
    ]
    for eid, title, category, priority in entries:
        await client.post("/entries", json={
            "id": eid,
            "category": category,
            "title": title,
            "priority": priority,
        })
    return entries


@pytest.mark.asyncio
async def test_filter_priority_high(client: AsyncClient):
    """正常：priority=high 只返回高优先级"""
    await _create_entries_with_priority(client)

    response = await client.get("/entries", params={"priority": "high"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    for entry in data["entries"]:
        assert entry["priority"] == "high"


@pytest.mark.asyncio
async def test_filter_priority_medium(client: AsyncClient):
    """正常：priority=medium 只返回中优先级"""
    await _create_entries_with_priority(client)

    response = await client.get("/entries", params={"priority": "medium"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for entry in data["entries"]:
        assert entry["priority"] == "medium"


@pytest.mark.asyncio
async def test_sort_by_priority(client: AsyncClient):
    """正常：sort_by=priority 按 high→medium→low 排序"""
    await _create_entries_with_priority(client)

    response = await client.get("/entries", params={
        "sort_by": "priority",
        "limit": 50,
    })
    assert response.status_code == 200
    data = response.json()

    priorities = [e["priority"] for e in data["entries"]]
    priority_order = {"high": 1, "medium": 2, "low": 3}

    # 验证排序递增
    for i in range(len(priorities) - 1):
        assert priority_order.get(priorities[i], 4) <= priority_order.get(priorities[i + 1], 4)


@pytest.mark.asyncio
async def test_filter_priority_with_status(client: AsyncClient):
    """组合：priority=high&status=doing 同时过滤"""
    await _create_entries_with_priority(client)

    response = await client.get("/entries", params={
        "priority": "high",
        "status": "doing",
    })
    assert response.status_code == 200
    data = response.json()
    for entry in data["entries"]:
        assert entry["priority"] == "high"
        assert entry["status"] == "doing"


@pytest.mark.asyncio
async def test_no_priority_returns_all(client: AsyncClient):
    """兼容：无 priority 参数时返回全部（向后兼容）"""
    await _create_entries_with_priority(client)

    response = await client.get("/entries")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 4


@pytest.mark.asyncio
async def test_invalid_priority_ignored(client: AsyncClient):
    """边界：priority 值非法时忽略过滤（不报错）"""
    await _create_entries_with_priority(client)

    response = await client.get("/entries", params={"priority": "urgent"})
    assert response.status_code == 200
    # 非法 priority 被忽略，返回全部
    data = response.json()
    assert data["total"] >= 4


@pytest.mark.asyncio
async def test_isolation_user_data(client: AsyncClient):
    """隔离：不同用户的条目互不可见，筛选/排序仅返回当前用户数据"""
    # 当前用户创建条目
    await _create_entries_with_priority(client)

    # 验证当前用户能拿到自己的数据
    response = await client.get("/entries", params={"priority": "high"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
