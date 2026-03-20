"""条目 CRUD 测试 - 边界条件和数据获取逻辑"""

import os
import tempfile
import shutil
import pytest
from datetime import datetime
from pathlib import Path

from app.infrastructure.storage.markdown import MarkdownStorage
from app.infrastructure.storage.sqlite import SQLiteStorage
from app.services.sync_service import SyncService
from app.services.entry_service import EntryService
from app.models import Task, Category, TaskStatus, Priority
from app.api.schemas import EntryCreate, EntryUpdate


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def markdown_storage(temp_data_dir):
    """创建 MarkdownStorage 实例"""
    return MarkdownStorage(data_dir=temp_data_dir)


@pytest.fixture
def sqlite_storage(temp_data_dir):
    """创建 SQLiteStorage 实例"""
    db_path = os.path.join(temp_data_dir, "test.db")
    return SQLiteStorage(db_path=db_path)


@pytest.fixture
def sync_service(markdown_storage, sqlite_storage):
    """创建 SyncService 实例"""
    return SyncService(markdown_storage=markdown_storage, sqlite_storage=sqlite_storage)


@pytest.fixture
def entry_service(sync_service):
    """创建 EntryService 实例"""
    return EntryService(storage=sync_service)


# === Markdown 解析边界测试 ===

class TestMarkdownParsingEdgeCases:
    """Markdown 解析边界条件测试"""

    def test_empty_file(self, markdown_storage):
        """测试空文件"""
        # 创建空文件
        file_path = markdown_storage.data_dir / "notes" / "test-empty.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")

        entry = markdown_storage.read_entry("test-empty")
        assert entry is not None
        assert entry.title == "Untitled"

    def test_only_whitespace(self, markdown_storage):
        """测试只有空白字符的文件"""
        file_path = markdown_storage.data_dir / "notes" / "test-whitespace.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("   \n\n   \t\n  ", encoding="utf-8")

        entry = markdown_storage.read_entry("test-whitespace")
        assert entry is not None

    def test_only_front_matter_no_body(self, markdown_storage):
        """测试只有 YAML Front Matter 没有正文"""
        file_path = markdown_storage.data_dir / "notes" / "test-no-body.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = """---
id: test-no-body
type: note
title: 只有元数据
status: doing
priority: medium
created_at: 2026-03-19T10:00:00
updated_at: 2026-03-19T10:00:00
tags: []
---
"""
        file_path.write_text(content, encoding="utf-8")

        entry = markdown_storage.read_entry("test-no-body")
        assert entry is not None
        assert entry.title == "只有元数据"
        assert entry.content == ""

    def test_malformed_yaml_front_matter(self, markdown_storage):
        """测试格式错误的 YAML Front Matter"""
        file_path = markdown_storage.data_dir / "notes" / "test-bad-yaml.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # 缺少结束的 ---
        content = """---
id: test-bad-yaml
type: note
title: 错误的YAML
status: doing

# 正文内容
这是正文
"""
        file_path.write_text(content, encoding="utf-8")

        entry = markdown_storage.read_entry("test-bad-yaml")
        # 应该回退到旧格式解析
        assert entry is not None

    def test_yaml_with_special_chars(self, markdown_storage):
        """测试 YAML 中包含特殊字符"""
        file_path = markdown_storage.data_dir / "notes" / "test-special.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = """---
id: test-special
type: note
title: "特殊字符: 测试 '引号' & <标签>"
status: doing
priority: medium
created_at: 2026-03-19T10:00:00
updated_at: 2026-03-19T10:00:00
tags:
  - "标签:带冒号"
  - "标签'带引号"
---
# 正文

包含特殊字符的内容：<script>alert('xss')</script>
"""
        file_path.write_text(content, encoding="utf-8")

        entry = markdown_storage.read_entry("test-special")
        assert entry is not None
        assert "特殊字符" in entry.title

    def test_very_long_content(self, markdown_storage):
        """测试非常长的内容"""
        file_path = markdown_storage.data_dir / "notes" / "test-long.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        long_body = "这是一段很长的内容。" * 10000
        content = f"""---
id: test-long
type: note
title: 长内容测试
status: doing
priority: medium
created_at: 2026-03-19T10:00:00
updated_at: 2026-03-19T10:00:00
tags: []
---

{long_body}
"""
        file_path.write_text(content, encoding="utf-8")

        entry = markdown_storage.read_entry("test-long")
        assert entry is not None
        assert len(entry.content) >= 100000

    def test_missing_required_fields(self, markdown_storage):
        """测试缺少必需字段"""
        file_path = markdown_storage.data_dir / "notes" / "test-missing.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # 缺少 id 和 type
        content = """---
title: 缺少必需字段
status: doing
---
正文内容
"""
        file_path.write_text(content, encoding="utf-8")

        entry = markdown_storage.read_entry("test-missing")
        assert entry is not None
        # 应该使用默认值
        assert entry.id == "test-missing"  # 从文件名获取

    def test_old_format_without_front_matter(self, markdown_storage):
        """测试旧格式（没有 Front Matter）"""
        file_path = markdown_storage.data_dir / "notes" / "test-old-format.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = """# 旧格式标题

> 2026-03-19

这是正文内容，带有 #标签1 #标签2
"""
        file_path.write_text(content, encoding="utf-8")

        entry = markdown_storage.read_entry("test-old-format")
        assert entry is not None
        assert entry.title == "旧格式标题"
        assert "标签1" in entry.tags
        assert "标签2" in entry.tags

    def test_unicode_and_emoji(self, markdown_storage):
        """测试 Unicode 和 Emoji"""
        file_path = markdown_storage.data_dir / "notes" / "test-unicode.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = """---
id: test-unicode
type: note
title: "🎉 Unicode 测试 你好世界"
status: doing
priority: medium
created_at: 2026-03-19T10:00:00
updated_at: 2026-03-19T10:00:00
tags:
  - "中文标签"
  - "emoji-🎊"
---

## 正文 📝

这是一段包含中文、English、数字123和emoji 🚀 的内容。

- 列表项 1
- 列表项 2
"""
        file_path.write_text(content, encoding="utf-8")

        entry = markdown_storage.read_entry("test-unicode")
        assert entry is not None
        assert "🎉" in entry.title
        assert "中文标签" in entry.tags


# === EntryService CRUD 测试 ===

class TestEntryServiceCRUD:
    """EntryService CRUD 操作测试"""

    @pytest.mark.asyncio
    async def test_create_and_read_entry(self, entry_service):
        """测试创建和读取条目"""
        request = EntryCreate(
            category="note",
            title="测试笔记",
            content="这是测试内容",
            tags=["测试"],
        )

        # 创建
        response = await entry_service.create_entry(request)
        assert response.id is not None
        assert response.title == "测试笔记"

        # 读取
        entry = await entry_service.get_entry(response.id)
        assert entry is not None
        assert entry.title == "测试笔记"
        assert entry.content == "这是测试内容"

    @pytest.mark.asyncio
    async def test_update_and_read_entry(self, entry_service):
        """测试更新和读取条目"""
        # 先创建
        create_request = EntryCreate(
            category="task",
            title="原始标题",
            content="原始内容",
            status="doing",
        )
        created = await entry_service.create_entry(create_request)

        # 更新
        update_request = EntryUpdate(
            title="更新后的标题",
            content="更新后的内容",
        )
        success, message = await entry_service.update_entry(created.id, update_request)
        assert success

        # 读取验证
        entry = await entry_service.get_entry(created.id)
        assert entry is not None
        assert entry.title == "更新后的标题"
        assert entry.content == "更新后的内容"

    @pytest.mark.asyncio
    async def test_update_content_multiple_times(self, entry_service):
        """测试多次更新内容（模拟前端编辑场景）"""
        # 创建
        create_request = EntryCreate(
            category="note",
            title="多次编辑测试",
            content="初始内容",
        )
        created = await entry_service.create_entry(create_request)

        # 第一次更新
        await entry_service.update_entry(created.id, EntryUpdate(content="第一次编辑"))

        # 第二次更新
        await entry_service.update_entry(created.id, EntryUpdate(content="第二次编辑"))

        # 第三次更新
        await entry_service.update_entry(created.id, EntryUpdate(content="第三次编辑，包含更多内容\n\n新段落"))

        # 验证最终结果
        entry = await entry_service.get_entry(created.id)
        assert entry is not None
        assert "第三次编辑" in entry.content
        assert "新段落" in entry.content

    @pytest.mark.asyncio
    async def test_read_nonexistent_entry(self, entry_service):
        """测试读取不存在的条目"""
        entry = await entry_service.get_entry("nonexistent-id")
        assert entry is None

    @pytest.mark.asyncio
    async def test_update_nonexistent_entry(self, entry_service):
        """测试更新不存在的条目"""
        success, message = await entry_service.update_entry(
            "nonexistent-id",
            EntryUpdate(title="新标题")
        )
        assert not success
        assert "不存在" in message

    @pytest.mark.asyncio
    async def test_delete_and_read_entry(self, entry_service):
        """测试删除后读取"""
        # 创建
        create_request = EntryCreate(
            category="note",
            title="将被删除",
            content="内容",
        )
        created = await entry_service.create_entry(create_request)

        # 确认存在
        entry = await entry_service.get_entry(created.id)
        assert entry is not None

        # 删除
        success, _ = await entry_service.delete_entry(created.id)
        assert success

        # 确认不存在
        entry = await entry_service.get_entry(created.id)
        assert entry is None


# === 文件编辑后读取测试 ===

class TestFileEditAndRead:
    """模拟外部编辑文件后的读取测试"""

    def test_external_edit_preserves_format(self, markdown_storage):
        """测试外部编辑后格式保持"""
        # 1. 先写入一个条目
        entry = Task(
            id="external-edit-test",
            title="外部编辑测试",
            content="原始内容",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/external-edit-test.md",
        )
        markdown_storage.write_entry(entry)

        # 2. 模拟外部编辑（直接修改文件）
        file_path = markdown_storage.data_dir / "notes" / "external-edit-test.md"
        original_content = file_path.read_text(encoding="utf-8")

        # 在正文末尾添加内容
        new_content = original_content + "\n\n## 新增章节\n\n这是外部编辑添加的内容。"
        file_path.write_text(new_content, encoding="utf-8")

        # 3. 重新读取
        read_entry = markdown_storage.read_entry("external-edit-test")
        assert read_entry is not None
        assert "新增章节" in read_entry.content
        assert "外部编辑添加" in read_entry.content

    def test_external_edit_changes_metadata(self, markdown_storage):
        """测试外部修改元数据后读取"""
        # 1. 写入
        entry = Task(
            id="metadata-change-test",
            title="元数据修改测试",
            content="内容",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["original"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="tasks/metadata-change-test.md",
        )
        markdown_storage.write_entry(entry)

        # 2. 修改文件中的元数据
        file_path = markdown_storage.data_dir / "tasks" / "metadata-change-test.md"
        content = file_path.read_text(encoding="utf-8")

        # 修改 status 和 tags
        content = content.replace("status: doing", "status: complete")
        content = content.replace("- original", "- modified")

        file_path.write_text(content, encoding="utf-8")

        # 3. 重新读取验证
        read_entry = markdown_storage.read_entry("metadata-change-test")
        assert read_entry is not None
        assert read_entry.status == TaskStatus.COMPLETE
        assert "modified" in read_entry.tags

    def test_corrupted_file_recovery(self, markdown_storage):
        """测试损坏文件的恢复（应该不崩溃）"""
        file_path = markdown_storage.data_dir / "notes" / "corrupted.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入损坏的内容（二进制数据混入）
        file_path.write_bytes(b"\x00\x01\x02\x03\xff\xfe invalid utf-8 \x00")

        # 读取不应该崩溃
        try:
            entry = markdown_storage.read_entry("corrupted")
            # 可能返回 None 或解析出默认值
        except Exception as e:
            # 如果抛出异常，记录但不应该崩溃整个应用
            print(f"Expected error for corrupted file: {e}")


# === 并发和缓存测试 ===

class TestConcurrencyAndCache:
    """并发和缓存一致性测试"""

    @pytest.mark.asyncio
    async def test_rapid_updates(self, entry_service):
        """测试快速连续更新"""
        # 创建
        create_request = EntryCreate(
            category="note",
            title="快速更新测试",
            content="v1",
        )
        created = await entry_service.create_entry(create_request)

        # 快速连续更新
        for i in range(10):
            await entry_service.update_entry(
                created.id,
                EntryUpdate(content=f"version-{i}")
            )

        # 验证最终状态
        entry = await entry_service.get_entry(created.id)
        assert entry is not None
        assert entry.content == "version-9"

    def test_markdown_sqlite_sync(self, markdown_storage, sqlite_storage):
        """测试 Markdown 和 SQLite 数据同步"""
        # 创建条目
        entry = Task(
            id="sync-test",
            title="同步测试",
            content="测试内容",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=["sync"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/sync-test.md",
        )

        # 写入 Markdown
        markdown_storage.write_entry(entry)

        # 同步到 SQLite
        sqlite_storage.upsert_entry(entry)

        # 从 Markdown 读取
        md_entry = markdown_storage.read_entry("sync-test")
        assert md_entry is not None

        # 从 SQLite 读取
        sqlite_entries = sqlite_storage.list_entries(limit=10)
        sqlite_entry = next((e for e in sqlite_entries if e.get("id") == "sync-test"), None)
        assert sqlite_entry is not None

        # 验证一致性
        assert md_entry.title == sqlite_entry.get("title")
        assert md_entry.status.value == sqlite_entry.get("status")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
