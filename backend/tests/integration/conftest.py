"""集成测试 Fixtures - 通过 Docker 部署环境测试"""
import os
import pytest
import httpx

# 标记所有集成测试
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (needs Docker)"
    )


# 通过 Traefik 网关访问（本地 Docker 部署后可用）
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost/growth/api")
# Auth 路由挂载在 /auth（无 /api 前缀），需要独立的 base URL
# 容器内直接访问 uvicorn（host:port），宿主机通过 Traefik 网关（带 path 前缀）
_in_container = os.path.exists("/.dockerenv")
if _in_container:
    # 容器内: 从 API_BASE_URL 提取 scheme://host:port 部分
    from urllib.parse import urlparse
    _parsed = urlparse(API_BASE_URL)
    _DEFAULT_AUTH_BASE = f"{_parsed.scheme}://{_parsed.netloc}"
else:
    _DEFAULT_AUTH_BASE = API_BASE_URL.replace("/api", "")
AUTH_BASE_URL = os.getenv("AUTH_BASE_URL", _DEFAULT_AUTH_BASE)

# 直连数据库配置（需要在 pga 容器网络内执行，或基础设施 debug 模式）
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "changeme123")


@pytest.fixture(scope="module")
def api_base_url():
    """通过 Traefik 网关的 API 基础 URL"""
    return API_BASE_URL


@pytest.fixture(scope="module")
def app_base_url():
    """应用根 URL（不含 /api 前缀），用于 auth/search 等无前缀路由"""
    return AUTH_BASE_URL


@pytest.fixture(scope="module")
def auth_token(app_base_url):
    """获取集成测试用的 auth token"""
    import uuid
    username = f"e2e_test_{uuid.uuid4().hex[:6]}"
    # Auth 路由挂载在 /auth（无 /api 前缀），使用 AUTH_BASE_URL
    auth_base = AUTH_BASE_URL
    # 注册
    resp = httpx.post(
        f"{auth_base}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "testpass123"},
        timeout=10,
    )
    if resp.status_code not in (200, 201, 409):
        pytest.skip("认证服务不可用，跳过集成测试")
    # 登录
    resp = httpx.post(
        f"{auth_base}/auth/login",
        json={"username": username, "password": "testpass123"},
        timeout=10,
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    pytest.skip("登录失败，跳过集成测试")


@pytest.fixture(scope="module")
def qdrant_url():
    """Qdrant URL（容器网络内）"""
    return QDRANT_URL


@pytest.fixture(scope="module")
def neo4j_config():
    """Neo4j 配置（容器网络内）"""
    return {
        "uri": NEO4J_URI,
        "username": NEO4J_USERNAME,
        "password": NEO4J_PASSWORD,
    }


@pytest.fixture
async def qdrant_client_with_container(qdrant_url):
    """使用容器内 Qdrant 的客户端（需要在容器网络内执行）"""
    from app.infrastructure.storage.qdrant_client import QdrantClient

    class MockEmbeddingService:
        async def get_embedding(self, text: str):
            return [0.1] * 1024

    client = QdrantClient(
        url=qdrant_url,
        embedding_service=MockEmbeddingService(),
        vector_size=1024,
    )
    await client.connect()

    yield client

    await client.close()


@pytest.fixture
async def neo4j_client_with_container(neo4j_config):
    """使用容器内 Neo4j 的客户端（需要在容器网络内执行）"""
    from app.infrastructure.storage.neo4j_client import Neo4jClient

    client = Neo4jClient(
        uri=neo4j_config["uri"],
        username=neo4j_config["username"],
        password=neo4j_config["password"],
    )
    await client.connect()
    await client.create_indexes()

    yield client

    await client.close()
