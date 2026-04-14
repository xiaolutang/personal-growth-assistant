"""B18 Export 导出 API 单元测试"""

import io
import os
import sys
import tempfile
import types
import zipfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

if "langgraph.checkpoint.sqlite.aio" not in sys.modules:
    sqlite_pkg = types.ModuleType("langgraph.checkpoint.sqlite")
    aio_pkg = types.ModuleType("langgraph.checkpoint.sqlite.aio")

    class AsyncSqliteSaver:  # pragma: no cover
        pass

    aio_pkg.AsyncSqliteSaver = AsyncSqliteSaver
    sys.modules["langgraph.checkpoint.sqlite"] = sqlite_pkg
    sys.modules["langgraph.checkpoint.sqlite.aio"] = aio_pkg

from app.infrastructure.storage.sqlite import SQLiteStorage
from app.infrastructure.storage.storage_factory import StorageFactory
from app.infrastructure.storage.user_storage import UserStorage
from app.models import Category, Priority, Task, TaskStatus
from app.routers.entries import router as entries_router
from app.services.sync_service import SyncService
import app.routers.deps as deps

from tests.conftest import _make_entry


# --- Fixtures ---


@pytest.fixture
def user_storage(tmp_path):
    db_path = str(tmp_path / "test_users.db")
    return UserStorage(db_path)


@pytest.fixture
def client(user_storage, tmp_path):
    """创建 TestClient，注入完整 deps"""
    data_dir = str(tmp_path / "data")
    with patch.dict("os.environ", {
        "JWT_SECRET": "test-secret-key-for-testing",
        "DATA_DIR": data_dir,
    }):
        from app.core.config import get_settings
        get_settings.cache_clear()

        settings = get_settings()
        app = FastAPI()
        app.include_router(entries_router)

        # 注入 deps
        deps._user_storage = user_storage
        storage_factory = StorageFactory(settings.DATA_DIR)
        deps.storage = SyncService(
            markdown_storage=storage_factory.get_markdown_storage("_default"),
            storage_factory=storage_factory,
            sqlite_storage=SQLiteStorage(f"{settings.DATA_DIR}/index.db"),
        )
        deps.reset_all_services()

        # 注册测试用户并登录获取 token
        from app.services.auth_service import create_access_token
        from app.models.user import UserCreate

        test_user = user_storage.create_user(UserCreate(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        ))
        token = create_access_token(test_user.id)

        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        c._test_user_id = test_user.id
        c._data_dir = settings.DATA_DIR
        yield c

        # 清理
        deps._user_storage = None
        deps.storage = None
        deps.reset_all_services()
        get_settings.cache_clear()


def _seed_entries(client, count=3, category=Category.TASK, user_id=None):
    """向 SQLite + Markdown 写入测试条目"""
    user_id = user_id or client._test_user_id
    entries = []
    for i in range(count):
        entry_id = f"entry-{category.value}-{i:03d}"
        dir_name = MarkdownStorage.CATEGORY_DIRS.get(category, "notes")
        # inbox 的 dir_name 为空字符串，文件直接在根目录
        file_path = f"{dir_name}/{entry_id}.md" if dir_name else f"{entry_id}.md"
        entry = _make_entry(
            entry_id,
            title=f"测试条目-{i}",
            content=f"这是条目 {i} 的内容",
            category=category,
            created_at=datetime.now() - timedelta(days=count - i),
            file_path=file_path,
        )
        deps.storage.sqlite.upsert_entry(entry, user_id=user_id)
        deps.storage.get_markdown_storage(user_id).write_entry(entry)
        entries.append(entry)
    return entries


from app.infrastructure.storage.markdown import MarkdownStorage


# === Markdown 格式导出测试 ===


class TestExportMarkdown:
    """GET /entries/export?format=markdown"""

    def test_export_markdown_returns_zip(self, client):
        """正常导出返回可下载的 zip"""
        _seed_entries(client, count=2)

        resp = client.get("/entries/export?format=markdown")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert "attachment" in resp.headers.get("content-disposition", "")

        # 验证 zip 有效
        buf = io.BytesIO(resp.content)
        assert zipfile.is_zipfile(buf)

    def test_export_markdown_zip_has_category_dirs(self, client):
        """zip 内文件按 category 子目录组织"""
        _seed_entries(client, count=2, category=Category.TASK)
        _seed_entries(client, count=2, category=Category.NOTE)

        resp = client.get("/entries/export?format=markdown")
        assert resp.status_code == 200

        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
            # task 文件在 tasks/ 子目录
            task_files = [n for n in names if n.startswith("tasks/")]
            assert len(task_files) == 2
            # note 文件在 notes/ 子目录
            note_files = [n for n in names if n.startswith("notes/")]
            assert len(note_files) == 2

    def test_export_markdown_empty_data(self, client):
        """空数据返回空 zip（zip 结构有效但无文件）"""
        resp = client.get("/entries/export?format=markdown")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"

        buf = io.BytesIO(resp.content)
        assert zipfile.is_zipfile(buf)
        with zipfile.ZipFile(buf, "r") as zf:
            assert len(zf.namelist()) == 0


# === JSON 格式导出测试 ===


class TestExportJson:
    """GET /entries/export?format=json"""

    def test_export_json_returns_array(self, client):
        """json 格式返回完整条目数组"""
        _seed_entries(client, count=3)

        resp = client.get("/entries/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3

        # 验证条目结构
        entry = data[0]
        assert "id" in entry
        assert "title" in entry
        assert "category" in entry
        assert "content" in entry
        assert "tags" in entry
        assert "status" in entry
        assert "created_at" in entry
        assert "updated_at" in entry

    def test_export_json_empty_data(self, client):
        """空数据返回空数组"""
        resp = client.get("/entries/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 0


# === 过滤测试 ===


class TestExportFiltering:
    """type / start_date / end_date 过滤"""

    def test_type_filter(self, client):
        """type 参数只导出指定 category"""
        _seed_entries(client, count=2, category=Category.TASK)
        _seed_entries(client, count=3, category=Category.NOTE)

        resp = client.get("/entries/export?format=json&type=task")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert all(e["category"] == "task" for e in data)

    def test_type_filter_inbox(self, client):
        """type=inbox 只导出灵感"""
        _seed_entries(client, count=1, category=Category.INBOX)
        _seed_entries(client, count=2, category=Category.TASK)

        resp = client.get("/entries/export?format=json&type=inbox")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["category"] == "inbox"

    def test_date_range_filter(self, client):
        """start_date / end_date 日期范围过滤"""
        now = datetime.now()
        user_id = client._test_user_id

        # 创建不同日期的条目
        entry_old = _make_entry(
            "entry-old",
            title="旧条目",
            category=Category.TASK,
            created_at=now - timedelta(days=10),
        )
        entry_mid = _make_entry(
            "entry-mid",
            title="中间条目",
            category=Category.TASK,
            created_at=now - timedelta(days=5),
        )
        entry_new = _make_entry(
            "entry-new",
            title="新条目",
            category=Category.TASK,
            created_at=now - timedelta(days=1),
        )

        for e in [entry_old, entry_mid, entry_new]:
            deps.storage.sqlite.upsert_entry(e, user_id=user_id)

        # 只导出最近 3 天
        start = (now - timedelta(days=3)).strftime("%Y-%m-%d")
        resp = client.get(f"/entries/export?format=json&start_date={start}")
        assert resp.status_code == 200
        data = resp.json()
        ids = [e["id"] for e in data]
        assert "entry-new" in ids
        assert "entry-old" not in ids

    def test_type_filter_markdown(self, client):
        """type 过滤在 markdown 导出中生效"""
        _seed_entries(client, count=2, category=Category.TASK)
        _seed_entries(client, count=3, category=Category.PROJECT)

        resp = client.get("/entries/export?format=markdown&type=project")
        assert resp.status_code == 200
        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
            # 只有 projects/ 子目录下的文件
            assert all(n.startswith("projects/") for n in names)
            assert len(names) == 3


# === 异常测试 ===


class TestExportErrors:
    """异常和参数校验"""

    def test_invalid_format(self, client):
        """无效 format 参数返回 422"""
        resp = client.get("/entries/export?format=csv")
        assert resp.status_code == 422

    def test_default_format_is_markdown(self, client):
        """不传 format 默认为 markdown"""
        _seed_entries(client, count=1)

        resp = client.get("/entries/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"


# === 用户隔离测试 ===


class TestExportUserIsolation:
    """user_id 隔离：只导出当前用户的条目"""

    def test_only_exports_current_user_entries(self, client, user_storage):
        """只导出当前用户的条目，不包含其他用户的"""
        from app.services.auth_service import create_access_token
        from app.models.user import UserCreate

        # 当前用户已种 2 条
        _seed_entries(client, count=2)

        # 创建第二个用户并种 3 条
        user2 = user_storage.create_user(UserCreate(
            username="user2",
            email="user2@example.com",
            password="testpass123",
        ))
        for i in range(3):
            entry = _make_entry(
                f"entry-user2-{i:03d}",
                title=f"user2 条目-{i}",
                category=Category.NOTE,
            )
            deps.storage.sqlite.upsert_entry(entry, user_id=user2.id)

        # 当前用户导出只有自己的 2 条
        resp = client.get("/entries/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # 所有条目属于当前用户
        for e in data:
            assert "entry-task-" in e["id"]


# === 新增测试: Code Review 修复验证 ===


class TestExportInboxDirectory:
    """inbox 条目在 zip 中应放入 inbox/ 子目录"""

    def test_inbox_entries_in_inbox_subdir(self, client):
        """markdown 导出 inbox 条目时文件在 inbox/ 子目录"""
        _seed_entries(client, count=2, category=Category.INBOX)

        resp = client.get("/entries/export?format=markdown")
        assert resp.status_code == 200

        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
            # inbox 文件应在 inbox/ 子目录中
            inbox_files = [n for n in names if n.startswith("inbox/")]
            assert len(inbox_files) == 2, f"期望 2 个 inbox 文件，实际: {names}"
            # 不应在根目录出现 md 文件
            root_md = [n for n in names if "/" not in n and n.endswith(".md")]
            assert len(root_md) == 0, f"根目录不应有 md 文件: {root_md}"


class TestExportParameterValidation:
    """参数校验: type / start_date / end_date"""

    def test_invalid_type_returns_422(self, client):
        """非法 type 参数返回 422"""
        resp = client.get("/entries/export?format=json&type=invalid_type")
        assert resp.status_code == 422

    def test_invalid_start_date_returns_422(self, client):
        """非法 start_date 格式返回 422"""
        resp = client.get("/entries/export?format=json&start_date=not-a-date")
        assert resp.status_code == 422

    def test_invalid_start_date_format_returns_422(self, client):
        """非法 start_date 格式（如 2024/01/01）返回 422"""
        resp = client.get("/entries/export?format=json&start_date=2024/01/01")
        assert resp.status_code == 422

    def test_invalid_end_date_returns_422(self, client):
        """非法 end_date 格式返回 422"""
        resp = client.get("/entries/export?format=json&end_date=2024-13-45")
        assert resp.status_code == 422

    def test_valid_params_pass(self, client):
        """合法参数正常通过"""
        resp = client.get("/entries/export?format=json&type=task&start_date=2024-01-01&end_date=2026-12-31")
        assert resp.status_code == 200


class TestExportEndDateFilter:
    """end_date 单独过滤"""

    def test_end_date_filter_alone(self, client):
        """只传 end_date 也能正确过滤"""
        now = datetime.now()
        user_id = client._test_user_id

        entry_old = _make_entry(
            "entry-old-end",
            title="旧条目",
            category=Category.TASK,
            created_at=now - timedelta(days=10),
        )
        entry_new = _make_entry(
            "entry-new-end",
            title="新条目",
            category=Category.TASK,
            created_at=now - timedelta(days=1),
        )

        for e in [entry_old, entry_new]:
            deps.storage.sqlite.upsert_entry(e, user_id=user_id)

        # end_date 设为 5 天前：旧条目应该在范围内，新条目可能不在
        end = (now - timedelta(days=3)).strftime("%Y-%m-%d")
        resp = client.get(f"/entries/export?format=json&end_date={end}")
        assert resp.status_code == 200
        data = resp.json()
        ids = [e["id"] for e in data]
        assert "entry-old-end" in ids
        assert "entry-new-end" not in ids


class TestExportFilename:
    """Content-Disposition 文件名"""

    def test_markdown_export_filename(self, client):
        """zip 下载文件名为 entries_export.zip"""
        _seed_entries(client, count=1)

        resp = client.get("/entries/export?format=markdown")
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        assert "entries_export.zip" in cd


# === 流式导出测试 ===


class TestExportStreaming:
    """验证真正的流式导出行为（分块 yield）"""

    @pytest.mark.asyncio
    async def test_stream_yields_multiple_chunks(self, client):
        """大数据导出时分块 yield，chunk 数 > 1"""
        import app.routers.deps as deps

        user_id = client._test_user_id
        md_storage = deps.storage.get_markdown_storage(user_id)

        # 创建多个大条目，使用高熵随机内容确保压缩后仍 > 8KB
        import random
        import string

        random.seed(42)
        entries_created = []
        for i in range(20):
            # 生成高熵内容，压缩率低
            big_content = "".join(random.choices(string.ascii_letters + string.digits, k=5_000))
            entry_id = f"entry-task-big{i:03d}"
            entry = _make_entry(
                entry_id,
                title=f"大文件条目-{i}",
                content=big_content,
                category=Category.TASK,
                file_path=f"tasks/{entry_id}.md",
            )
            deps.storage.sqlite.upsert_entry(entry, user_id=user_id)
            md_storage.write_entry(entry)
            entries_created.append(entry_id)

        # 直接调用 service 层 generator
        service = deps.get_entry_service()
        chunks = []
        async for chunk in service.export_markdown_stream(
            type="task", user_id=user_id
        ):
            chunks.append(chunk)

        # 应该有多个 chunk（8KB 分块）
        assert len(chunks) > 1, f"期望多个 chunk，实际只有 {len(chunks)} 个"

        # 合并后应该是有效的 zip
        full_bytes = b"".join(chunks)
        buf = io.BytesIO(full_bytes)
        assert zipfile.is_zipfile(buf)
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
            assert len(names) == 20

    @pytest.mark.asyncio
    async def test_stream_cleans_up_temp_file(self, client):
        """流式导出完成后临时文件被清理"""
        import app.routers.deps as deps

        user_id = client._test_user_id
        service = deps.get_entry_service()

        _seed_entries(client, count=1)

        # patch mkstemp 捕获临时文件路径
        real_mkstemp = tempfile.mkstemp
        captured_tmp_path = None

        def mock_mkstemp(*args, **kwargs):
            nonlocal captured_tmp_path
            fd, path = real_mkstemp(*args, **kwargs)
            captured_tmp_path = path
            return fd, path

        with patch("app.services.entry_service.tempfile.mkstemp", side_effect=mock_mkstemp):
            chunks = []
            async for chunk in service.export_markdown_stream(user_id=user_id):
                chunks.append(chunk)

        # 临时文件应该已被清理（unlink）
        assert captured_tmp_path is not None, "未捕获到临时文件路径"
        assert not os.path.exists(captured_tmp_path), f"临时文件未被清理: {captured_tmp_path}"
