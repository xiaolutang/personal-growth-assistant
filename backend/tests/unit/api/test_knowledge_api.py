"""知识图谱 API 测试

测试覆盖:
- 全局图谱 API (GET /knowledge-map)
- 概念统计 API (GET /knowledge/stats)
- 掌握度计算
- 视图模式切换
- 用户隔离
- 空数据边界
- 现有 API 回归
"""
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models import Task, Category, TaskStatus, Priority


def _make_test_user_id(client) -> str:
    """从 client 认证头中提取测试用户 ID"""
    from app.routers import deps
    user_storage = deps._user_storage
    user = user_storage.get_by_username("testuser")
    return user.id if user else "test-user"


class TestKnowledgeMapAPI:
    """知识图谱 API 测试"""

    @pytest.fixture(autouse=True)
    async def setup_data(self, storage, client):
        """每个测试前准备数据"""
        if storage.sqlite:
            storage.sqlite.clear_all()

        user_id = _make_test_user_id(client)
        now = datetime.now()

        # 创建带标签的任务
        for i in range(3):
            entry = Task(
                id=f"kmap-task-{i}",
                title=f"Python学习任务-{i}",
                content="学习 Python 编程",
                category=Category.TASK,
                status=TaskStatus.COMPLETE if i == 0 else TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["Python", "编程"],
                created_at=now,
                updated_at=now,
                file_path=f"tasks/kmap-task-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        # 创建带标签的笔记
        for i in range(4):
            note = Task(
                id=f"kmap-note-{i}",
                title=f"Python学习笔记-{i}",
                content="Python 笔记内容",
                category=Category.NOTE,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["Python", "编程", "AI"],
                created_at=now,
                updated_at=now,
                file_path=f"notes/kmap-note-{i}.md",
            )
            storage.sqlite.upsert_entry(note, user_id=user_id)

        # 创建不同主题的条目
        entry_other = Task(
            id="kmap-task-other",
            title="FastAPI后端开发",
            content="FastAPI 框架使用",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["FastAPI", "Python"],
            created_at=now,
            updated_at=now,
            file_path="tasks/kmap-task-other.md",
        )
        storage.sqlite.upsert_entry(entry_other, user_id=user_id)

    async def test_knowledge_map_with_data(self, client: AsyncClient):
        """有条目时返回图谱数据含 nodes 和 edges"""
        response = await client.get("/knowledge-map")
        assert response.status_code == 200

        data = response.json()
        assert "nodes" in data
        assert "edges" in data

        nodes = data["nodes"]
        edges = data["edges"]

        assert len(nodes) > 0
        # 应该包含 Python, 编程, AI, FastAPI 概念
        node_names = {n["name"] for n in nodes}
        assert "Python" in node_names
        assert "编程" in node_names

        # 验证节点结构
        for node in nodes:
            assert "id" in node
            assert "name" in node
            assert "mastery" in node
            assert "entry_count" in node
            assert node["mastery"] in ("new", "beginner", "intermediate", "advanced")

        # 有共同标签的条目应该产生边
        assert len(edges) > 0
        for edge in edges:
            assert "source" in edge
            assert "target" in edge
            assert "relationship" in edge

    async def test_mastery_calculation(self, storage, client: AsyncClient):
        """掌握度计算正确"""
        user_id = _make_test_user_id(client)

        # Python 有 3 任务 + 4 笔记 + 1 其他 = 8 条目，6+ 且有大量笔记
        response = await client.get("/knowledge-map")
        data = response.json()

        nodes_by_name = {n["name"]: n for n in data["nodes"]}

        python_node = nodes_by_name.get("Python")
        assert python_node is not None
        assert python_node["entry_count"] >= 6
        assert python_node["mastery"] == "advanced"

    async def test_knowledge_stats(self, client: AsyncClient):
        """统计接口返回正确计数和分布"""
        response = await client.get("/knowledge/stats")
        assert response.status_code == 200

        data = response.json()
        assert "concept_count" in data
        assert "relation_count" in data
        assert "category_distribution" in data
        assert "top_concepts" in data

        # 至少有 Python, 编程, AI, FastAPI 4 个概念
        assert data["concept_count"] >= 3

        # top_concepts 按条目数排序
        top = data["top_concepts"]
        if len(top) > 1:
            assert top[0]["entry_count"] >= top[1]["entry_count"]

    async def test_knowledge_map_empty(self, storage, client: AsyncClient):
        """空图谱返回空数据"""
        storage.sqlite.clear_all()

        response = await client.get("/knowledge-map")
        assert response.status_code == 200

        data = response.json()
        assert data["nodes"] == []
        assert data["edges"] == []

    async def test_knowledge_stats_empty(self, storage, client: AsyncClient):
        """空数据统计返回零值"""
        storage.sqlite.clear_all()

        response = await client.get("/knowledge/stats")
        assert response.status_code == 200

        data = response.json()
        assert data["concept_count"] == 0
        assert data["relation_count"] == 0
        assert data["top_concepts"] == []

    async def test_knowledge_map_with_depth(self, client: AsyncClient):
        """depth 参数正常工作"""
        for depth in [1, 2, 3]:
            response = await client.get(f"/knowledge-map?depth={depth}")
            assert response.status_code == 200

    async def test_knowledge_map_user_isolation(self, storage, client: AsyncClient):
        """只返回当前用户的概念"""
        # 创建另一个用户的条目（带独特标签）
        other_user_id = "other-user-knowledge-test"
        entry = Task(
            id="kmap-other-user-1",
            title="其他用户专属任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["其他用户专属标签"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/kmap-other-user-1.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=other_user_id)

        # 当前用户不应看到其他用户的标签
        response = await client.get("/knowledge-map")
        assert response.status_code == 200

        data = response.json()
        node_names = {n["name"] for n in data["nodes"]}
        assert "其他用户专属标签" not in node_names

    async def test_existing_knowledge_api_unchanged(self, client: AsyncClient):
        """现有 knowledge API 不受影响（返回 503 因为 Neo4j 不可用）"""
        # knowledge-graph 需要概念名参数
        response = await client.get("/knowledge-graph/Python")
        # Neo4j 不可用应返回 503
        assert response.status_code == 503

        # learning-path 正常工作（有 SQLite 降级）
        response = await client.get("/learning-path/Python")
        assert response.status_code == 200

    async def test_knowledge_map_view_mastery(self, client: AsyncClient):
        """view=mastery 参数按掌握度排序"""
        response = await client.get("/knowledge-map?view=mastery")
        assert response.status_code == 200

        data = response.json()
        nodes = data["nodes"]
        if len(nodes) > 1:
            mastery_order = {"advanced": 0, "intermediate": 1, "beginner": 2, "new": 3}
            for i in range(len(nodes) - 1):
                curr = mastery_order.get(nodes[i]["mastery"], 4)
                next_val = mastery_order.get(nodes[i + 1]["mastery"], 4)
                assert curr <= next_val

    async def test_knowledge_map_view_project(self, client: AsyncClient):
        """view=project 参数正常工作"""
        response = await client.get("/knowledge-map?view=project")
        assert response.status_code == 200

        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    async def test_knowledge_map_view_domain(self, client: AsyncClient):
        """view=domain 参数（默认）按类别排序"""
        response = await client.get("/knowledge-map?view=domain")
        assert response.status_code == 200

        # 默认值也是 domain
        response2 = await client.get("/knowledge-map")
        assert response2.status_code == 200

    async def test_knowledge_map_invalid_view(self, client: AsyncClient):
        """无效的 view 参数返回 422"""
        response = await client.get("/knowledge-map?view=invalid")
        assert response.status_code == 422

    async def test_knowledge_map_no_auth(self, storage):
        """无 token 返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.routers import deps

        deps.storage = storage
        deps.reset_all_services()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/knowledge-map")
            assert response.status_code == 401

    async def test_knowledge_stats_no_auth(self, storage):
        """统计接口无 token 返回 401"""
        from httpx import ASGITransport, AsyncClient
        from app.main import app
        from app.routers import deps

        deps.storage = storage
        deps.reset_all_services()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/knowledge/stats")
            assert response.status_code == 401

    async def test_mastery_beginner(self, storage, client: AsyncClient):
        """单个条目的概念应为 beginner"""
        storage.sqlite.clear_all()
        user_id = _make_test_user_id(client)

        # 只创建 1 个带 "Rust" 标签的条目
        entry = Task(
            id="kmap-beginner-1",
            title="Rust入门",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["Rust"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/kmap-beginner-1.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=user_id)

        response = await client.get("/knowledge-map")
        data = response.json()

        nodes_by_name = {n["name"]: n for n in data["nodes"]}
        rust_node = nodes_by_name.get("Rust")
        assert rust_node is not None
        assert rust_node["mastery"] == "beginner"
        assert rust_node["entry_count"] == 1

    async def test_mastery_intermediate(self, storage, client: AsyncClient):
        """3 个条目且有最近活跃应为 intermediate"""
        storage.sqlite.clear_all()
        user_id = _make_test_user_id(client)
        now = datetime.now()

        # 创建 3 个带 "Go" 标签的条目
        for i in range(3):
            entry = Task(
                id=f"kmap-inter-{i}",
                title=f"Go学习-{i}",
                content="",
                category=Category.TASK,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=["Go"],
                created_at=now,
                updated_at=now,
                file_path=f"tasks/kmap-inter-{i}.md",
            )
            storage.sqlite.upsert_entry(entry, user_id=user_id)

        response = await client.get("/knowledge-map")
        data = response.json()

        nodes_by_name = {n["name"]: n for n in data["nodes"]}
        go_node = nodes_by_name.get("Go")
        assert go_node is not None
        assert go_node["mastery"] == "intermediate"

    async def test_stats_user_isolation(self, storage, client: AsyncClient):
        """统计接口也遵循用户隔离"""
        other_user_id = "other-user-stats-test"
        entry = Task(
            id="kmap-stats-other",
            title="其他用户统计任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["其他用户独有概念"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/kmap-stats-other.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=other_user_id)

        response = await client.get("/knowledge/stats")
        assert response.status_code == 200

        data = response.json()
        # 验证 top_concepts 中不包含其他用户的概念
        top_names = [c["name"] for c in data["top_concepts"]]
        assert "其他用户独有概念" not in top_names
