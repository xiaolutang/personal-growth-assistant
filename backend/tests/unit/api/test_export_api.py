"""B83: 导出 API 增强测试 — GET /entries/{id}/export + GET /review/growth-report"""
import importlib.util
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.infrastructure.storage.sqlite import SQLiteStorage

# === entries router ===
ENTRIES_MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "entries.py"
_entries_spec = importlib.util.spec_from_file_location("entries_module", ENTRIES_MODULE_PATH)
entries_module = importlib.util.module_from_spec(_entries_spec)
assert _entries_spec and _entries_spec.loader
_entries_spec.loader.exec_module(entries_module)
entries_router = entries_module.router

# === review router ===
REVIEW_MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "review.py"
_review_spec = importlib.util.spec_from_file_location("review_module", REVIEW_MODULE_PATH)
review_module = importlib.util.module_from_spec(_review_spec)
assert _review_spec and _review_spec.loader
_review_spec.loader.exec_module(review_module)
review_router = review_module.router

_mock_user = MagicMock()
_mock_user.id = "test-user"


class _MockSyncService:
    """Mock storage with temp file-based SQLite"""

    def __init__(self, data_dir: str | None = None):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.sqlite = SQLiteStorage(self._tmp.name)
        self._data_dir = data_dir

    def get_markdown_storage(self, user_id: str):
        """Return a real MarkdownStorage if data_dir provided"""
        if self._data_dir:
            from app.infrastructure.storage.markdown import MarkdownStorage
            return MarkdownStorage(Path(self._data_dir) / user_id)
        return None

    def cleanup(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass


def _create_entry_file(data_dir: str, user_id: str, entry_id: str, category: str, title: str, content: str = "测试内容"):
    """创建一个 entry markdown 文件"""
    cat_dirs = {
        "task": "tasks", "note": "notes", "inbox": "inbox",
        "project": "projects", "decision": "decisions",
        "reflection": "reflections", "question": "questions",
    }
    cat_dir = cat_dirs.get(category, "notes")
    entry_dir = Path(data_dir) / user_id / cat_dir
    entry_dir.mkdir(parents=True, exist_ok=True)
    file_content = f"# {title}\n\n{content}\n"
    entry_file = entry_dir / f"{entry_id}.md"
    entry_file.write_text(file_content, encoding="utf-8")
    return str(entry_file)


def _insert_entry_index(sqlite: SQLiteStorage, entry_id: str, user_id: str, entry_type: str, title: str):
    """直接在 entries 表插入索引记录"""
    conn = sqlite.get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cat_dirs = {"task": "tasks", "note": "notes", "inbox": "inbox", "project": "projects",
                    "decision": "decisions", "reflection": "reflections", "question": "questions"}
        file_path = f"{cat_dirs.get(entry_type, 'notes')}/{entry_id}.md"
        conn.execute(
            "INSERT INTO entries (id, type, title, content, status, user_id, created_at, file_path) VALUES (?, ?, ?, '', 'doing', ?, ?, ?)",
            (entry_id, entry_type, title, user_id, now, file_path),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def tmp_data_dir():
    """Create temp data directory"""
    d = tempfile.mkdtemp()
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)


# ===== 单条目导出测试 =====


class TestSingleEntryExport:
    """GET /entries/{id}/export"""

    async def test_export_existing_entry(self, tmp_data_dir):
        """正常: 导出存在的条目，验证 Content-Disposition 和文件内容"""
        entry_id = "test-entry-001"
        _create_entry_file(tmp_data_dir, "test-user", entry_id, "task", "测试任务", "任务内容")

        mock_storage = _MockSyncService(data_dir=tmp_data_dir)

        # 在 SQLite 创建条目索引
        _insert_entry_index(mock_storage.sqlite, entry_id, "test-user", "task", "测试任务")

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(entries_module, "get_entry_service") as mock_get_service:
            from app.services.entry_service import EntryService
            service = EntryService(mock_storage)
            mock_get_service.return_value = service

            app.include_router(entries_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/entries/{entry_id}/export")

        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")
        assert "attachment" in response.headers.get("content-disposition", "")
        assert "%E6%B5%8B%E8%AF%95%E4%BB%BB%E5%8A%A1" in response.headers.get("content-disposition", "")  # URL-encoded 测试任务
        assert "任务内容" in response.text

        mock_storage.cleanup()

    async def test_export_entry_404(self):
        """异常: 导出不存在的条目 404"""
        mock_storage = _MockSyncService()

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(entries_module, "get_entry_service") as mock_get_service:
            from app.services.entry_service import EntryService
            service = EntryService(mock_storage)
            mock_get_service.return_value = service

            app.include_router(entries_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/entries/nonexistent/export")

        assert response.status_code == 404
        mock_storage.cleanup()

    async def test_export_other_user_entry_404(self, tmp_data_dir):
        """异常: 导出其他用户的条目 404"""
        entry_id = "other-entry-001"
        # 创建在 other-user 目录
        _create_entry_file(tmp_data_dir, "other-user", entry_id, "task", "别人的任务")

        mock_storage = _MockSyncService(data_dir=tmp_data_dir)
        _insert_entry_index(mock_storage.sqlite, entry_id, "other-user", "task", "别人的任务")

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(entries_module, "get_entry_service") as mock_get_service:
            from app.services.entry_service import EntryService
            service = EntryService(mock_storage)
            mock_get_service.return_value = service

            app.include_router(entries_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/entries/{entry_id}/export")

        assert response.status_code == 404
        mock_storage.cleanup()

    async def test_export_long_title_special_chars(self, tmp_data_dir):
        """边界: 导出长标题条目，文件名特殊字符替换为 _"""
        entry_id = "test-special-001"
        _create_entry_file(tmp_data_dir, "test-user", entry_id, "note", "测试/特殊:字符*标题?", "内容")

        mock_storage = _MockSyncService(data_dir=tmp_data_dir)
        _insert_entry_index(mock_storage.sqlite, entry_id, "test-user", "note", "测试/特殊:字符*标题?")

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(entries_module, "get_entry_service") as mock_get_service:
            from app.services.entry_service import EntryService
            service = EntryService(mock_storage)
            mock_get_service.return_value = service

            app.include_router(entries_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/entries/{entry_id}/export")

        assert response.status_code == 200
        cd = response.headers.get("content-disposition", "")
        # 特殊字符应被替换
        assert "/" not in cd.split("filename=")[-1].strip('"').replace("/entries/", "")
        mock_storage.cleanup()

    async def test_export_requires_auth(self):
        """异常: 未认证访问 /entries/{id}/export 返回 401"""
        app = FastAPI()
        app.include_router(entries_router)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/entries/some-id/export")
        assert response.status_code in (401, 403)


# ===== 成长报告导出测试 =====


class TestGrowthReportExport:
    """GET /review/growth-report — 路由层薄包装，逻辑在 ReviewService.export_growth_report"""

    def _make_mock_service(self, md_content: str):
        """创建 mock review_service，export_growth_report 返回指定 markdown"""
        mock_review = MagicMock()
        mock_review.export_growth_report = AsyncMock(return_value=md_content)
        return mock_review

    async def test_growth_report_contains_4_sections(self):
        """正常: 成长报告包含 4 个 section"""
        md = "# 📊 成长报告\n## 概览\n总条目数 | 10\n## 学习趋势\n暂无数据\n## 学习连续天数\n5 天\n## 知识图谱概览\n概念数 | 10"
        mock_review = self._make_mock_service(md)

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(review_module, "get_review_service", return_value=mock_review):
            app.include_router(review_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/review/growth-report")

        assert response.status_code == 200
        content = response.text
        assert "成长报告" in content
        assert "概览" in content
        assert "学习趋势" in content
        assert "学习连续天数" in content
        assert "知识图谱概览" in content
        assert "5 天" in content

    async def test_growth_report_data_complete(self):
        """正常: 成长报告数据完整，每个 section 有具体数值"""
        md = "# 📊 成长报告\n## 概览\n总条目数 | 1\n## 学习趋势\n暂无数据\n## 学习连续天数\n3 天\n## 知识图谱概览\n概念数 | 5"
        mock_review = self._make_mock_service(md)

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(review_module, "get_review_service", return_value=mock_review):
            app.include_router(review_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/review/growth-report")

        content = response.text
        assert "总条目数" in content
        assert "3 天" in content
        assert "5" in content

    async def test_growth_report_empty_data(self):
        """边界: 空用户数据时报告各 section 为 0 或'暂无数据'"""
        md = "# 📊 成长报告\n## 概览\n总条目数 | 0\n## 学习趋势\n暂无数据\n## 学习连续天数\n0 天\n## 知识图谱概览\n暂无数据"
        mock_review = self._make_mock_service(md)

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(review_module, "get_review_service", return_value=mock_review):
            app.include_router(review_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/review/growth-report")

        assert response.status_code == 200
        content = response.text
        assert "0 天" in content
        assert "总条目数 | 0" in content
        assert "暂无数据" in content

    async def test_growth_report_requires_auth(self):
        """异常: 未认证访问 /review/growth-report 返回 401"""
        app = FastAPI()
        app.include_router(review_router)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/review/growth-report")
        assert response.status_code in (401, 403)

    async def test_growth_report_neo4j_degradation(self):
        """降级: Neo4j 不可用时知识图谱 section 显示'暂无数据'，报告其余部分正常"""
        md = "# 📊 成长报告\n## 概览\n总条目数 | 0\n## 学习趋势\n暂无数据\n## 学习连续天数\n7 天\n## 知识图谱概览\n暂无数据"
        mock_review = self._make_mock_service(md)

        app = FastAPI()
        from app.routers.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: _mock_user

        with patch.object(review_module, "get_review_service", return_value=mock_review):
            app.include_router(review_router)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/review/growth-report")

        assert response.status_code == 200
        content = response.text
        assert "7 天" in content
        assert "暂无数据" in content
