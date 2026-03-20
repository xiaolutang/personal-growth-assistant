"""测试编辑后列表页数据同步"""

import os
import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import init_storage
from app.routers import deps


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(temp_data_dir):
    """创建测试客户端"""
    import asyncio

    storage = asyncio.get_event_loop().run_until_complete(
        init_storage(data_dir=temp_data_dir)
    )

    deps.storage = storage
    deps.reset_all_services()

    return TestClient(app)


class TestEditThenListSync:
    """测试：编辑条目 → 列表页刷新 → 验证数据一致性"""

    def test_edit_then_list_shows_updated_title(self, client):
        """
        场景：编辑标题后，列表页应显示新标题
        """
        # 1. 创建任务
        create_resp = client.post("/entries", json={
            "type": "task",
            "title": "原始标题",
            "content": "原始内容",
            "status": "doing",
        })
        entry_id = create_resp.json()["id"]
        print(f"创建条目: {entry_id}")

        # 2. 编辑标题
        edit_resp = client.put(f"/entries/{entry_id}", json={
            "title": "编辑后的新标题",
        })
        assert edit_resp.status_code == 200
        print(f"编辑标题成功")

        # 3. 刷新列表页
        list_resp = client.get("/entries?type=task")
        assert list_resp.status_code == 200
        entries = list_resp.json()["entries"]

        # 4. 验证列表中显示的是新标题
        found = next((e for e in entries if e["id"] == entry_id), None)
        assert found is not None, f"列表中找不到条目 {entry_id}"
        assert found["title"] == "编辑后的新标题", f"列表标题不一致: {found['title']}"
        print(f"✅ 列表页显示更新后的标题: {found['title']}")

    def test_edit_then_list_shows_updated_status(self, client):
        """
        场景：编辑状态后，列表页应显示新状态
        """
        # 1. 创建任务
        create_resp = client.post("/entries", json={
            "type": "task",
            "title": "状态测试",
            "status": "doing",
        })
        entry_id = create_resp.json()["id"]

        # 2. 编辑状态为完成
        edit_resp = client.put(f"/entries/{entry_id}", json={
            "status": "complete",
        })
        assert edit_resp.status_code == 200

        # 3. 刷新列表页
        list_resp = client.get("/entries?type=task")
        entries = list_resp.json()["entries"]

        # 4. 验证列表中显示的是新状态
        found = next((e for e in entries if e["id"] == entry_id), None)
        assert found is not None
        assert found["status"] == "complete", f"列表状态不一致: {found['status']}"
        print(f"✅ 列表页显示更新后的状态: {found['status']}")

    def test_edit_then_list_shows_updated_tags(self, client):
        """
        场景：编辑标签后，列表页应显示新标签
        """
        # 1. 创建笔记
        create_resp = client.post("/entries", json={
            "type": "note",
            "title": "标签测试",
            "tags": ["原始标签"],
        })
        entry_id = create_resp.json()["id"]

        # 2. 编辑标签
        edit_resp = client.put(f"/entries/{entry_id}", json={
            "tags": ["新标签A", "新标签B"],
        })
        assert edit_resp.status_code == 200

        # 3. 刷新列表页
        list_resp = client.get("/entries?type=note")
        entries = list_resp.json()["entries"]

        # 4. 验证列表中显示的是新标签
        found = next((e for e in entries if e["id"] == entry_id), None)
        assert found is not None
        assert found["tags"] == ["新标签A", "新标签B"], f"列表标签不一致: {found['tags']}"
        print(f"✅ 列表页显示更新后的标签: {found['tags']}")

    def test_edit_content_then_list(self, client):
        """
        场景：编辑内容后，列表页返回的数据应包含新内容
        （虽然列表页可能只显示摘要，但 API 返回的数据应该是最新的）
        """
        # 1. 创建任务
        create_resp = client.post("/entries", json={
            "type": "task",
            "title": "内容测试",
            "content": "原始内容",
        })
        entry_id = create_resp.json()["id"]

        # 2. 编辑内容
        new_content = "这是编辑后的新内容，包含更多信息。"
        edit_resp = client.put(f"/entries/{entry_id}", json={
            "content": new_content,
        })
        assert edit_resp.status_code == 200

        # 3. 刷新列表页
        list_resp = client.get("/entries?type=task")
        entries = list_resp.json()["entries"]

        # 4. 验证列表 API 返回的数据
        found = next((e for e in entries if e["id"] == entry_id), None)
        assert found is not None
        # 注意：列表页可能不返回完整 content，取决于 API 设计
        # 但如果返回了 content，应该是新的
        if "content" in found:
            assert found["content"] == new_content, f"列表内容不一致"
        print(f"✅ 列表 API 返回数据正确")

    def test_detail_vs_list_consistency(self, client):
        """
        关键测试：详情页和列表页数据应该一致
        """
        # 1. 创建任务
        create_resp = client.post("/entries", json={
            "type": "task",
            "title": "一致性测试",
            "content": "初始内容",
            "status": "doing",
            "tags": ["测试"],
        })
        entry_id = create_resp.json()["id"]

        # 2. 编辑
        edit_resp = client.put(f"/entries/{entry_id}", json={
            "title": "编辑后的标题",
            "content": "编辑后的内容",
            "status": "complete",
            "tags": ["已更新"],
        })
        assert edit_resp.status_code == 200

        # 3. 获取详情页数据（从 Markdown 读取）
        detail_resp = client.get(f"/entries/{entry_id}")
        detail = detail_resp.json()

        # 4. 获取列表页数据（从 SQLite 读取）
        list_resp = client.get("/entries?type=task")
        entries = list_resp.json()["entries"]
        list_entry = next((e for e in entries if e["id"] == entry_id), None)

        # 5. 验证一致性
        assert list_entry is not None, "列表中找不到条目"

        # 比较关键字段
        assert detail["title"] == list_entry["title"], \
            f"标题不一致: detail={detail['title']}, list={list_entry['title']}"

        assert detail["status"] == list_entry["status"], \
            f"状态不一致: detail={detail['status']}, list={list_entry['status']}"

        assert detail["tags"] == list_entry["tags"], \
            f"标签不一致: detail={detail['tags']}, list={list_entry['tags']}"

        print(f"✅ 详情页和列表页数据一致")
        print(f"   title: {detail['title']}")
        print(f"   status: {detail['status']}")
        print(f"   tags: {detail['tags']}")

    def test_multiple_edits_list_consistency(self, client):
        """
        多次编辑后，列表页应该显示最新数据
        """
        # 1. 创建
        create_resp = client.post("/entries", json={
            "type": "note",
            "title": "v1",
            "content": "v1",
        })
        entry_id = create_resp.json()["id"]

        # 2. 连续编辑 5 次
        for i in range(5):
            client.put(f"/entries/{entry_id}", json={
                "title": f"v{i+2}",
                "content": f"content-v{i+2}",
            })

        # 3. 获取列表
        list_resp = client.get("/entries?type=note")
        entries = list_resp.json()["entries"]
        found = next((e for e in entries if e["id"] == entry_id), None)

        # 4. 验证是最后一次编辑的值
        assert found is not None
        assert found["title"] == "v6", f"期望 v6，实际: {found['title']}"
        print(f"✅ 多次编辑后列表页显示最新数据: {found['title']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
