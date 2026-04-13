"""StorageFactory 用户隔离目录测试"""
import os
from pathlib import Path

import pytest

from app.infrastructure.storage.storage_factory import StorageFactory
from app.models import Task, Category, TaskStatus, Priority
from datetime import datetime


def _make_entry(entry_id: str, category: Category = Category.TASK) -> Task:
    return Task(
        id=entry_id,
        title=f"测试-{entry_id}",
        content="测试内容",
        category=category,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path=f"{category.value}/{entry_id}.md",
    )


class TestStorageFactory:
    """StorageFactory 用户隔离"""

    def test_creates_user_dirs_on_first_access(self, tmp_path):
        """新用户首次访问时自动创建目录"""
        factory = StorageFactory(str(tmp_path))
        storage = factory.get_markdown_storage("usr_alice")

        user_dir = tmp_path / "users" / "usr_alice"
        assert user_dir.exists()
        assert (user_dir / "tasks").exists()
        assert (user_dir / "notes").exists()
        assert (user_dir / "projects").exists()

    def test_different_users_isolated_dirs(self, tmp_path):
        """不同用户目录隔离"""
        factory = StorageFactory(str(tmp_path))

        alice = factory.get_markdown_storage("usr_alice")
        bob = factory.get_markdown_storage("usr_bob")

        alice.write_entry(_make_entry("alice-task"))
        bob.write_entry(_make_entry("bob-task"))

        alice_dir = tmp_path / "users" / "usr_alice" / "tasks"
        bob_dir = tmp_path / "users" / "usr_bob" / "tasks"

        assert (alice_dir / "alice-task.md").exists()
        assert (bob_dir / "bob-task.md").exists()
        assert not (alice_dir / "bob-task.md").exists()
        assert not (bob_dir / "alice-task.md").exists()

    def test_cache_returns_same_instance(self, tmp_path):
        """缓存命中返回同一实例"""
        factory = StorageFactory(str(tmp_path))

        s1 = factory.get_markdown_storage("usr_alice")
        s2 = factory.get_markdown_storage("usr_alice")

        assert s1 is s2

    def test_data_isolation_between_users(self, tmp_path):
        """用户 A 的数据在用户 B 的目录中不存在"""
        factory = StorageFactory(str(tmp_path))

        alice = factory.get_markdown_storage("usr_alice")
        alice.write_entry(_make_entry("secret-note", Category.NOTE))

        bob = factory.get_markdown_storage("usr_bob")
        bob_entries = bob.list_entries(category=Category.NOTE)

        assert len(bob_entries) == 0

    def test_migrate_default_user(self, tmp_path):
        """迁移已有数据到 _default 用户"""
        # 在原始目录创建一些文件
        original = tmp_path / "original"
        (original / "tasks").mkdir(parents=True)
        (original / "notes").mkdir(parents=True)

        (original / "tasks" / "existing-task.md").write_text("# 测试\n内容")
        (original / "notes" / "existing-note.md").write_text("# 笔记\n内容")

        factory = StorageFactory(str(tmp_path / "data"))
        count = factory.migrate_default_user(str(original))

        assert count == 2

        # 验证 _default 目录有文件
        default_storage = factory.get_markdown_storage("_default")
        default_dir = tmp_path / "data" / "users" / "_default"
        assert (default_dir / "tasks" / "existing-task.md").exists()
        assert (default_dir / "notes" / "existing-note.md").exists()

    def test_migrate_idempotent(self, tmp_path):
        """迁移幂等，重复执行不报错"""
        original = tmp_path / "original"
        (original / "tasks").mkdir(parents=True)
        (original / "tasks" / "task.md").write_text("# T")

        factory = StorageFactory(str(tmp_path / "data"))

        count1 = factory.migrate_default_user(str(original))
        count2 = factory.migrate_default_user(str(original))

        assert count1 == 1
        assert count2 == 0  # 已存在不重复复制

    def test_migrate_inbox(self, tmp_path):
        """迁移 inbox.md"""
        original = tmp_path / "original"
        original.mkdir()
        (original / "inbox.md").write_text("# Inbox\n灵感")

        factory = StorageFactory(str(tmp_path / "data"))
        count = factory.migrate_default_user(str(original))

        assert count == 1
        default_dir = tmp_path / "data" / "users" / "_default"
        assert (default_dir / "inbox.md").exists()
