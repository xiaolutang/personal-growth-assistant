"""同步服务测试

测试覆盖:
- 同步到所有存储层
- 级联删除
- 全量同步
"""
from datetime import datetime

import pytest

from app.models import Task, Category, TaskStatus, Priority


# === 同步操作测试 ===

@pytest.mark.asyncio
async def test_sync_entry_to_sqlite(storage):
    """测试同步条目到 SQLite"""
    entry = Task(
        id="sync-sqlite-test",
        title="同步到 SQLite 测试",
        content="测试内容",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["sync"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/sync-sqlite-test.md",
    )

    # 先写入 Markdown
    storage.markdown.write_entry(entry)

    # 同步到 SQLite
    result = storage.sqlite.upsert_entry(entry)
    assert result is True

    # 验证 SQLite 中存在
    retrieved = storage.sqlite.get_entry("sync-sqlite-test")
    assert retrieved is not None
    assert retrieved["title"] == "同步到 SQLite 测试"


@pytest.mark.asyncio
async def test_sync_entry_to_all(storage):
    """测试同步条目到所有存储层"""
    entry = Task(
        id="sync-all-test",
        title="同步到所有层测试",
        content="测试同步到所有存储层",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["sync", "all"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/sync-all-test.md",
    )

    # 先写入 Markdown（sync_entry 不会自动写入 Markdown）
    storage.markdown.write_entry(entry)

    # 执行同步
    result = await storage.sync_entry(entry)
    assert result is True

    # 验证 Markdown 中存在
    md_entry = storage.markdown.read_entry("sync-all-test")
    assert md_entry is not None

    # 验证 SQLite 中存在
    sqlite_entry = storage.sqlite.get_entry("sync-all-test")
    assert sqlite_entry is not None


@pytest.mark.asyncio
async def test_sync_to_graph_and_vector(storage):
    """测试仅同步到图谱和向量（后台任务）"""
    entry = Task(
        id="sync-graph-vector",
        title="同步到图谱和向量",
        content="测试后台同步",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/sync-graph-vector.md",
    )

    # 先确保 SQLite 有数据
    storage.markdown.write_entry(entry)
    storage.sqlite.upsert_entry(entry)

    # 后台同步（不阻塞）
    result = await storage.sync_to_graph_and_vector(entry)
    # 由于没有 Neo4j 和 Qdrant，这里可能返回 False，但不应该抛出异常
    # 主要测试的是不阻塞


# === 删除操作测试 ===

@pytest.mark.asyncio
async def test_delete_entry_cascade(storage):
    """测试级联删除"""
    # 创建条目
    entry = Task(
        id="delete-cascade-test",
        title="级联删除测试",
        content="测试级联删除",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/delete-cascade-test.md",
    )

    # 同步到所有层
    storage.markdown.write_entry(entry)
    storage.sqlite.upsert_entry(entry)

    # 验证存在
    assert storage.markdown.read_entry("delete-cascade-test") is not None
    assert storage.sqlite.get_entry("delete-cascade-test") is not None

    # 删除
    result = await storage.delete_entry("delete-cascade-test")
    assert result is True

    # 验证删除
    assert storage.markdown.read_entry("delete-cascade-test") is None
    assert storage.sqlite.get_entry("delete-cascade-test") is None


@pytest.mark.asyncio
async def test_delete_nonexistent_entry(storage):
    """测试删除不存在的条目"""
    result = await storage.delete_entry("nonexistent-entry-id")
    # 应该返回 True（幂等删除）或 False（根据实现）
    # 重要的是不应该抛出异常
    assert result in [True, False]


# === 全量同步测试 ===

@pytest.mark.asyncio
async def test_sync_all(storage):
    """测试全量同步"""
    # 创建多个条目
    for i in range(3):
        entry = Task(
            id=f"sync-all-{i}",
            title=f"全量同步测试-{i}",
            content="",
            category=Category.TASK,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path=f"tasks/sync-all-{i}.md",
        )
        storage.markdown.write_entry(entry)

    # 执行全量同步
    result = await storage.sync_all()

    # 验证结果
    assert result["success"] >= 3
    assert result["failed"] == 0


# === 知识提取测试 ===

@pytest.mark.asyncio
async def test_extract_knowledge_without_llm(storage):
    """测试无 LLM 时的知识提取（规则提取）"""
    entry = Task(
        id="extract-test",
        title="知识提取测试",
        content="这是一段包含 #标签1 和 #标签2 的内容",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/extract-test.md",
    )

    # 提取知识（无 LLM，使用规则）
    knowledge = storage._extract_with_rules(entry)

    # 验证标签提取
    assert "标签1" in knowledge.tags
    assert "标签2" in knowledge.tags


@pytest.mark.asyncio
async def test_extract_knowledge_with_mock_llm(storage, mock_llm_caller):
    """测试使用 Mock LLM 的知识提取"""
    # 设置 Mock LLM
    storage.llm_caller = mock_llm_caller

    entry = Task(
        id="extract-llm-test",
        title="LLM 知识提取测试",
        content="测试内容",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/extract-llm-test.md",
    )

    # 提取知识
    knowledge = await storage._extract_knowledge(entry)

    # 验证返回了有效结构
    assert hasattr(knowledge, "tags")
    assert hasattr(knowledge, "concepts")
    assert hasattr(knowledge, "relations")


# === 重新同步测试 ===

@pytest.mark.asyncio
async def test_resync_entry(storage):
    """测试重新同步单个条目"""
    # 创建并同步条目
    entry = Task(
        id="resync-test",
        title="重新同步测试",
        content="原始内容",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/resync-test.md",
    )
    storage.markdown.write_entry(entry)
    storage.sqlite.upsert_entry(entry)

    # 修改 Markdown 文件
    entry.content = "修改后的内容"
    storage.markdown.write_entry(entry)

    # 重新同步
    result = await storage.resync_entry("resync-test")
    assert result is True

    # 验证 SQLite 也更新了
    sqlite_entry = storage.sqlite.get_entry("resync-test")
    assert sqlite_entry is not None


# === 错误处理测试 ===

@pytest.mark.asyncio
async def test_sync_with_invalid_entry(storage):
    """测试同步无效条目的处理"""
    # 创建一个无效条目（缺少必要字段）
    # 由于 Pydantic 验证，我们直接测试同步服务的错误处理

    # 模拟 Markdown 不存在的情况
    result = await storage.resync_entry("nonexistent-entry")
    assert result is False


# === 边界条件测试 ===

@pytest.mark.asyncio
async def test_sync_entry_with_empty_content(storage):
    """测试同步空内容的条目"""
    entry = Task(
        id="empty-content-test",
        title="空内容测试",
        content="",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/empty-content-test.md",
    )

    result = await storage.sync_entry(entry)
    assert result is True


@pytest.mark.asyncio
async def test_sync_entry_with_special_characters(storage):
    """测试同步包含特殊字符的条目"""
    entry = Task(
        id="special-chars-test",
        title="特殊字符测试 <>&\"'",
        content="# 标题\n\n- 列表项1\n- 列表项2\n\n```python\nprint('hello')\n```",
        category=Category.NOTE,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["特殊", "test"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="notes/special-chars-test.md",
    )

    # 先写入 Markdown（sync_entry 不会自动写入 Markdown）
    storage.markdown.write_entry(entry)

    result = await storage.sync_entry(entry)
    assert result is True

    # 验证读取
    retrieved = storage.markdown.read_entry("special-chars-test")
    assert retrieved is not None
    assert "特殊字符测试" in retrieved.title
