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
def auth_token(api_base_url):
    """获取集成测试用的 auth token"""
    import uuid
    username = f"e2e_test_{uuid.uuid4().hex[:6]}"
    # 注册
    resp = httpx.post(
        f"{api_base_url}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": "testpass123"},
        timeout=10,
    )
    if resp.status_code not in (200, 201, 409):
        pytest.skip("认证服务不可用，跳过集成测试")
    # 登录
    resp = httpx.post(
        f"{api_base_url}/auth/login",
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
