"""Embedding 服务 - 支持阿里云 multimodal-embedding-v1"""
import os
from typing import List, Optional
import httpx


class EmbeddingService:
    """Embedding 服务"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "text-embedding-v3",
    ):
        self.api_key = api_key or os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    async def get_embedding(self, text: str) -> List[float]:
        """获取文本的向量表示"""
        if not self.api_key:
            raise ValueError("Embedding API key not configured")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": text,
                    "encoding_format": "float",
                },
            )

            if response.status_code != 200:
                raise Exception(f"Embedding API error: {response.status_code} - {response.text}")

            data = response.json()
            return data["data"][0]["embedding"]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取向量"""
        if not self.api_key:
            raise ValueError("Embedding API key not configured")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                    "encoding_format": "float",
                },
            )

            if response.status_code != 200:
                raise Exception(f"Embedding API error: {response.status_code} - {response.text}")

            data = response.json()
            return [item["embedding"] for item in data["data"]]


# 支持的模型及其向量维度
EMBEDDING_MODELS = {
    # 智谱 AI
    "embedding-3": 2048,
    "embedding-2": 1024,
    # 阿里云
    "text-embedding-v3": 1024,
    "text-embedding-v2": 1536,
    "text-embedding-v1": 1536,
    "multimodal-embedding-v1": 1024,  # 多模态 embedding
}


def get_embedding_dimension(model: str) -> int:
    """获取模型的向量维度"""
    return EMBEDDING_MODELS.get(model, 1024)
