"""条目 API 流程测试 - 模拟用户编辑保存后刷新页面"""

import os
import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import init_storage
from app.routers import deps


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(temp_data_dir):
    """创建测试客户端，使用临时存储"""
    import asyncio

    # 初始化临时存储
    storage = asyncio.get_event_loop().run_until_complete(
        init_storage(data_dir=temp_data_dir)
    )

    # 替换全局存储
    deps.storage = storage
    deps.reset_entry_service()  # 重置 service 缓存

    return TestClient(app)


class TestEntryEditRefreshFlow:
    """测试编辑保存后刷新页面的完整流程"""

    def test_create_edit_refresh_flow(self, client):
        """
        完整流程测试：
        1. 创建条目
        2. 获取条目（模拟进入编辑页面）
        3. 更新条目（模拟编辑保存）
        4. 再次获取条目（模拟刷新页面）
        5. 验证数据一致性
        """
        # 1. 创建条目
        create_response = client.post(
            "/entries",
            json={
                "type": "note",
                "title": "测试笔记",
                "content": "初始内容",
                "status": "doing",
                "tags": ["测试"],
            },
        )
        assert create_response.status_code == 200
        entry_id = create_response.json()["id"]
        print(f"✅ 创建条目成功: {entry_id}")

        # 2. 获取条目（模拟进入编辑页面）
        get_response1 = client.get(f"/entries/{entry_id}")
        assert get_response1.status_code == 200
        data1 = get_response1.json()
        assert data1["title"] == "测试笔记"
        assert data1["content"] == "初始内容"
        print(f"✅ 首次获取成功: title={data1['title']}")

        # 3. 更新条目（模拟编辑保存）
        update_response = client.put(
            f"/entries/{entry_id}",
            json={
                "title": "修改后的标题",
                "content": "这是编辑后的内容\n\n新增段落",
            },
        )
        assert update_response.status_code == 200
        print(f"✅ 更新成功: {update_response.json()}")

        # 4. 再次获取条目（模拟刷新页面）
        get_response2 = client.get(f"/entries/{entry_id}")
        assert get_response2.status_code == 200
        data2 = get_response2.json()

        # 5. 验证数据一致性
        assert data2["title"] == "修改后的标题", f"标题不一致: {data2['title']}"
        assert "编辑后的内容" in data2["content"], f"内容不一致: {data2['content']}"
        assert "新增段落" in data2["content"], f"新段落丢失: {data2['content']}"
        print(f"✅ 刷新后获取成功: title={data2['title']}, content 长度={len(data2['content'])}")

    def test_multiple_edits_and_refresh(self, client):
        """测试多次编辑后刷新"""
        # 创建
        create_response = client.post(
            "/entries",
            json={
                "type": "task",
                "title": "多次编辑测试",
                "content": "v1",
                "status": "doing",
            },
        )
        entry_id = create_response.json()["id"]

        # 连续编辑 5 次
        for i in range(5):
            update_response = client.put(
                f"/entries/{entry_id}",
                json={"content": f"version-{i + 1}"},
            )
            assert update_response.status_code == 200

        # 刷新获取
        get_response = client.get(f"/entries/{entry_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["content"] == "version-5", f"期望 version-5，实际: {data['content']}"
        print(f"✅ 5次编辑后刷新正常: content={data['content']}")

    def test_edit_content_with_special_chars(self, client):
        """测试编辑包含特殊字符的内容"""
        # 创建
        create_response = client.post(
            "/entries",
            json={
                "type": "note",
                "title": "特殊字符测试",
                "content": "初始",
            },
        )
        entry_id = create_response.json()["id"]

        # 编辑包含特殊字符的内容
        special_content = """# 标题

这是一段包含特殊字符的内容：

- 中文：你好世界 🎉
- English: Hello World
- 代码：`const x = "test"`
- 符号：<>&"'特殊引号"
- 多行：
  第一行
  第二行
  第三行
"""
        update_response = client.put(
            f"/entries/{entry_id}",
            json={"content": special_content},
        )
        assert update_response.status_code == 200

        # 刷新获取
        get_response = client.get(f"/entries/{entry_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert "你好世界" in data["content"]
        assert "🎉" in data["content"]
        assert "const x" in data["content"]
        print(f"✅ 特殊字符编辑后刷新正常")

    def test_edit_status_and_refresh(self, client):
        """测试编辑状态后刷新"""
        # 创建
        create_response = client.post(
            "/entries",
            json={
                "type": "task",
                "title": "状态变更测试",
                "content": "内容",
                "status": "doing",
            },
        )
        entry_id = create_response.json()["id"]

        # 修改状态为完成
        update_response = client.put(
            f"/entries/{entry_id}",
            json={"status": "complete"},
        )
        assert update_response.status_code == 200

        # 刷新获取
        get_response = client.get(f"/entries/{entry_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["status"] == "complete", f"状态不一致: {data['status']}"
        print(f"✅ 状态修改后刷新正常: status={data['status']}")

    def test_edit_tags_and_refresh(self, client):
        """测试编辑标签后刷新"""
        # 创建
        create_response = client.post(
            "/entries",
            json={
                "type": "note",
                "title": "标签测试",
                "content": "内容",
                "tags": ["初始标签"],
            },
        )
        entry_id = create_response.json()["id"]

        # 修改标签
        update_response = client.put(
            f"/entries/{entry_id}",
            json={"tags": ["新标签1", "新标签2", "测试"]},
        )
        assert update_response.status_code == 200

        # 刷新获取
        get_response = client.get(f"/entries/{entry_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["tags"] == ["新标签1", "新标签2", "测试"], f"标签不一致: {data['tags']}"
        print(f"✅ 标签修改后刷新正常: tags={data['tags']}")

    def test_concurrent_edit_refresh(self, client):
        """测试快速连续编辑刷新"""
        # 创建
        create_response = client.post(
            "/entries",
            json={
                "type": "note",
                "title": "并发测试",
                "content": "初始",
            },
        )
        entry_id = create_response.json()["id"]

        # 快速连续编辑并刷新
        for i in range(10):
            # 编辑
            client.put(f"/entries/{entry_id}", json={"content": f"v{i}"})
            # 立即刷新
            response = client.get(f"/entries/{entry_id}")
            assert response.status_code == 200

        # 最终验证
        final_response = client.get(f"/entries/{entry_id}")
        assert final_response.json()["content"] == "v9"
        print(f"✅ 10次连续编辑刷新正常")

    def test_empty_content_edit(self, client):
        """测试编辑为空内容（系统会自动添加标题）"""
        # 创建
        create_response = client.post(
            "/entries",
            json={
                "type": "note",
                "title": "空内容测试",
                "content": "有内容",
            },
        )
        entry_id = create_response.json()["id"]

        # 编辑为空内容
        update_response = client.put(
            f"/entries/{entry_id}",
            json={"content": ""},
        )
        assert update_response.status_code == 200

        # 刷新获取
        get_response = client.get(f"/entries/{entry_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        # 系统设计：空内容会自动添加标题
        assert "# 空内容测试" in data["content"], f"空内容应自动添加标题: {data['content']}"
        print(f"✅ 空内容编辑后刷新正常（自动添加标题）")

    def test_long_content_edit_refresh(self, client):
        """测试编辑超长内容后刷新"""
        # 创建
        create_response = client.post(
            "/entries",
            json={
                "type": "note",
                "title": "长内容测试",
                "content": "短",
            },
        )
        entry_id = create_response.json()["id"]

        # 编辑超长内容
        long_content = "这是一段很长的内容。" * 1000  # 约 10KB
        update_response = client.put(
            f"/entries/{entry_id}",
            json={"content": long_content},
        )
        assert update_response.status_code == 200

        # 刷新获取
        get_response = client.get(f"/entries/{entry_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert len(data["content"]) == len(long_content), f"长内容长度不一致: {len(data['content'])} != {len(long_content)}"
        print(f"✅ 长内容编辑后刷新正常: 长度={len(data['content'])}")

    def test_get_nonexistent_entry(self, client):
        """测试获取不存在的条目"""
        response = client.get("/entries/nonexistent-id-12345")
        assert response.status_code == 404
        print(f"✅ 不存在条目返回 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
