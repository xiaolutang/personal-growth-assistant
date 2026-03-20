"""EntryMapper 单元测试"""
import pytest
from datetime import datetime

from app.mappers.entry_mapper import EntryMapper
from app.models import Task, Category, Priority, TaskStatus


class TestEntryMapper:
    """EntryMapper 测试"""

    def test_str_to_category(self):
        """测试字符串转 Category"""
        assert EntryMapper.str_to_category("project") == Category.PROJECT
        assert EntryMapper.str_to_category("task") == Category.TASK
        assert EntryMapper.str_to_category("note") == Category.NOTE
        assert EntryMapper.str_to_category("inbox") == Category.INBOX
        # 未知类型默认返回 NOTE
        assert EntryMapper.str_to_category("unknown") == Category.NOTE

    def test_str_to_status(self):
        """测试字符串转 TaskStatus"""
        assert EntryMapper.str_to_status("waitStart") == TaskStatus.WAIT_START
        assert EntryMapper.str_to_status("doing") == TaskStatus.DOING
        assert EntryMapper.str_to_status("complete") == TaskStatus.COMPLETE
        assert EntryMapper.str_to_status("paused") == TaskStatus.PAUSED
        assert EntryMapper.str_to_status("cancelled") == TaskStatus.CANCELLED
        # 空值默认返回 DOING
        assert EntryMapper.str_to_status(None) == TaskStatus.DOING
        assert EntryMapper.str_to_status("") == TaskStatus.DOING
        # 未知类型默认返回 DOING
        assert EntryMapper.str_to_status("unknown") == TaskStatus.DOING

    def test_str_to_priority(self):
        """测试字符串转 Priority"""
        assert EntryMapper.str_to_priority("high") == Priority.HIGH
        assert EntryMapper.str_to_priority("medium") == Priority.MEDIUM
        assert EntryMapper.str_to_priority("low") == Priority.LOW
        # 空值默认返回 MEDIUM
        assert EntryMapper.str_to_priority(None) == Priority.MEDIUM
        assert EntryMapper.str_to_priority("") == Priority.MEDIUM
        # 未知类型默认返回 MEDIUM
        assert EntryMapper.str_to_priority("unknown") == Priority.MEDIUM

    def test_parse_datetime(self):
        """测试日期时间解析"""
        # ISO 格式
        result = EntryMapper.parse_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

        # 带时区
        result = EntryMapper.parse_datetime("2024-01-15T10:30:00Z")
        assert result is not None

        # 空值
        assert EntryMapper.parse_datetime(None) is None
        assert EntryMapper.parse_datetime("") is None

        # 无效格式
        assert EntryMapper.parse_datetime("invalid") is None

    def test_task_to_response(self):
        """测试 Task 模型转响应字典"""
        task = Task(
            id="test-task",
            title="测试任务",
            content="这是测试内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=["测试", "单元测试"],
            file_path="/data/tasks/test-task.md",
            created_at=datetime(2024, 1, 15, 10, 30, 0),
            updated_at=datetime(2024, 1, 15, 11, 0, 0),
        )

        response = EntryMapper.task_to_response(task)

        assert response["id"] == "test-task"
        assert response["title"] == "测试任务"
        assert response["content"] == "这是测试内容"
        assert response["category"] == "task"
        assert response["status"] == "doing"
        assert response["priority"] == "high"
        assert response["tags"] == ["测试", "单元测试"]
        assert "2024-01-15" in response["created_at"]

    def test_dict_to_response(self):
        """测试字典转响应字典"""
        data = {
            "id": "test-note",
            "title": "测试笔记",
            "content": "笔记内容",
            "type": "note",  # 使用旧字段名 type
            "status": "complete",
            "priority": "low",
            "tags": ["学习"],
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T11:00:00",
            "file_path": "/data/notes/test-note.md",
        }

        response = EntryMapper.dict_to_response(data)

        assert response["id"] == "test-note"
        assert response["title"] == "测试笔记"
        assert response["category"] == "note"  # type 转换为 category
        assert response["status"] == "complete"
        assert response["priority"] == "low"

    def test_dict_to_response_with_category(self):
        """测试字典（含 category 字段）转响应字典"""
        data = {
            "id": "test-project",
            "title": "测试项目",
            "category": "project",  # 使用新字段名 category
            "status": "doing",
            "file_path": "/data/projects/test-project.md",
        }

        response = EntryMapper.dict_to_response(data)

        assert response["category"] == "project"
