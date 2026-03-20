"""混合搜索服务：向量 + 全文"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any

from app.api.schemas.entry import EntryResponse
from app.mappers.entry_mapper import EntryMapper
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """混合搜索结果"""
    entry_id: str
    score: float
    vector_score: float
    text_score: float
    entry_data: Optional[Dict] = None


class HybridSearchService:
    """混合搜索：向量 + 全文"""

    def __init__(self, storage: SyncService):
        self.storage = storage

    @staticmethod
    def _normalize_scores(scores: List[float]) -> List[float]:
        """归一化分数到 0-1 范围"""
        if not scores:
            return []
        max_score = max(scores)
        if max_score <= 0:
            return [0.0] * len(scores)
        return [s / max_score for s in scores]

    async def search(
        self,
        query: str,
        limit: int = 10,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        min_score: float = 0.25,
    ) -> List[EntryResponse]:
        """
        混合搜索流程：
        1. 并行执行向量搜索和全文搜索
        2. 归一化分数 (0-1)
        3. 加权合并: score = vector_weight * vec_score + text_weight * fts_score
        4. 按合并分数排序返回

        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            vector_weight: 向量搜索权重（默认 0.7）
            text_weight: 全文搜索权重（默认 0.3）
            min_score: 最低分数阈值（默认 0.25）

        Returns:
            排序后的条目响应列表
        """
        search_limit = limit * 2

        # 并行执行向量搜索和全文搜索
        vector_results: Dict[str, float] = {}
        text_results: Dict[str, Dict[str, Any]] = {}

        async def do_vector_search() -> Dict[str, float]:
            if not self.storage.qdrant:
                return {}
            try:
                results = await self.storage.qdrant.search(query, limit=search_limit)
                return {r["id"]: r.get("score", 0) for r in results if r.get("id")}
            except Exception as e:
                logger.warning(f"向量搜索失败: {e}")
                return {}

        def do_text_search() -> Dict[str, Dict[str, Any]]:
            if not self.storage.sqlite:
                return {}
            try:
                results = self.storage.sqlite.search(query, limit=search_limit)
                return {r["id"]: r for r in results if r.get("id")}
            except Exception as e:
                logger.warning(f"全文搜索失败: {e}")
                return {}

        # 在线程池中运行同步的 SQLite 搜索
        loop = asyncio.get_event_loop()
        vector_task = do_vector_search()
        text_task = loop.run_in_executor(None, do_text_search)

        # 并行等待
        vector_results, text_results = await asyncio.gather(
            vector_task, text_task, return_exceptions=False
        )

        # 合并所有 ID
        all_ids = set(vector_results.keys()) | set(text_results.keys())
        if not all_ids:
            return []

        # 归一化向量分数
        normalized_vector = self._normalize_dict_scores(vector_results)

        # 加权合并
        combined_results: List[HybridSearchResult] = []
        for entry_id in all_ids:
            vec_score = normalized_vector.get(entry_id, 0)
            text_score = 1.0 if entry_id in text_results else 0.0
            combined = vector_weight * vec_score + text_weight * text_score

            if combined >= min_score:
                combined_results.append(HybridSearchResult(
                    entry_id=entry_id,
                    score=combined,
                    vector_score=vec_score,
                    text_score=text_score,
                    entry_data=text_results.get(entry_id),
                ))

        # 按分数排序并限制数量
        combined_results.sort(key=lambda x: x.score, reverse=True)
        combined_results = combined_results[:limit]

        # 转换为 EntryResponse
        responses: List[EntryResponse] = []
        for result in combined_results:
            if result.entry_data:
                responses.append(EntryResponse(**EntryMapper.dict_to_response(result.entry_data)))
            else:
                entry = self.storage.markdown.read_entry(result.entry_id)
                if entry:
                    responses.append(EntryResponse(**EntryMapper.task_to_response(entry)))

        return responses

    def _normalize_dict_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """归一化字典分数到 0-1 范围"""
        if not scores:
            return {}
        max_score = max(scores.values())
        if max_score <= 0:
            return {k: 0.0 for k in scores}
        return {k: v / max_score for k, v in scores.items()}
