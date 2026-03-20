"""Embedding 服务单元测试 - Mock LLM API"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.embedding import (
    EmbeddingService,
    EMBEDDING_MODELS,
    get_embedding_dimension,
)


class TestEmbeddingService:
    """Embedding 服务测试 - Mock LLM API"""

    def test_init_with_api_key(self):
        """测试使用 API key 初始化"""
        service = EmbeddingService(api_key="test-key", base_url="http://test.com")
        assert service.api_key == "test-key"
        assert service.base_url == "http://test.com"

    def test_init_without_api_key(self):
        """测试没有 API key 时初始化"""
        with patch.dict("os.environ", {}, clear=True):
            service = EmbeddingService()
            assert service.api_key is None

    def test_default_model(self):
        """测试默认模型"""
        service = EmbeddingService(api_key="test-key")
        assert service.model == "text-embedding-v3"

    def test_custom_model(self):
        """测试自定义模型"""
        service = EmbeddingService(api_key="test-key", model="embedding-3")
        assert service.model == "embedding-3"

    async def test_get_embedding_success(self, mock_embedding_success):
        """测试正常生成 embedding"""
        service = EmbeddingService(api_key="test-key", base_url="http://test.com")

        result = await service.get_embedding("测试文本")

        assert len(result) == 1024
        assert all(v == 0.1 for v in result)
        mock_embedding_success.post.assert_called_once()

    async def test_get_embedding_no_api_key(self):
        """测试没有 API key 时抛出异常"""
        # 清除环境变量
        with patch.dict("os.environ", {}, clear=True):
            service = EmbeddingService()
            # 此时 api_key 应该是 None（因为环境变量也被清除了）
            assert service.api_key is None

            with pytest.raises(ValueError, match="Embedding API key not configured"):
                await service.get_embedding("测试文本")

    async def test_get_embedding_api_error(self, mock_embedding_api_error):
        """测试 API 错误时抛出异常"""
        service = EmbeddingService(api_key="test-key", base_url="http://test.com")

        with pytest.raises(Exception, match="Embedding API error"):
            await service.get_embedding("测试文本")

    async def test_get_embedding_timeout(self, mock_embedding_timeout):
        """测试超时时抛出异常"""
        service = EmbeddingService(api_key="test-key", base_url="http://test.com")

        with pytest.raises(httpx.TimeoutException):
            await service.get_embedding("测试文本")

    async def test_get_embeddings_batch_success(self):
        """测试批量生成 embedding"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "data": [
                    {"embedding": [0.1] * 1024},
                    {"embedding": [0.2] * 1024},
                ]
            })
            mock_client.post = AsyncMock(return_value=mock_response)

            service = EmbeddingService(api_key="test-key", base_url="http://test.com")
            results = await service.get_embeddings(["文本1", "文本2"])

            assert len(results) == 2
            assert all(v == 0.1 for v in results[0])
            assert all(v == 0.2 for v in results[1])

    async def test_get_embeddings_no_api_key(self):
        """测试批量生成时没有 API key"""
        # 清除环境变量
        with patch.dict("os.environ", {}, clear=True):
            service = EmbeddingService()
            assert service.api_key is None

            with pytest.raises(ValueError, match="Embedding API key not configured"):
                await service.get_embeddings(["文本1", "文本2"])

    async def test_get_embeddings_api_error(self):
        """测试批量生成时 API 错误"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Error"
            mock_client.post = AsyncMock(return_value=mock_response)

            service = EmbeddingService(api_key="test-key", base_url="http://test.com")

            with pytest.raises(Exception, match="Embedding API error"):
                await service.get_embeddings(["文本1", "文本2"])

    async def test_request_headers_correct(self):
        """测试请求头正确设置"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "data": [{"embedding": [0.1] * 1024}]
            })
            mock_client.post = AsyncMock(return_value=mock_response)

            service = EmbeddingService(api_key="test-api-key", base_url="http://test.com")
            await service.get_embedding("测试")

            # 验证请求参数
            call_args = mock_client.post.call_args
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-api-key"
            assert call_args[1]["headers"]["Content-Type"] == "application/json"
            assert call_args[1]["json"]["model"] == "text-embedding-v3"
            assert call_args[1]["json"]["input"] == "测试"
            assert call_args[1]["json"]["encoding_format"] == "float"

    async def test_request_url_correct(self):
        """测试请求 URL 正确"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "data": [{"embedding": [0.1] * 1024}]
            })
            mock_client.post = AsyncMock(return_value=mock_response)

            service = EmbeddingService(api_key="test-key", base_url="http://custom.api.com/v1")
            await service.get_embedding("测试")

            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://custom.api.com/v1/embeddings"


class TestEmbeddingModels:
    """Embedding 模型配置测试"""

    def test_supported_models_defined(self):
        """测试支持的模型已定义"""
        assert "text-embedding-v3" in EMBEDDING_MODELS
        assert "embedding-3" in EMBEDDING_MODELS
        assert "multimodal-embedding-v1" in EMBEDDING_MODELS

    def test_get_embedding_dimension_known_model(self):
        """测试获取已知模型的维度"""
        assert get_embedding_dimension("text-embedding-v3") == 1024
        assert get_embedding_dimension("embedding-3") == 2048
        assert get_embedding_dimension("embedding-2") == 1024

    def test_get_embedding_dimension_unknown_model(self):
        """测试获取未知模型的维度（默认值）"""
        assert get_embedding_dimension("unknown-model") == 1024

    def test_model_dimensions_correct(self):
        """测试模型维度正确"""
        # 阿里云模型
        assert EMBEDDING_MODELS["text-embedding-v3"] == 1024
        assert EMBEDDING_MODELS["text-embedding-v2"] == 1536
        assert EMBEDDING_MODELS["multimodal-embedding-v1"] == 1024

        # 智谱 AI 模型
        assert EMBEDDING_MODELS["embedding-3"] == 2048
        assert EMBEDDING_MODELS["embedding-2"] == 1024
