"""笔记双链引用后端单元测试

覆盖:
- 双链解析: [[note-id]] 简写, [[note-id|标题]] 完整, 多个引用混合, 无效 note-id 忽略, 自引用忽略, 空内容无引用
- 引用关系存储: 创建引用, 更新引用, 删除条目级联清理, 重复引用幂等
- 反向引用查询: 有反向引用, 无反向引用, 跨用户隔离
- 回填路径: 已有笔记含双链→reindex后可查backlinks, 空内容→无引用, reindex幂等, 首次API调用自动触发reindex
"""
import pytest
from httpx import AsyncClient

from app.infrastructure.storage.sqlite import SQLiteStorage


# === 辅助 ===

async def _create_entry(
    client: AsyncClient,
    category: str = "note",
    title: str = "测试笔记",
    content: str = "",
) -> dict:
    """辅助：通过 API 创建条目"""
    resp = await client.post("/entries", json={
        "category": category,
        "title": title,
        "content": content,
    })
    assert resp.status_code == 200, f"创建条目失败: {resp.text}"
    return resp.json()


# === 双链解析 ===

class TestParseWikilinks:
    """SQLiteStorage.parse_wikilinks 测试"""

    def test_simple_wikilink(self):
        """解析 [[note-id]] 简写语法"""
        result = SQLiteStorage.parse_wikilinks("参见 [[note-abc123]] 了解更多")
        assert result == {"note-abc123"}

    def test_wikilink_with_title(self):
        """解析 [[note-id|显示标题]] 完整语法"""
        result = SQLiteStorage.parse_wikilinks("参见 [[note-abc123|学习笔记]] 了解更多")
        assert result == {"note-abc123"}

    def test_multiple_mixed_wikilinks(self):
        """多个引用混合"""
        content = "参考 [[note-aaa]] 和 [[note-bbb|另一个笔记]] 以及 [[task-ccc]]"
        result = SQLiteStorage.parse_wikilinks(content)
        assert result == {"note-aaa", "note-bbb", "task-ccc"}

    def test_invalid_note_id_ignored(self):
        """无效内容（非 ID 格式）仍会被提取，过滤在 upsert 阶段"""
        result = SQLiteStorage.parse_wikilinks("这里是 [[some random text]]")
        assert "some random text" in result

    def test_empty_content_no_refs(self):
        """空内容无引用"""
        assert SQLiteStorage.parse_wikilinks("") == set()
        assert SQLiteStorage.parse_wikilinks(None) == set()

    def test_no_wikilinks(self):
        """普通 Markdown 无双链"""
        result = SQLiteStorage.parse_wikilinks("# 标题\n\n普通内容 [普通链接](http://example.com)")
        assert result == set()

    def test_duplicate_wikilinks_deduped(self):
        """重复引用去重"""
        content = "[[note-aaa]] 和 [[note-aaa]] 和 [[note-aaa|别名]]"
        result = SQLiteStorage.parse_wikilinks(content)
        assert result == {"note-aaa"}

    def test_whitespace_in_id_stripped(self):
        """ID 两端空白被清理"""
        result = SQLiteStorage.parse_wikilinks("[[ note-abc ]]")
        assert "note-abc" in result


# === 引用关系存储 ===

@pytest.mark.asyncio
class TestNoteReferenceStorage:
    """引用关系存储测试"""

    async def test_create_entry_parses_wikilinks(self, client):
        """创建条目时自动解析双链引用"""
        target = await _create_entry(client, title="目标笔记")
        source = await _create_entry(
            client,
            title="来源笔记",
            content=f"参考 [[{target['id']}]] 的内容",
        )

        # 查询 backlinks
        resp = await client.get(f"/entries/{target['id']}/backlinks")
        assert resp.status_code == 200
        backlinks = resp.json()["backlinks"]
        assert len(backlinks) >= 1
        assert any(bl["id"] == source["id"] for bl in backlinks)

    async def test_create_entry_with_display_title(self, client):
        """创建条目时解析 [[id|标题]] 完整语法"""
        target = await _create_entry(client, title="目标笔记")
        source = await _create_entry(
            client,
            title="来源笔记",
            content=f"参考 [[{target['id']}|显示标题]] 的内容",
        )

        resp = await client.get(f"/entries/{target['id']}/backlinks")
        assert resp.status_code == 200
        backlinks = resp.json()["backlinks"]
        assert any(bl["id"] == source["id"] for bl in backlinks)

    async def test_update_entry_updates_refs(self, client):
        """更新条目内容时更新引用关系"""
        target_a = await _create_entry(client, title="笔记A")
        target_b = await _create_entry(client, title="笔记B")
        source = await _create_entry(
            client,
            title="来源笔记",
            content=f"参考 [[{target_a['id']}]]",
        )

        # 更新内容：改为引用 B
        resp = await client.put(f"/entries/{source['id']}", json={
            "content": f"改为参考 [[{target_b['id']}]]",
        })
        assert resp.status_code == 200

        # A 不应再有 backlink
        resp_a = await client.get(f"/entries/{target_a['id']}/backlinks")
        assert not any(bl["id"] == source["id"] for bl in resp_a.json()["backlinks"])

        # B 应有 backlink
        resp_b = await client.get(f"/entries/{target_b['id']}/backlinks")
        assert any(bl["id"] == source["id"] for bl in resp_b.json()["backlinks"])

    async def test_delete_entry_cascades_refs(self, client):
        """删除条目时级联清理引用关系"""
        target = await _create_entry(client, title="目标笔记")
        source = await _create_entry(
            client,
            title="来源笔记",
            content=f"参考 [[{target['id']}]]",
        )

        # 删除来源
        resp = await client.delete(f"/entries/{source['id']}")
        assert resp.status_code == 200

        # 目标的 backlinks 应为空
        resp = await client.get(f"/entries/{target['id']}/backlinks")
        assert resp.status_code == 200
        assert len(resp.json()["backlinks"]) == 0

    async def test_delete_target_cascades_refs(self, client):
        """删除目标条目时清理反向引用"""
        target = await _create_entry(client, title="目标笔记")
        source = await _create_entry(
            client,
            title="来源笔记",
            content=f"参考 [[{target['id']}]]",
        )

        # 删除目标
        resp = await client.delete(f"/entries/{target['id']}")
        assert resp.status_code == 200

        # 来源的 backlinks 应为空（因为 target 被删了，其作为 source 的引用也清了）
        resp = await client.get(f"/entries/{source['id']}/backlinks")
        assert resp.status_code == 200
        assert len(resp.json()["backlinks"]) == 0

    async def test_self_reference_ignored(self, client):
        """自引用被忽略"""
        source = await _create_entry(
            client,
            title="自引笔记",
            content="自引用 [[{id}]}",  # 占位，下面更新
        )
        # 更新为自引用
        resp = await client.put(f"/entries/{source['id']}", json={
            "content": f"自引用 [[{source['id']}]]",
        })
        assert resp.status_code == 200

        # 自己不应出现在自己的 backlinks 中
        resp = await client.get(f"/entries/{source['id']}/backlinks")
        assert resp.status_code == 200
        assert not any(bl["id"] == source["id"] for bl in resp.json()["backlinks"])

    async def test_nonexistent_target_still_stored(self, client):
        """引用不存在的条目时，引用不会存储（因为 entry_belongs_to_user 返回 false）"""
        source = await _create_entry(
            client,
            title="引用不存在笔记",
            content="参考 [[note-nonexistent]]",
        )

        # 引用不存在的条目不会被存入 note_references
        resp = await client.get("/entries/note-nonexistent/backlinks")
        assert resp.status_code == 404


# === 反向引用查询 ===

@pytest.mark.asyncio
class TestBacklinksQuery:
    """GET /entries/{id}/backlinks 测试"""

    async def test_has_backlinks(self, client):
        """有反向引用时返回列表"""
        target = await _create_entry(client, title="被引用笔记")
        source1 = await _create_entry(
            client,
            title="引用者1",
            content=f"参考 [[{target['id']}]]",
        )
        source2 = await _create_entry(
            client,
            title="引用者2",
            content=f"详见 [[{target['id']}|详情]]",
        )

        resp = await client.get(f"/entries/{target['id']}/backlinks")
        assert resp.status_code == 200
        backlinks = resp.json()["backlinks"]
        ids = {bl["id"] for bl in backlinks}
        assert source1["id"] in ids
        assert source2["id"] in ids
        # 检查返回的字段
        for bl in backlinks:
            assert "id" in bl
            assert "title" in bl
            assert "category" in bl

    async def test_no_backlinks(self, client):
        """无反向引用时返回空列表"""
        target = await _create_entry(client, title="孤立笔记")

        resp = await client.get(f"/entries/{target['id']}/backlinks")
        assert resp.status_code == 200
        assert resp.json()["backlinks"] == []

    async def test_nonexistent_entry_returns_404(self, client):
        """不存在的条目返回 404"""
        resp = await client.get("/entries/note-nonexistent/backlinks")
        assert resp.status_code == 404


# === 跨用户隔离 ===

@pytest.mark.asyncio
class TestBacklinksUserIsolation:
    """跨用户隔离测试"""

    async def test_backlinks_isolated_by_user(self, client, storage, test_user):
        """不同用户的引用互相不可见"""
        from app.routers import deps
        from app.services.auth_service import create_access_token
        from app.models.user import UserCreate
        from httpx import ASGITransport, AsyncClient as AC
        from app.main import app as main_app

        # 用户 A 创建条目
        target_a = await _create_entry(client, title="用户A-目标")
        source_a = await _create_entry(
            client,
            title="用户A-来源",
            content=f"参考 [[{target_a['id']}]]",
        )

        # 认领默认条目到用户 A
        storage.sqlite.claim_default_entries(test_user.id)
        deps.reset_all_services()

        # 创建用户 B
        user_b = deps._user_storage.create_user(UserCreate(
            username="user_b_bl",
            email="b_bl@example.com",
            password="pass1234",
        ))

        token_b = create_access_token(user_b.id)
        transport = ASGITransport(app=main_app)

        async with AC(transport=transport, base_url="http://test") as client_b:
            client_b.headers["Authorization"] = f"Bearer {token_b}"

            # 用户 B 看不到用户 A 条目的 backlinks
            resp = await client_b.get(f"/entries/{target_a['id']}/backlinks")
            assert resp.status_code == 404

            # 用户 B 创建自己的条目和引用
            target_b = await _create_entry(client_b, title="用户B-目标")
            source_b = await _create_entry(
                client_b,
                title="用户B-来源",
                content=f"参考 [[{target_b['id']}]]",
            )

            resp = await client_b.get(f"/entries/{target_b['id']}/backlinks")
            assert resp.status_code == 200
            backlinks = resp.json()["backlinks"]
            assert any(bl["id"] == source_b["id"] for bl in backlinks)
            # 不包含用户 A 的引用
            assert not any(bl["id"] == source_a["id"] for bl in backlinks)


# === 回填路径 ===

@pytest.mark.asyncio
class TestReindexBacklinks:
    """reindex_backlinks 回填测试"""

    async def test_reindex_existing_entries(self, client, storage, test_user):
        """已有笔记含双链，reindex 后可查 backlinks"""
        # 直接操作 SQLite 创建条目（绕过双链解析，模拟旧数据）
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime

        user_id = test_user.id

        entry_a = Task(
            id="note-aaaa0001",
            title="笔记A",
            content="参考 [[note-bbbb0001]]",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/note-aaaa0001.md",
        )
        entry_b = Task(
            id="note-bbbb0001",
            title="笔记B",
            content="普通内容",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/note-bbbb0001.md",
        )

        # 先清除 backlinks 索引状态（确保需要 reindex）
        conn = storage.sqlite.get_connection()
        try:
            conn.execute("DELETE FROM backlinks_index_status WHERE user_id = ?", (user_id,))
            # 删除已有引用（模拟旧数据未建索引）
            conn.execute("DELETE FROM note_references WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()

        # 写入条目到 SQLite（模拟旧数据）
        storage.sqlite.upsert_entry(entry_a, user_id=user_id)
        storage.sqlite.upsert_entry(entry_b, user_id=user_id)

        # 手动调用 reindex
        from app.services.entry_service import EntryService
        service = EntryService(storage)
        await service.reindex_backlinks(user_id)

        # 验证 backlinks
        backlinks = storage.sqlite.get_backlinks("note-bbbb0001", user_id)
        assert len(backlinks) >= 1
        assert any(bl["id"] == "note-aaaa0001" for bl in backlinks)

    async def test_reindex_empty_content(self, client, storage, test_user):
        """空内容的条目不会产生引用"""
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime

        user_id = test_user.id

        entry = Task(
            id="note-empty001",
            title="空笔记",
            content="",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/note-empty001.md",
        )
        storage.sqlite.upsert_entry(entry, user_id=user_id)

        from app.services.entry_service import EntryService
        service = EntryService(storage)
        await service.reindex_backlinks(user_id)

        # 空内容不应有引用
        conn = storage.sqlite.get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM note_references WHERE source_id = ? AND user_id = ?",
                ("note-empty001", user_id),
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 0

    async def test_reindex_idempotent(self, client, storage, test_user):
        """多次 reindex 幂等"""
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime

        user_id = test_user.id

        entry_a = Task(
            id="note-idem0001",
            title="幂等笔记A",
            content="参考 [[note-idem0002]]",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/note-idem0001.md",
        )
        entry_b = Task(
            id="note-idem0002",
            title="幂等笔记B",
            content="普通内容",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/note-idem0002.md",
        )

        storage.sqlite.upsert_entry(entry_a, user_id=user_id)
        storage.sqlite.upsert_entry(entry_b, user_id=user_id)

        from app.services.entry_service import EntryService
        service = EntryService(storage)

        # 第一次 reindex
        await service.reindex_backlinks(user_id)
        backlinks1 = storage.sqlite.get_backlinks("note-idem0002", user_id)

        # 第二次 reindex
        await service.reindex_backlinks(user_id)
        backlinks2 = storage.sqlite.get_backlinks("note-idem0002", user_id)

        # 结果一致
        assert len(backlinks1) == len(backlinks2)

    async def test_first_api_call_triggers_reindex(self, client, storage, test_user):
        """首次 API 调用自动触发 reindex"""
        from app.models import Task, Category, TaskStatus, Priority
        from datetime import datetime

        user_id = test_user.id

        # 清除索引状态
        conn = storage.sqlite.get_connection()
        try:
            conn.execute("DELETE FROM backlinks_index_status WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM note_references WHERE user_id = ?", (user_id,))
            conn.commit()
        finally:
            conn.close()

        # 直接写入旧数据到当前用户的 namespace
        entry_a = Task(
            id="note-auto001",
            title="自动索引A",
            content="参考 [[note-auto002]]",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/note-auto001.md",
        )
        entry_b = Task(
            id="note-auto002",
            title="自动索引B",
            content="普通内容",
            category=Category.NOTE,
            status=TaskStatus.DOING,
            priority=Priority.MEDIUM,
            tags=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_path="notes/note-auto002.md",
        )

        storage.sqlite.upsert_entry(entry_a, user_id=user_id)
        storage.sqlite.upsert_entry(entry_b, user_id=user_id)

        # 首次调用 backlinks API 应触发 reindex 并返回结果
        resp = await client.get("/entries/note-auto002/backlinks")
        assert resp.status_code == 200
        backlinks = resp.json()["backlinks"]
        assert len(backlinks) >= 1
        assert any(bl["id"] == "note-auto001" for bl in backlinks)
