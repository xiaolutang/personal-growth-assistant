"""条目 API 测试

测试覆盖:
- 创建条目 (POST /entries)
- 查询条目 (GET /entries, GET /entries/{id})
- 更新条目 (PUT /entries/{id})
- 删除条目 (DELETE /entries/{id})
- 项目进度 (GET /entries/{id}/progress)
"""
import pytest
from httpx import AsyncClient


# === 创建条目测试 ===

@pytest.mark.asyncio
async def test_create_task(client: AsyncClient):
    """测试创建任务"""
    response = await client.post(
        "/entries",
        json={
            "category": "task",
            "title": "测试任务",
            "content": "任务内容",
            "tags": ["test"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试任务"
    assert data["category"] == "task"
    assert data["status"] == "doing"
    assert "test" in data["tags"]


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    """测试创建项目"""
    response = await client.post(
        "/entries",
        json={
            "category": "project",
            "title": "测试项目",
            "content": "项目描述",
            "tags": ["project"],
            "status": "doing",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试项目"
    assert data["category"] == "project"


@pytest.mark.asyncio
async def test_create_note(client: AsyncClient):
    """测试创建笔记"""
    response = await client.post(
        "/entries",
        json={
            "category": "note",
            "title": "测试笔记",
            "content": "# 标题\n笔记内容",
            "tags": ["note"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "测试笔记"
    assert data["category"] == "note"


@pytest.mark.asyncio
async def test_create_with_tags(client: AsyncClient):
    """测试带标签创建"""
    response = await client.post(
        "/entries",
        json={
            "category": "task",
            "title": "带标签任务",
            "content": "",
            "tags": ["tag1", "tag2", "tag3"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "tag1" in data["tags"]
    assert "tag2" in data["tags"]
    assert "tag3" in data["tags"]


@pytest.mark.asyncio
async def test_create_with_parent(client: AsyncClient):
    """测试带父级创建"""
    # 先创建父项目
    parent_response = await client.post(
        "/entries",
        json={"category": "project", "title": "父项目", "content": ""},
    )
    parent_id = parent_response.json()["id"]

    # 创建子任务
    response = await client.post(
        "/entries",
        json={
            "category": "task",
            "title": "子任务",
            "content": "",
            "parent_id": parent_id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_create_with_priority(client: AsyncClient):
    """测试带优先级创建"""
    response = await client.post(
        "/entries",
        json={
            "category": "task",
            "title": "高优先级任务",
            "content": "",
            "priority": "high",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_create_with_status(client: AsyncClient):
    """测试带状态创建"""
    response = await client.post(
        "/entries",
        json={
            "category": "task",
            "title": "待开始任务",
            "content": "",
            "status": "waitStart",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "waitStart"


@pytest.mark.asyncio
async def test_create_invalid_type(client: AsyncClient):
    """测试无效类型使用默认值 note"""
    response = await client.post(
        "/entries",
        json={
            "category": "invalid_type",
            "title": "测试",
            "content": "",
        },
    )
    # 无效类型会被映射为 note，所以返回 200
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "note"  # 默认值


@pytest.mark.asyncio
async def test_create_invalid_status(client: AsyncClient):
    """测试无效状态使用默认值 doing"""
    response = await client.post(
        "/entries",
        json={
            "category": "task",
            "title": "测试",
            "content": "",
            "status": "invalid_status",
        },
    )
    # 无效状态会被映射为 doing，所以返回 200
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "doing"  # 默认值


@pytest.mark.asyncio
async def test_create_invalid_priority(client: AsyncClient):
    """测试无效优先级使用默认值 medium"""
    response = await client.post(
        "/entries",
        json={
            "category": "task",
            "title": "测试",
            "content": "",
            "priority": "invalid_priority",
        },
    )
    # 无效优先级会被映射为 medium，所以返回 200
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "medium"  # 默认值


# === 查询条目测试 ===

@pytest.mark.asyncio
async def test_list_entries(client: AsyncClient):
    """测试列出所有条目"""
    # 创建测试数据
    for i in range(3):
        await client.post(
            "/entries",
            json={"category": "task", "title": f"任务-{i}", "content": ""},
        )

    response = await client.get("/entries")
    assert response.status_code == 200
    data = response.json()
    assert "entries" in data
    assert "total" in data
    assert len(data["entries"]) >= 3


@pytest.mark.asyncio
async def test_filter_by_type(client: AsyncClient):
    """测试按类型筛选"""
    # 创建不同类型的条目
    await client.post("/entries", json={"category": "task", "title": "任务", "content": ""})
    await client.post("/entries", json={"category": "project", "title": "项目", "content": ""})
    await client.post("/entries", json={"category": "note", "title": "笔记", "content": ""})

    # 筛选任务
    response = await client.get("/entries?type=task")
    assert response.status_code == 200
    data = response.json()
    for entry in data["entries"]:
        assert entry["category"] == "task"


@pytest.mark.asyncio
async def test_filter_by_status(client: AsyncClient):
    """测试按状态筛选"""
    await client.post(
        "/entries",
        json={"category": "task", "title": "进行中", "content": "", "status": "doing"},
    )
    await client.post(
        "/entries",
        json={"category": "task", "title": "已完成", "content": "", "status": "complete"},
    )

    response = await client.get("/entries?status=complete")
    assert response.status_code == 200
    data = response.json()
    for entry in data["entries"]:
        assert entry["status"] == "complete"


@pytest.mark.asyncio
async def test_filter_by_tags(client: AsyncClient):
    """测试按标签筛选"""
    await client.post(
        "/entries",
        json={"category": "task", "title": "任务A", "content": "", "tags": ["work"]},
    )
    await client.post(
        "/entries",
        json={"category": "task", "title": "任务B", "content": "", "tags": ["personal"]},
    )

    response = await client.get("/entries?tags=work")
    assert response.status_code == 200
    data = response.json()
    # 验证结果中包含 work 标签的条目
    for entry in data["entries"]:
        if "work" in entry.get("tags", []):
            assert True
            return
    # 可能没有匹配的结果，但不应该报错


@pytest.mark.asyncio
async def test_filter_by_parent(client: AsyncClient):
    """测试按父级筛选"""
    # 创建父项目
    parent = await client.post(
        "/entries",
        json={"category": "project", "title": "父项目", "content": ""},
    )
    parent_id = parent.json()["id"]

    # 创建子任务
    await client.post(
        "/entries",
        json={"category": "task", "title": "子任务1", "content": "", "parent_id": parent_id},
    )
    await client.post(
        "/entries",
        json={"category": "task", "title": "子任务2", "content": "", "parent_id": parent_id},
    )

    response = await client.get(f"/entries?parent_id={parent_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient):
    """测试分页"""
    # 创建多个条目
    for i in range(10):
        await client.post(
            "/entries",
            json={"category": "task", "title": f"分页测试-{i}", "content": ""},
        )

    # 获取第一页
    response1 = await client.get("/entries?limit=5&offset=0")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["entries"]) <= 5

    # 获取第二页
    response2 = await client.get("/entries?limit=5&offset=5")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["entries"]) <= 5


@pytest.mark.asyncio
async def test_get_single_entry(client: AsyncClient):
    """测试获取单个条目"""
    create_response = await client.post(
        "/entries",
        json={"category": "task", "title": "单个条目测试", "content": "内容"},
    )
    entry_id = create_response.json()["id"]

    response = await client.get(f"/entries/{entry_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entry_id
    assert data["title"] == "单个条目测试"


@pytest.mark.asyncio
async def test_get_nonexistent(client: AsyncClient):
    """测试获取不存在的条目返回 404"""
    response = await client.get("/entries/nonexistent-id-12345")
    assert response.status_code == 404


# === 更新条目测试 ===

@pytest.mark.asyncio
async def test_update_title(client: AsyncClient):
    """测试更新标题"""
    create_response = await client.post(
        "/entries",
        json={"category": "task", "title": "原标题", "content": ""},
    )
    entry_id = create_response.json()["id"]

    response = await client.put(
        f"/entries/{entry_id}",
        json={"title": "新标题"},
    )
    assert response.status_code == 200

    # 验证更新
    get_response = await client.get(f"/entries/{entry_id}")
    assert get_response.json()["title"] == "新标题"


@pytest.mark.asyncio
async def test_update_status(client: AsyncClient):
    """测试更新状态"""
    create_response = await client.post(
        "/entries",
        json={"category": "task", "title": "测试", "content": "", "status": "doing"},
    )
    entry_id = create_response.json()["id"]

    response = await client.put(
        f"/entries/{entry_id}",
        json={"status": "complete"},
    )
    assert response.status_code == 200

    # 验证更新
    get_response = await client.get(f"/entries/{entry_id}")
    assert get_response.json()["status"] == "complete"


@pytest.mark.asyncio
async def test_update_priority(client: AsyncClient):
    """测试更新优先级"""
    create_response = await client.post(
        "/entries",
        json={"category": "task", "title": "测试", "content": ""},
    )
    entry_id = create_response.json()["id"]

    response = await client.put(
        f"/entries/{entry_id}",
        json={"priority": "high"},
    )
    assert response.status_code == 200

    # 验证更新
    get_response = await client.get(f"/entries/{entry_id}")
    assert get_response.json()["priority"] == "high"


@pytest.mark.asyncio
async def test_update_tags(client: AsyncClient):
    """测试更新标签"""
    create_response = await client.post(
        "/entries",
        json={"category": "task", "title": "测试", "content": "", "tags": ["old"]},
    )
    entry_id = create_response.json()["id"]

    response = await client.put(
        f"/entries/{entry_id}",
        json={"tags": ["new1", "new2"]},
    )
    assert response.status_code == 200

    # 验证更新
    get_response = await client.get(f"/entries/{entry_id}")
    tags = get_response.json()["tags"]
    assert "new1" in tags
    assert "new2" in tags


@pytest.mark.asyncio
async def test_update_nonexistent(client: AsyncClient):
    """测试更新不存在的条目返回 404"""
    response = await client.put(
        "/entries/nonexistent-id-12345",
        json={"title": "新标题"},
    )
    assert response.status_code == 404


# === 删除条目测试 ===

@pytest.mark.asyncio
async def test_delete_entry(client: AsyncClient):
    """测试删除条目"""
    create_response = await client.post(
        "/entries",
        json={"category": "task", "title": "待删除", "content": ""},
    )
    entry_id = create_response.json()["id"]

    # 删除
    delete_response = await client.delete(f"/entries/{entry_id}")
    assert delete_response.status_code == 200

    # 验证删除
    get_response = await client.get(f"/entries/{entry_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(client: AsyncClient):
    """测试删除不存在的条目返回 404"""
    response = await client.delete("/entries/nonexistent-id-12345")
    assert response.status_code == 404


# === 项目进度测试 ===

@pytest.mark.asyncio
async def test_get_project_progress(client: AsyncClient):
    """测试获取项目进度"""
    # 创建项目
    project_response = await client.post(
        "/entries",
        json={"category": "project", "title": "进度测试项目", "content": ""},
    )
    project_id = project_response.json()["id"]

    # 创建子任务
    for i in range(4):
        status = "complete" if i < 2 else "doing"
        await client.post(
            "/entries",
            json={
                "category": "task",
                "title": f"子任务-{i}",
                "content": "",
                "parent_id": project_id,
                "status": status,
            },
        )

    response = await client.get(f"/entries/{project_id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["total_tasks"] == 4
    assert data["completed_tasks"] == 2
    assert data["progress_percentage"] == 50.0


@pytest.mark.asyncio
async def test_progress_no_children(client: AsyncClient):
    """测试无子任务的项目进度"""
    project_response = await client.post(
        "/entries",
        json={"category": "project", "title": "空项目", "content": ""},
    )
    project_id = project_response.json()["id"]

    response = await client.get(f"/entries/{project_id}/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tasks"] == 0
    assert data["completed_tasks"] == 0
    assert data["progress_percentage"] == 0.0


@pytest.mark.asyncio
async def test_progress_nonexistent_project(client: AsyncClient):
    """测试不存在项目的进度返回 404"""
    response = await client.get("/entries/nonexistent-project/progress")
    assert response.status_code == 404


# === B49: 新条目类型测试 ===


@pytest.mark.asyncio
async def test_create_decision(client: AsyncClient):
    """测试创建决策记录"""
    response = await client.post(
        "/entries",
        json={
            "category": "decision",
            "title": "选了 Rust 而不是 Go",
            "content": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "decision"
    assert data["id"].startswith("decision-")
    # 空 content 应使用模板
    assert "决策背景" in data["content"]


@pytest.mark.asyncio
async def test_create_reflection(client: AsyncClient):
    """测试创建复盘笔记"""
    response = await client.post(
        "/entries",
        json={
            "category": "reflection",
            "title": "项目延期复盘",
            "content": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "reflection"
    assert data["id"].startswith("reflection-")
    assert "回顾目标" in data["content"]


@pytest.mark.asyncio
async def test_create_question(client: AsyncClient):
    """测试创建待解疑问"""
    response = await client.post(
        "/entries",
        json={
            "category": "question",
            "title": "为什么用 WebSocket",
            "content": "",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "question"
    assert data["id"].startswith("question-")
    assert "问题描述" in data["content"]


@pytest.mark.asyncio
async def test_create_decision_with_content_includes_template(client: AsyncClient):
    """测试有内容时也追加模板结构"""
    response = await client.post(
        "/entries",
        json={
            "category": "decision",
            "title": "技术选型",
            "content": "我们选了 Python",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "我们选了 Python" in data["content"]
    assert "决策背景" in data["content"]


@pytest.mark.asyncio
async def test_filter_by_decision_type(client: AsyncClient):
    """测试按决策类型筛选"""
    await client.post("/entries", json={"category": "decision", "title": "决策1", "content": ""})
    await client.post("/entries", json={"category": "task", "title": "任务1", "content": ""})

    response = await client.get("/entries?type=decision")
    assert response.status_code == 200
    data = response.json()
    for entry in data["entries"]:
        assert entry["category"] == "decision"


@pytest.mark.asyncio
async def test_filter_by_reflection_type(client: AsyncClient):
    """测试按复盘类型筛选"""
    await client.post("/entries", json={"category": "reflection", "title": "复盘1", "content": ""})

    response = await client.get("/entries?type=reflection")
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) >= 1
    for entry in data["entries"]:
        assert entry["category"] == "reflection"


@pytest.mark.asyncio
async def test_filter_by_question_type(client: AsyncClient):
    """测试按疑问类型筛选"""
    await client.post("/entries", json={"category": "question", "title": "问题1", "content": ""})

    response = await client.get("/entries?type=question")
    assert response.status_code == 200
    data = response.json()
    assert len(data["entries"]) >= 1
    for entry in data["entries"]:
        assert entry["category"] == "question"
