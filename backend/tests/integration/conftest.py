"""集成测试 Fixtures - 使用现有 Docker 容器"""
import os
import pytest

# 标记所有集成测试
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (needs Docker)"
    )


# 使用现有容器的配置
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:16333")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:17687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")


@pytest.fixture(scope="module")
def qdrant_url():
    """使用现有 Qdrant 容器的 URL"""
    return QDRANT_URL


@pytest.fixture(scope="module")
def neo4j_config():
    """使用现有 Neo4j 容器的配置"""
    return {
        "uri": NEO4J_URI,
        "username": NEO4J_USERNAME,
        "password": NEO4J_PASSWORD,
    }


@pytest.fixture
async def qdrant_client_with_container(qdrant_url):
    """使用现有容器的 Qdrant 客户端"""
    from app.storage.qdrant_client import QdrantClient

    # 创建 mock embedding 服务（不需要真实 LLM）
    class MockEmbeddingService:
        async def get_embedding(self, text: str):
            # 返回固定的 mock 向量
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
    """使用现有容器的 Neo4j 客户端"""
    from app.storage.neo4j_client import Neo4jClient

    client = Neo4jClient(
        uri=neo4j_config["uri"],
        username=neo4j_config["username"],
        password=neo4j_config["password"],
    )
    await client.connect()
    await client.create_indexes()

    yield client

    await client.close()
