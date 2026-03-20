"""Knowledge API 集成测试 - 真实 Neo4j"""
import pytest
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority, Concept, ConceptRelation


@pytest.mark.integration
class TestKnowledgeIntegration:
    """Knowledge API 集成测试 - 真实 Neo4j"""

    @pytest.fixture
    def sample_entry(self):
        """创建测试用条目"""
        return Task(
            id="knowledge-test-1",
            title="知识图谱测试任务",
            content="这是一个用于知识图谱测试的任务",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["knowledge", "test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/knowledge-test-1.md",
        )

    @pytest.fixture
    def sample_concept(self):
        """创建测试用概念"""
        return Concept(
            name="测试概念",
            description="用于集成测试的概念",
            category="技术",
        )

    async def test_create_and_get_entry(self, neo4j_client_with_container, sample_entry):
        """测试创建和获取条目"""
        client = neo4j_client_with_container

        # 创建
        result = await client.create_entry(sample_entry)
        assert result is True

        # 获取
        entry = await client.get_entry(sample_entry.id)
        assert entry is not None
        assert entry["id"] == sample_entry.id
        assert entry["title"] == sample_entry.title

        # 清理
        await client.delete_entry(sample_entry.id)

    async def test_update_entry(self, neo4j_client_with_container, sample_entry):
        """测试更新条目"""
        client = neo4j_client_with_container

        # 创建
        await client.create_entry(sample_entry)

        # 更新标题
        sample_entry.title = "更新后的标题"
        result = await client.update_entry(sample_entry)
        assert result is True

        # 验证更新
        entry = await client.get_entry(sample_entry.id)
        assert entry["title"] == "更新后的标题"

        # 清理
        await client.delete_entry(sample_entry.id)

    async def test_delete_entry(self, neo4j_client_with_container, sample_entry):
        """测试删除条目"""
        client = neo4j_client_with_container

        # 创建
        await client.create_entry(sample_entry)

        # 删除
        result = await client.delete_entry(sample_entry.id)
        assert result is True

        # 验证删除
        entry = await client.get_entry(sample_entry.id)
        assert entry is None

    async def test_create_and_get_concept(self, neo4j_client_with_container, sample_concept):
        """测试创建和获取概念"""
        client = neo4j_client_with_container

        # 创建
        result = await client.create_concept(sample_concept)
        assert result is True

        # 获取
        concept = await client.get_concept(sample_concept.name)
        assert concept is not None
        assert concept["name"] == sample_concept.name

    async def test_create_entry_mentions(self, neo4j_client_with_container, sample_entry):
        """测试创建条目与概念的关系"""
        client = neo4j_client_with_container

        # 创建条目
        await client.create_entry(sample_entry)

        # 创建关系
        result = await client.create_entry_mentions(
            sample_entry.id,
            ["Python", "FastAPI"]
        )
        assert result is True

        # 验证概念被创建
        python_concept = await client.get_concept("Python")
        assert python_concept is not None

        # 清理
        await client.delete_entry(sample_entry.id)

    async def test_create_concept_relation(self, neo4j_client_with_container):
        """测试创建概念之间的关系"""
        client = neo4j_client_with_container

        # 先创建概念
        concept_a = Concept(name="概念A", category="技术")
        concept_b = Concept(name="概念B", category="技术")
        await client.create_concept(concept_a)
        await client.create_concept(concept_b)

        # 创建关系
        relation = ConceptRelation(
            from_concept="概念A",
            to_concept="概念B",
            relation_type="RELATED_TO"
        )
        result = await client.create_concept_relation(relation)
        assert result is True

    async def test_list_entries(self, neo4j_client_with_container):
        """测试列出条目"""
        client = neo4j_client_with_container

        # 创建多个条目
        entries = [
            Task(
                id=f"list-test-{i}",
                title=f"列表测试任务 {i}",
                content=f"内容 {i}",
                category=Category.TASK,
                status=TaskStatus.DOING if i % 2 == 0 else TaskStatus.COMPLETE,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                file_path=f"tasks/list-test-{i}.md",
            )
            for i in range(3)
        ]

        for entry in entries:
            await client.create_entry(entry)

        # 列出所有
        all_entries = await client.list_entries()
        assert len(all_entries) >= 3

        # 过滤状态
        doing_entries = await client.list_entries(status="doing")
        for e in doing_entries:
            assert e["status"] == "doing"

        # 清理
        for entry in entries:
            await client.delete_entry(entry.id)


@pytest.mark.integration
class TestKnowledgeGraphTraversal:
    """知识图谱遍历测试"""

    async def test_get_entries_by_concept(self, neo4j_client_with_container):
        """测试获取提及某概念的所有条目"""
        client = neo4j_client_with_container

        # 创建条目
        entry1 = Task(
            id="concept-entry-1",
            title="概念测试条目1",
            content="内容1",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/concept-entry-1.md",
        )
        await client.create_entry(entry1)

        # 创建关系
        await client.create_entry_mentions(entry1.id, ["共享概念"])

        # 获取提及该概念的条目
        entries = await client.get_entries_by_concept("共享概念")
        assert len(entries) >= 1

        # 清理
        await client.delete_entry(entry1.id)

    async def test_get_entry_with_relations(self, neo4j_client_with_container):
        """测试获取条目及其关系"""
        client = neo4j_client_with_container

        # 创建条目
        entry = Task(
            id="relation-entry-1",
            title="关系测试条目",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/relation-entry-1.md",
        )
        await client.create_entry(entry)

        # 创建概念关系
        await client.create_entry_mentions(entry.id, ["关系概念"])

        # 获取条目及其关系
        result = await client.get_entry_with_relations(entry.id)
        assert result["entry"] is not None

        # 清理
        await client.delete_entry(entry.id)
