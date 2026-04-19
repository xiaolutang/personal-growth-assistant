"""项目详情页完整链路测试

模拟前端 EntryDetail.tsx 的数据获取流程：
1. getEntry(id) → 获取项目条目（含 content）
2. getProjectProgress(id) → 获取项目进度
3. getEntries({ parent_id: id }) → 获取子任务列表
4. 验证项目描述、进度、子任务列表均可正常获取
"""

import pytest
from httpx import AsyncClient


class TestProjectDetailFullFlow:
    """模拟前端 EntryDetail 页面的完整数据流"""

    async def test_project_detail_with_children(self, client: AsyncClient):
        """项目详情页：有子任务时显示描述、进度、子任务列表"""
        # 1. 创建项目（含描述内容）
        project_resp = await client.post("/entries", json={
            "category": "project",
            "title": "个人成长系统",
            "content": "# 目标\n\n构建一个完整的个人知识管理和成长追踪系统。\n\n## 关键里程碑\n\n- MVP 上线\n- 用户测试",
        })
        assert project_resp.status_code == 200
        project_id = project_resp.json()["id"]

        # 2. 创建子任务（不同状态）
        await client.post("/entries", json={
            "category": "task",
            "title": "设计数据模型",
            "content": "完成 ER 图和 API 设计",
            "parent_id": project_id,
            "status": "complete",
        })
        await client.post("/entries", json={
            "category": "task",
            "title": "实现后端 API",
            "content": "FastAPI + SQLite",
            "parent_id": project_id,
            "status": "doing",
        })
        await client.post("/entries", json={
            "category": "task",
            "title": "前端页面开发",
            "parent_id": project_id,
            "status": "waitStart",
        })

        # === 前端 EntryDetail 的三个 API 调用 ===

        # getEntry(id)
        detail_resp = await client.get(f"/entries/{project_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["category"] == "project"
        assert detail["title"] == "个人成长系统"
        assert "# 目标" in detail["content"]
        assert "关键里程碑" in detail["content"]

        # getProjectProgress(id)
        progress_resp = await client.get(f"/entries/{project_id}/progress")
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        assert progress["total_tasks"] == 3
        assert progress["completed_tasks"] == 1
        assert progress["progress_percentage"] == pytest.approx(33.333, abs=0.1)

        # getEntries({ parent_id: id })
        children_resp = await client.get("/entries", params={"parent_id": project_id})
        assert children_resp.status_code == 200
        children = children_resp.json()["entries"]
        assert len(children) == 3
        titles = {c["title"] for c in children}
        assert titles == {"设计数据模型", "实现后端 API", "前端页面开发"}

    async def test_project_detail_empty_project(self, client: AsyncClient):
        """项目详情页：空项目（无子任务）正常显示描述，进度为 0"""
        project_resp = await client.post("/entries", json={
            "category": "project",
            "title": "空项目测试",
            "content": "这是一个还没有子任务的项目",
        })
        project_id = project_resp.json()["id"]

        # getEntry → 有内容
        detail = (await client.get(f"/entries/{project_id}")).json()
        assert detail["content"] == "这是一个还没有子任务的项目"

        # getProjectProgress → 0%
        progress = (await client.get(f"/entries/{project_id}/progress")).json()
        assert progress["total_tasks"] == 0
        assert progress["progress_percentage"] == 0.0

        # getEntries → 空
        children = (await client.get("/entries", params={"parent_id": project_id})).json()["entries"]
        assert len(children) == 0

    async def test_project_detail_no_content(self, client: AsyncClient):
        """项目详情页：无描述内容时仍能正常返回"""
        project_resp = await client.post("/entries", json={
            "category": "project",
            "title": "无描述项目",
        })
        project_id = project_resp.json()["id"]

        detail = (await client.get(f"/entries/{project_id}")).json()
        assert detail["title"] == "无描述项目"
        # content 可能为空或包含自动生成的标题
        assert detail["category"] == "project"

    async def test_project_detail_nonexistent(self, client: AsyncClient):
        """项目详情页：不存在的条目返回 404"""
        resp = await client.get("/entries/project-nonexistent-12345")
        assert resp.status_code == 404
