"""Test type_history field and POST /entries/{id}/convert endpoint (TDD for S01)"""

import pytest
from datetime import datetime
from httpx import AsyncClient

from app.models import Task, Category, TaskStatus, Priority


# ── Unit: TypeHistoryRecord model ──────────────────────────


class TestTypeHistoryRecord:
    """TypeHistoryRecord Pydantic model tests"""

    def test_create_record(self):
        from app.models.task import TypeHistoryRecord

        rec = TypeHistoryRecord(
            from_category="inbox",
            to_category="task",
            at="2026-04-30T10:00:00",
        )
        assert rec.from_category == "inbox"
        assert rec.to_category == "task"
        assert rec.at == "2026-04-30T10:00:00"

    def test_record_requires_all_fields(self):
        from app.models.task import TypeHistoryRecord

        with pytest.raises(Exception):
            TypeHistoryRecord(from_category="inbox")  # type: ignore


# ── Unit: Task model type_history field ────────────────────


class TestTaskTypeHistory:
    """Task model type_history field tests"""

    def test_default_empty_list(self):
        task = Task(
            id="test-1",
            title="Test",
            content="",
            category=Category.INBOX,
            file_path="inbox.md",
        )
        assert hasattr(task, "type_history")
        assert task.type_history == []

    def test_with_history(self):
        task = Task(
            id="test-1",
            title="Test",
            content="",
            category=Category.TASK,
            file_path="tasks/test-1.md",
            type_history=[
                {"from_category": "inbox", "to_category": "task", "at": "2026-04-30T10:00:00"},
            ],
        )
        assert len(task.type_history) == 1
        assert task.type_history[0]["from_category"] == "inbox"


# ── Unit: VALID_CONVERSIONS constant ───────────────────────


class TestValidConversions:
    """Allowed / disallowed conversion rules"""

    def test_allowed_inbox_to_task(self):
        from app.services.entry_service import EntryService

        assert EntryService.is_valid_conversion(Category.INBOX, Category.TASK)

    def test_allowed_inbox_to_decision(self):
        from app.services.entry_service import EntryService

        assert EntryService.is_valid_conversion(Category.INBOX, Category.DECISION)

    def test_allowed_inbox_to_note(self):
        from app.services.entry_service import EntryService

        assert EntryService.is_valid_conversion(Category.INBOX, Category.NOTE)

    def test_disallowed_task_to_inbox(self):
        from app.services.entry_service import EntryService

        assert not EntryService.is_valid_conversion(Category.TASK, Category.INBOX)

    def test_disallowed_task_to_reflection(self):
        from app.services.entry_service import EntryService

        assert not EntryService.is_valid_conversion(Category.TASK, Category.REFLECTION)

    def test_disallowed_decision_to_task(self):
        from app.services.entry_service import EntryService

        assert not EntryService.is_valid_conversion(Category.DECISION, Category.TASK)

    def test_disallowed_note_to_inbox(self):
        from app.services.entry_service import EntryService

        assert not EntryService.is_valid_conversion(Category.NOTE, Category.INBOX)

    def test_disallowed_same_category(self):
        from app.services.entry_service import EntryService

        assert not EntryService.is_valid_conversion(Category.INBOX, Category.INBOX)


# ── Unit: MarkdownStorage read/write type_history ──────────


class TestMarkdownTypeHistory:
    """MarkdownStorage reads and writes type_history in YAML frontmatter"""

    def test_write_and_read_type_history(self, markdown_storage):
        task = Task(
            id="test-hist-1",
            title="Test History",
            content="# Test History\n\nbody",
            category=Category.INBOX,
            file_path="inbox-test-hist-1.md",
            type_history=[
                {"from_category": "inbox", "to_category": "task", "at": "2026-04-30T10:00:00"},
            ],
        )
        markdown_storage.write_entry(task)
        loaded = markdown_storage.read_entry("test-hist-1")
        assert loaded is not None
        assert len(loaded.type_history) == 1
        assert loaded.type_history[0]["from_category"] == "inbox"
        assert loaded.type_history[0]["to_category"] == "task"

    def test_read_old_file_without_type_history_is_empty(self, markdown_storage):
        """旧文件无 type_history 字段时视为空列表"""
        from pathlib import Path
        # 手动写入一个没有 type_history 的文件
        md_content = """---
id: old-entry-1
type: note
title: Old Note
status: doing
priority: medium
created_at: '2026-01-01T00:00:00'
updated_at: '2026-01-01T00:00:00'
tags: []
---

# Old Note

Some content
"""
        file_path: Path = markdown_storage.data_dir / "notes" / "old-entry-1.md"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(md_content, encoding="utf-8")

        loaded = markdown_storage.read_entry("old-entry-1")
        assert loaded is not None
        assert loaded.type_history == []


# ── Unit: EntryMapper includes type_history ────────────────


class TestEntryMapperTypeHistory:
    """EntryMapper maps type_history between storage and response"""

    def test_task_to_response_includes_type_history(self):
        from app.mappers.entry_mapper import EntryMapper

        task = Task(
            id="mapper-1",
            title="Test",
            content="",
            category=Category.TASK,
            file_path="tasks/mapper-1.md",
            type_history=[
                {"from_category": "inbox", "to_category": "task", "at": "2026-04-30T10:00:00"},
            ],
        )
        result = EntryMapper.task_to_response(task)
        assert "type_history" in result
        assert len(result["type_history"]) == 1

    def test_dict_to_response_includes_type_history(self):
        from app.mappers.entry_mapper import EntryMapper

        data = {
            "id": "dict-1",
            "title": "Test",
            "content": "",
            "category": "task",
            "status": "doing",
            "priority": "medium",
            "tags": [],
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "file_path": "tasks/dict-1.md",
            "type_history": '[{"from_category": "inbox", "to_category": "task", "at": "2026-04-30T10:00:00"}]',
        }
        result = EntryMapper.dict_to_response(data)
        assert "type_history" in result
        assert len(result["type_history"]) == 1

    def test_dict_to_response_empty_type_history(self):
        from app.mappers.entry_mapper import EntryMapper

        data = {
            "id": "dict-2",
            "title": "Test",
            "content": "",
            "category": "note",
            "status": "doing",
            "priority": "medium",
            "tags": [],
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "file_path": "notes/dict-2.md",
        }
        result = EntryMapper.dict_to_response(data)
        assert result["type_history"] == []


# ── Integration: API endpoint tests ────────────────────────


@pytest.mark.asyncio
class TestConvertEndpoint:
    """POST /entries/{id}/convert integration tests"""

    async def _create_inbox(self, client: AsyncClient) -> dict:
        """Helper: create an inbox entry"""
        resp = await client.post("/entries", json={
            "category": "inbox",
            "title": "Inbox item",
            "content": "test content",
        })
        assert resp.status_code == 200
        return resp.json()

    async def test_convert_inbox_to_task(self, client: AsyncClient):
        """正常转换：inbox -> task"""
        entry = await self._create_inbox(client)

        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "task",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "task"
        assert len(data["type_history"]) == 1
        assert data["type_history"][0]["from_category"] == "inbox"
        assert data["type_history"][0]["to_category"] == "task"
        assert data["type_history"][0]["at"] is not None

    async def test_convert_inbox_to_task_with_priority_and_date(self, client: AsyncClient):
        """带额外字段转换：inbox -> task + priority=high + planned_date"""
        entry = await self._create_inbox(client)

        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "task",
            "priority": "high",
            "planned_date": "2026-05-15",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "task"
        assert data["priority"] == "high"
        assert data["planned_date"] is not None

    async def test_convert_inbox_to_decision(self, client: AsyncClient):
        """inbox -> decision"""
        entry = await self._create_inbox(client)

        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "decision",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "decision"
        assert len(data["type_history"]) == 1

    async def test_convert_inbox_to_note(self, client: AsyncClient):
        """inbox -> note"""
        entry = await self._create_inbox(client)

        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "note",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "note"

    async def test_convert_task_to_inbox_returns_422(self, client: AsyncClient):
        """非法转换：task -> inbox"""
        resp = await client.post("/entries", json={
            "category": "task",
            "title": "A task",
            "content": "content",
        })
        assert resp.status_code == 200
        entry = resp.json()

        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "inbox",
        })
        assert resp.status_code == 422

    async def test_convert_task_to_reflection_returns_422(self, client: AsyncClient):
        """非法转换：task -> reflection（应创建新条目，不走 convert）"""
        resp = await client.post("/entries", json={
            "category": "task",
            "title": "A task",
            "content": "content",
        })
        assert resp.status_code == 200
        entry = resp.json()

        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "reflection",
        })
        assert resp.status_code == 422

    async def test_convert_nonexistent_returns_404(self, client: AsyncClient):
        """条目不存在时 convert 返回 404"""
        resp = await client.post("/entries/nonexistent-id/convert", json={
            "target_category": "task",
        })
        assert resp.status_code == 404

    async def test_convert_invalid_target_category_returns_422(self, client: AsyncClient):
        """target_category 不在合法枚举中时返回 422"""
        entry = await self._create_inbox(client)

        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "invalid_category",
        })
        assert resp.status_code == 422

    async def test_convert_missing_target_category_returns_422(self, client: AsyncClient):
        """请求 body 缺少 target_category 时返回 422"""
        entry = await self._create_inbox(client)

        resp = await client.post(f"/entries/{entry['id']}/convert", json={})
        assert resp.status_code == 422

    async def test_two_independent_conversions(self, client: AsyncClient):
        """两条 inbox 分别转为 task 和 decision，各自 type_history 独立正确"""
        entry1 = await self._create_inbox(client)
        entry2 = await self._create_inbox(client)

        resp1 = await client.post(f"/entries/{entry1['id']}/convert", json={
            "target_category": "task",
        })
        resp2 = await client.post(f"/entries/{entry2['id']}/convert", json={
            "target_category": "decision",
        })

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        data1 = resp1.json()
        data2 = resp2.json()

        assert data1["category"] == "task"
        assert data1["type_history"][0]["to_category"] == "task"
        assert data2["category"] == "decision"
        assert data2["type_history"][0]["to_category"] == "decision"

    async def test_convert_with_parent_id(self, client: AsyncClient):
        """转换时可以设置 parent_id"""
        # 创建一个 project
        proj = await client.post("/entries", json={
            "category": "project",
            "title": "Parent Project",
        })
        assert proj.status_code == 200
        project_id = proj.json()["id"]

        entry = await self._create_inbox(client)
        resp = await client.post(f"/entries/{entry['id']}/convert", json={
            "target_category": "task",
            "parent_id": project_id,
        })
        assert resp.status_code == 200
        assert resp.json()["parent_id"] == project_id

    async def test_entry_response_includes_type_history(self, client: AsyncClient):
        """EntryResponse 中包含 type_history 字段"""
        entry = await self._create_inbox(client)

        # Before conversion, type_history should be empty
        resp = await client.get(f"/entries/{entry['id']}")
        assert resp.status_code == 200
        assert "type_history" in resp.json()
        assert resp.json()["type_history"] == []

    async def test_concurrent_convert_no_history_loss(self, client: AsyncClient):
        """并发转换同一条目：两个请求同时转换，type_history 不丢失记录"""
        import asyncio

        entry = await self._create_inbox(client)

        # 两个请求并发：一个合法，一个非法（已在前面转为 task 后，第二个也会尝试）
        async def do_convert(target: str):
            return await client.post(f"/entries/{entry['id']}/convert", json={
                "target_category": target,
            })

        # 第一个合法，第二个应该因已是 task 而失败
        results = await asyncio.gather(
            do_convert("task"),
            do_convert("task"),
            return_exceptions=True,
        )

        # 至少一个成功
        success_count = sum(
            1 for r in results
            if isinstance(r, Exception) is False and r.status_code == 200
        )
        assert success_count >= 1

        # 验证最终状态
        resp = await client.get(f"/entries/{entry['id']}")
        assert resp.status_code == 200
        data = resp.json()
        # type_history 至少有一条记录（不能丢）
        assert len(data["type_history"]) >= 1
