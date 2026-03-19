"""测试 DTO 转换函数"""
import pytest
from datetime import datetime

from app.dto import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    SearchResult,
    SuccessResponse,
    ProjectProgressResponse,
    task_to_response,
    dict_to_response,
)
from app.models import Task, Category, TaskStatus, Priority


class TestEntryCreate:
    """EntryCreate DTO 测试"""

    def test_entry_create_minimal(self):
        """测试最小化创建请求"""
        entry = EntryCreate(type="task", title="测试任务")
        assert entry.type == "task"
        assert entry.title == "测试任务"
        assert entry.content == ""
        assert entry.tags == []

    def test_entry_create_full(self):
        """测试完整创建请求"""
        entry = EntryCreate(
            type="project",
            title="测试项目",
            content="项目描述",
            tags=["重要"],
            status="doing",
            priority="high",
            parent_id="parent-001",
            planned_date="2026-03-20",
            time_spent=120,
        )
        assert entry.type == "project"
        assert entry.title == "测试项目"
        assert entry.content == "项目描述"
        assert entry.tags == ["重要"]
        assert entry.status == "doing"
        assert entry.priority == "high"


class TestEntryUpdate:
    """EntryUpdate DTO 测试"""

    def test_entry_update_partial(self):
        """测试部分更新"""
        entry = EntryUpdate(title="新标题")
        assert entry.title == "新标题"
        assert entry.content is None
        assert entry.status is None

    def test_entry_update_multiple(self):
        """测试多字段更新"""
        entry = EntryUpdate(
            title="更新标题",
            status="complete",
            priority="high",
            tags=["新标签"],
        )
        assert entry.title == "更新标题"
        assert entry.status == "complete"
        assert entry.priority == "high"
        assert entry.tags == ["新标签"]


class TestEntryResponse:
    """EntryResponse DTO 测试"""

    def test_entry_response_creation(self):
        """测试响应创建"""
        response = EntryResponse(
            id="task-001",
            title="测试",
            content="内容",
            category="task",
            status="doing",
            priority="medium",
            tags=["test"],
            created_at="2026-03-20T10:00:00",
            updated_at="2026-03-20T10:00:00",
            file_path="tasks/task-001.md",
        )
        assert response.id == "task-001"
        assert response.title == "测试"
        assert response.category == "task"
        assert response.planned_date is None


class TestTaskToResponse:
    """task_to_response 转换函数测试"""

    def test_convert_task(self):
        """测试 Task 模型转 Response"""
        now = datetime(2026, 3, 20, 10, 0, 0)
        task = Task(
            id="task-001",
            title="测试任务",
            content="任务内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=["测试"],
            created_at=now,
            updated_at=now,
            file_path="tasks/task-001.md",
        )

        response = task_to_response(task)

        assert isinstance(response, EntryResponse)
        assert response.id == "task-001"
        assert response.title == "测试任务"
        assert response.category == "task"
        assert response.status == "doing"
        assert response.priority == "high"
        assert response.tags == ["测试"]
        assert response.created_at == now.isoformat()

    def test_convert_task_with_optional_fields(self):
        """测试带可选字段的转换"""
        now = datetime(2026, 3, 20, 10, 0, 0)
        task = Task(
            id="task-002",
            title="带可选字段",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=now,
            updated_at=now,
            planned_date=now,
            completed_at=now,
            time_spent=60,
            parent_id="project-001",
            file_path="tasks/task-002.md",
        )

        response = task_to_response(task)

        assert response.planned_date == now.isoformat()
        assert response.completed_at == now.isoformat()
        assert response.time_spent == 60
        assert response.parent_id == "project-001"


class TestDictToResponse:
    """dict_to_response 转换函数测试"""

    def test_convert_dict(self):
        """测试字典转 Response"""
        data = {
            "id": "task-003",
            "title": "字典任务",
            "content": "字典内容",
            "category": "task",
            "type": "task",
            "status": "doing",
            "priority": "low",
            "tags": ["dict"],
            "created_at": "2026-03-20T10:00:00",
            "updated_at": "2026-03-20T10:00:00",
            "file_path": "tasks/task-003.md",
        }

        response = dict_to_response(data)

        assert isinstance(response, EntryResponse)
        assert response.id == "task-003"
        assert response.title == "字典任务"
        assert response.category == "task"
        assert response.priority == "low"

    def test_convert_dict_missing_fields(self):
        """测试缺失字段使用默认值"""
        data = {
            "id": "task-004",
            "title": "缺失字段任务",
        }

        response = dict_to_response(data)

        assert response.id == "task-004"
        assert response.content == ""
        assert response.status == "doing"
        assert response.priority == "medium"
        assert response.tags == []


class TestSuccessResponse:
    """SuccessResponse 测试"""

    def test_success_response(self):
        """测试成功响应"""
        response = SuccessResponse(success=True, message="操作成功")
        assert response.success is True
        assert response.message == "操作成功"

    def test_error_response(self):
        """测试失败响应"""
        response = SuccessResponse(success=False, message="操作失败")
        assert response.success is False


class TestProjectProgressResponse:
    """ProjectProgressResponse 测试"""

    def test_progress_response(self):
        """测试进度响应"""
        response = ProjectProgressResponse(
            project_id="project-001",
            total_tasks=10,
            completed_tasks=6,
            progress_percentage=60.0,
            status_distribution={"doing": 4, "complete": 6},
        )
        assert response.project_id == "project-001"
        assert response.total_tasks == 10
        assert response.completed_tasks == 6
        assert response.progress_percentage == 60.0


class TestSearchResult:
    """SearchResult 测试"""

    def test_search_result(self):
        """测试搜索结果"""
        entries = [
            EntryResponse(
                id="task-001",
                title="结果1",
                content="内容1",
                category="task",
                status="doing",
                priority="medium",
                tags=[],
                created_at="2026-03-20T10:00:00",
                updated_at="2026-03-20T10:00:00",
                file_path="tasks/task-001.md",
            )
        ]
        result = SearchResult(entries=entries, query="测试")
        assert len(result.entries) == 1
        assert result.query == "测试"
