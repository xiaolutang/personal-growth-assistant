"""测试 Entries API 路由"""
import pytest

from app.api.schemas import EntryCreate, EntryUpdate


class TestEntriesAPI:
    """Entries API 集成测试"""

    @pytest.mark.asyncio
    async def test_list_entries(self, client):
        """测试列出条目 API"""
        response = await client.get("/entries")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert isinstance(data["entries"], list)

    @pytest.mark.asyncio
    async def test_list_entries_with_filters(self, client):
        """测试带筛选条件的列表 API"""
        response = await client.get(
            "/entries",
            params={
                "type": "task",
                "status": "doing",
                "limit": 10,
                "offset": 0,
            }
        )

        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["category"] == "task"
            assert entry["status"] == "doing"

    @pytest.mark.asyncio
    async def test_create_entry(self, client):
        """测试创建条目 API"""
        response = await client.post(
            "/entries",
            json={
                "category": "task",
                "title": "API测试任务",
                "content": "测试内容",
                "tags": ["api", "test"],
                "status": "doing",
                "priority": "high",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "API测试任务"
        assert data["category"] == "task"
        assert data["status"] == "doing"
        assert data["priority"] == "high"
        assert "api" in data["tags"]

    @pytest.mark.asyncio
    async def test_create_entry_invalid_type(self, client):
        """测试创建无效类型的条目 - 无效类型会使用默认值 note"""
        response = await client.post(
            "/entries",
            json={
                "category": "invalid_type",
                "title": "测试",
            }
        )

        # 无效类型会被映射为 note，所以返回 200
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "note"  # 默认值

    @pytest.mark.asyncio
    async def test_create_entry_missing_title(self, client):
        """测试创建缺少标题的条目"""
        response = await client.post(
            "/entries",
            json={
                "category": "task",
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_entry(self, client):
        """测试获取单个条目 API"""
        # 先创建
        create_response = await client.post(
            "/entries",
            json={"category": "task", "title": "获取测试"}
        )
        entry_id = create_response.json()["id"]

        # 再获取
        response = await client.get(f"/entries/{entry_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id
        assert data["title"] == "获取测试"

    @pytest.mark.asyncio
    async def test_get_entry_not_found(self, client):
        """测试获取不存在的条目"""
        response = await client.get("/entries/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_entry(self, client):
        """测试更新条目 API"""
        # 先创建
        create_response = await client.post(
            "/entries",
            json={"category": "task", "title": "更新前标题"}
        )
        entry_id = create_response.json()["id"]

        # 更新
        response = await client.put(
            f"/entries/{entry_id}",
            json={"title": "更新后标题", "status": "complete"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证
        get_response = await client.get(f"/entries/{entry_id}")
        assert get_response.json()["title"] == "更新后标题"
        assert get_response.json()["status"] == "complete"

    @pytest.mark.asyncio
    async def test_update_entry_not_found(self, client):
        """测试更新不存在的条目"""
        response = await client.put(
            "/entries/nonexistent-id",
            json={"title": "新标题"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_entry(self, client):
        """测试删除条目 API"""
        # 先创建
        create_response = await client.post(
            "/entries",
            json={"category": "task", "title": "待删除"}
        )
        entry_id = create_response.json()["id"]

        # 删除
        response = await client.delete(f"/entries/{entry_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证删除
        get_response = await client.get(f"/entries/{entry_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_entry_not_found(self, client):
        """测试删除不存在的条目"""
        response = await client.delete("/entries/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_search_entries(self, client):
        """测试搜索条目 API"""
        # 先创建带特殊关键词的条目
        await client.post(
            "/entries",
            json={
                "category": "note",
                "title": "搜索测试文档",
                "content": "包含SEARCH_KEYWORD的内容",
            }
        )

        # 搜索
        response = await client.get(
            "/entries/search/query",
            params={"q": "SEARCH_KEYWORD", "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert data["query"] == "SEARCH_KEYWORD"
        assert len(data["entries"]) >= 1

    @pytest.mark.asyncio
    async def test_search_entries_missing_query(self, client):
        """测试搜索缺少关键词"""
        response = await client.get("/entries/search/query")

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_project_progress(self, client):
        """测试获取项目进度 API"""
        # 创建项目
        project_response = await client.post(
            "/entries",
            json={"category": "project", "title": "进度测试项目"}
        )
        project_id = project_response.json()["id"]

        # 创建子任务
        await client.post(
            "/entries",
            json={
                "category": "task",
                "title": "子任务1",
                "parent_id": project_id,
                "status": "complete",
            }
        )
        await client.post(
            "/entries",
            json={
                "category": "task",
                "title": "子任务2",
                "parent_id": project_id,
                "status": "doing",
            }
        )

        # 获取进度
        response = await client.get(f"/entries/{project_id}/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project_id
        assert data["total_tasks"] == 2
        assert data["completed_tasks"] == 1
        assert data["progress_percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_get_project_progress_not_found(self, client):
        """测试获取不存在项目的进度"""
        response = await client.get("/entries/nonexistent/progress")

        assert response.status_code == 404


class TestEntriesAPIPagination:
    """Entries API 分页测试"""

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        """测试分页功能"""
        # 创建多个条目
        for i in range(15):
            await client.post(
                "/entries",
                json={"category": "task", "title": f"分页测试{i:03d}"}
            )

        # 第一页
        response1 = await client.get("/entries", params={"limit": 5, "offset": 0})
        assert len(response1.json()["entries"]) == 5

        # 第二页
        response2 = await client.get("/entries", params={"limit": 5, "offset": 5})
        assert len(response2.json()["entries"]) == 5

        # 验证不同页内容不同
        ids1 = {e["id"] for e in response1.json()["entries"]}
        ids2 = {e["id"] for e in response2.json()["entries"]}
        assert ids1.isdisjoint(ids2)


class TestHealthEndpoint:
    """健康检查端点测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """测试健康检查"""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ("ok", "degraded")
        assert "services" in data
        assert data["services"]["sqlite"] == "ok"
