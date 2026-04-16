"""Goals CRUD API 测试"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.auth_service import create_access_token
from app.routers import deps
from app.infrastructure.storage.user_storage import UserStorage
import tempfile
import os


# === 辅助函数 ===

async def _create_second_user_client():
    """创建第二个用户的客户端（用于隔离测试）"""
    user_db = tempfile.mktemp(suffix=".db")
    us = UserStorage(user_db)
    from app.models.user import UserCreate
    user_b = us.create_user(UserCreate(
        username="user_b", email="b@example.com", password="pass123"
    ))
    token_b = create_access_token(user_b.id)
    transport = ASGITransport(app=app)
    client_b = AsyncClient(transport=transport, base_url="http://test", timeout=60.0)
    client_b.headers["Authorization"] = f"Bearer {token_b}"
    return client_b, user_b, user_db


async def _create_goal(client: AsyncClient, **overrides) -> dict:
    """创建测试目标"""
    payload = {
        "title": "测试目标",
        "metric_type": "count",
        "target_value": 10,
    }
    payload.update(overrides)
    resp = await client.post("/goals", json=payload)
    assert resp.status_code == 201, f"创建目标失败: {resp.text}"
    return resp.json()


# === 创建测试 ===

@pytest.mark.asyncio
class TestCreateGoal:
    async def test_create_count_goal(self, client):
        goal = await _create_goal(client)
        assert goal["metric_type"] == "count"
        assert goal["status"] == "active"
        assert goal["current_value"] == 0
        assert goal["progress_percentage"] == 0.0
        assert goal["target_value"] == 10
        assert "id" in goal
        assert "created_at" in goal

    async def test_create_tag_auto_goal_with_tags(self, client):
        goal = await _create_goal(
            client,
            metric_type="tag_auto",
            auto_tags=["react", "hooks"],
            target_value=5,
        )
        assert goal["metric_type"] == "tag_auto"
        assert goal["auto_tags"] == ["react", "hooks"]

    async def test_create_checklist_goal_with_items(self, client):
        goal = await _create_goal(
            client,
            metric_type="checklist",
            checklist_items=["学习 Hooks", "完成项目", "写总结"],
        )
        assert goal["metric_type"] == "checklist"
        assert len(goal["checklist_items"]) == 3
        for item in goal["checklist_items"]:
            assert "id" in item
            assert item["checked"] is False

    async def test_create_goal_with_dates(self, client):
        goal = await _create_goal(
            client,
            start_date="2026-04-01",
            end_date="2026-06-30",
        )
        assert goal["start_date"] == "2026-04-01"
        assert goal["end_date"] == "2026-06-30"

    async def test_create_tag_auto_without_tags_returns_422(self, client):
        resp = await client.post("/goals", json={
            "title": "无标签",
            "metric_type": "tag_auto",
            "target_value": 5,
        })
        assert resp.status_code == 422

    async def test_create_checklist_without_items_returns_422(self, client):
        resp = await client.post("/goals", json={
            "title": "无检查项",
            "metric_type": "checklist",
            "target_value": 3,
        })
        assert resp.status_code == 422

    async def test_create_goal_invalid_metric_type_returns_422(self, client):
        resp = await client.post("/goals", json={
            "title": "非法类型",
            "metric_type": "invalid",
            "target_value": 5,
        })
        assert resp.status_code == 422


# === 列表测试 ===

@pytest.mark.asyncio
class TestListGoals:
    async def test_list_goals_empty(self, client):
        resp = await client.get("/goals")
        assert resp.status_code == 200
        assert resp.json()["goals"] == []

    async def test_list_goals_with_data(self, client):
        await _create_goal(client, title="目标A")
        await _create_goal(client, title="目标B")
        resp = await client.get("/goals")
        assert resp.status_code == 200
        assert len(resp.json()["goals"]) == 2

    async def test_list_goals_filter_by_status(self, client):
        await _create_goal(client, title="活跃目标")
        resp = await client.get("/goals", params={"status": "active"})
        assert resp.status_code == 200
        goals = resp.json()["goals"]
        assert len(goals) == 1
        assert goals[0]["status"] == "active"

        resp_completed = await client.get("/goals", params={"status": "completed"})
        assert len(resp_completed.json()["goals"]) == 0


# === 详情测试 ===

@pytest.mark.asyncio
class TestGetGoal:
    async def test_get_goal_detail(self, client):
        goal = await _create_goal(client)
        resp = await client.get(f"/goals/{goal['id']}")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == goal["id"]
        assert "linked_entries_count" in detail

    async def test_get_goal_not_found(self, client):
        resp = await client.get("/goals/nonexistent")
        assert resp.status_code == 404


# === 更新测试 ===

@pytest.mark.asyncio
class TestUpdateGoal:
    async def test_update_goal_status_to_completed(self, client):
        goal = await _create_goal(client)
        resp = await client.put(f"/goals/{goal['id']}", json={"status": "completed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    async def test_update_goal_reactivate(self, client):
        goal = await _create_goal(client)
        # 先完成
        await client.put(f"/goals/{goal['id']}", json={"status": "completed"})
        # 再重新激活
        resp = await client.put(f"/goals/{goal['id']}", json={"status": "active"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_update_goal_title(self, client):
        goal = await _create_goal(client)
        resp = await client.put(f"/goals/{goal['id']}", json={"title": "新标题"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "新标题"

    async def test_update_nonexistent_goal(self, client):
        resp = await client.put("/goals/nonexistent", json={"title": "test"})
        assert resp.status_code == 404


# === 删除测试 ===

@pytest.mark.asyncio
class TestDeleteGoal:
    async def test_delete_abandoned_goal(self, client):
        goal = await _create_goal(client)
        # 先放弃
        await client.put(f"/goals/{goal['id']}", json={"status": "abandoned"})
        # 再删除
        resp = await client.delete(f"/goals/{goal['id']}")
        assert resp.status_code == 200

        # 确认已删除
        resp_get = await client.get(f"/goals/{goal['id']}")
        assert resp_get.status_code == 404

    async def test_delete_active_goal_returns_400(self, client):
        goal = await _create_goal(client)
        resp = await client.delete(f"/goals/{goal['id']}")
        assert resp.status_code == 400


# === 认证与隔离测试 ===

@pytest.mark.asyncio
class TestAuthAndIsolation:
    async def test_unauthenticated_returns_401(self, storage, test_user):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as anon_client:
            resp = await anon_client.post("/goals", json={
                "title": "未认证",
                "metric_type": "count",
                "target_value": 1,
            })
            assert resp.status_code == 401

    async def test_goal_isolated_by_user(self, client, storage, test_user):
        """用户 A 的目标对用户 B 不可见"""
        from app.infrastructure.storage.user_storage import UserStorage
        from app.models.user import UserCreate

        goal = await _create_goal(client, title="用户A的目标")

        # 创建用户 B（复用同一个 UserStorage）
        user_b = deps._user_storage.create_user(UserCreate(
            username="user_b", email="b@example.com", password="pass123"
        ))
        token_b = create_access_token(user_b.id)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client_b:
            client_b.headers["Authorization"] = f"Bearer {token_b}"

            # B 直接访问 A 的目标返回 404
            resp_detail = await client_b.get(f"/goals/{goal['id']}")
            assert resp_detail.status_code == 404

            # B 无法更新 A 的目标
            resp_update = await client_b.put(f"/goals/{goal['id']}", json={"title": "hacked"})
            assert resp_update.status_code == 404

            # B 无法删除 A 的目标
            resp_delete = await client_b.delete(f"/goals/{goal['id']}")
            assert resp_delete.status_code == 404
