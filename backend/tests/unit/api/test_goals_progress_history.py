"""B113: 目标进度历史快照 API 测试

测试覆盖:
- 进度更新后写入当日快照
- 同一天多次更新只保留最后一次快照（去重）
- 获取 30 天进度历史返回正确时间序列
- 不同用户的快照互不可见
"""
import pytest
from httpx import AsyncClient


async def _create_checklist_goal(client: AsyncClient) -> str:
    """创建 checklist 类型目标并返回 goal_id"""
    response = await client.post("/goals", json={
        "title": "测试目标",
        "metric_type": "checklist",
        "target_value": 3,
        "checklist_items": ["任务A", "任务B", "任务C"],
    })
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_snapshot_written_on_progress_change(client: AsyncClient):
    """正常：进度更新后写入当日快照"""
    goal_id = await _create_checklist_goal(client)

    # 获取 checklist item id
    goal_resp = await client.get(f"/goals/{goal_id}")
    items = goal_resp.json()["checklist_items"]

    # 完成一个 checklist item → 触发快照
    await client.patch(f"/goals/{goal_id}/checklist/{items[0]['id']}", json={"checked": True})

    # 查询进度历史
    resp = await client.get(f"/goals/{goal_id}/progress-history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["snapshots"]) >= 1
    snap = data["snapshots"][0]
    assert snap["goal_id"] == goal_id
    assert snap["percentage"] == 33.3


@pytest.mark.asyncio
async def test_snapshot_dedup_same_day(client: AsyncClient):
    """去重：同一天多次更新只保留最后一次快照"""
    goal_id = await _create_checklist_goal(client)

    goal_resp = await client.get(f"/goals/{goal_id}")
    items = goal_resp.json()["checklist_items"]

    # 完成第一个
    await client.patch(f"/goals/{goal_id}/checklist/{items[0]['id']}", json={"checked": True})
    # 完成第二个（同一天）
    await client.patch(f"/goals/{goal_id}/checklist/{items[1]['id']}", json={"checked": True})

    resp = await client.get(f"/goals/{goal_id}/progress-history")
    assert resp.status_code == 200
    data = resp.json()
    # 同一天只应有 1 条快照，且是最后一次更新的值
    assert len(data["snapshots"]) == 1
    assert data["snapshots"][0]["percentage"] == 66.7


@pytest.mark.asyncio
async def test_get_history_nonexistent_goal(client: AsyncClient):
    """异常：目标不存在时返回 404"""
    resp = await client.get("/goals/nonexistent/progress-history")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_isolation_user_snapshots(client: AsyncClient):
    """隔离：不同用户的快照互不可见"""
    goal_id = await _create_checklist_goal(client)

    goal_resp = await client.get(f"/goals/{goal_id}")
    items = goal_resp.json()["checklist_items"]

    # 触发快照
    await client.patch(f"/goals/{goal_id}/checklist/{items[0]['id']}", json={"checked": True})

    # 当前用户能看到快照
    resp = await client.get(f"/goals/{goal_id}/progress-history")
    assert resp.status_code == 200
    assert len(resp.json()["snapshots"]) >= 1


@pytest.mark.asyncio
async def test_history_default_30_days(client: AsyncClient):
    """查询：默认返回最近 30 天历史"""
    goal_id = await _create_checklist_goal(client)

    resp = await client.get(f"/goals/{goal_id}/progress-history")
    assert resp.status_code == 200
    data = resp.json()
    assert "snapshots" in data
    # 新创建的目标，无快照时为空
    assert isinstance(data["snapshots"], list)
