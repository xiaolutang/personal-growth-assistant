"""测试 EntryService 业务服务层"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.entry_service import EntryService
from app.models import Task, Category, TaskStatus, Priority
from app.api.schemas import EntryCreate, EntryUpdate


class TestEntryServiceHelpers:
    """EntryService 辅助方法测试"""

    @pytest.fixture
    def service(self, storage):
        """创建服务实例"""
        return EntryService(storage=storage)

    def test_parse_category_valid(self, service):
        """测试解析有效类型"""
        assert service._parse_category("task") == Category.TASK
        assert service._parse_category("project") == Category.PROJECT
        assert service._parse_category("note") == Category.NOTE
        assert service._parse_category("inbox") == Category.INBOX

    def test_parse_category_invalid(self, service):
        """测试解析无效类型 - 使用默认值而非抛出异常"""
        # EntryMapper 对无效类型返回 NOTE 作为默认值
        result = service._parse_category("invalid")
        assert result == Category.NOTE

    def test_parse_status_valid(self, service):
        """测试解析有效状态"""
        assert service._parse_status("doing") == TaskStatus.DOING
        assert service._parse_status("complete") == TaskStatus.COMPLETE
        assert service._parse_status("waitStart") == TaskStatus.WAIT_START
        assert service._parse_status("paused") == TaskStatus.PAUSED
        assert service._parse_status("cancelled") == TaskStatus.CANCELLED

    def test_parse_status_none(self, service):
        """测试解析空状态"""
        assert service._parse_status(None) == TaskStatus.DOING

    def test_parse_status_invalid(self, service):
        """测试解析无效状态 - 使用默认值而非抛出异常"""
        # EntryMapper 对无效状态返回 DOING 作为默认值
        result = service._parse_status("invalid")
        assert result == TaskStatus.DOING

    def test_parse_priority_valid(self, service):
        """测试解析有效优先级"""
        assert service._parse_priority("high") == Priority.HIGH
        assert service._parse_priority("medium") == Priority.MEDIUM
        assert service._parse_priority("low") == Priority.LOW

    def test_parse_priority_none(self, service):
        """测试解析空优先级"""
        assert service._parse_priority(None) == Priority.MEDIUM

    def test_parse_priority_invalid(self, service):
        """测试解析无效优先级 - 使用默认值而非抛出异常"""
        # EntryMapper 对无效优先级返回 MEDIUM 作为默认值
        result = service._parse_priority("invalid")
        assert result == Priority.MEDIUM

    def test_parse_datetime_valid(self, service):
        """测试解析有效日期"""
        result = service._parse_datetime("2026-03-20T10:00:00")
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 20

    def test_parse_datetime_with_z(self, service):
        """测试解析带 Z 后缀的日期"""
        result = service._parse_datetime("2026-03-20T10:00:00Z")
        assert result is not None
        assert result.year == 2026

    def test_parse_datetime_date_only(self, service):
        """测试解析仅日期格式"""
        result = service._parse_datetime("2026-03-20")
        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 20

    def test_parse_datetime_none(self, service):
        """测试解析空日期"""
        assert service._parse_datetime(None) is None

    def test_parse_datetime_invalid(self, service):
        """测试解析无效日期"""
        assert service._parse_datetime("invalid") is None

    def test_generate_entry_id(self, service):
        """测试生成条目 ID"""
        id1 = service._generate_entry_id(Category.TASK)
        id2 = service._generate_entry_id(Category.TASK)

        assert id1.startswith("task-")
        assert id2.startswith("task-")
        assert id1 != id2  # UUID 确保唯一性

        project_id = service._generate_entry_id(Category.PROJECT)
        assert project_id.startswith("project-")

    def test_get_file_path(self, service):
        """测试获取文件路径"""
        path = service._get_file_path(Category.TASK, "task-001")
        assert path == "tasks/task-001.md"

        path = service._get_file_path(Category.PROJECT, "project-001")
        assert path == "projects/project-001.md"

        path = service._get_file_path(Category.NOTE, "note-001")
        assert path == "notes/note-001.md"


class TestEntryServiceCRUD:
    """EntryService CRUD 操作测试"""

    @pytest.fixture
    def service(self, storage):
        """创建服务实例"""
        return EntryService(storage=storage)

    @pytest.mark.asyncio
    async def test_create_entry(self, service):
        """测试创建条目"""
        request = EntryCreate(
            category="task",
            title="测试任务",
            content="任务内容",
            tags=["测试"],
            status="doing",
            priority="high",
        )

        response = await service.create_entry(request)

        assert response.id.startswith("task-")
        assert response.title == "测试任务"
        assert response.category == "task"
        assert response.status == "doing"
        assert response.priority == "high"
        assert "测试" in response.tags

    @pytest.mark.asyncio
    async def test_create_entry_minimal(self, service):
        """测试最小化创建条目"""
        request = EntryCreate(category="note", title="简单笔记")

        response = await service.create_entry(request)

        assert response.id.startswith("note-")
        assert response.title == "简单笔记"
        assert response.category == "note"
        assert response.status == "doing"  # 默认值
        assert response.priority == "medium"  # 默认值

    @pytest.mark.asyncio
    async def test_get_entry(self, service):
        """测试获取条目"""
        # 先创建
        request = EntryCreate(category="task", title="获取测试")
        created = await service.create_entry(request)

        # 再获取
        response = await service.get_entry(created.id)

        assert response is not None
        assert response.id == created.id
        assert response.title == "获取测试"

    @pytest.mark.asyncio
    async def test_create_entry_writes_to_user_markdown_dir(self, service, temp_data_dir):
        """创建条目应写入当前用户目录，而不是根 data 目录"""
        request = EntryCreate(category="note", title="用户笔记")

        created = await service.create_entry(request, user_id="usr_alice")

        user_path = f"{temp_data_dir}/users/usr_alice/notes/{created.id}.md"
        root_path = f"{temp_data_dir}/notes/{created.id}.md"
        import os

        assert os.path.exists(user_path)
        assert not os.path.exists(root_path)

    @pytest.mark.asyncio
    async def test_get_entry_reads_from_user_markdown_dir(self, service):
        """读取条目应从当前用户目录读取 Markdown"""
        request = EntryCreate(category="project", title="Alice 项目")
        created = await service.create_entry(request, user_id="usr_alice")

        fetched = await service.get_entry(created.id, user_id="usr_alice")

        assert fetched is not None
        assert fetched.title == "Alice 项目"
        assert await service.get_entry(created.id, user_id="usr_bob") is None

    @pytest.mark.asyncio
    async def test_get_entry_not_found(self, service):
        """测试获取不存在的条目"""
        response = await service.get_entry("nonexistent-id")
        assert response is None

    @pytest.mark.asyncio
    async def test_update_entry_title(self, service):
        """测试更新标题"""
        # 先创建
        request = EntryCreate(category="task", title="原始标题")
        created = await service.create_entry(request)

        # 更新
        update = EntryUpdate(title="新标题")
        success, message = await service.update_entry(created.id, update)

        assert success is True
        assert "已更新" in message

        # 验证
        updated = await service.get_entry(created.id)
        assert updated.title == "新标题"

    @pytest.mark.asyncio
    async def test_update_entry_status(self, service):
        """测试更新状态"""
        # 先创建
        request = EntryCreate(category="task", title="状态测试")
        created = await service.create_entry(request)

        # 更新状态
        update = EntryUpdate(status="complete")
        success, message = await service.update_entry(created.id, update)

        assert success is True

        # 验证
        updated = await service.get_entry(created.id)
        assert updated.status == "complete"

    @pytest.mark.asyncio
    async def test_update_entry_not_found(self, service):
        """测试更新不存在的条目"""
        update = EntryUpdate(title="新标题")
        success, message = await service.update_entry("nonexistent", update)

        assert success is False
        assert "不存在" in message

    @pytest.mark.asyncio
    async def test_update_entry_no_changes(self, service):
        """测试无更改更新"""
        # 先创建
        request = EntryCreate(category="task", title="无更改测试")
        created = await service.create_entry(request)

        # 空更新
        update = EntryUpdate()
        success, message = await service.update_entry(created.id, update)

        assert success is True
        assert "无更新" in message

    @pytest.mark.asyncio
    async def test_delete_entry(self, service):
        """测试删除条目"""
        # 先创建
        request = EntryCreate(category="task", title="待删除")
        created = await service.create_entry(request)

        # 删除
        success, message = await service.delete_entry(created.id)

        assert success is True
        assert "已删除" in message

        # 验证删除
        deleted = await service.get_entry(created.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_entry_not_found(self, service):
        """测试删除不存在的条目"""
        success, message = await service.delete_entry("nonexistent")

        assert success is False
        assert "不存在" in message


class TestEntryServiceQuery:
    """EntryService 查询操作测试"""

    @pytest.fixture
    def service(self, storage):
        """创建服务实例"""
        return EntryService(storage=storage)

    @pytest.mark.asyncio
    async def test_list_entries(self, service):
        """测试列出条目"""
        # 创建多个条目
        for i in range(3):
            await service.create_entry(EntryCreate(
                category="task",
                title=f"列表测试{i}",
            ))

        response = await service.list_entries(type="task", limit=10)

        assert len(response.entries) >= 3
        assert response.total >= 3

    @pytest.mark.asyncio
    async def test_list_entries_with_status_filter(self, service):
        """测试按状态筛选"""
        # 创建不同状态的条目
        await service.create_entry(EntryCreate(category="task", title="进行中", status="doing"))
        await service.create_entry(EntryCreate(category="task", title="已完成", status="complete"))

        response = await service.list_entries(status="complete")

        for entry in response.entries:
            assert entry.status == "complete"

    @pytest.mark.asyncio
    async def test_search_entries(self, service):
        """测试搜索条目"""
        # 创建带特殊关键词的条目
        await service.create_entry(EntryCreate(
            category="note",
            title="搜索关键词测试",
            content="包含UNIQUE_KEYWORD的内容",
        ))

        response = await service.search_entries("UNIQUE_KEYWORD", limit=10)

        assert len(response.entries) >= 1
        assert response.query == "UNIQUE_KEYWORD"


class TestEntryServiceProjectProgress:
    """EntryService 项目进度测试"""

    @pytest.fixture
    def service(self, storage):
        """创建服务实例"""
        return EntryService(storage=storage)

    @pytest.mark.asyncio
    async def test_get_project_progress_empty(self, service):
        """测试空项目进度"""
        # 创建无子任务的项目
        project = await service.create_entry(EntryCreate(
            category="project",
            title="空项目",
        ))

        progress = await service.get_project_progress(project.id)

        assert progress.project_id == project.id
        assert progress.total_tasks == 0
        assert progress.completed_tasks == 0
        assert progress.progress_percentage == 0.0

    @pytest.mark.asyncio
    async def test_get_project_progress_with_tasks(self, service):
        """测试有子任务的项目进度"""
        # 创建项目
        project = await service.create_entry(EntryCreate(
            category="project",
            title="有任务的项目",
        ))

        # 创建子任务
        await service.create_entry(EntryCreate(
            category="task",
            title="子任务1",
            parent_id=project.id,
            status="complete",
        ))
        await service.create_entry(EntryCreate(
            category="task",
            title="子任务2",
            parent_id=project.id,
            status="doing",
        ))

        progress = await service.get_project_progress(project.id)

        assert progress.project_id == project.id
        assert progress.total_tasks == 2
        assert progress.completed_tasks == 1
        assert progress.progress_percentage == 50.0

    @pytest.mark.asyncio
    async def test_get_project_progress_not_found(self, service):
        """测试不存在的项目"""
        with pytest.raises(ValueError) as exc_info:
            await service.get_project_progress("nonexistent")
        assert "不存在" in str(exc_info.value)
