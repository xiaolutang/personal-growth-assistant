"""Goals CRUD + 条目关联 + 进度计算 + progress-summary API 测试"""
import uuid as _uuid
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


def _create_test_entry(storage, user_id: str, entry_id: str = None, **kwargs) -> str:
    """在 SQLite 中创建测试条目，返回 entry_id"""
    eid = entry_id or _uuid.uuid4().hex
    from app.models import Task, Category, TaskStatus, Priority
    from datetime import datetime
    entry = Task(
        id=eid,
        title=kwargs.get("title", f"测试条目-{eid[:6]}"),
        content=kwargs.get("content", ""),
        category=kwargs.get("category", Category.TASK),
        status=kwargs.get("status", TaskStatus.DOING),
        priority=Priority.MEDIUM,
        tags=kwargs.get("tags", []),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path=f"tasks/{eid}.md",
    )
    storage.sqlite.upsert_entry(entry, user_id=user_id)
    return eid


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


# === 条目关联测试 ===

@pytest.mark.asyncio
class TestLinkEntry:
    async def test_link_entry_success(self, client, storage, test_user):
        """成功关联条目到 count 目标"""
        goal = await _create_goal(client, target_value=3)
        entry_id = _create_test_entry(storage, test_user.id)

        resp = await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        assert resp.status_code == 201
        data = resp.json()
        assert data["entry_id"] == entry_id
        assert data["entry"]["id"] == entry_id
        assert data["goal"]["progress_percentage"] > 0

    async def test_link_entry_updates_progress(self, client, storage, test_user):
        """关联条目后进度正确更新"""
        goal = await _create_goal(client, target_value=2)
        entry_id = _create_test_entry(storage, test_user.id)

        resp = await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        assert resp.status_code == 201
        assert resp.json()["goal"]["current_value"] == 1
        assert resp.json()["goal"]["progress_percentage"] == 50.0

    async def test_link_entry_auto_complete(self, client, storage, test_user):
        """进度达到 100% 时自动完成"""
        goal = await _create_goal(client, target_value=1)
        entry_id = _create_test_entry(storage, test_user.id)

        resp = await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        assert resp.status_code == 201
        assert resp.json()["goal"]["status"] == "completed"
        assert resp.json()["goal"]["progress_percentage"] == 100.0

    async def test_link_entry_400_for_non_count(self, client, storage, test_user):
        """非 count 类型目标返回 400"""
        goal = await _create_goal(client, metric_type="checklist", checklist_items=["项1"])
        entry_id = _create_test_entry(storage, test_user.id)

        resp = await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        assert resp.status_code == 400

    async def test_link_entry_404_for_missing_entry(self, client, test_user):
        """不存在的条目返回 404"""
        goal = await _create_goal(client)
        fake_id = _uuid.uuid4().hex

        resp = await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": fake_id})
        assert resp.status_code == 404

    async def test_link_entry_409_duplicate(self, client, storage, test_user):
        """重复关联返回 409"""
        goal = await _create_goal(client, target_value=5)
        entry_id = _create_test_entry(storage, test_user.id)

        resp1 = await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        assert resp1.status_code == 201

        resp2 = await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        assert resp2.status_code == 409

    async def test_link_entry_404_for_missing_goal(self, client, storage, test_user):
        """不存在的目标返回 404"""
        entry_id = _create_test_entry(storage, test_user.id)

        resp = await client.post(f"/goals/nonexistent/entries", json={"entry_id": entry_id})
        assert resp.status_code == 404


# === 取消关联测试 ===

@pytest.mark.asyncio
class TestUnlinkEntry:
    async def test_unlink_entry_success(self, client, storage, test_user):
        """成功取消关联"""
        goal = await _create_goal(client, target_value=5)
        entry_id = _create_test_entry(storage, test_user.id)

        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        resp = await client.delete(f"/goals/{goal['id']}/entries/{entry_id}")
        assert resp.status_code == 204

    async def test_unlink_progress_drops(self, client, storage, test_user):
        """取消关联后进度下降"""
        goal = await _create_goal(client, target_value=2)
        e1 = _create_test_entry(storage, test_user.id)
        e2 = _create_test_entry(storage, test_user.id)

        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": e1})
        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": e2})

        # 取消一个
        resp = await client.delete(f"/goals/{goal['id']}/entries/{e1}")
        assert resp.status_code == 204

        # 验证进度
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["current_value"] == 1
        assert detail.json()["progress_percentage"] == 50.0

    async def test_unlink_completed_status_stays(self, client, storage, test_user):
        """取消关联后 completed 状态不会自动回退"""
        goal = await _create_goal(client, target_value=1)
        entry_id = _create_test_entry(storage, test_user.id)

        # 关联 → 自动完成
        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["status"] == "completed"

        # 取消关联
        resp = await client.delete(f"/goals/{goal['id']}/entries/{entry_id}")
        assert resp.status_code == 204

        # 状态仍然是 completed（不自动回退）
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["status"] == "completed"

    async def test_unlink_nonexistent_returns_404(self, client, test_user):
        """取消不存在的关联返回 404"""
        goal = await _create_goal(client)
        resp = await client.delete(f"/goals/{goal['id']}/entries/nonexistent")
        assert resp.status_code == 404


# === 列出关联条目测试 ===

@pytest.mark.asyncio
class TestListGoalEntries:
    async def test_list_entries_empty(self, client, test_user):
        """目标无关联条目时返回空列表"""
        goal = await _create_goal(client)
        resp = await client.get(f"/goals/{goal['id']}/entries")
        assert resp.status_code == 200
        assert resp.json()["entries"] == []

    async def test_list_entries_with_data(self, client, storage, test_user):
        """列出关联条目"""
        goal = await _create_goal(client, target_value=5)
        e1 = _create_test_entry(storage, test_user.id)
        e2 = _create_test_entry(storage, test_user.id)

        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": e1})
        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": e2})

        resp = await client.get(f"/goals/{goal['id']}/entries")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 2
        for entry in data["entries"]:
            assert "entry" in entry
            assert "id" in entry["entry"]
            assert "title" in entry["entry"]

    async def test_list_entries_404_for_missing_goal(self, client, test_user):
        """不存在的目标返回 404"""
        resp = await client.get("/goals/nonexistent/entries")
        assert resp.status_code == 404


# === Checklist 切换测试 ===

@pytest.mark.asyncio
class TestChecklistToggle:
    async def test_toggle_item(self, client, test_user):
        """切换 checklist 项"""
        goal = await _create_goal(
            client,
            metric_type="checklist",
            checklist_items=["项1", "项2", "项3"],
        )
        item_id = goal["checklist_items"][0]["id"]

        resp = await client.patch(f"/goals/{goal['id']}/checklist/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_value"] == 1
        assert data["progress_percentage"] > 0

        # 找到切换的 item
        toggled_item = next(i for i in data["checklist_items"] if i["id"] == item_id)
        assert toggled_item["checked"] is True

    async def test_toggle_item_twice(self, client, test_user):
        """切换两次回到原始状态"""
        goal = await _create_goal(
            client,
            metric_type="checklist",
            checklist_items=["项1"],
        )
        item_id = goal["checklist_items"][0]["id"]

        await client.patch(f"/goals/{goal['id']}/checklist/{item_id}")
        resp = await client.patch(f"/goals/{goal['id']}/checklist/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_value"] == 0

    async def test_toggle_auto_complete_at_100(self, client, test_user):
        """所有项勾选后自动完成"""
        goal = await _create_goal(
            client,
            metric_type="checklist",
            checklist_items=["项1", "项2"],
            target_value=2,
        )
        for item in goal["checklist_items"]:
            resp = await client.patch(f"/goals/{goal['id']}/checklist/{item['id']}")
            assert resp.status_code == 200

        data = resp.json()
        assert data["status"] == "completed"
        assert data["progress_percentage"] == 100.0

    async def test_toggle_400_for_non_checklist(self, client, test_user):
        """非 checklist 类型返回 400"""
        goal = await _create_goal(client)
        resp = await client.patch(f"/goals/{goal['id']}/checklist/fakeid")
        assert resp.status_code == 400

    async def test_toggle_404_for_missing_item(self, client, test_user):
        """不存在的检查项返回 404"""
        goal = await _create_goal(
            client,
            metric_type="checklist",
            checklist_items=["项1"],
        )
        resp = await client.patch(f"/goals/{goal['id']}/checklist/nonexistent")
        assert resp.status_code == 404

    async def test_toggle_404_for_missing_goal(self, client, test_user):
        """不存在的目标返回 404"""
        resp = await client.patch("/goals/nonexistent/checklist/fakeid")
        assert resp.status_code == 404


# === 进度汇总测试 ===

@pytest.mark.asyncio
class TestProgressSummary:
    async def test_summary_empty(self, client, test_user):
        """无目标时返回空汇总"""
        resp = await client.get("/goals/progress-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_count"] == 0
        assert data["completed_count"] == 0
        assert data["goals"] == []

    async def test_summary_with_active_goals(self, client, test_user):
        """包含活跃目标的汇总"""
        await _create_goal(client, title="目标1", target_value=5)
        await _create_goal(client, title="目标2", target_value=3)

        resp = await client.get("/goals/progress-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_count"] == 2
        assert data["completed_count"] == 0
        assert len(data["goals"]) == 2

    async def test_summary_with_completed_goals(self, client, storage, test_user):
        """已完成目标不计入 goals 列表，但计入 completed_count"""
        goal = await _create_goal(client, title="已完成", target_value=1)
        entry_id = _create_test_entry(storage, test_user.id)
        # 关联条目触发自动完成
        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})

        resp = await client.get("/goals/progress-summary")
        data = resp.json()
        assert data["active_count"] == 0
        assert data["completed_count"] == 1
        assert len(data["goals"]) == 0  # 已完成目标不在 goals 列表中

    async def test_summary_mixed_goals(self, client, storage, test_user):
        """混合活跃和已完成目标，goals 只含活跃目标"""
        await _create_goal(client, title="活跃1")
        goal = await _create_goal(client, title="将完成", target_value=1)
        entry_id = _create_test_entry(storage, test_user.id)
        await client.post(f"/goals/{goal['id']}/entries", json={"entry_id": entry_id})

        resp = await client.get("/goals/progress-summary")
        data = resp.json()
        assert data["active_count"] == 1
        assert data["completed_count"] == 1
        assert len(data["goals"]) == 1  # 只有活跃目标

    async def test_summary_progress_delta_tag_auto(self, client, storage, test_user):
        """tag_auto + start_date + end_date 时 progress_delta 有值"""
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        start = (now - timedelta(days=60)).strftime("%Y-%m-%d")
        end = (now + timedelta(days=30)).strftime("%Y-%m-%d")

        resp = await client.post("/goals", json={
            "title": "Tag Delta Goal",
            "metric_type": "tag_auto",
            "target_value": 10,
            "auto_tags": ["test-delta"],
            "start_date": start,
            "end_date": end,
        })
        assert resp.status_code == 201

        # 无 period 参数时 delta 为 None
        resp = await client.get("/goals/progress-summary")
        data = resp.json()
        assert len(data["goals"]) == 1
        assert data["goals"][0]["progress_delta"] is None

        # weekly 参数时 delta 有值
        resp = await client.get("/goals/progress-summary?period=weekly")
        data = resp.json()
        assert len(data["goals"]) == 1
        assert data["goals"][0]["progress_delta"] is not None

    async def test_summary_progress_delta_count_type_is_none(self, client, storage, test_user):
        """count 类型目标 progress_delta 始终为 None"""
        await _create_goal(client, title="Count Goal")

        resp = await client.get("/goals/progress-summary?period=weekly")
        data = resp.json()
        assert len(data["goals"]) == 1
        assert data["goals"][0]["progress_delta"] is None
