"""Qdrant 向量检索客户端"""
import asyncio
import logging
import os
import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.models import Task

if TYPE_CHECKING:
    from app.services.embedding import EmbeddingService


logger = logging.getLogger(__name__)

# 命名空间 UUID（用于生成确定性 UUID）
NAMESPACE_UUID = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def str_to_uuid(text_id: str) -> str:
    """将字符串 ID 转换为 UUID 格式（Qdrant 要求）"""
    return str(uuid.uuid5(NAMESPACE_UUID, text_id))


class QdrantClient:
    """Qdrant 向量检索客户端"""

    COLLECTION_NAME = "growth_entries"

    def __init__(
        self,
        url: str = None,
        api_key: str = None,
        embedding_service: "EmbeddingService" = None,
        vector_size: int = 1024,
    ):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self._client: Optional[AsyncQdrantClient] = None
        self._embedding_service = embedding_service
        self.vector_size = vector_size

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._client is not None

    async def check_alive(self) -> bool:
        """检查 Qdrant 服务是否可达（公共接口）"""
        if not self._client:
            return False
        try:
            await self._client.get_collections()
            return True
        except (OSError, ConnectionError, UnexpectedResponse) as e:
            logger.debug(f"Qdrant 健康检查失败: {e}")
            return False

    async def connect(self):
        """连接数据库，失败时设 _client=None 并抛 ConnectionError"""
        if not self._client:
            new_client = None
            try:
                new_client = AsyncQdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                )
                await new_client.get_collection(self.COLLECTION_NAME)
                # 连接和 collection 检查成功后才赋值
                self._client = new_client
                await self._ensure_collection()
            except Exception as e:
                # 清理未成功的 client
                if new_client:
                    try:
                        await new_client.close()
                    except (OSError, ConnectionError):
                        pass
                logger.warning(f"Qdrant 连接失败: {e}")
                self._client = None
                raise ConnectionError(f"Qdrant 连接失败: {e}") from e

    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None

    async def _ensure_collection(self):
        """确保 collection 存在且维度正确"""
        try:
            collection_info = await self._client.get_collection(self.COLLECTION_NAME)
            # 检查维度是否匹配
            existing_size = collection_info.config.params.vectors.size
            if existing_size != self.vector_size:
                # 维度不匹配，删除旧 collection 重建
                logger.warning(
                    f"Qdrant collection dimension mismatch: "
                    f"existing={existing_size}, expected={self.vector_size}. "
                    f"Recreating collection..."
                )
                await self._client.delete_collection(self.COLLECTION_NAME)
                await self._client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
        except UnexpectedResponse:
            # collection 不存在，创建新的
            await self._client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    def set_embedding_service(self, service: "EmbeddingService"):
        """设置 embedding 服务"""
        self._embedding_service = service

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本的向量（未配置 embedding 服务时返回空列表）"""
        if self._embedding_service:
            return await self._embedding_service.get_embedding(text)
        logger.warning("Embedding service not configured, returning empty vector")
        return []

    def _build_payload(self, entry: Task, user_id: str = "_default") -> Dict[str, Any]:
        """构建向量存储的 payload"""
        return {
            "original_id": entry.id,
            "title": entry.title,
            "type": entry.category.value,
            "status": entry.status.value,
            "tags": entry.tags,
            "file_path": entry.file_path,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "user_id": user_id,
        }

    # ==================== 向量操作 ====================

    async def upsert_entry(self, entry: Task, user_id: str = "_default") -> bool:
        """创建或更新条目向量"""
        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return False

        try:
            # 获取向量
            vector = await self._get_embedding(f"{entry.title}\n\n{entry.content}")

            # embedding 未配置时返回空向量，短路降级
            if not vector:
                logger.warning("Embedding not available, skipping upsert")
                return False

            # 存储向量（ID 转换为 UUID）
            await self._client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=str_to_uuid(entry.id),
                        vector=vector,
                        payload=self._build_payload(entry, user_id),
                    )
                ],
            )
            return True
        except (OSError, ConnectionError) as e:
            # 连接/IO 类异常：降级
            logger.warning(f"Qdrant upsert 失败: {e}")
            return False

    async def delete_entry(self, entry_id: str) -> bool:
        """删除条目向量"""
        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return False

        try:
            await self._client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=models.PointIdsList(
                    points=[str_to_uuid(entry_id)],
                ),
            )
            return True
        except (OSError, ConnectionError) as e:
            logger.warning(f"Qdrant delete 失败: {e}")
            return False

    async def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """获取单个条目向量"""
        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return None

        try:
            result = await self._client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[str_to_uuid(entry_id)],
                with_vectors=True,
            )
            if result:
                point = result[0]
                return {
                    "id": point.payload.get("original_id", str(point.id)),
                    "vector": point.vector,
                    "payload": point.payload,
                }
            return None
        except (OSError, ConnectionError) as e:
            logger.warning(f"Qdrant get_entry 失败: {e}")
            return None

    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_type: Optional[str] = None,
        filter_status: Optional[str] = None,
        user_id: str = "_default",
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return []

        try:
            # 获取查询向量
            query_vector = await self._get_embedding(query)

            # embedding 未配置时返回空向量，短路降级
            if not query_vector:
                logger.warning("Embedding not available, returning empty search results")
                return []

            # 构建过滤条件
            must_conditions = [
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            ]
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

            # 搜索 (使用新版 query_points API)
            response = await self._client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=query_vector,
                limit=limit,
                query_filter=filter_obj,
            )

            return [
                {
                    "id": result.payload.get("original_id", str(result.id)),
                    "score": result.score,
                    "payload": result.payload,
                }
                for result in response.points
            ]
        except (OSError, ConnectionError) as e:
            logger.warning(f"Qdrant search 失败: {e}")
            return []

    async def search_by_vector(
        self,
        vector: List[float],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """按向量搜索"""
        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return []

        try:
            response = await self._client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=vector,
                limit=limit,
            )

            return [
                {
                    "id": result.payload.get("original_id", str(result.id)),
                    "score": result.score,
                    "payload": result.payload,
                }
                for result in response.points
            ]
        except (OSError, ConnectionError) as e:
            logger.warning(f"Qdrant search_by_vector 失败: {e}")
            return []

    # ==================== 批量操作 ====================

    async def batch_upsert(self, entries: List[Task], user_id: str = "_default") -> int:
        """批量创建或更新向量（并行获取 embedding）"""
        if not entries:
            return 0

        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return 0

        try:
            # 并行获取所有 embedding
            texts = [f"{e.title}\n\n{e.content}" for e in entries]
            vectors = await asyncio.gather(*[self._get_embedding(t) for t in texts])

            # embedding 未配置时返回空向量列表，短路降级
            if not vectors or not vectors[0]:
                logger.warning("Embedding not available, skipping batch upsert")
                return 0

            points = [
                models.PointStruct(
                    id=str_to_uuid(entry.id),
                    vector=vector,
                    payload=self._build_payload(entry, user_id),
                )
                for entry, vector in zip(entries, vectors)
            ]

            await self._client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
            )
            return len(points)
        except (OSError, ConnectionError) as e:
            logger.warning(f"Qdrant batch_upsert 失败: {e}")
            return 0

    async def batch_delete(self, entry_ids: List[str]) -> int:
        """批量删除向量"""
        if not entry_ids:
            return 0

        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return 0

        try:
            await self._client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=models.PointIdsList(
                    points=[str_to_uuid(eid) for eid in entry_ids],
                ),
            )
            return len(entry_ids)
        except (OSError, ConnectionError) as e:
            logger.warning(f"Qdrant batch_delete 失败: {e}")
            return 0

    # ==================== 统计信息 ====================

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._client:
            try:
                await self.connect()
            except ConnectionError:
                return {"points_count": 0, "status": "unavailable"}

        try:
            info = await self._client.get_collection(self.COLLECTION_NAME)
            return {
                "points_count": info.points_count,
                "status": info.status.value,
            }
        except (OSError, ConnectionError) as e:
            logger.warning(f"Qdrant get_stats 失败: {e}")
            return {"points_count": 0, "status": "unavailable"}
