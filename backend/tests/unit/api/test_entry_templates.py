"""测试 B110 笔记模板 API"""
import pytest


class TestListTemplates:
    """GET /entries/templates"""

    @pytest.mark.asyncio
    async def test_list_templates_returns_all(self, client):
        """返回所有可用模板（至少 3 个 note 模板）"""
        resp = await client.get("/entries/templates")
        assert resp.status_code == 200
        data = resp.json()
        templates = data["templates"]
        assert len(templates) >= 3
        ids = [t["id"] for t in templates]
        assert "learning" in ids
        assert "reading" in ids
        assert "meeting" in ids

    @pytest.mark.asyncio
    async def test_list_templates_filter_note(self, client):
        """GET /entries/templates?category=note 只返回 note 类型模板"""
        resp = await client.get("/entries/templates", params={"category": "note"})
        assert resp.status_code == 200
        data = resp.json()
        templates = data["templates"]
        assert len(templates) >= 3
        for t in templates:
            assert t["category"] == "note"

    @pytest.mark.asyncio
    async def test_list_templates_filter_task_returns_empty(self, client):
        """GET /entries/templates?category=task 返回空列表"""
        resp = await client.get("/entries/templates", params={"category": "task"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["templates"] == []

    @pytest.mark.asyncio
    async def test_template_structure(self, client):
        """模板结构包含必要字段"""
        resp = await client.get("/entries/templates")
        data = resp.json()
        for t in data["templates"]:
            assert "id" in t
            assert "name" in t
            assert "category" in t
            assert "description" in t
            assert "content" in t


class TestCreateWithTemplate:
    """POST /entries with template_id"""

    @pytest.mark.asyncio
    async def test_create_with_template_id(self, client):
        """POST /entries 带 template_id 使用模板内容"""
        resp = await client.post("/entries", json={
            "category": "note",
            "title": "学习测试",
            "template_id": "learning",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "核心概念" in data["content"]
        assert "关键要点" in data["content"]
        assert data["category"] == "note"
        assert data["title"] == "学习测试"

    @pytest.mark.asyncio
    async def test_create_without_template_id_unchanged(self, client):
        """POST /entries 不带 template_id 行为不变"""
        resp = await client.post("/entries", json={
            "category": "task",
            "title": "普通任务",
            "content": "任务内容",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "普通任务"
        assert "任务内容" in data["content"]

    @pytest.mark.asyncio
    async def test_create_invalid_template_id_uses_content(self, client):
        """template_id 无效时使用 request.content"""
        resp = await client.post("/entries", json={
            "category": "note",
            "title": "无效模板测试",
            "content": "用户内容",
            "template_id": "nonexistent",
        })
        assert resp.status_code == 200
        data = resp.json()
        # 无效 template_id 不生效，走原有流程（note 没有 CATEGORY_TEMPLATES）
        assert "用户内容" in data["content"]

    @pytest.mark.asyncio
    async def test_create_template_category_mismatch(self, client):
        """template_id 与 category 不匹配时忽略模板"""
        resp = await client.post("/entries", json={
            "category": "task",
            "title": "分类不匹配测试",
            "template_id": "learning",
        })
        assert resp.status_code == 200
        data = resp.json()
        # task 没有 CATEGORY_TEMPLATES，content 为空字符串经 _apply_category_template 后无变化
        assert "核心概念" not in data["content"]

    @pytest.mark.asyncio
    async def test_create_template_does_not_override_nonempty_content(self, client):
        """content 非空且有 template_id 时不覆盖用户内容"""
        resp = await client.post("/entries", json={
            "category": "note",
            "title": "不覆盖测试",
            "content": "我自己的内容",
            "template_id": "learning",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "我自己的内容" in data["content"]
        assert "核心概念" not in data["content"]

    @pytest.mark.asyncio
    async def test_create_template_with_empty_content(self, client):
        """content 为空字符串 + template_id 使用模板"""
        resp = await client.post("/entries", json={
            "category": "note",
            "title": "空内容模板测试",
            "content": "",
            "template_id": "meeting",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "会议主题" in data["content"]
        assert "讨论要点" in data["content"]


class TestTemplateAuth:
    """认证隔离"""

    @pytest.mark.asyncio
    async def test_templates_require_auth(self, client):
        """GET /entries/templates 需要认证（client fixture 自带 token，验证可正常访问）"""
        resp = await client.get("/entries/templates")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_templates_unauthorized(self, storage, test_user):
        """未认证访问返回 401"""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/entries/templates")
            assert resp.status_code == 401
