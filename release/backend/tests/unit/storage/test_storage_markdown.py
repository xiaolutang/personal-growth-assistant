"""测试 Markdown 存储层"""
import pytest
from datetime import datetime
from pathlib import Path

from app.models import Task, Category, TaskStatus, Priority
from app.infrastructure.storage.markdown import MarkdownStorage


class TestMarkdownStorage:
    """MarkdownStorage 测试"""

    def test_init_creates_dirs(self, temp_data_dir: str):
        """测试初始化创建目录"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        assert (Path(temp_data_dir) / "projects").exists()
        assert (Path(temp_data_dir) / "tasks").exists()
        assert (Path(temp_data_dir) / "notes").exists()

    def test_write_and_read_entry(self, temp_data_dir: str):
        """测试写入和读取条目"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        now = datetime(2026, 3, 20, 10, 0, 0)
        task = Task(
            id="task-001",
            title="测试任务",
            content="这是测试内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["测试"],
            created_at=now,
            updated_at=now,
            file_path="tasks/task-001.md",
        )

        # 写入
        file_path = storage.write_entry(task)
        assert Path(temp_data_dir) / "tasks" / "task-001.md"

        # 读取
        read_task = storage.read_entry("task-001")
        assert read_task is not None
        assert read_task.id == "task-001"
        assert read_task.title == "测试任务"
        assert read_task.category == Category.TASK
        assert read_task.status == TaskStatus.DOING
        assert read_task.tags == ["测试"]

    def test_write_with_front_matter(self, temp_data_dir: str):
        """测试 YAML Front Matter 格式写入"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        now = datetime(2026, 3, 20, 10, 0, 0)
        task = Task(
            id="project-001",
            title="测试项目",
            content="# 项目描述\n\n项目内容",
            category=Category.PROJECT,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=["项目"],
            created_at=now,
            updated_at=now,
            planned_date=now,
            time_spent=120,
            parent_id=None,
            file_path="projects/project-001.md",
        )

        storage.write_entry(task)

        # 验证文件内容
        file_path = Path(temp_data_dir) / "projects" / "project-001.md"
        content = file_path.read_text(encoding="utf-8")

        # 检查 Front Matter
        assert content.startswith("---")
        assert "id: project-001" in content
        assert "title: 测试项目" in content
        assert "type: project" in content
        assert "status: doing" in content
        assert "priority: high" in content

    def test_read_entry_not_found(self, temp_data_dir: str):
        """测试读取不存在的条目"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        result = storage.read_entry("nonexistent")
        assert result is None

    def test_delete_entry(self, temp_data_dir: str):
        """测试删除条目"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        # 创建并写入
        task = Task(
            id="task-delete",
            title="待删除",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/task-delete.md",
        )
        storage.write_entry(task)

        # 验证存在
        assert storage.read_entry("task-delete") is not None

        # 删除
        result = storage.delete_entry("task-delete")
        assert result is True

        # 验证不存在
        assert storage.read_entry("task-delete") is None

    def test_delete_entry_not_found(self, temp_data_dir: str):
        """测试删除不存在的条目"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        result = storage.delete_entry("nonexistent")
        assert result is False

    def test_list_entries(self, temp_data_dir: str):
        """测试列出条目"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        # 创建多个条目
        for i in range(3):
            task = Task(
                id=f"task-{i:03d}",
                title=f"任务{i}",
                content=f"内容{i}",
                category=Category.TASK,
                status=TaskStatus.DOING if i < 2 else TaskStatus.COMPLETE,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                file_path=f"tasks/task-{i:03d}.md",
            )
            storage.write_entry(task)

        # 列出所有
        entries = storage.list_entries(category=Category.TASK)
        assert len(entries) == 3

        # 按状态筛选
        doing_entries = storage.list_entries(
            category=Category.TASK,
            status=TaskStatus.DOING
        )
        assert len(doing_entries) == 2

    def test_list_entries_with_limit(self, temp_data_dir: str):
        """测试限制返回数量"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        # 创建 5 个条目
        for i in range(5):
            task = Task(
                id=f"note-{i:03d}",
                title=f"笔记{i}",
                content="",
                category=Category.NOTE,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=[],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                file_path=f"notes/note-{i:03d}.md",
            )
            storage.write_entry(task)

        # 限制数量
        entries = storage.list_entries(category=Category.NOTE, limit=3)
        assert len(entries) == 3

    def test_parse_old_format(self, temp_data_dir: str):
        """测试解析旧格式（无 Front Matter）"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        # 写入旧格式文件
        old_content = """# 旧格式笔记

> 2026-03-20

这是旧格式的内容。
包含 #标签1 #标签2
"""
        file_path = Path(temp_data_dir) / "notes" / "old-note.md"
        file_path.write_text(old_content, encoding="utf-8")

        # 读取并验证
        entry = storage.read_entry("old-note")
        assert entry is not None
        assert entry.title == "旧格式笔记"
        assert "标签1" in entry.tags or "标签2" in entry.tags
        assert entry.category == Category.NOTE

    def test_different_categories(self, temp_data_dir: str):
        """测试不同类型的条目存储"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        now = datetime.now()

        # 创建任务
        task = Task(
            id="task-001",
            title="任务",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=now,
            updated_at=now,
            file_path="tasks/task-001.md",
        )
        storage.write_entry(task)

        # 创建项目
        project = Task(
            id="project-001",
            title="项目",
            content="",
            category=Category.PROJECT,
            status=TaskStatus.DOING,
            priority=Priority.HIGH,
            tags=[],
            created_at=now,
            updated_at=now,
            file_path="projects/project-001.md",
        )
        storage.write_entry(project)

        # 创建笔记
        note = Task(
            id="note-001",
            title="笔记",
            content="",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.LOW,
            tags=[],
            created_at=now,
            updated_at=now,
            file_path="notes/note-001.md",
        )
        storage.write_entry(note)

        # 验证路径
        assert (Path(temp_data_dir) / "tasks" / "task-001.md").exists()
        assert (Path(temp_data_dir) / "projects" / "project-001.md").exists()
        assert (Path(temp_data_dir) / "notes" / "note-001.md").exists()

    def test_scan_all(self, temp_data_dir: str):
        """测试扫描所有文件"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        # 创建多个条目
        now = datetime.now()
        for i in range(2):
            for cat, dir_name in [(Category.TASK, "tasks"), (Category.NOTE, "notes")]:
                task = Task(
                    id=f"{cat.value}-{i:03d}",
                    title=f"{cat.value}-{i}",
                    content="",
                    category=cat,
                    status=TaskStatus.DOING,
                    priority=Priority.MEDIUM,
                    tags=[],
                    created_at=now,
                    updated_at=now,
                    file_path=f"{dir_name}/{cat.value}-{i:03d}.md",
                )
                storage.write_entry(task)

        entries = storage.scan_all()
        assert len(entries) >= 4


class TestFrontMatterParsing:
    """Front Matter 解析测试"""

    def test_parse_front_matter(self, temp_data_dir: str):
        """测试解析 Front Matter"""
        storage = MarkdownStorage(data_dir=temp_data_dir)

        content = """---
id: test-001
title: 测试标题
type: task
status: doing
priority: high
tags:
  - tag1
  - tag2
created_at: '2026-03-20T10:00:00'
updated_at: '2026-03-20T10:00:00'
---

# 正文内容

这是正文。
"""
        file_path = Path(temp_data_dir) / "notes" / "test-fm.md"
        file_path.write_text(content, encoding="utf-8")

        entry = storage.read_entry("test-fm")

        assert entry is not None
        assert entry.id == "test-001"
        assert entry.title == "测试标题"
        assert entry.category == Category.TASK
        assert entry.status == TaskStatus.DOING
        assert entry.priority == Priority.HIGH
        assert "tag1" in entry.tags
        assert "tag2" in entry.tags
        assert "正文内容" in entry.content
