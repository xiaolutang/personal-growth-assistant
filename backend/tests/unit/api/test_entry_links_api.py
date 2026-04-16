"""条目关联 API 单元测试"""
import pytest
from httpx import AsyncClient


async def _create_entry(client: AsyncClient, category: str = "task", title: str = "测试条目") -> dict:
    """辅助：通过 API 创建条目"""
    resp = await client.post("/entries", json={
        "category": category,
        "title": title,
        "content": f"内容-{title}",
    })
    assert resp.status_code == 200, f"创建条目失败: {resp.text}"
    return resp.json()


@pytest.mark.asyncio
class TestCreateEntryLink:
    """POST /entries/{id}/links 测试"""

    async def test_create_link_success(self, client):
        """正常创建双向关联"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        resp = await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_id"] == e1["id"]
        assert data["target_id"] == e2["id"]
        assert data["relation_type"] == "related"
        assert data["target_entry"]["id"] == e2["id"]
        assert data["target_entry"]["title"] == "条目B"
        assert "id" in data
        assert "created_at" in data

    async def test_create_link_bidirectional(self, client):
        """创建 A→B 时自动创建 B→A"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "depends_on",
        })

        # 检查 B→A 也存在
        resp = await client.get(f"/entries/{e2['id']}/links", params={"direction": "out"})
        assert resp.status_code == 200
        links = resp.json()["links"]
        assert any(l["target_id"] == e1["id"] and l["relation_type"] == "depends_on" for l in links)

    async def test_create_self_link_returns_400(self, client):
        """自关联返回 400"""
        e1 = await _create_entry(client, title="条目A")

        resp = await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e1["id"],
            "relation_type": "related",
        })
        assert resp.status_code == 400
        assert "自关联" in resp.json()["detail"]

    async def test_create_duplicate_link_returns_409(self, client):
        """重复关联返回 409"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        resp1 = await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })
        assert resp1.status_code == 201

        resp2 = await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })
        assert resp2.status_code == 409

    async def test_create_link_invalid_relation_type_returns_422(self, client):
        """无效关联类型返回 422"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        resp = await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "invalid_type",
        })
        assert resp.status_code == 422

    async def test_create_link_nonexistent_source_returns_404(self, client):
        """源条目不存在返回 404"""
        e2 = await _create_entry(client, title="条目B")

        resp = await client.post("/entries/nonexistent-id/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })
        assert resp.status_code == 404

    async def test_create_link_nonexistent_target_returns_404(self, client):
        """目标条目不存在返回 404"""
        e1 = await _create_entry(client, title="条目A")

        resp = await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": "nonexistent-id",
            "relation_type": "related",
        })
        assert resp.status_code == 404

    async def test_create_link_all_relation_types(self, client):
        """所有合法关联类型均可创建"""
        e1 = await _create_entry(client, title="条目A")
        valid_types = ["related", "depends_on", "derived_from", "references"]
        for rt in valid_types:
            e2 = await _create_entry(client, title=f"条目-{rt}")
            resp = await client.post(f"/entries/{e1['id']}/links", json={
                "target_id": e2["id"],
                "relation_type": rt,
            })
            assert resp.status_code == 201, f"关联类型 {rt} 创建失败: {resp.text}"


@pytest.mark.asyncio
class TestListEntryLinks:
    """GET /entries/{id}/links 测试"""

    async def test_list_links_both_direction(self, client):
        """both 方向列出所有关联"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")
        e3 = await _create_entry(client, title="条目C")

        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })
        await client.post(f"/entries/{e3['id']}/links", json={
            "target_id": e1["id"],
            "relation_type": "references",
        })

        resp = await client.get(f"/entries/{e1['id']}/links", params={"direction": "both"})
        assert resp.status_code == 200
        links = resp.json()["links"]
        # e1→e2 (out) + e3→e1 中 e1 是 target (in)
        assert len(links) >= 2

    async def test_list_links_out_direction(self, client):
        """out 方向只列出 source_id = entry_id 的关联"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })

        resp = await client.get(f"/entries/{e1['id']}/links", params={"direction": "out"})
        assert resp.status_code == 200
        links = resp.json()["links"]
        assert len(links) == 1
        assert links[0]["direction"] == "out"
        assert links[0]["target_id"] == e2["id"]

    async def test_list_links_in_direction(self, client):
        """in 方向只列出 target_id = entry_id 的关联"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "depends_on",
        })

        # e2 的 in 方向应包含 e1→e2
        resp = await client.get(f"/entries/{e2['id']}/links", params={"direction": "in"})
        assert resp.status_code == 200
        links = resp.json()["links"]
        assert len(links) == 1
        assert links[0]["direction"] == "in"

    async def test_list_links_empty(self, client):
        """无关联时返回空列表"""
        e1 = await _create_entry(client, title="条目A")

        resp = await client.get(f"/entries/{e1['id']}/links")
        assert resp.status_code == 200
        assert resp.json()["links"] == []

    async def test_list_links_nonexistent_entry_returns_404(self, client):
        """条目不存在返回 404"""
        resp = await client.get("/entries/nonexistent-id/links")
        assert resp.status_code == 404

    async def test_list_links_includes_target_entry(self, client):
        """关联列表包含 target_entry 信息"""
        e1 = await _create_entry(client, category="task", title="源条目")
        e2 = await _create_entry(client, category="note", title="目标笔记")

        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "references",
        })

        resp = await client.get(f"/entries/{e1['id']}/links", params={"direction": "out"})
        assert resp.status_code == 200
        links = resp.json()["links"]
        assert len(links) == 1
        assert links[0]["target_entry"]["id"] == e2["id"]
        assert links[0]["target_entry"]["title"] == "目标笔记"


@pytest.mark.asyncio
class TestDeleteEntryLink:
    """DELETE /entries/{id}/links/{link_id} 测试"""

    async def test_delete_link_success(self, client):
        """正常删除关联"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        create_resp = await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })
        link_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/entries/{e1['id']}/links/{link_id}")
        assert delete_resp.status_code == 204

        # 确认双向都已删除
        resp1 = await client.get(f"/entries/{e1['id']}/links")
        assert all(l["id"] != link_id for l in resp1.json()["links"])

        resp2 = await client.get(f"/entries/{e2['id']}/links")
        assert len(resp2.json()["links"]) == 0

    async def test_delete_nonexistent_link_returns_404(self, client):
        """删除不存在的关联返回 404"""
        e1 = await _create_entry(client, title="条目A")

        resp = await client.delete(f"/entries/{e1['id']}/links/nonexistent-link")
        assert resp.status_code == 404

    async def test_delete_link_from_target_entry(self, client):
        """从目标条目侧删除关联"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")

        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "derived_from",
        })

        # 从 e2 侧获取 links，找到反向 link
        resp = await client.get(f"/entries/{e2['id']}/links", params={"direction": "in"})
        links = resp.json()["links"]
        assert len(links) == 1
        reverse_link_id = links[0]["id"]

        # 从 e2 侧删除
        del_resp = await client.delete(f"/entries/{e2['id']}/links/{reverse_link_id}")
        assert del_resp.status_code == 204

        # 双向都已清理
        resp1 = await client.get(f"/entries/{e1['id']}/links")
        assert len(resp1.json()["links"]) == 0
        resp2 = await client.get(f"/entries/{e2['id']}/links")
        assert len(resp2.json()["links"]) == 0

    async def test_delete_link_nonexistent_entry_returns_404(self, client):
        """条目不存在时返回 404"""
        resp = await client.delete("/entries/nonexistent-id/links/some-link")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestCascadeDelete:
    """删除条目时级联清理关联"""

    async def test_delete_entry_cascades_links(self, client):
        """删除条目时自动清理所有关联"""
        e1 = await _create_entry(client, title="条目A")
        e2 = await _create_entry(client, title="条目B")
        e3 = await _create_entry(client, title="条目C")

        # e1→e2, e3→e1
        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })
        await client.post(f"/entries/{e3['id']}/links", json={
            "target_id": e1["id"],
            "relation_type": "references",
        })

        # 删除 e1
        del_resp = await client.delete(f"/entries/{e1['id']}")
        assert del_resp.status_code == 200

        # e2 和 e3 不应再有关联
        resp2 = await client.get(f"/entries/{e2['id']}/links")
        assert len(resp2.json()["links"]) == 0

        resp3 = await client.get(f"/entries/{e3['id']}/links")
        assert len(resp3.json()["links"]) == 0


@pytest.mark.asyncio
class TestUserIsolation:
    """用户隔离测试"""

    async def test_links_isolated_by_user(self, client, storage, test_user):
        """不同用户的关联互相不可见"""
        from app.routers import deps
        from app.services.auth_service import create_access_token
        from app.models.user import UserCreate
        from httpx import ASGITransport, AsyncClient as AC
        from app.main import app as main_app

        # 创建用户 A 的条目和关联
        e1 = await _create_entry(client, title="用户A-条目1")
        e2 = await _create_entry(client, title="用户A-条目2")
        await client.post(f"/entries/{e1['id']}/links", json={
            "target_id": e2["id"],
            "relation_type": "related",
        })

        # 在全局 user_storage 中创建用户 B
        user_b = deps._user_storage.create_user(UserCreate(
            username="user_b_iso",
            email="b_iso@example.com",
            password="pass1234",
        ))

        # 认领默认条目到用户 A，确保用户 B 看不到
        storage.sqlite.claim_default_entries(test_user.id)

        # 重置 entry_service 缓存
        deps.reset_all_services()

        # 用用户 B 的 token 创建客户端
        token_b = create_access_token(user_b.id)
        transport = ASGITransport(app=main_app)

        async with AC(transport=transport, base_url="http://test") as client_b:
            client_b.headers["Authorization"] = f"Bearer {token_b}"

            # 用户 B 看不到用户 A 的条目
            resp = await client_b.get(f"/entries/{e1['id']}/links")
            assert resp.status_code == 404

            # 用户 B 不能创建指向用户 A 条目的关联
            e_b = await _create_entry(client_b, title="用户B-条目1")
            resp = await client_b.post(f"/entries/{e_b['id']}/links", json={
                "target_id": e2["id"],
                "relation_type": "related",
            })
            assert resp.status_code == 404  # target 不属于用户 B
