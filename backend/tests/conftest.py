"""共享测试 Fixtures"""
import asyncio
import tempfile
import shutil
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient, ASGITransport

# 添加项目路径
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
    from app.storage import init_storage

    s = await init_storage(
        data_dir=temp_data_dir,
        neo4j_uri=None,
        qdrant_url=None,
        llm_caller=None,
    )
    yield s


@pytest.fixture
async def client(storage) -> AsyncGenerator[AsyncClient, None]:
    """创建测试客户端"""
    from app.main import app
    from app.routers import deps

    # 注入存储服务
    deps.storage = storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as c:
        yield c


@pytest.fixture
def sqlite_storage(temp_data_dir: str):
    """创建 SQLite 存储实例"""
    from app.storage.sqlite import SQLiteStorage

    s = SQLiteStorage(db_path=f"{temp_data_dir}/test.db")
    yield s


@pytest.fixture
def markdown_storage(temp_data_dir: str):
    """创建 Markdown 存储实例"""
    from app.storage.markdown import MarkdownStorage

    s = MarkdownStorage(data_dir=temp_data_dir)
    yield s


@pytest.fixture
def mock_llm_caller():
    """Mock LLM Caller"""
    from app.callers.mock_caller import MockCaller

    return MockCaller(response='{"intent": "create", "tasks": [], "tags": [], "concepts": [], "relations": []}')


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
