"""B69: API 集成测试覆盖缺口

补充 entries export、goal CRUD、feedback 边界场景的集成测试。
验证 auth 要求和用户隔离。
"""

from httpx import AsyncClient


# client fixture 由根 conftest.py 提供（AsyncClient + auth token）


class TestEntriesExportFlow:
    """entries export API 集成测试"""

    async def test_export_json_format(self, client: AsyncClient):
        """JSON 格式导出"""
        # 创建一些条目
        await client.post("/entries", json={"category": "task", "title": "导出任务1", "content": "内容1"})
        await client.post("/entries", json={"category": "note", "title": "导出笔记1", "content": "内容2"})

        resp = await client.get("/entries/export", params={"format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_export_markdown_format(self, client: AsyncClient):
        """Markdown zip 格式导出"""
        await client.post("/entries", json={"category": "task", "title": "zip导出测试", "content": "zip内容"})

        resp = await client.get("/entries/export", params={"format": "markdown"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"

    async def test_export_with_type_filter(self, client: AsyncClient):
        """按类型过滤导出"""
        await client.post("/entries", json={"category": "task", "title": "任务"})
        await client.post("/entries", json={"category": "note", "title": "笔记"})

        resp = await client.get("/entries/export", params={"format": "json", "type": "task"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["category"] == "task" for e in data)

    async def test_export_empty_data(self, client: AsyncClient):
        """空数据导出"""
        resp = await client.get("/entries/export", params={"format": "json"})
        assert resp.status_code == 200

    async def test_export_no_token(self):
        """无 token 导出返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/entries/export", params={"format": "json"})
            assert resp.status_code == 401


class TestGoalCRUDFlow:
    """goal CRUD API 集成测试"""

    async def test_goal_create_and_list(self, client: AsyncClient):
        """创建目标并列表查看"""
        create_resp = await client.post("/goals", json={
            "title": "学习 FastAPI",
            "description": "掌握 FastAPI 框架",
            "metric_type": "count",
            "target_value": 10,
            "target_date": "2026-06-30",
        })
        assert create_resp.status_code == 201
        goal = create_resp.json()
        assert goal["title"] == "学习 FastAPI"
        goal_id = goal["id"]

        list_resp = await client.get("/goals")
        assert list_resp.status_code == 200
        goals = list_resp.json()["goals"]
        assert any(g["id"] == goal_id for g in goals)

    async def test_goal_update(self, client: AsyncClient):
        """更新目标"""
        create_resp = await client.post("/goals", json={"title": "原始目标", "metric_type": "count", "target_value": 1})
        goal_id = create_resp.json()["id"]

        update_resp = await client.put(f"/goals/{goal_id}", json={
            "title": "更新后的目标",
            "current_value": 50,
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "更新后的目标"

    async def test_goal_delete(self, client: AsyncClient):
        """删除目标（需先 abandon）"""
        create_resp = await client.post("/goals", json={"title": "待删除目标", "metric_type": "count", "target_value": 1})
        goal_id = create_resp.json()["id"]

        # 先 abandon 才能删除
        await client.put(f"/goals/{goal_id}", json={"status": "abandoned"})
        delete_resp = await client.delete(f"/goals/{goal_id}")
        assert delete_resp.status_code == 200

        # 确认已删除
        list_resp = await client.get("/goals")
        goals = list_resp.json()["goals"]
        assert not any(g["id"] == goal_id for g in goals)

    async def test_goal_no_token(self):
        """无 token 操作目标返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/goals")
            assert resp.status_code == 401

    async def test_goal_get_detail(self, client: AsyncClient):
        """获取单个目标详情"""
        create_resp = await client.post("/goals", json={"title": "详情测试", "metric_type": "count", "target_value": 5})
        goal_id = create_resp.json()["id"]

        detail_resp = await client.get(f"/goals/{goal_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["title"] == "详情测试"


class TestFeedbackBoundaryFlow:
    """feedback 边界场景集成测试"""

    async def test_feedback_default_severity(self, client: AsyncClient):
        """不传 severity 时默认 medium"""
        from unittest.mock import patch
        mock_resp = {"id": 1, "title": "t", "status": "open", "severity": "medium"}
        with patch("app.routers.feedback.report_issue", return_value=mock_resp):
            resp = await client.post("/feedback", json={"title": "默认测试"})
        assert resp.status_code == 200
        assert resp.json()["feedback"]["severity"] == "medium"

    async def test_feedback_no_description(self, client: AsyncClient):
        """不传 description 时为 None"""
        from unittest.mock import patch
        mock_resp = {"id": 2, "title": "t", "status": "open", "severity": "low"}
        with patch("app.routers.feedback.report_issue", return_value=mock_resp):
            resp = await client.post("/feedback", json={"title": "无描述", "severity": "low"})
        assert resp.status_code == 200
        assert resp.json()["feedback"]["description"] is None

    async def test_feedback_empty_title_422(self, client: AsyncClient):
        """空标题返回 422"""
        resp = await client.post("/feedback", json={"title": "", "severity": "low"})
        assert resp.status_code == 422

    async def test_feedback_whitespace_title_422(self, client: AsyncClient):
        """纯空格标题返回 422"""
        resp = await client.post("/feedback", json={"title": "   ", "severity": "low"})
        assert resp.status_code == 422

    async def test_feedback_all_severity_values(self, client: AsyncClient):
        """所有合法 severity 值都能通过"""
        from unittest.mock import patch
        mock_resp = {"id": 3, "title": "t", "status": "open", "severity": "low"}
        for sev in ["low", "medium", "high", "critical"]:
            with patch("app.routers.feedback.report_issue", return_value=mock_resp):
                resp = await client.post("/feedback", json={
                    "title": f"severity={sev}",
                    "severity": sev,
                })
            assert resp.status_code == 200

    async def test_feedback_no_token(self):
        """无 token 提交反馈返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/feedback", json={"title": "test", "severity": "low"})
            assert resp.status_code == 401

    async def test_feedback_submit_and_list_own(self, client: AsyncClient):
        """用户提交反馈后可在列表中查看"""
        from unittest.mock import patch
        mock_resp = {"id": 10, "title": "我的反馈", "status": "open", "severity": "medium"}
        with patch("app.routers.feedback.report_issue", return_value=mock_resp):
            resp = await client.post("/feedback", json={"title": "我的反馈"})
        assert resp.status_code == 200

        # 查看自己的反馈列表
        list_resp = await client.get("/feedback")
        assert list_resp.status_code == 200
