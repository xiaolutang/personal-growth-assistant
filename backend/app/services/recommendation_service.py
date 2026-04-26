"""知识推荐服务 — 提供知识缺口检测、复习推荐、共现推荐三种能力"""
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==================== 响应模型 ====================

class KnowledgeGapItem(BaseModel):
    """知识缺口项"""
    concept: str
    missing_prerequisites: List[str] = []


class ReviewSuggestionItem(BaseModel):
    """复习推荐项"""
    concept: str
    category: Optional[str] = None
    last_seen_days_ago: int = 0
    entry_count: int = 0


class RelatedConceptItem(BaseModel):
    """共现推荐项"""
    concept: str
    score: float = 0.0
    source: str = "tag"  # tag | neo4j


class RecommendationResponse(BaseModel):
    """推荐响应"""
    knowledge_gaps: List[KnowledgeGapItem] = []
    review_suggestions: List[ReviewSuggestionItem] = []
    related_concepts: List[RelatedConceptItem] = []
    source: str = "sqlite"  # sqlite | neo4j


class RecommendationService:
    """知识推荐服务

    三种推荐能力：
    1. knowledge_gaps: 知识缺口检测（PREREQUISITE 关系链中未涉足的概念）
    2. review_suggestions: 复习推荐（间隔重复策略，推荐近期未复习的概念）
    3. related_concepts: 共现推荐（基于标签共现扩展）
    """

    def __init__(self, neo4j_client=None, sqlite_storage=None):
        self._neo4j = neo4j_client
        self._sqlite = sqlite_storage

    def set_neo4j_client(self, client):
        """设置 Neo4j 客户端"""
        self._neo4j = client

    def set_sqlite_storage(self, storage):
        """设置 SQLite 存储"""
        self._sqlite = storage

    def is_neo4j_available(self) -> bool:
        """检查 Neo4j 是否可用"""
        return self._neo4j is not None and self._neo4j.is_connected

    # ==================== 知识缺口检测 ====================

    async def knowledge_gaps(self, user_id: str = "_default") -> List[KnowledgeGapItem]:
        """检测知识缺口：有前置关系(PREREQUISITE)但用户未学习的概念

        Neo4j 可用时从图查询，不可用时返回空列表（SQLite 无法推断 PREREQUISITE 关系）。
        """
        if not self.is_neo4j_available():
            return []

        try:
            gaps = await self._neo4j.find_prerequisite_gaps(user_id=user_id)
            return [
                KnowledgeGapItem(
                    concept=g["concept"],
                    missing_prerequisites=g.get("missing_prerequisites", []),
                )
                for g in gaps
            ]
        except Exception as e:
            logger.warning("knowledge_gaps Neo4j 查询失败: %s", e)
            return []

    # ==================== 复习推荐 ====================

    async def review_suggestions(
        self, user_id: str = "_default", days_threshold: int = 14, limit: int = 10,
    ) -> List[ReviewSuggestionItem]:
        """推荐近期未复习的概念（间隔重复策略）

        从 SQLite 查询标签，找出超过 days_threshold 天未出现的标签。

        Args:
            user_id: 用户 ID
            days_threshold: 超过 N 天未出现视为待复习
            limit: 最大返回数
        """
        if not self._sqlite:
            return []

        today = date.today()
        cutoff = today - timedelta(days=days_threshold)

        # 获取用户所有标签统计
        try:
            tag_stats = self._sqlite.get_tag_stats_in_range(
                user_id=user_id,
                start_date="2000-01-01",  # 全量
                end_date=today.isoformat(),
                top_n=200,
            )
        except Exception as e:
            logger.warning("review_suggestions 标签统计失败: %s", e)
            return []

        # 获取最近活跃标签
        recent_cutoff = cutoff.isoformat()
        try:
            recent_tags = self._sqlite.get_tag_stats_in_range(
                user_id=user_id,
                start_date=recent_cutoff,
                end_date=today.isoformat() + "\uffff",
                top_n=200,
            )
        except Exception as e:
            logger.warning("review_suggestions 近期标签统计失败: %s", e)
            return []

        recent_tag_set = {t[0] for t in recent_tags}

        # 找出：有使用过但最近未出现的标签
        suggestions = []
        for tag_name, freq in tag_stats:
            if tag_name in recent_tag_set:
                continue
            # 尝试估算上次出现距今天数
            last_seen_days = self._estimate_last_seen_days(tag_name, user_id, today)
            suggestions.append(ReviewSuggestionItem(
                concept=tag_name,
                category="tag",
                last_seen_days_ago=last_seen_days,
                entry_count=freq,
            ))

        suggestions.sort(key=lambda s: s.last_seen_days_ago, reverse=True)
        return suggestions[:limit]

    def _estimate_last_seen_days(self, tag_name: str, user_id: str, today: date) -> int:
        """估算标签最后一次出现在多少天前

        使用 SQLite 的 search_tags_by_keyword 间接估算，
        如果无法获取精确日期则返回一个默认值。
        """
        try:
            entries = self._sqlite.find_entries_by_concept(
                concept=tag_name, days=365, user_id=user_id,
            )
            if not entries:
                return 999

            latest_date = None
            for e in entries:
                created = e.get("created_at", "")
                if not created:
                    continue
                try:
                    if isinstance(created, str):
                        d = datetime.fromisoformat(created.replace("Z", "").replace("+00:00", ""))
                    elif isinstance(created, datetime):
                        d = created
                    else:
                        continue
                    d = d.replace(tzinfo=None)
                    if latest_date is None or d > latest_date:
                        latest_date = d
                except (ValueError, TypeError):
                    continue

            if latest_date:
                return (today - latest_date.date()).days
        except Exception:
            pass
        return 999

    # ==================== 共现推荐 ====================

    async def related_concepts(
        self, user_id: str = "_default", limit: int = 10,
    ) -> List[RelatedConceptItem]:
        """基于标签共现的推荐

        Neo4j 可用时使用概念中心度排序；不可用时使用 SQLite 标签频次。
        """
        if self.is_neo4j_available():
            try:
                centrality = await self._neo4j.get_concept_centrality(
                    user_id=user_id, limit=limit,
                )
                return [
                    RelatedConceptItem(
                        concept=c["name"],
                        score=float(c["centrality"]),
                        source="neo4j",
                    )
                    for c in centrality
                ]
            except Exception as e:
                logger.warning("related_concepts Neo4j 查询失败，降级到 SQLite: %s", e)

        # SQLite 降级：使用近期高频标签
        return self._related_concepts_from_sqlite(user_id, limit)

    def _related_concepts_from_sqlite(
        self, user_id: str, limit: int,
    ) -> List[RelatedConceptItem]:
        """SQLite 降级方案：基于近期标签频次推荐"""
        if not self._sqlite:
            return []

        try:
            today = date.today()
            start = (today - timedelta(days=30)).isoformat()
            tags = self._sqlite.get_tag_stats_in_range(
                user_id=user_id, start_date=start,
                end_date=today.isoformat(), top_n=limit,
            )
        except Exception as e:
            logger.warning("_related_concepts_from_sqlite 失败: %s", e)
            return []

        if not tags:
            return []

        max_freq = max(t[1] for t in tags) if tags else 1
        return [
            RelatedConceptItem(
                concept=name,
                score=round(freq / max_freq, 2) if max_freq > 0 else 0.0,
                source="tag",
            )
            for name, freq in tags
        ]

    # ==================== 聚合推荐 ====================

    async def get_recommendations(
        self, user_id: str = "_default", gap_limit: int = 10,
        review_limit: int = 10, related_limit: int = 10,
    ) -> RecommendationResponse:
        """获取三类推荐

        Args:
            user_id: 用户 ID
            gap_limit: 知识缺口最大返回数
            review_limit: 复习推荐最大返回数
            related_limit: 共现推荐最大返回数
        """
        gaps = await self.knowledge_gaps(user_id=user_id)
        review = await self.review_suggestions(user_id=user_id, limit=review_limit)
        related = await self.related_concepts(user_id=user_id, limit=related_limit)

        source = "neo4j" if self.is_neo4j_available() else "sqlite"

        return RecommendationResponse(
            knowledge_gaps=gaps[:gap_limit],
            review_suggestions=review,
            related_concepts=related,
            source=source,
        )
