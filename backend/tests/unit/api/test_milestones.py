"""里程碑 CRUD + 排序 + 进度计算 + 用户隔离 API 测试"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.auth_service import create_access_token
from app.routers import deps


# === 辅助函数 ===

async def _create_milestone_goal(client, **overrides) -> dict:
    """创建 milestone 类型目标"""
    payload = {
        "title": "里程碑目标",
        "metric_type": "milestone",
        "target_value": 3,
    }
    payload.update(overrides)
    resp = await client.post("/goals", json=payload)
    assert resp.status_code == 201, f"创建目标失败: {resp.text}"
    return resp.json()


async def _create_milestone(client, goal_id: str, **overrides) -> dict:
    """创建里程碑"""
    payload = {"title": "测试里程碑"}
    payload.update(overrides)
    resp = await client.post(f"/goals/{goal_id}/milestones", json=payload)
    assert resp.status_code == 201, f"创建里程碑失败: {resp.text}"
    return resp.json()


# === 创建里程碑测试 ===

@pytest.mark.asyncio
class TestCreateMilestone:
    async def test_create_milestone_success(self, client):
        """成功创建里程碑"""
        goal = await _create_milestone_goal(client, target_value=3)
        ms = await _create_milestone(client, goal["id"], title="阶段1")
        assert ms["title"] == "阶段1"
        assert ms["status"] == "pending"
        assert ms["goal_id"] == goal["id"]
        assert "id" in ms
        assert "created_at" in ms
        assert "sort_order" in ms

    async def test_create_milestone_with_details(self, client):
        """创建带描述和截止日期的里程碑"""
        goal = await _create_milestone_goal(client)
        ms = await _create_milestone(
            client, goal["id"],
            title="阶段1",
            description="完成基础架构",
            due_date="2026-06-30",
        )
        assert ms["description"] == "完成基础架构"
        assert ms["due_date"] == "2026-06-30"

    async def test_create_milestone_auto_sort_order(self, client):
        """里程碑自动递增 sort_order"""
        goal = await _create_milestone_goal(client)
        ms1 = await _create_milestone(client, goal["id"], title="阶段1")
        ms2 = await _create_milestone(client, goal["id"], title="阶段2")
        assert ms1["sort_order"] == 0
        assert ms2["sort_order"] == 1

    async def test_create_milestone_non_milestone_goal_400(self, client):
        """非 milestone 类型目标返回 400"""
        resp = await client.post("/goals", json={
            "title": "计数目标",
            "metric_type": "count",
            "target_value": 5,
        })
        goal = resp.json()
        resp = await client.post(f"/goals/{goal['id']}/milestones", json={"title": "ms"})
        assert resp.status_code == 400

    async def test_create_milestone_goal_not_found(self, client):
        """目标不存在返回 404"""
        resp = await client.post("/goals/nonexistent/milestones", json={"title": "ms"})
        assert resp.status_code == 404

    async def test_create_milestone_empty_title_422(self, client):
        """空标题返回 422"""
        goal = await _create_milestone_goal(client)
        resp = await client.post(f"/goals/{goal['id']}/milestones", json={"title": ""})
        assert resp.status_code == 422


# === 列出里程碑测试 ===

@pytest.mark.asyncio
class TestListMilestones:
    async def test_list_milestones_empty(self, client):
        """无里程碑时返回空列表"""
        goal = await _create_milestone_goal(client)
        resp = await client.get(f"/goals/{goal['id']}/milestones")
        assert resp.status_code == 200
        assert resp.json()["milestones"] == []

    async def test_list_milestones_ordered(self, client):
        """里程碑按 sort_order 排序"""
        goal = await _create_milestone_goal(client)
        await _create_milestone(client, goal["id"], title="阶段1")
        await _create_milestone(client, goal["id"], title="阶段2")
        await _create_milestone(client, goal["id"], title="阶段3")

        resp = await client.get(f"/goals/{goal['id']}/milestones")
        assert resp.status_code == 200
        milestones = resp.json()["milestones"]
        assert len(milestones) == 3
        assert milestones[0]["sort_order"] == 0
        assert milestones[1]["sort_order"] == 1
        assert milestones[2]["sort_order"] == 2

    async def test_list_milestones_goal_not_found(self, client):
        """目标不存在返回 404"""
        resp = await client.get("/goals/nonexistent/milestones")
        assert resp.status_code == 404


# === 更新里程碑测试 ===

@pytest.mark.asyncio
class TestUpdateMilestone:
    async def test_update_milestone_title(self, client):
        """更新里程碑标题"""
        goal = await _create_milestone_goal(client)
        ms = await _create_milestone(client, goal["id"], title="旧标题")

        resp = await client.put(
            f"/goals/{goal['id']}/milestones/{ms['id']}",
            json={"title": "新标题"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "新标题"

    async def test_update_milestone_status_to_completed(self, client):
        """更新里程碑状态为已完成"""
        goal = await _create_milestone_goal(client)
        ms = await _create_milestone(client, goal["id"])

        resp = await client.put(
            f"/goals/{goal['id']}/milestones/{ms['id']}",
            json={"status": "completed"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    async def test_update_milestone_goal_not_found(self, client):
        """目标不存在返回 404"""
        resp = await client.put("/goals/nonexistent/milestones/fakeid", json={"title": "x"})
        assert resp.status_code == 404

    async def test_update_milestone_not_found(self, client):
        """里程碑不存在返回 404"""
        goal = await _create_milestone_goal(client)
        resp = await client.put(
            f"/goals/{goal['id']}/milestones/nonexistent",
            json={"title": "x"},
        )
        assert resp.status_code == 404

    async def test_update_milestone_wrong_goal(self, client):
        """里程碑不属于指定目标返回 404"""
        goal1 = await _create_milestone_goal(client)
        goal2 = await _create_milestone_goal(client)
        ms = await _create_milestone(client, goal1["id"])

        # 用 goal2 的 id 去访问 goal1 的里程碑
        resp = await client.put(
            f"/goals/{goal2['id']}/milestones/{ms['id']}",
            json={"title": "x"},
        )
        assert resp.status_code == 404


# === 删除里程碑测试 ===

@pytest.mark.asyncio
class TestDeleteMilestone:
    async def test_delete_milestone_success(self, client):
        """成功删除里程碑"""
        goal = await _create_milestone_goal(client)
        ms = await _create_milestone(client, goal["id"])

        resp = await client.delete(f"/goals/{goal['id']}/milestones/{ms['id']}")
        assert resp.status_code == 204

        # 确认已删除
        list_resp = await client.get(f"/goals/{goal['id']}/milestones")
        assert len(list_resp.json()["milestones"]) == 0

    async def test_delete_milestone_not_found(self, client):
        """里程碑不存在返回 404"""
        goal = await _create_milestone_goal(client)
        resp = await client.delete(f"/goals/{goal['id']}/milestones/nonexistent")
        assert resp.status_code == 404

    async def test_delete_milestone_goal_not_found(self, client):
        """目标不存在返回 404"""
        resp = await client.delete("/goals/nonexistent/milestones/fakeid")
        assert resp.status_code == 404


# === 重排序里程碑测试 ===

@pytest.mark.asyncio
class TestReorderMilestones:
    async def test_reorder_milestones(self, client):
        """重排序后 sort_order 正确"""
        goal = await _create_milestone_goal(client)
        ms1 = await _create_milestone(client, goal["id"], title="阶段1")
        ms2 = await _create_milestone(client, goal["id"], title="阶段2")
        ms3 = await _create_milestone(client, goal["id"], title="阶段3")

        # 倒序排列
        resp = await client.patch(
            f"/goals/{goal['id']}/milestones/reorder",
            json={"milestone_ids": [ms3["id"], ms2["id"], ms1["id"]]},
        )
        assert resp.status_code == 200
        milestones = resp.json()["milestones"]
        assert milestones[0]["id"] == ms3["id"]
        assert milestones[0]["sort_order"] == 0
        assert milestones[1]["id"] == ms2["id"]
        assert milestones[1]["sort_order"] == 1
        assert milestones[2]["id"] == ms1["id"]
        assert milestones[2]["sort_order"] == 2

    async def test_reorder_incomplete_ids_400(self, client):
        """ID 列表不完整返回 400"""
        goal = await _create_milestone_goal(client)
        await _create_milestone(client, goal["id"], title="阶段1")
        await _create_milestone(client, goal["id"], title="阶段2")

        resp = await client.patch(
            f"/goals/{goal['id']}/milestones/reorder",
            json={"milestone_ids": ["only_one_id"]},
        )
        assert resp.status_code == 400

    async def test_reorder_goal_not_found(self, client):
        """目标不存在返回 404"""
        resp = await client.patch(
            "/goals/nonexistent/milestones/reorder",
            json={"milestone_ids": ["id1"]},
        )
        assert resp.status_code == 404


# === 里程碑进度计算测试 ===

@pytest.mark.asyncio
class TestMilestoneProgress:
    async def test_progress_updates_on_complete(self, client):
        """完成里程碑后目标进度自动更新"""
        goal = await _create_milestone_goal(client, target_value=3)
        ms1 = await _create_milestone(client, goal["id"])
        ms2 = await _create_milestone(client, goal["id"])
        await _create_milestone(client, goal["id"])

        # 完成 1 个
        await client.put(
            f"/goals/{goal['id']}/milestones/{ms1['id']}",
            json={"status": "completed"},
        )
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["current_value"] == 1
        assert detail.json()["progress_percentage"] == pytest.approx(33.3, abs=0.1)

        # 再完成 1 个
        await client.put(
            f"/goals/{goal['id']}/milestones/{ms2['id']}",
            json={"status": "completed"},
        )
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["current_value"] == 2
        assert detail.json()["progress_percentage"] == pytest.approx(66.7, abs=0.1)

    async def test_progress_auto_complete(self, client):
        """所有里程碑完成后目标自动变为 completed"""
        goal = await _create_milestone_goal(client, target_value=2)
        ms1 = await _create_milestone(client, goal["id"])
        ms2 = await _create_milestone(client, goal["id"])

        # 完成 2 个
        await client.put(
            f"/goals/{goal['id']}/milestones/{ms1['id']}",
            json={"status": "completed"},
        )
        await client.put(
            f"/goals/{goal['id']}/milestones/{ms2['id']}",
            json={"status": "completed"},
        )
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["status"] == "completed"
        assert detail.json()["progress_percentage"] == 100.0

    async def test_progress_recalc_on_delete(self, client):
        """删除里程碑后进度重新计算"""
        goal = await _create_milestone_goal(client, target_value=2)
        ms1 = await _create_milestone(client, goal["id"])
        ms2 = await _create_milestone(client, goal["id"])

        # 完成 ms1
        await client.put(
            f"/goals/{goal['id']}/milestones/{ms1['id']}",
            json={"status": "completed"},
        )
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["current_value"] == 1
        assert detail.json()["progress_percentage"] == 50.0

        # 删除 ms2（pending）
        await client.delete(f"/goals/{goal['id']}/milestones/{ms2['id']}")

        # 现在 target_value=2 但 total_milestones=1, completed=1 → 进度 100%
        detail = await client.get(f"/goals/{goal['id']}")
        assert detail.json()["current_value"] == 1
        assert detail.json()["progress_percentage"] == 50.0  # target_value 仍是 2

    async def test_progress_snapshot_written(self, client):
        """里程碑操作触发进度快照"""
        goal = await _create_milestone_goal(client, target_value=1)
        ms = await _create_milestone(client, goal["id"])

        # 完成里程碑 → 应写入快照
        await client.put(
            f"/goals/{goal['id']}/milestones/{ms['id']}",
            json={"status": "completed"},
        )

        # 查看进度历史
        resp = await client.get(f"/goals/{goal['id']}/progress-history")
        assert resp.status_code == 200
        snapshots = resp.json()["snapshots"]
        assert len(snapshots) >= 1
        assert snapshots[0]["percentage"] == 100.0


# === 用户隔离测试 ===

@pytest.mark.asyncio
class TestMilestoneIsolation:
    async def test_milestones_isolated_by_user(self, client, storage, test_user):
        """用户 B 无法看到用户 A 的里程碑"""
        goal = await _create_milestone_goal(client, target_value=3)
        await _create_milestone(client, goal["id"], title="用户A的里程碑")

        # 创建用户 B
        from app.models.user import UserCreate
        user_b = deps._user_storage.create_user(UserCreate(
            username="user_b_milestone", email="bm@example.com", password="pass123"
        ))
        token_b = create_access_token(user_b.id)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client_b:
            client_b.headers["Authorization"] = f"Bearer {token_b}"

            # B 无法看到 A 的里程碑列表
            resp = await client_b.get(f"/goals/{goal['id']}/milestones")
            assert resp.status_code == 404  # 目标不存在（隔离）

            # B 无法创建里程碑到 A 的目标
            resp = await client_b.post(f"/goals/{goal['id']}/milestones", json={"title": "hack"})
            assert resp.status_code == 404

    async def test_milestone_crud_isolated(self, client, storage, test_user):
        """用户 B 无法操作用户 A 的里程碑"""
        goal = await _create_milestone_goal(client, target_value=3)
        ms = await _create_milestone(client, goal["id"])

        from app.models.user import UserCreate
        user_b = deps._user_storage.create_user(UserCreate(
            username="user_b_crud", email="bc@example.com", password="pass123"
        ))
        token_b = create_access_token(user_b.id)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client_b:
            client_b.headers["Authorization"] = f"Bearer {token_b}"

            # B 无法更新 A 的里程碑
            resp = await client_b.put(
                f"/goals/{goal['id']}/milestones/{ms['id']}",
                json={"status": "completed"},
            )
            assert resp.status_code == 404

            # B 无法删除 A 的里程碑
            resp = await client_b.delete(f"/goals/{goal['id']}/milestones/{ms['id']}")
            assert resp.status_code == 404
