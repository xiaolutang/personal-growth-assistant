"""B43: 条目知识上下文 API 测试

测试覆盖:
- 有标签条目返回正确的子图（nodes, edges, center_concepts）
- 节点结构包含 id, name, category, mastery, entry_count
- 边结构包含 source, target, relationship
- center_concepts = entry.tags
- 无标签条目返回空子图
- 条目不存在返回 404
- 用户隔离
- Neo4j 不可用时 SQLite 降级正常工作
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models import Task, Category, TaskStatus, Priority


def _make_test_user_id(client) -> str:
    """从 client 认证头中提取测试用户 ID"""
    from app.routers import deps
    user_storage = deps._user_storage
    user = user_storage.get_by_username("testuser")
    return user.id if user else "test-user"


class TestKnowledgeContextAPI:
    """条目知识上下文 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        now = datetime.now()

        # 条目 A: 有多个标签
        self.entry_a_id = "kctx-entry-a"
        entry_a = Task(
            id=self.entry_a_id,
            title="Python学习任务",
            content="学习 Python 和 FastAPI",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["Python", "FastAPI", "Web开发"],
            created_at=now,
            updated_at=now,
            file_path=f"tasks/{self.entry_a_id}.md",
        )
        storage.sqlite.upsert_entry(entry_a, user_id=user_id)

        # 条目 B: 有重叠标签
        self.entry_b_id = "kctx-entry-b"
        entry_b = Task(
            id=self.entry_b_id,
            title="FastAPI后端开发",
            content="FastAPI 框架使用笔记",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["FastAPI", "Python", "API设计"],
            created_at=now,
            updated_at=now,
            file_path=f"notes/{self.entry_b_id}.md",
        )
        storage.sqlite.upsert_entry(entry_b, user_id=user_id)

        # 条目 C: 无标签
        self.entry_c_id = "kctx-entry-c"
        entry_c = Task(
            id=self.entry_c_id,
            title="无标签条目",
            content="这是一个没有标签的条目",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=now,
            updated_at=now,
            file_path=f"tasks/{self.entry_c_id}.md",
        )
        storage.sqlite.upsert_entry(entry_c, user_id=user_id)

        # 同时写入 markdown 文件，使 get_entry 能通过 markdown storage 读取
        md = storage.get_markdown_storage(user_id)
        for entry in [entry_a, entry_b, entry_c]:
            md.write_entry(entry)

    async def test_knowledge_context_with_tags(self, client: AsyncClient):
        """有标签的条目返回知识上下文子图"""
        response = await client.get(f"/entries/{self.entry_a_id}/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "center_concepts" in data

        # center_concepts = entry.tags
        assert set(data["center_concepts"]) == {"Python", "FastAPI", "Web开发"}

        # 应该有节点
        assert len(data["nodes"]) > 0

        # 验证节点结构
        node_names = set()
        for node in data["nodes"]:
            assert "id" in node
            assert "name" in node
            assert "entry_count" in node
            node_names.add(node["name"])

        # 种子概念应该在节点中
        assert "Python" in node_names
        assert "FastAPI" in node_names
        # 关联标签也应该出现（因为 SQLite 共现）
        # FastAPI 在条目 B 中还关联了 API设计，所以可能出现

        # 有边
        assert len(data["edges"]) > 0
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "relationship" in edge

    async def test_knowledge_context_node_structure(self, client: AsyncClient):
        """节点包含完整的字段结构"""
        response = await client.get(f"/entries/{self.entry_a_id}/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        for node in data["nodes"]:
            assert "id" in node
            assert "name" in node
            # category 可选
            assert "entry_count" in node
            assert isinstance(node["entry_count"], int)
            # mastery 可选（SQLite 降级时有值）
            assert "mastery" in node

    async def test_knowledge_context_empty_tags(self, client: AsyncClient):
        """无标签条目返回空子图"""
        response = await client.get(f"/entries/{self.entry_c_id}/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []
        assert data["center_concepts"] == []

    async def test_knowledge_context_entry_not_found(self, client: AsyncClient):
        """不存在的条目返回 404"""
        response = await client.get("/entries/nonexistent-entry-xyz/knowledge-context")
        assert response.status_code == 404

    async def test_knowledge_context_user_isolation(self, storage, client: AsyncClient):
        """只返回当前用户的数据"""
        # 创建另一个用户的条目
        other_user_id = "other-user-kctx-test"
        other_entry = Task(
            id="kctx-other-entry",
            title="其他用户条目",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["SecretConcept"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/kctx-other-entry.md",
        )
        storage.sqlite.upsert_entry(other_entry, user_id=other_user_id)

        # 当前用户的条目上下文不应包含其他用户的标签
        response = await client.get(f"/entries/{self.entry_a_id}/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        node_names = {n["name"] for n in data["nodes"]}
        assert "SecretConcept" not in node_names

    async def test_knowledge_context_co_occurrence_edges(self, client: AsyncClient):
        """共享标签的条目产生共现边"""
        response = await client.get(f"/entries/{self.entry_a_id}/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        # entry_a 有 [Python, FastAPI, Web开发]
        # entry_b 有 [FastAPI, Python, API设计]
        # 共同标签: Python, FastAPI
        # 所以子图中应该有 Python-FastAPI 共现边，也可能有 Python-Web开发, FastAPI-Web开发 等

        edges = data["edges"]
        assert len(edges) > 0

        # 至少应该有一条包含两个种子概念的边
        edge_pairs = {(e["source"], e["target"]) for e in edges}
        assert any(
            ("Python", "FastAPI") in edge_pairs or ("FastAPI", "Python") in edge_pairs
            for _ in [1]
        )

    async def test_knowledge_context_max_20_nodes(self, storage, client: AsyncClient):
        """子图节点不超过 20 个"""
        user_id = _make_test_user_id(client)
        now = datetime.now()

        # 创建大量不同标签的条目来测试节点限制
        tags_list = []
        for i in range(30):
            tag = f"Tag-{i:02d}"
            tags_list.append(tag)

        # 创建一个有大量标签的条目
        heavy_entry = Task(
            id="kctx-heavy",
            title="大量标签条目",
            content="test",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=tags_list,
            created_at=now,
            updated_at=now,
            file_path="tasks/kctx-heavy.md",
        )
        storage.sqlite.upsert_entry(heavy_entry, user_id=user_id)
        md = storage.get_markdown_storage(user_id)
        md.write_entry(heavy_entry)

        response = await client.get("/entries/kctx-heavy/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        assert len(data["nodes"]) <= 20

    async def test_knowledge_context_no_auth(self, storage):
        """无 token 返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.routers import deps

        deps.storage = storage
        deps.reset_all_services()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get(f"/entries/{self.entry_a_id}/knowledge-context")
            assert response.status_code == 401

    async def test_knowledge_context_sqlite_fallback(self, storage, client: AsyncClient):
        """SQLite 降级时 mastery 有值（非 null）"""
        response = await client.get(f"/entries/{self.entry_a_id}/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        # SQLite 降级模式下 mastery 应该有计算值
        for node in data["nodes"]:
            assert node["mastery"] is not None
            assert node["mastery"] in ("new", "beginner", "intermediate", "advanced")

    async def test_knowledge_context_cross_entry_concepts(self, client: AsyncClient):
        """其他条目中的关联概念也出现在子图中"""
        response = await client.get(f"/entries/{self.entry_a_id}/knowledge-context")
        assert response.status_code == 200

        data = response.json()
        node_names = {n["name"] for n in data["nodes"]}

        # entry_a 的标签
        assert "Python" in node_names
        assert "FastAPI" in node_names
        assert "Web开发" in node_names

        # entry_b 的 API设计 也应该出现（因为 FastAPI 共现）
        # 这取决于 SQLite 的 tag 共现逻辑
        # entry_a 和 entry_b 共享 FastAPI 和 Python，
        # entry_b 的 API设计 标签应该通过共现被拉入
        assert "API设计" in node_names
