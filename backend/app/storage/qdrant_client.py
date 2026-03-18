"""Qdrant 向量检索客户端"""
import os
from typing import List, Optional, Dict, Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.models import Task


class QdrantClient:
    """Qdrant 向量检索客户端"""

    COLLECTION_NAME = "growth_entries"
    VECTOR_SIZE = 1536  # OpenAI embedding 维度

    def __init__(
        self,
        url: str = None,
        api_key: str = None,
        embedding_func=None,
    ):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self._client: Optional[AsyncQdrantClient] = None
        self._embedding_func = embedding_func

    async def connect(self):
        """连接数据库"""
        if not self._client:
            self._client = AsyncQdrantClient(
                url=self.url,
                api_key=self.api_key,
            )
            await self._ensure_collection()

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None

    async def _ensure_collection(self):
        """确保 collection 存在"""
        try:
            await self._client.get_collection(self.COLLECTION_NAME)
        except UnexpectedResponse:
            await self._client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )

    def set_embedding_func(self, func):
        """设置 embedding 函数"""
        self._embedding_func = func

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本的向量"""
        if self._embedding_func:
            return await self._embedding_func(text)
        raise NotImplementedError("Embedding function not set")

    # ==================== 向量操作 ====================

    async def upsert_entry(self, entry: Task) -> bool:
        """创建或更新条目向量"""
        if not self._client:
            await self.connect()

        # 获取向量
        vector = await self._get_embedding(f"{entry.title}\n\n{entry.content}")

        # 构建 payload
        payload = {
            "title": entry.title,
            "type": entry.category.value,
            "status": entry.status.value,
            "tags": entry.tags,
            "file_path": entry.file_path,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
        }

        # 存储向量
        await self._client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=entry.id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        return True

    async def delete_entry(self, entry_id: str) -> bool:
        """删除条目向量"""
        if not self._client:
            await self.connect()

        try:
            await self._client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=models.PointIdsList(
                    points=[entry_id],
                ),
            )
            return True
        except UnexpectedResponse:
            return False

    async def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """获取单个条目向量"""
        if not self._client:
            await self.connect()

        try:
            result = await self._client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[entry_id],
                with_vectors=True,
            )
            if result:
                point = result[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload,
                }
            return None
        except UnexpectedResponse:
            return None

    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_type: Optional[str] = None,
        filter_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        if not self._client:
            await self.connect()

        # 获取查询向量
        query_vector = await self._get_embedding(query)

        # 构建过滤条件
        must_conditions = []
        if filter_type:
            must_conditions.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value=filter_type),
                )
            )
        if filter_status:
            must_conditions.append(
                models.FieldCondition(
                    key="status",
                    match=models.MatchValue(value=filter_status),
                )
            )

        filter_obj = None
        if must_conditions:
            filter_obj = models.Filter(must=must_conditions)

        # 搜索
        results = await self._client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            query_filter=filter_obj,
        )

        return [
            {
                "id": str(result.id),
                "score": result.score,
                "payload": result.payload,
            }
            for result in results
        ]

    async def search_by_vector(
        self,
        vector: List[float],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """按向量搜索"""
        if not self._client:
            await self.connect()

        results = await self._client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=vector,
            limit=limit,
        )

        return [
            {
                "id": str(result.id),
                "score": result.score,
                "payload": result.payload,
            }
            for result in results
        ]

    # ==================== 批量操作 ====================

    async def batch_upsert(self, entries: List[Task]) -> int:
        """批量创建或更新向量"""
        if not entries:
            return 0

        if not self._client:
            await self.connect()

        points = []
        for entry in entries:
            vector = await self._get_embedding(f"{entry.title}\n\n{entry.content}")
            payload = {
                "title": entry.title,
                "type": entry.category.value,
                "status": entry.status.value,
                "tags": entry.tags,
                "file_path": entry.file_path,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
            points.append(
                models.PointStruct(
                    id=entry.id,
                    vector=vector,
                    payload=payload,
                )
            )

        await self._client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points,
        )
        return len(points)

    async def batch_delete(self, entry_ids: List[str]) -> int:
        """批量删除向量"""
        if not entry_ids:
            return 0

        if not self._client:
            await self.connect()

        await self._client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=models.PointIdsList(
                points=entry_ids,
            ),
        )
        return len(entry_ids)

    # ==================== 统计信息 ====================

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._client:
            await self.connect()

        info = await self._client.get_collection(self.COLLECTION_NAME)
        return {
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status.value,
        }
