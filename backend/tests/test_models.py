"""测试数据模型"""
import pytest
from datetime import datetime

from app.models import Task, Category, TaskStatus, Priority, Concept, ConceptRelation, ExtractedKnowledge


class TestCategory:
    """Category 枚举测试"""

    def test_category_values(self):
        """测试枚举值"""
        assert Category.PROJECT.value == "project"
        assert Category.TASK.value == "task"
        assert Category.NOTE.value == "note"
        assert Category.INBOX.value == "inbox"

    def test_category_from_string(self):
        """测试从字符串创建枚举"""
        assert Category("project") == Category.PROJECT
        assert Category("task") == Category.TASK
        assert Category("note") == Category.NOTE
        assert Category("inbox") == Category.INBOX

    def test_category_invalid_value(self):
        """测试无效值抛出异常"""
        with pytest.raises(ValueError):
            Category("invalid")


class TestTaskStatus:
    """TaskStatus 枚举测试"""

    def test_status_values(self):
        """测试枚举值"""
        assert TaskStatus.WAIT_START.value == "waitStart"
        assert TaskStatus.DOING.value == "doing"
        assert TaskStatus.COMPLETE.value == "complete"
        assert TaskStatus.PAUSED.value == "paused"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_status_from_string(self):
        """测试从字符串创建枚举"""
        assert TaskStatus("waitStart") == TaskStatus.WAIT_START
        assert TaskStatus("doing") == TaskStatus.DOING
        assert TaskStatus("complete") == TaskStatus.COMPLETE


class TestPriority:
    """Priority 枚举测试"""

    def test_priority_values(self):
        """测试枚举值"""
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"


class TestTask:
    """Task 模型测试"""

    def test_task_creation_minimal(self):
        """测试最小化创建任务"""
        task = Task(
            id="task-001",
            title="测试任务",
            category=Category.TASK,
            file_path="tasks/task-001.md",
        )
        assert task.id == "task-001"
        assert task.title == "测试任务"
        assert task.category == Category.TASK
        assert task.status == TaskStatus.DOING  # 默认值
        assert task.priority == Priority.MEDIUM  # 默认值
        assert task.tags == []
        assert task.content == ""

    def test_task_creation_full(self):
        """测试完整创建任务"""
        now = datetime(2026, 3, 20, 10, 0, 0)
        task = Task(
            id="task-002",
            title="完整任务",
            content="任务内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=["重要", "紧急"],
            created_at=now,
            updated_at=now,
            planned_date=now,
            time_spent=60,
            parent_id="project-001",
            file_path="tasks/task-002.md",
        )
        assert task.id == "task-002"
        assert task.title == "完整任务"
        assert task.content == "任务内容"
        assert task.status == TaskStatus.DOING
        assert task.priority == Priority.HIGH
        assert task.tags == ["重要", "紧急"]
        assert task.time_spent == 60
        assert task.parent_id == "project-001"

    def test_task_default_timestamps(self):
        """测试默认时间戳"""
        task = Task(
            id="task-003",
            title="时间测试",
            category=Category.TASK,
            file_path="tasks/task-003.md",
        )
        assert task.created_at is not None
        assert task.updated_at is not None
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)


class TestConcept:
    """Concept 模型测试"""

    def test_concept_creation(self):
        """测试创建概念"""
        concept = Concept(
            name="MCP",
            description="Model Context Protocol",
            category="技术",
        )
        assert concept.name == "MCP"
        assert concept.description == "Model Context Protocol"
        assert concept.category == "技术"

    def test_concept_minimal(self):
        """测试最小化创建概念"""
        concept = Concept(name="LLM")
        assert concept.name == "LLM"
        assert concept.description is None
        assert concept.category is None


class TestConceptRelation:
    """ConceptRelation 模型测试"""

    def test_relation_creation(self):
        """测试创建概念关系"""
        relation = ConceptRelation(
            from_concept="MCP",
            to_concept="LLM",
            relation_type="PART_OF",
        )
        assert relation.from_concept == "MCP"
        assert relation.to_concept == "LLM"
        assert relation.relation_type == "PART_OF"


class TestExtractedKnowledge:
    """ExtractedKnowledge 模型测试"""

    def test_empty_knowledge(self):
        """测试空知识提取"""
        knowledge = ExtractedKnowledge()
        assert knowledge.tags == []
        assert knowledge.concepts == []
        assert knowledge.relations == []

    def test_full_knowledge(self):
        """测试完整知识提取"""
        concepts = [
            Concept(name="MCP", category="技术"),
            Concept(name="LLM", category="技术"),
        ]
        relations = [
            ConceptRelation(from_concept="MCP", to_concept="LLM", relation_type="RELATED_TO"),
        ]
        knowledge = ExtractedKnowledge(
            tags=["AI", "开发"],
            concepts=concepts,
            relations=relations,
        )
        assert knowledge.tags == ["AI", "开发"]
        assert len(knowledge.concepts) == 2
        assert len(knowledge.relations) == 1
