"""SQLite 存储层测试

测试覆盖:
- CRUD 操作
- 筛选功能
- FTS5 全文搜索
- 标签管理
"""
from datetime import datetime

import pytest

from app.models import Task, Category, TaskStatus, Priority


# === CRUD 操作测试 ===

def test_upsert_entry(sqlite_storage):
    """测试插入/更新条目"""
    entry = Task(
        id="test-entry-1",
        title="测试条目",
        content="测试内容",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["test"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/test-entry-1.md",
    )

    # 插入
    result = sqlite_storage.upsert_entry(entry)
    assert result is True

    # 查询验证
    retrieved = sqlite_storage.get_entry("test-entry-1")
    assert retrieved is not None
    assert retrieved["title"] == "测试条目"
    assert "test" in retrieved["tags"]

    # 更新
    entry.title = "更新后的标题"
    entry.tags = ["updated"]
    result = sqlite_storage.upsert_entry(entry)
    assert result is True

    # 验证更新
    updated = sqlite_storage.get_entry("test-entry-1")
    assert updated["title"] == "更新后的标题"
    assert "updated" in updated["tags"]


def test_delete_entry(sqlite_storage):
    """测试删除条目"""
    entry = Task(
        id="test-delete-1",
        title="待删除条目",
        content="",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/test-delete-1.md",
    )
    sqlite_storage.upsert_entry(entry)

    # 删除
    result = sqlite_storage.delete_entry("test-delete-1")
    assert result is True

    # 验证删除
    retrieved = sqlite_storage.get_entry("test-delete-1")
    assert retrieved is None


def test_get_nonexistent_entry(sqlite_storage):
    """测试获取不存在的条目"""
    result = sqlite_storage.get_entry("nonexistent-id")
    assert result is None


# === 列表查询测试 ===

def test_list_entries(sqlite_storage):
    """测试列表查询"""
    # 创建多个条目
    for i in range(5):
        entry = Task(
            id=f"list-test-{i}",
            title=f"列表测试-{i}",
            content=f"内容 {i}",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path=f"tasks/list-test-{i}.md",
        )
        sqlite_storage.upsert_entry(entry)

    # 查询
    results = sqlite_storage.list_entries(limit=10)
    assert len(results) >= 5


def test_filter_by_type(sqlite_storage):
    """测试按类型筛选"""
    # 创建不同类型的条目
    task_entry = Task(
        id="filter-task",
        title="任务",
        content="",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/filter-task.md",
    )
    project_entry = Task(
        id="filter-project",
        title="项目",
        content="",
        category=Category.PROJECT,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="projects/filter-project.md",
    )
    sqlite_storage.upsert_entry(task_entry)
    sqlite_storage.upsert_entry(project_entry)

    # 筛选任务
    results = sqlite_storage.list_entries(type="task")
    for r in results:
        assert r["type"] == "task"

    # 筛选项目
    results = sqlite_storage.list_entries(type="project")
    for r in results:
        assert r["type"] == "project"


def test_filter_by_status(sqlite_storage):
    """测试按状态筛选"""
    # 创建不同状态的条目
    for status in [TaskStatus.DOING, TaskStatus.COMPLETE, TaskStatus.WAIT_START]:
        entry = Task(
            id=f"status-{status.value}",
            title=f"状态测试-{status.value}",
            content="",
            category=Category.TASK,
            status=status,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path=f"tasks/status-{status.value}.md",
        )
        sqlite_storage.upsert_entry(entry)

    # 筛选完成状态
    results = sqlite_storage.list_entries(status="complete")
    for r in results:
        assert r["status"] == "complete"


def test_filter_by_tags(sqlite_storage):
    """测试按标签筛选"""
    # 创建带不同标签的条目
    entry1 = Task(
        id="tag-test-1",
        title="标签测试1",
        content="",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["work", "important"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/tag-test-1.md",
    )
    entry2 = Task(
        id="tag-test-2",
        title="标签测试2",
        content="",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["personal"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/tag-test-2.md",
    )
    sqlite_storage.upsert_entry(entry1)
    sqlite_storage.upsert_entry(entry2)

    # 按 work 标签筛选
    results = sqlite_storage.list_entries(tags=["work"])
    assert len(results) >= 1
    for r in results:
        assert "work" in r.get("tags", [])


def test_filter_by_parent(sqlite_storage):
    """测试按父级筛选"""
    # 创建父项目
    parent = Task(
        id="parent-project",
        title="父项目",
        content="",
        category=Category.PROJECT,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="projects/parent-project.md",
    )
    sqlite_storage.upsert_entry(parent)

    # 创建子任务
    for i in range(3):
        child = Task(
            id=f"child-task-{i}",
            title=f"子任务{i}",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path=f"tasks/child-task-{i}.md",
            parent_id="parent-project",
        )
        sqlite_storage.upsert_entry(child)

    # 按父级筛选
    results = sqlite_storage.list_entries(parent_id="parent-project")
    assert len(results) == 3


def test_count_entries(sqlite_storage):
    """测试统计数量"""
    # 清空
    sqlite_storage.clear_all()

    # 创建条目
    for i in range(5):
        entry = Task(
            id=f"count-test-{i}",
            title=f"统计测试-{i}",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING if i < 3 else TaskStatus.COMPLETE,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path=f"tasks/count-test-{i}.md",
        )
        sqlite_storage.upsert_entry(entry)

    # 统计总数
    total = sqlite_storage.count_entries()
    assert total == 5

    # 按状态统计
    doing_count = sqlite_storage.count_entries(status="doing")
    assert doing_count == 3

    complete_count = sqlite_storage.count_entries(status="complete")
    assert complete_count == 2


# === 全文搜索测试 ===

def test_search_fts5(sqlite_storage):
    """测试 FTS5 全文搜索"""
    # 创建带英文内容的条目
    entry = Task(
        id="search-english",
        title="English Task",
        content="This is a test task with English content for FTS5 search",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/search-english.md",
    )
    sqlite_storage.upsert_entry(entry)

    # 搜索
    results = sqlite_storage.search("English")
    assert len(results) >= 1
    assert any(r["id"] == "search-english" for r in results)


def test_search_chinese(sqlite_storage):
    """测试中文搜索（使用 LIKE 回退）"""
    # 创建中文内容条目
    entry = Task(
        id="search-chinese",
        title="中文搜索测试",
        content="这是一段中文内容，用于测试搜索功能",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/search-chinese.md",
    )
    sqlite_storage.upsert_entry(entry)

    # 搜索中文
    results = sqlite_storage.search("中文")
    assert len(results) >= 1
    assert any(r["id"] == "search-chinese" for r in results)


def test_search_in_content(sqlite_storage):
    """测试搜索内容中的关键词"""
    entry = Task(
        id="search-content",
        title="普通标题",
        content="这里有一个特殊关键词 PYTHON_PROGRAMMING",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/search-content.md",
    )
    sqlite_storage.upsert_entry(entry)

    # 搜索内容中的关键词
    results = sqlite_storage.search("PYTHON_PROGRAMMING")
    assert len(results) >= 1


# === 同步操作测试 ===

def test_sync_from_markdown(sqlite_storage, markdown_storage):
    """测试从 Markdown 同步"""
    # 在 Markdown 中创建条目
    entry = Task(
        id="sync-test-1",
        title="同步测试",
        content="同步内容",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["sync"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/sync-test-1.md",
    )
    markdown_storage.write_entry(entry)

    # 同步到 SQLite
    count = sqlite_storage.sync_from_markdown(markdown_storage)
    assert count >= 1

    # 验证同步结果
    retrieved = sqlite_storage.get_entry("sync-test-1")
    assert retrieved is not None
    assert retrieved["title"] == "同步测试"


# === 并发写入测试 ===

def test_concurrent_upsert(sqlite_storage):
    """测试并发写入（使用线程）"""
    import concurrent.futures

    def upsert_entry(idx):
        entry = Task(
            id=f"concurrent-{idx}",
            title=f"并发写入-{idx}",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path=f"tasks/concurrent-{idx}.md",
        )
        return sqlite_storage.upsert_entry(entry)

    # 并发写入 10 个条目
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(upsert_entry, range(10)))

    # 所有写入应该成功
    assert all(results)

    # 验证数据完整性
    for i in range(10):
        entry = sqlite_storage.get_entry(f"concurrent-{i}")
        assert entry is not None


# === 清理测试 ===

def test_clear_all(sqlite_storage):
    """测试清空所有数据"""
    # 创建一些条目
    for i in range(3):
        entry = Task(
            id=f"clear-test-{i}",
            title=f"清理测试-{i}",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path=f"tasks/clear-test-{i}.md",
        )
        sqlite_storage.upsert_entry(entry)

    # 清空
    result = sqlite_storage.clear_all()
    assert result is True

    # 验证清空
    count = sqlite_storage.count_entries()
    assert count == 0
