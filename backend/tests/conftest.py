"""共享测试 Fixtures"""
import asyncio
import tempfile
import shutil
from datetime import datetime
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient, ASGITransport

# 添加项目路径
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 确保测试环境有 JWT_SECRET（避免因 .env 缺失导致认证相关测试失败）
if not os.environ.get("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "test-secret-key-for-unit-tests"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_data_dir() -> Generator[str, None, None]:
    """创建临时数据目录"""
    dir_path = tempfile.mkdtemp(prefix="pga_test_")
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
async def storage(temp_data_dir: str):
    """初始化存储服务（无外部依赖）"""
    from app.services import init_storage

    s = await init_storage(
        data_dir=temp_data_dir,
        neo4j_uri=None,
        qdrant_url=None,
        llm_caller=None,
    )
    yield s


@pytest.fixture
async def test_user(storage):
    """创建测试用户（独立 fixture，供 client 和测试共用）"""
    from app.routers import deps
    from app.infrastructure.storage.user_storage import UserStorage
    import tempfile

    # 保存之前的全局状态，确保 teardown 后完整恢复
    _DEPS_GLOBALS = [
        'storage', '_user_storage',
        '_entry_service',
        '_review_service', '_knowledge_service',
        '_notification_service', '_goal_service',
    ]
    _prev = {k: getattr(deps, k, None) for k in _DEPS_GLOBALS}

    deps.storage = storage
    deps.reset_all_services()

    user_db = tempfile.mktemp(suffix=".db")
    deps._user_storage = UserStorage(user_db)

    from app.models.user import UserCreate
    user = deps._user_storage.create_user(UserCreate(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    ))
    yield user

    # 恢复全局状态（包括 reset_all_services 清空的缓存）
    for k, v in _prev.items():
        setattr(deps, k, v)

    import os
    try:
        os.unlink(user_db)
    except OSError:
        pass


@pytest.fixture
async def client(storage, test_user) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端（自动注入认证 token）"""
    from app.main import app
    from app.services.auth_service import create_access_token

    token = create_access_token(test_user.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.fixture
def sqlite_storage(temp_data_dir: str):
    """创建 SQLite 存储实例"""
    from app.infrastructure.storage.sqlite import SQLiteStorage

    s = SQLiteStorage(db_path=f"{temp_data_dir}/test.db")
    yield s


@pytest.fixture
def markdown_storage(temp_data_dir: str):
    """创建 Markdown 存储实例"""
    from app.infrastructure.storage.markdown import MarkdownStorage

    s = MarkdownStorage(data_dir=temp_data_dir)
    yield s


@pytest.fixture
def mock_llm_caller():
    """Mock LLM Caller"""
    from app.infrastructure.llm.mock_caller import MockCaller

    return MockCaller(response='{"intent": "create", "tasks": [], "tags": [], "concepts": [], "relations": []}')


# === 共享辅助函数 ===


def _make_entry(entry_id: str, title: str = "", content: str = "", **kwargs) -> "Task":
    """快速创建测试用 Task（供各测试模块复用）"""
    from app.models import Task, Category, TaskStatus, Priority

    return Task(
        id=entry_id,
        title=title or f"测试-{entry_id}",
        content=content,
        category=kwargs.get("category", Category.TASK),
        status=kwargs.get("status", TaskStatus.DOING),
        priority=kwargs.get("priority", Priority.MEDIUM),
        tags=kwargs.get("tags", []),
        created_at=kwargs.get("created_at", datetime.now()),
        updated_at=kwargs.get("updated_at", datetime.now()),
        file_path=kwargs.get("file_path", f"tasks/{entry_id}.md"),
    )


@pytest.fixture
def sample_task():
    """示例任务数据"""
    from datetime import datetime
    from app.models import Task, Category, TaskStatus, Priority

    return Task(
        id="task-test123",
        title="测试任务",
        content="这是一个测试任务的内容",
        category=Category.TASK,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["test", "sample"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="tasks/task-test123.md",
    )


@pytest.fixture
def sample_project():
    """示例项目数据"""
    from datetime import datetime
    from app.models import Task, Category, TaskStatus, Priority

    return Task(
        id="project-test123",
        title="测试项目",
        content="这是一个测试项目",
        category=Category.PROJECT,
        status=TaskStatus.DOING,
        priority=Priority.HIGH,
        tags=["project"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="projects/project-test123.md",
    )


@pytest.fixture
def sample_note():
    """示例笔记数据"""
    from datetime import datetime
    from app.models import Task, Category, TaskStatus, Priority

    return Task(
        id="note-test123",
        title="测试笔记",
        content="# 标题\n\n这是笔记内容",
        category=Category.NOTE,
        status=TaskStatus.DOING,
        priority=Priority.MEDIUM,
        tags=["note", "test"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        file_path="notes/note-test123.md",
    )


# ============ Qdrant Mock Fixtures ============
@pytest.fixture
def mock_qdrant_available():
    """Mock Qdrant 可用状态"""
    from unittest.mock import AsyncMock, patch, MagicMock
    from qdrant_client.http import models

    with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient') as mock_client_class:
        mock_instance = AsyncMock()
        mock_client_class.return_value = mock_instance

        # Mock get_collection (collection exists)
        mock_instance.get_collection = AsyncMock()

        # Mock query_points
        mock_result = MagicMock()
        mock_result.id = "test-uuid-1"
        mock_result.score = 0.9
        mock_result.payload = {"original_id": "task-1", "title": "测试任务"}
        mock_response = MagicMock()
        mock_response.points = [mock_result]
        mock_instance.query_points = AsyncMock(return_value=mock_response)

        # Mock upsert
        mock_instance.upsert = AsyncMock()

        # Mock delete
        mock_instance.delete = AsyncMock()

        # Mock retrieve
        mock_instance.retrieve = AsyncMock(return_value=[])

        # Mock close
        mock_instance.close = AsyncMock()

        yield mock_instance


@pytest.fixture
def mock_qdrant_unavailable():
    """Mock Qdrant 不可用状态"""
    from unittest.mock import patch

    with patch('app.infrastructure.storage.qdrant_client.AsyncQdrantClient') as mock_client:
        mock_client.side_effect = ConnectionError("Qdrant not available")
        yield mock_client


# ============ Neo4j Mock Fixtures ============
@pytest.fixture
def mock_neo4j_available():
    """Mock Neo4j 可用状态"""
    from unittest.mock import AsyncMock, patch, MagicMock

    with patch('app.infrastructure.storage.neo4j_client.AsyncGraphDatabase') as mock_graph_db:
        mock_driver = AsyncMock()
        mock_graph_db.driver.return_value = mock_driver

        # Mock session
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session.return_value = mock_session

        # Mock run result
        mock_result = MagicMock()
        mock_result.single = AsyncMock(return_value={"name": "测试概念", "description": "描述", "category": "技术"})
        mock_result.__aiter__ = MagicMock(return_value=iter([]))
        mock_session.run = AsyncMock(return_value=mock_result)

        # Mock close
        mock_driver.close = AsyncMock()

        yield mock_driver


@pytest.fixture
def mock_neo4j_unavailable():
    """Mock Neo4j 不可用状态"""
    from unittest.mock import patch
    from neo4j.exceptions import ServiceUnavailable

    with patch('app.infrastructure.storage.neo4j_client.AsyncGraphDatabase') as mock_graph_db:
        mock_graph_db.driver.side_effect = ServiceUnavailable("Neo4j not available")
        yield mock_graph_db


# ============ Embedding/LLM Mock Fixtures ============
@pytest.fixture
def mock_embedding_success():
    """Mock Embedding 服务成功响应"""
    from unittest.mock import patch, AsyncMock, MagicMock

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "data": [{"embedding": [0.1] * 1024}]
        })
        mock_client.post = AsyncMock(return_value=mock_response)

        yield mock_client


@pytest.fixture
def mock_embedding_api_error():
    """Mock Embedding API 错误"""
    from unittest.mock import patch, AsyncMock

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.post = AsyncMock(return_value=mock_response)

        yield mock_client


@pytest.fixture
def mock_embedding_timeout():
    """Mock Embedding 超时"""
    from unittest.mock import patch, AsyncMock
    import httpx

    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))

        yield mock_client
