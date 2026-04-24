"""B89 搜索过滤增强测试：时间 + 标签 + 空 query"""
import sys
import types

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock langgraph before importing app modules
import sys
import types

if "langgraph.checkpoint.sqlite.aio" not in sys.modules:
    sqlite_pkg = types.ModuleType("langgraph.checkpoint.sqlite")
    aio_pkg = types.ModuleType("langgraph.checkpoint.sqlite.aio")
    aio_pkg.AsyncSqliteSaver = type("AsyncSqliteSaver", (), {})
    sys.modules["langgraph.checkpoint.sqlite"] = sqlite_pkg
    sys.modules["langgraph.checkpoint.sqlite.aio"] = aio_pkg

from app.api.schemas.entry import EntryResponse, EntryListResponse
from app.routers.search import router as search_router


def _entry(
    id="e1", title="测试", category="note", status="doing",
    tags=None, created_at="2026-04-22T10:00:00", **kw,
):
    """构造 EntryResponse 字典"""
    return {
        "id": id, "title": title, "content": "内容",
        "category": category, "status": status, "priority": "medium",
        "tags": tags or [], "created_at": created_at,
        "updated_at": created_at, "file_path": f"data/notes/{id}.md",
        **kw,
    }


@pytest.fixture
def mock_deps():
    """Mock 所有 search 路由依赖"""
    from unittest.mock import patch
    from app.routers.deps import get_current_user

    mock_storage = MagicMock()
    mock_entry_svc = AsyncMock()
    mock_hybrid = AsyncMock()
    mock_user = MagicMock(id="user1")

    app = FastAPI()
    app.include_router(search_router)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch("app.routers.search.get_storage", return_value=mock_storage), \
         patch("app.routers.search.get_entry_service", return_value=mock_entry_svc), \
         patch("app.routers.search.get_hybrid_search_service", return_value=mock_hybrid):
        tc = TestClient(app)
        yield tc, mock_storage, mock_entry_svc, mock_hybrid


class TestSearchTimeFilter:
    """时间过滤测试"""

    def test_both_start_end_time(self, mock_deps):
        """start_time + end_time 都传，结果都在范围内"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", created_at="2026-04-20T10:00:00")),
            EntryResponse(**_entry(id="2", created_at="2026-04-22T10:00:00")),
            EntryResponse(**_entry(id="3", created_at="2026-04-25T10:00:00")),
        ]

        resp = tc.post("/search", json={
            "query": "test",
            "start_time": "2026-04-20T00:00:00",
            "end_time": "2026-04-22T23:59:59",
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 2
        assert {r["id"] for r in results} == {"1", "2"}

    def test_start_time_only(self, mock_deps):
        """只传 start_time，结果 >= start_time"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", created_at="2026-04-19T10:00:00")),
            EntryResponse(**_entry(id="2", created_at="2026-04-22T10:00:00")),
        ]

        resp = tc.post("/search", json={
            "query": "test", "start_time": "2026-04-20T00:00:00",
        })
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1
        assert resp.json()["results"][0]["id"] == "2"

    def test_end_time_only(self, mock_deps):
        """只传 end_time，结果 <= end_time"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", created_at="2026-04-19T10:00:00")),
            EntryResponse(**_entry(id="2", created_at="2026-04-25T10:00:00")),
        ]

        resp = tc.post("/search", json={
            "query": "test", "end_time": "2026-04-22T23:59:59",
        })
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1
        assert resp.json()["results"][0]["id"] == "1"

    def test_no_time_filter(self, mock_deps):
        """不传时间参数，不过滤"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1")),
            EntryResponse(**_entry(id="2")),
        ]

        resp = tc.post("/search", json={"query": "test"})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 2

    def test_start_gt_end_returns_empty(self, mock_deps):
        """start_time > end_time，返回空结果"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", created_at="2026-04-22T10:00:00")),
        ]

        resp = tc.post("/search", json={
            "query": "test",
            "start_time": "2026-04-25T00:00:00",
            "end_time": "2026-04-20T00:00:00",
        })
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_boundary_inclusive(self, mock_deps):
        """闭区间边界：start_time 和 end_time 精确匹配的条目都包含"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", created_at="2026-04-20T00:00:00")),
            EntryResponse(**_entry(id="2", created_at="2026-04-22T23:59:59")),
            EntryResponse(**_entry(id="3", created_at="2026-04-21T12:00:00")),
        ]

        resp = tc.post("/search", json={
            "query": "test",
            "start_time": "2026-04-20T00:00:00",
            "end_time": "2026-04-22T23:59:59",
        })
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 3


class TestSearchTagFilter:
    """标签过滤测试"""

    def test_tag_intersection(self, mock_deps):
        """传 tags=['python']，结果至少匹配一个"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", tags=["python", "ai"])),
            EntryResponse(**_entry(id="2", tags=["java"])),
            EntryResponse(**_entry(id="3", tags=[])),
        ]

        resp = tc.post("/search", json={"query": "test", "tags": ["python"]})
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == "1"

    def test_tag_no_match(self, mock_deps):
        """传不存在的标签，返回空"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", tags=["python"])),
        ]

        resp = tc.post("/search", json={"query": "test", "tags": ["不存在标签"]})
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_no_tag_filter(self, mock_deps):
        """不传 tags，不过滤"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", tags=["python"])),
            EntryResponse(**_entry(id="2", tags=[])),
        ]

        resp = tc.post("/search", json={"query": "test"})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 2

    def test_empty_tags_array(self, mock_deps):
        """tags=[] 等价于不筛选"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(id="1", tags=["python"])),
            EntryResponse(**_entry(id="2", tags=[])),
        ]

        resp = tc.post("/search", json={"query": "test", "tags": []})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 2


class TestSearchCombinedFilter:
    """组合过滤测试"""

    def test_time_tag_filter_type_combined(self, mock_deps):
        """时间 + 标签 + filter_type 同时传入"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()

        mock_hybrid.search.return_value = [
            EntryResponse(**_entry(
                id="1", category="task", tags=["python"],
                created_at="2026-04-21T10:00:00",
            )),
            EntryResponse(**_entry(
                id="2", category="note", tags=["python"],
                created_at="2026-04-21T10:00:00",
            )),
            EntryResponse(**_entry(
                id="3", category="task", tags=["java"],
                created_at="2026-04-21T10:00:00",
            )),
        ]

        resp = tc.post("/search", json={
            "query": "test", "filter_type": "task",
            "start_time": "2026-04-20T00:00:00",
            "end_time": "2026-04-22T23:59:59",
            "tags": ["python"],
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == "1"


class TestSearchEmptyQuery:
    """空 query 测试"""

    def test_empty_query_with_filters(self, mock_deps):
        """query 为空 + 过滤 → 走 getEntries + 后过滤"""
        tc, _, mock_entry_svc, _ = mock_deps

        mock_entry_svc.list_entries.return_value = EntryListResponse(entries=[
            EntryResponse(**_entry(id="1", tags=["python"], created_at="2026-04-21T10:00:00")),
            EntryResponse(**_entry(id="2", tags=["java"], created_at="2026-04-10T10:00:00")),
        ], total=2)

        resp = tc.post("/search", json={
            "query": "", "start_time": "2026-04-20T00:00:00", "tags": ["python"],
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == "1"

    def test_empty_query_no_filters(self, mock_deps):
        """query 为空 + 无过滤 → 返回全部条目"""
        tc, _, mock_entry_svc, _ = mock_deps

        mock_entry_svc.list_entries.return_value = EntryListResponse(entries=[
            EntryResponse(**_entry(id="1")),
            EntryResponse(**_entry(id="2")),
        ], total=2)

        resp = tc.post("/search", json={"query": ""})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 2

    def test_null_query_same_as_empty(self, mock_deps):
        """query 为 null 等同于空字符串"""
        tc, _, mock_entry_svc, _ = mock_deps

        mock_entry_svc.list_entries.return_value = EntryListResponse(entries=[], total=0)

        resp = tc.post("/search", json={"query": None})
        assert resp.status_code == 200
        mock_entry_svc.list_entries.assert_called_once()


class TestSearchSqliteFallback:
    """SQLite 降级路径过滤测试"""

    def test_sqlite_fallback_with_filters(self, mock_deps):
        """mock HybridSearchService 失败，降级后过滤仍生效"""
        tc, mock_storage, _, mock_hybrid = mock_deps
        mock_hybrid.search.side_effect = Exception("search failed")
        mock_storage.qdrant = MagicMock()
        mock_storage.sqlite = MagicMock()
        mock_storage.sqlite.search.return_value = [
            {"id": "1", "title": "py", "content": "c", "type": "note",
             "status": "doing", "tags": ["python"], "file_path": "",
             "created_at": "2026-04-21T10:00:00"},
            {"id": "2", "title": "jv", "content": "c", "type": "note",
             "status": "doing", "tags": ["java"], "file_path": "",
             "created_at": "2026-04-10T10:00:00"},
        ]

        resp = tc.post("/search", json={
            "query": "test", "tags": ["python"],
            "start_time": "2026-04-20T00:00:00",
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == "1"


class TestSearchValidation:
    """参数校验测试"""

    def test_invalid_start_time_422(self, mock_deps):
        """start_time 格式非法 → 422"""
        tc, _, _, _ = mock_deps
        resp = tc.post("/search", json={"query": "test", "start_time": "not-a-date"})
        assert resp.status_code == 422

    def test_invalid_end_time_422(self, mock_deps):
        """end_time 格式非法 → 422"""
        tc, _, _, _ = mock_deps
        resp = tc.post("/search", json={"query": "test", "end_time": "2026/04/20"})
        assert resp.status_code == 422
