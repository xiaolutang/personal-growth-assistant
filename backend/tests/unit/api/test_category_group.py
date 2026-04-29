"""B02: category_group 查询参数测试

测试覆盖:
- category_group=actionable 只返回 task/decision/project
- category_group=knowledge 只返回 inbox/note/reflection/question
- category_group + type 同时传返回 422
- category_group + status 组合筛选正常
- 无 category_group 时行为向后兼容
"""
import pytest
from httpx import AsyncClient


# === category_group=actionable 测试 ===

@pytest.mark.asyncio
async def test_actionable_returns_task_decision_project(client: AsyncClient):
    """category_group=actionable 只返回 task/decision/project"""
    # 创建各类型条目
    await client.post("/entries", json={"category": "task", "title": "任务", "content": ""})
    await client.post("/entries", json={"category": "decision", "title": "决策", "content": ""})
    await client.post("/entries", json={"category": "project", "title": "项目", "content": ""})
    await client.post("/entries", json={"category": "note", "title": "笔记", "content": ""})
    await client.post("/entries", json={"category": "inbox", "title": "灵感", "content": ""})
    await client.post("/entries", json={"category": "reflection", "title": "复盘", "content": ""})
    await client.post("/entries", json={"category": "question", "title": "疑问", "content": ""})

    response = await client.get("/entries?category_group=actionable")
    assert response.status_code == 200
    data = response.json()
    categories = {e["category"] for e in data["entries"]}
    # 只包含 actionable 类型
    assert categories <= {"task", "decision", "project"}
    # 不包含 knowledge 类型
    assert "note" not in categories
    assert "inbox" not in categories
    assert "reflection" not in categories
    assert "question" not in categories


# === category_group=knowledge 测试 ===

@pytest.mark.asyncio
async def test_knowledge_returns_inbox_note_reflection_question(client: AsyncClient):
    """category_group=knowledge 只返回 inbox/note/reflection/question"""
    await client.post("/entries", json={"category": "task", "title": "任务", "content": ""})
    await client.post("/entries", json={"category": "decision", "title": "决策", "content": ""})
    await client.post("/entries", json={"category": "project", "title": "项目", "content": ""})
    await client.post("/entries", json={"category": "note", "title": "笔记", "content": ""})
    await client.post("/entries", json={"category": "inbox", "title": "灵感", "content": ""})
    await client.post("/entries", json={"category": "reflection", "title": "复盘", "content": ""})
    await client.post("/entries", json={"category": "question", "title": "疑问", "content": ""})

    response = await client.get("/entries?category_group=knowledge")
    assert response.status_code == 200
    data = response.json()
    categories = {e["category"] for e in data["entries"]}
    assert categories <= {"inbox", "note", "reflection", "question"}
    assert "task" not in categories
    assert "decision" not in categories
    assert "project" not in categories


# === 互斥性测试 ===

@pytest.mark.asyncio
async def test_category_group_and_type_mutually_exclusive(client: AsyncClient):
    """category_group + type 同时传返回 422"""
    response = await client.get("/entries?category_group=actionable&type=task")
    assert response.status_code == 422


# === 组合筛选测试 ===

@pytest.mark.asyncio
async def test_category_group_with_status(client: AsyncClient):
    """category_group + status 组合筛选正常"""
    await client.post("/entries", json={"category": "task", "title": "进行中任务", "content": "", "status": "doing"})
    await client.post("/entries", json={"category": "task", "title": "已完成任务", "content": "", "status": "complete"})
    await client.post("/entries", json={"category": "project", "title": "进行中项目", "content": "", "status": "doing"})
    await client.post("/entries", json={"category": "note", "title": "笔记", "content": "", "status": "doing"})

    response = await client.get("/entries?category_group=actionable&status=doing")
    assert response.status_code == 200
    data = response.json()
    for entry in data["entries"]:
        assert entry["category"] in ("task", "decision", "project")
        assert entry["status"] == "doing"


@pytest.mark.asyncio
async def test_category_group_with_priority(client: AsyncClient):
    """category_group + priority 组合筛选"""
    await client.post("/entries", json={"category": "task", "title": "高优任务", "content": "", "priority": "high"})
    await client.post("/entries", json={"category": "task", "title": "低优任务", "content": "", "priority": "low"})
    await client.post("/entries", json={"category": "note", "title": "高优笔记", "content": "", "priority": "high"})

    response = await client.get("/entries?category_group=actionable&priority=high")
    assert response.status_code == 200
    data = response.json()
    for entry in data["entries"]:
        assert entry["category"] in ("task", "decision", "project")
        assert entry["priority"] == "high"


# === 向后兼容测试 ===

@pytest.mark.asyncio
async def test_no_category_group_backward_compatible(client: AsyncClient):
    """无 category_group 时行为向后兼容（返回全部）"""
    await client.post("/entries", json={"category": "task", "title": "任务", "content": ""})
    await client.post("/entries", json={"category": "note", "title": "笔记", "content": ""})
    await client.post("/entries", json={"category": "decision", "title": "决策", "content": ""})

    response = await client.get("/entries")
    assert response.status_code == 200
    data = response.json()
    categories = {e["category"] for e in data["entries"]}
    assert "task" in categories
    assert "note" in categories
    assert "decision" in categories


# === 无效值测试 ===

@pytest.mark.asyncio
async def test_invalid_category_group_value(client: AsyncClient):
    """无效的 category_group 值返回 422"""
    response = await client.get("/entries?category_group=invalid")
    assert response.status_code == 422
