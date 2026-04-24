"""知识图谱服务"""
import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from app.models import Concept, ConceptRelation, ExtractedKnowledge, Task

if TYPE_CHECKING:
    from app.callers import APICaller

logger = logging.getLogger(__name__)


class ConceptNode(BaseModel):
    """概念节点"""
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class ConceptRelationModel(BaseModel):
    """概念关系"""
    name: str
    relationship: str
    category: Optional[str] = None


class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应"""
    center: Optional[ConceptNode] = None
    connections: List[ConceptRelationModel] = []


class RelatedConceptsResponse(BaseModel):
    """相关概念响应"""
    concept: str
    related: List[ConceptNode]


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    concept: str
    prerequisites: List[ConceptNode] = []   # 前置知识
    current_level: str = "unknown"          # 掌握程度
    next_steps: List[ConceptNode] = []      # 下一步建议
    related_projects: List[str] = []        # 相关项目
    related_notes: List[str] = []           # 相关笔记


class MapNode(BaseModel):
    """图谱节点"""
    id: str
    name: str
    category: Optional[str] = None
    mastery: str = "new"  # new/beginner/intermediate/advanced
    entry_count: int = 0


class MapEdge(BaseModel):
    """图谱边"""
    source: str
    target: str
    relationship: str = "RELATED_TO"


class KnowledgeMapResponse(BaseModel):
    """全局图谱响应"""
    nodes: List[MapNode] = []
    edges: List[MapEdge] = []


class ConceptStatsResponse(BaseModel):
    """概念统计响应"""
    concept_count: int = 0
    relation_count: int = 0
    category_distribution: Dict[str, int] = {}
    top_concepts: List[Dict[str, Any]] = []


class ConceptSearchItem(BaseModel):
    """概念搜索结果项"""
    name: str
    entry_count: int = 0
    mastery: Optional[str] = None


class ConceptSearchResponse(BaseModel):
    """概念搜索响应"""
    items: List[ConceptSearchItem] = []


class TimelineEntry(BaseModel):
    """时间线条目"""
    id: str
    title: str
    type: str = "note"


class TimelineDay(BaseModel):
    """时间线日期组"""
    date: str
    entries: List[TimelineEntry] = []


class ConceptTimelineResponse(BaseModel):
    """概念学习时间线响应"""
    concept: str
    items: List[TimelineDay] = []


class MasteryDistributionResponse(BaseModel):
    """掌握度分布响应"""
    new: int = 0
    beginner: int = 0
    intermediate: int = 0
    advanced: int = 0
    total: int = 0


class CapabilityConcept(BaseModel):
    """能力地图中的概念项"""
    name: str
    mastery_level: Literal["new", "beginner", "intermediate", "advanced"] = "new"
    mastery_score: float = Field(0.0, ge=0.0, le=1.0)
    entry_count: int = 0


class CapabilityDomain(BaseModel):
    """能力领域"""
    name: str
    concepts: List[CapabilityConcept] = []
    average_mastery: float = Field(0.0, ge=0.0, le=1.0)
    concept_count: int = 0


class CapabilityMapResponse(BaseModel):
    """能力地图响应"""
    domains: List[CapabilityDomain] = []
    source: Literal["neo4j", "sqlite"] = "sqlite"


class KnowledgeService:
    """知识图谱服务"""

    def __init__(
        self,
        neo4j_client=None,
        sqlite_storage=None,
        llm_caller: Optional["APICaller"] = None,
    ):
        """
        初始化服务

        Args:
            neo4j_client: Neo4j 客户端实例
            sqlite_storage: SQLite 存储实例
            llm_caller: LLM 调用器（用于知识提取）
        """
        self._neo4j = neo4j_client
        self._sqlite = sqlite_storage
        self._llm_caller = llm_caller

    def set_neo4j_client(self, client):
        """设置 Neo4j 客户端"""
        self._neo4j = client

    def set_sqlite_storage(self, storage):
        """设置 SQLite 存储"""
        self._sqlite = storage

    def set_llm_caller(self, caller: "APICaller"):
        """设置 LLM 调用器"""
        self._llm_caller = caller

    def is_neo4j_available(self) -> bool:
        """检查 Neo4j 是否可用"""
        return self._neo4j is not None and self._neo4j._driver is not None

    async def _with_neo4j_fallback(self, neo4j_fn, sqlite_fn):
        """尝试 Neo4j 操作，失败则降级到 SQLite

        ConnectionError 表示 Neo4j 驱动不可用，静默降级到 SQLite。
        其他异常（如查询错误）也触发降级并记录警告。

        Args:
            neo4j_fn: async 零参 callable（调用方用 lambda/partial 绑定参数）
            sqlite_fn: 同步零参 callable（调用方用 lambda/partial 绑定参数）
        """
        if self.is_neo4j_available():
            try:
                return await neo4j_fn()
            except ConnectionError as e:
                # 驱动不可用是预期场景（连接失败），用 debug 级别
                logger.debug(f"Neo4j 不可用，降级到 SQLite: {e}")
            except Exception as e:
                logger.warning(f"Neo4j 操作失败，降级到 SQLite: {e}")
        if self._sqlite:
            return sqlite_fn()
        return None

    # ==================== 知识提取 ====================

    async def extract_knowledge(self, entry: Task) -> ExtractedKnowledge:
        """
        从条目中提取知识（tags, concepts, relations）

        优先使用 LLM 提取，如果没有 LLM 则使用简单规则

        Args:
            entry: 要提取知识的条目

        Returns:
            ExtractedKnowledge: 提取的知识
        """
        if self._llm_caller:
            return await self._extract_with_llm(entry)
        else:
            return self._extract_with_rules(entry)

    async def _extract_with_llm(self, entry: Task) -> ExtractedKnowledge:
        """使用 LLM 提取知识"""
        prompt = f"""请从以下文本中提取：
1. 标签（keywords）
2. 技术概念（concepts）
3. 概念之间的关系（relations）

文本：
{entry.title}
{entry.content}

返回 JSON 格式：
{{
  "tags": ["MCP", "LLM应用开发"],
  "concepts": [
    {{"name": "MCP", "category": "技术"}},
    {{"name": "Host", "category": "概念"}}
  ],
  "relations": [
    {{"from": "MCP", "to": "LLM应用开发", "type": "PART_OF"}},
    {{"from": "Host", "to": "MCP", "type": "PART_OF"}}
  ]
}}

只输出 JSON，不要有其他内容。"""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self._llm_caller.call(messages, {"type": "json_object"})
            data = json.loads(response)

            concepts = [
                Concept(
                    name=c["name"],
                    category=c.get("category", "技术"),
                )
                for c in data.get("concepts", [])
            ]

            relations = [
                ConceptRelation(
                    from_concept=r["from"],
                    to_concept=r["to"],
                    relation_type=r.get("type", "RELATED_TO"),
                )
                for r in data.get("relations", [])
            ]

            return ExtractedKnowledge(
                tags=data.get("tags", []),
                concepts=concepts,
                relations=relations,
            )
        except Exception as e:
            logger.warning(f"LLM 提取失败: {e}")
            return self._extract_with_rules(entry)

    def _extract_with_rules(self, entry: Task) -> ExtractedKnowledge:
        """使用简单规则提取知识"""
        # 从内容中提取 #标签
        content = entry.content or ""
        tags = re.findall(r"#(\w+)", content)
        tags = list(set(tags))  # 去重

        # 使用已有标签作为概念
        concepts = [
            Concept(name=tag, category="技术")
            for tag in tags
        ]

        # 不推断关系
        relations = []

        return ExtractedKnowledge(
            tags=tags,
            concepts=concepts,
            relations=relations,
        )

    # ==================== 知识图谱查询 ====================

    async def get_knowledge_graph(self, concept: str, depth: int = 2, user_id: str = "_default") -> KnowledgeGraphResponse:
        """
        获取概念的知识图谱

        Args:
            concept: 概念名称
            depth: 关系深度 (1-3)
            user_id: 用户 ID

        Returns:
            KnowledgeGraphResponse: 知识图谱数据
        """
        if not self.is_neo4j_available():
            raise ValueError("知识图谱服务未配置")

        graph = await self._neo4j.get_knowledge_graph(concept, depth, user_id=user_id)

        center = None
        if graph.get("center"):
            c = graph["center"]
            center = ConceptNode(
                name=c.get("name", concept),
                category=c.get("category"),
                description=c.get("description"),
            )

        connections = []
        for conn in graph.get("connections", []):
            node = conn.get("node", {})
            if node:
                connections.append(ConceptRelationModel(
                    name=node.get("name", ""),
                    relationship=conn.get("relationship", "RELATED_TO"),
                    category=node.get("category"),
                ))

        return KnowledgeGraphResponse(
            center=center,
            connections=connections,
        )

    async def get_related_concepts(self, concept: str, user_id: str = "_default") -> RelatedConceptsResponse:
        """
        获取相关概念

        Args:
            concept: 概念名称
            user_id: 用户 ID

        Returns:
            RelatedConceptsResponse: 相关概念数据
        """
        if not self.is_neo4j_available():
            raise ValueError("知识图谱服务未配置")

        related = await self._neo4j.get_related_concepts(concept, user_id=user_id)

        concepts = []
        for c in related:
            concepts.append(ConceptNode(
                name=c.get("name", ""),
                category=c.get("category"),
                description=c.get("description"),
            ))

        return RelatedConceptsResponse(
            concept=concept,
            related=concepts,
        )

    async def get_learning_path(self, concept: str, user_id: str = "_default") -> LearningPathResponse:
        """
        获取概念的学习路径

        Args:
            concept: 概念名称
            user_id: 用户 ID

        Returns:
            LearningPathResponse: 学习路径数据，包括:
                - prerequisites: 前置知识（需要先学习的概念）
                - current_level: 当前掌握程度（基于相关笔记/任务数量推断）
                - next_steps: 下一步建议学习的内容
                - related_projects: 相关项目
                - related_notes: 相关笔记
        """
        response = LearningPathResponse(concept=concept)

        # 1. 从 Neo4j 获取前置知识和后续概念（如果可用）
        if self.is_neo4j_available():
            try:
                graph = await self._neo4j.get_knowledge_graph(concept, depth=2, user_id=user_id)

                # 分析关系类型
                for conn in graph.get("connections", []):
                    node = conn.get("node", {})
                    relationship = conn.get("relationship", "RELATED_TO")

                    if relationship in ["PREREQUISITE_OF", "REQUIRES"]:
                        # 这是前置知识（概念需要先学它）
                        response.prerequisites.append(ConceptNode(
                            name=node.get("name", ""),
                            category=node.get("category"),
                            description=node.get("description"),
                        ))
                    elif relationship in ["FOLLOWS", "NEXT"]:
                        # 这是后续概念
                        response.next_steps.append(ConceptNode(
                            name=node.get("name", ""),
                            category=node.get("category"),
                            description=node.get("description"),
                        ))
            except Exception:
                # Neo4j 查询失败，继续使用 SQLite 数据
                pass

        # 2. 从 SQLite 搜索相关内容
        if self._sqlite:
            response = self._analyze_sqlite_data(concept, response, user_id=user_id)

        return response

    def _analyze_sqlite_data(
        self,
        concept: str,
        response: LearningPathResponse,
        user_id: str = "_default",
    ) -> LearningPathResponse:
        """分析 SQLite 数据来补充学习路径"""
        # 搜索包含该概念的条目
        results = self._sqlite.search(concept, limit=20, user_id=user_id)

        # 统计掌握程度
        note_count = 0
        task_count = 0
        complete_count = 0
        projects = []
        notes = []

        for entry in results:
            entry_type = entry.get("type", "note")
            status = entry.get("status", "")
            title = entry.get("title", "")

            if entry_type == "note":
                note_count += 1
                notes.append(title)
            elif entry_type == "task":
                task_count += 1
                if status == "complete":
                    complete_count += 1
            elif entry_type == "project":
                projects.append(title)

        # 推断掌握程度
        total_related = note_count + task_count
        if total_related >= 10 and complete_count >= 5:
            response.current_level = "advanced"
        elif total_related >= 5 and complete_count >= 2:
            response.current_level = "intermediate"
        elif total_related >= 1:
            response.current_level = "beginner"
        else:
            response.current_level = "new"

        response.related_projects = projects[:5]
        response.related_notes = notes[:5]

        # 3. 如果 Neo4j 没有返回后续建议，从标签关联推荐
        if not response.next_steps:
            response = self._recommend_from_tags(concept, response, user_id=user_id)

        return response

    def _recommend_from_tags(
        self,
        concept: str,
        response: LearningPathResponse,
        user_id: str = "_default",
    ) -> LearningPathResponse:
        """从标签关联推荐下一步学习内容（基于 SQLite 定向查询）"""
        if not concept or not concept.strip():
            return response

        try:
            matching_tags = self._sqlite.search_tags_by_keyword(
                keyword=concept, limit=10, user_id=user_id
            )
        except Exception:
            return response

        seen = set()
        for tag_info in matching_tags:
            tag = tag_info["name"]
            if tag.lower() != concept.lower() and tag not in seen:
                seen.add(tag)
                response.next_steps.append(ConceptNode(
                    name=tag,
                    category="tag",
                    description="相关标签",
                ))
                if len(response.next_steps) >= 5:
                    break

        return response

    # ==================== 全局图谱与统计 ====================

    async def get_knowledge_map(
        self,
        depth: int = 2,
        view: str = "domain",
        user_id: str = "_default",
    ) -> KnowledgeMapResponse:
        """
        获取全局知识图谱

        Args:
            depth: 关系深度 (1-3)
            view: 视图模式 (domain/mastery/project)
            user_id: 用户 ID

        Returns:
            KnowledgeMapResponse: 全局图谱数据
        """
        nodes, edges = await self._with_neo4j_fallback(
            lambda: self._build_map_from_neo4j(depth, user_id),
            lambda: self._build_map_from_sqlite(user_id),
        ) or ([], [])

        # 按 view 参数排序/分组（不影响数据内容，仅影响排序）
        if view == "mastery":
            nodes.sort(key=lambda n: {"advanced": 0, "intermediate": 1, "beginner": 2, "new": 3}.get(n.mastery, 4))
        elif view == "domain":
            nodes.sort(key=lambda n: (n.category or "zzz", n.name))
        elif view == "project":
            nodes.sort(key=lambda n: n.name)

        return KnowledgeMapResponse(nodes=nodes, edges=edges)

    async def _build_map_from_neo4j(
        self, depth: int, user_id: str
    ) -> tuple:
        """从 Neo4j 构建图谱数据"""
        concepts = await self._neo4j.get_all_concepts_with_stats(user_id=user_id)
        relationships = await self._neo4j.get_all_relationships(user_id=user_id)

        nodes = []
        for c in concepts:
            name = c.get("name", "")
            entry_count = c.get("entry_count", 0)
            mastery = self._calculate_mastery_from_stats(entry_count, 0, 0)
            nodes.append(MapNode(
                id=name,
                name=name,
                category=c.get("category"),
                mastery=mastery,
                entry_count=entry_count,
            ))

        edges = []
        for r in relationships:
            edges.append(MapEdge(
                source=r["source"],
                target=r["target"],
                relationship=r.get("type", "RELATED_TO"),
            ))

        return nodes, edges


    def _build_map_from_sqlite(self, user_id: str) -> tuple:
        """从 SQLite 构建图谱数据（Neo4j 不可用时的降级方案）

        使用 SQL 聚合查询替代 list_entries(limit=10000) 全表扫描。
        """
        result = self._sqlite.get_tag_stats_for_knowledge_map(user_id=user_id)

        # 构建 nodes
        nodes = []
        for tag_info in result["tags"]:
            mastery = self._calculate_mastery_from_stats(
                entry_count=tag_info["entry_count"],
                recent_count=tag_info["recent_count"],
                note_count=tag_info["note_count"],
            )
            nodes.append(MapNode(
                id=tag_info["name"],
                name=tag_info["name"],
                category="tag",
                mastery=mastery,
                entry_count=tag_info["entry_count"],
            ))

        # 构建 edges
        edges = []
        for source, target in result["co_occurrence_pairs"]:
            edges.append(MapEdge(
                source=source,
                target=target,
                relationship="CO_OCCURS",
            ))

        return nodes, edges

    def _calculate_mastery_from_stats(
        self, entry_count: int, recent_count: int, note_count: int
    ) -> str:
        """根据统计数据计算掌握度（委托到 ReviewService 统一实现）"""
        from app.services.review_service import ReviewService
        return ReviewService._calculate_mastery_from_stats(
            entry_count=entry_count,
            recent_count=recent_count,
            note_count=note_count,
        )

    async def get_knowledge_stats(self, user_id: str = "_default") -> ConceptStatsResponse:
        """
        获取知识概念统计

        Args:
            user_id: 用户 ID

        Returns:
            ConceptStatsResponse: 统计数据
        """
        return await self._with_neo4j_fallback(
            lambda: self._stats_from_neo4j(user_id),
            lambda: self._stats_from_sqlite(user_id),
        ) or ConceptStatsResponse()

    async def _stats_from_neo4j(self, user_id: str) -> ConceptStatsResponse:
        """从 Neo4j 获取统计"""
        concepts = await self._neo4j.get_all_concepts_with_stats(user_id=user_id)
        relationships = await self._neo4j.get_all_relationships(user_id=user_id)

        category_dist: Dict[str, int] = {}
        top_concepts: List[Dict[str, Any]] = []

        for c in concepts:
            cat = c.get("category") or "uncategorized"
            category_dist[cat] = category_dist.get(cat, 0) + 1

        # Top 10 by entry_count
        sorted_concepts = sorted(concepts, key=lambda x: x.get("entry_count", 0), reverse=True)
        for c in sorted_concepts[:10]:
            top_concepts.append({
                "name": c.get("name", ""),
                "entry_count": c.get("entry_count", 0),
                "category": c.get("category"),
            })

        return ConceptStatsResponse(
            concept_count=len(concepts),
            relation_count=len(relationships),
            category_distribution=category_dist,
            top_concepts=top_concepts,
        )

    def _stats_from_sqlite(self, user_id: str) -> ConceptStatsResponse:
        """从 SQLite 获取统计

        使用 SQL 聚合查询替代 list_entries(limit=10000) 全表扫描。
        """
        result = self._sqlite.get_tag_stats_for_concept_stats(user_id=user_id)

        # 所有标签的 category 统一为 "tag"
        category_dist: Dict[str, int] = {}
        for tag_info in result["tags"]:
            cat = tag_info.get("category") or "tag"
            category_dist[cat] = category_dist.get(cat, 0) + 1

        top_concepts = result["tags"][:10]

        return ConceptStatsResponse(
            concept_count=result["concept_count"],
            relation_count=result["edge_count"],
            category_distribution=category_dist,
            top_concepts=top_concepts,
        )

    # ==================== B28: 搜索 + 时间线 + 掌握度分布 ====================

    async def search_concepts(
        self, query: str, limit: int = 20, user_id: str = "_default"
    ) -> ConceptSearchResponse:
        """搜索概念（Neo4j 优先，SQLite tags 降级）"""
        return await self._with_neo4j_fallback(
            lambda: self._search_from_neo4j(query, limit, user_id),
            lambda: self._search_from_sqlite(query, limit, user_id),
        ) or ConceptSearchResponse()

    async def _search_from_neo4j(
        self, query: str, limit: int, user_id: str
    ) -> ConceptSearchResponse:
        """从 Neo4j 搜索概念"""
        concepts = await self._neo4j.get_all_concepts_with_stats(user_id=user_id)
        q_lower = query.lower()
        matched = [c for c in concepts if q_lower in c.get("name", "").lower()]
        matched.sort(key=lambda x: x.get("entry_count", 0), reverse=True)
        matched = matched[:limit]

        items = []
        for c in matched:
            name = c.get("name", "")
            entry_count = c.get("entry_count", 0)
            mastery = self._calculate_mastery_from_stats(entry_count, 0, 0)
            items.append(ConceptSearchItem(name=name, entry_count=entry_count, mastery=mastery))

        return ConceptSearchResponse(items=items)

    def _search_from_sqlite(
        self, query: str, limit: int, user_id: str
    ) -> ConceptSearchResponse:
        """从 SQLite tags 搜索概念（降级，mastery=null）

        使用 SQL 聚合查询替代 list_entries(limit=10000) 全表扫描。
        """
        matched_tags = self._sqlite.search_tags_by_keyword(query, limit=limit, user_id=user_id)
        items = [
            ConceptSearchItem(name=t["name"], entry_count=t["entry_count"], mastery=None)
            for t in matched_tags
        ]
        return ConceptSearchResponse(items=items)

    async def get_concept_timeline(
        self, concept: str, days: int = 90, user_id: str = "_default"
    ) -> ConceptTimelineResponse:
        """获取概念学习时间线"""
        return await self._with_neo4j_fallback(
            lambda: self._timeline_from_neo4j(concept, days, user_id),
            lambda: self._timeline_from_sqlite(concept, days, user_id),
        ) or ConceptTimelineResponse(concept=concept)

    async def _timeline_from_neo4j(
        self, concept: str, days: int, user_id: str
    ) -> ConceptTimelineResponse:
        """从 Neo4j 获取时间线"""
        try:
            entries = await self._neo4j.get_entries_by_concept(concept, user_id=user_id)
        except Exception:
            entries = []

        return self._build_timeline(concept, entries, days)

    def _timeline_from_sqlite(
        self, concept: str, days: int, user_id: str
    ) -> ConceptTimelineResponse:
        """从 SQLite 获取时间线（基于 tags + title/content 搜索）

        使用 SQL 聚合查询替代 list_entries(limit=10000) 全表扫描。
        """
        results = self._sqlite.find_entries_by_concept(concept, days=days, user_id=user_id)
        return self._build_timeline(concept, results, days)

    def _build_timeline(
        self, concept: str, entries: list, days: int
    ) -> ConceptTimelineResponse:
        """构建时间线（按日期聚合）"""
        cutoff = datetime.now() - timedelta(days=days)
        day_map: Dict[str, List[TimelineEntry]] = {}

        for e in entries:
            created_str = e.get("created_at", "") or e.get("updated_at", "")
            if not created_str:
                continue
            try:
                if isinstance(created_str, str):
                    created_at = datetime.fromisoformat(created_str.replace("Z", "").replace("+00:00", ""))
                else:
                    created_at = created_str if created_str.tzinfo is None else created_str.replace(tzinfo=None)
            except (ValueError, TypeError):
                continue

            if created_at < cutoff:
                continue

            date_key = created_at.strftime("%Y-%m-%d")
            if date_key not in day_map:
                day_map[date_key] = []

            day_map[date_key].append(TimelineEntry(
                id=e.get("id", ""),
                title=e.get("title", ""),
                type=e.get("type", "note"),
            ))

        items = [
            TimelineDay(date=date, entries=ents)
            for date, ents in sorted(day_map.items(), reverse=True)
        ]
        return ConceptTimelineResponse(concept=concept, items=items)

    async def get_mastery_distribution(self, user_id: str = "_default") -> MasteryDistributionResponse:
        """获取掌握度分布统计"""
        dist = await self._with_neo4j_fallback(
            lambda: self._mastery_dist_from_neo4j(user_id),
            lambda: self._mastery_dist_from_sqlite(user_id),
        ) or {"new": 0, "beginner": 0, "intermediate": 0, "advanced": 0}

        return MasteryDistributionResponse(
            new=dist["new"],
            beginner=dist["beginner"],
            intermediate=dist["intermediate"],
            advanced=dist["advanced"],
            total=sum(dist.values()),
        )

    async def _mastery_dist_from_neo4j(self, user_id: str) -> dict:
        """从 Neo4j 计算掌握度分布"""
        dist = {"new": 0, "beginner": 0, "intermediate": 0, "advanced": 0}
        concepts = await self._neo4j.get_all_concepts_with_stats(user_id=user_id)
        for c in concepts:
            entry_count = c.get("entry_count", 0)
            mastery = self._calculate_mastery_from_stats(entry_count, 0, 0)
            dist[mastery] = dist.get(mastery, 0) + 1
        return dist

    def _mastery_dist_from_sqlite(self, user_id: str) -> dict:
        """从 SQLite 计算掌握度分布"""
        dist = {"new": 0, "beginner": 0, "intermediate": 0, "advanced": 0}
        nodes, _ = self._build_map_from_sqlite(user_id)
        for node in nodes:
            dist[node.mastery] = dist.get(node.mastery, 0) + 1
        return dist

    # ==================== B81: 能力地图 ====================

    def _mastery_to_score(self, mastery_level: str) -> float:
        """将掌握度级别映射为 0-1 分数"""
        return {"new": 0.0, "beginner": 0.25, "intermediate": 0.5, "advanced": 0.75}.get(
            mastery_level, 0.0
        )

    async def get_capability_map(
        self,
        mastery_level: Optional[str] = None,
        user_id: str = "_default",
    ) -> CapabilityMapResponse:
        """
        获取能力地图数据

        按领域聚合概念和掌握度。Neo4j 优先，不可用时降级为 SQLite tags 聚合。

        Args:
            mastery_level: 按掌握度过滤（new/beginner/intermediate/advanced）
            user_id: 用户 ID

        Returns:
            CapabilityMapResponse 能力地图
        """
        return await self._with_neo4j_fallback(
            lambda: self._build_capability_map_from_neo4j(mastery_level, user_id),
            lambda: self._build_capability_map_from_sqlite(mastery_level, user_id),
        ) or CapabilityMapResponse(domains=[], source="sqlite")

    async def _build_capability_map_from_neo4j(
        self, mastery_level: Optional[str], user_id: str
    ) -> CapabilityMapResponse:
        """从 Neo4j 构建能力地图

        Note: 掌握度计算使用 _calculate_mastery_from_stats 内存计算，
        避免逐概念 N+1 查询。
        """
        concepts = await self._neo4j.get_all_concepts_with_stats(user_id=user_id)

        # 按领域（category）聚合
        domain_map: Dict[str, List[CapabilityConcept]] = {}
        for c in concepts:
            name = c.get("name", "")
            entry_count = c.get("entry_count", 0)
            category = c.get("category") or "未分类"

            mastery = self._calculate_mastery_from_stats(entry_count, 0, 0)

            if mastery_level and mastery != mastery_level:
                continue

            score = self._mastery_to_score(mastery)
            concept_item = CapabilityConcept(
                name=name,
                mastery_level=mastery,
                mastery_score=score,
                entry_count=entry_count,
            )
            domain_map.setdefault(category, []).append(concept_item)

        domains = self._aggregate_domains(domain_map)
        return CapabilityMapResponse(domains=domains, source="neo4j")

    def _build_capability_map_from_sqlite(
        self, mastery_level: Optional[str], user_id: str
    ) -> CapabilityMapResponse:
        """从 SQLite 构建能力地图（降级方案）"""
        result = self._sqlite.get_tag_stats_for_knowledge_map(user_id=user_id)

        domain_map: Dict[str, List[CapabilityConcept]] = {}
        for tag_info in result["tags"]:
            mastery = self._calculate_mastery_from_stats(
                entry_count=tag_info["entry_count"],
                recent_count=tag_info["recent_count"],
                note_count=tag_info["note_count"],
            )

            if mastery_level and mastery != mastery_level:
                continue

            score = self._mastery_to_score(mastery)
            concept_item = CapabilityConcept(
                name=tag_info["name"],
                mastery_level=mastery,
                mastery_score=score,
                entry_count=tag_info["entry_count"],
            )
            domain_map.setdefault("tag", []).append(concept_item)

        domains = self._aggregate_domains(domain_map)
        return CapabilityMapResponse(domains=domains, source="sqlite")

    def _aggregate_domains(
        self, domain_map: Dict[str, List[CapabilityConcept]]
    ) -> List[CapabilityDomain]:
        """聚合领域数据"""
        domains = []
        for domain_name, concepts in sorted(domain_map.items()):
            scores = [c.mastery_score for c in concepts]
            avg_mastery = sum(scores) / len(scores) if scores else 0.0
            domains.append(CapabilityDomain(
                name=domain_name,
                concepts=concepts,
                average_mastery=round(avg_mastery, 2),
                concept_count=len(concepts),
            ))
        return domains

    # ==================== B43: 条目知识上下文 ====================

    async def get_entry_knowledge_context(
        self, entry_id: str, user_id: str = "_default"
    ) -> dict:
        """
        获取条目的知识图谱子图上下文

        以条目的 tags 为种子概念，返回 1-hop 子图。

        Args:
            entry_id: 条目 ID
            user_id: 用户 ID

        Returns:
            dict: { nodes, edges, center_concepts }
        """
        # 1. 获取条目的 tags
        tags = self._get_entry_tags(entry_id, user_id)

        # 2. 无 tags → 空子图
        if not tags:
            return {"nodes": [], "edges": [], "center_concepts": []}

        # 3. Neo4j 优先，降级到 SQLite
        result = await self._with_neo4j_fallback(
            lambda: self._build_subgraph_from_neo4j(tags, user_id),
            lambda: self._build_subgraph_from_sqlite(tags, user_id),
        ) or ([], [])

        nodes, edges = result
        return {
            "nodes": [n.dict() for n in nodes],
            "edges": [e.dict() for e in edges],
            "center_concepts": tags,
        }

    def _get_entry_tags(self, entry_id: str, user_id: str) -> List[str]:
        """从 SQLite 获取条目的 tags"""
        if not self._sqlite:
            return []
        entry = self._sqlite.get_entry(entry_id, user_id=user_id)
        if not entry:
            return []
        return entry.get("tags", [])

    async def _build_subgraph_from_neo4j(
        self, seed_concepts: List[str], user_id: str
    ) -> tuple:
        """从 Neo4j 构建种子概念的 1-hop 子图"""
        all_nodes: Dict[str, MapNode] = {}
        all_edges: List[MapEdge] = []

        # 一次性获取所有概念的统计数据，避免 N+1 查询
        concepts_stats_lookup: Dict[str, Dict] = {}
        try:
            all_concepts_stats = await self._neo4j.get_all_concepts_with_stats(user_id=user_id)
            concepts_stats_lookup = {
                cs.get("name", ""): cs
                for cs in all_concepts_stats
                if cs.get("name")
            }
        except Exception:
            pass

        for concept in seed_concepts:
            try:
                graph = await self._neo4j.get_knowledge_graph(
                    concept, depth=1, user_id=user_id
                )
            except Exception:
                continue

            # 中心节点
            center = graph.get("center")
            if center:
                name = center.get("name", concept)
                if name not in all_nodes:
                    cs = concepts_stats_lookup.get(name, {})
                    entry_count = cs.get("entry_count", 0)
                    mastery = self._calculate_mastery_from_stats(
                        entry_count, cs.get("recent_count", 0), cs.get("note_count", 0)
                    )
                    all_nodes[name] = MapNode(
                        id=name,
                        name=name,
                        category=center.get("category"),
                        mastery=mastery,
                        entry_count=entry_count,
                    )

            # 1-hop 邻居
            for conn in graph.get("connections", []):
                node_data = conn.get("node", {})
                if not node_data:
                    continue
                neighbor_name = node_data.get("name", "")
                if not neighbor_name:
                    continue

                if neighbor_name not in all_nodes:
                    cs = concepts_stats_lookup.get(neighbor_name, {})
                    entry_count = cs.get("entry_count", 0)
                    mastery = self._calculate_mastery_from_stats(
                        entry_count, cs.get("recent_count", 0), cs.get("note_count", 0)
                    )
                    all_nodes[neighbor_name] = MapNode(
                        id=neighbor_name,
                        name=neighbor_name,
                        category=node_data.get("category"),
                        mastery=mastery,
                        entry_count=entry_count,
                    )

                # 边：从种子概念到邻居
                if center:
                    center_name = center.get("name", concept)
                    edge = MapEdge(
                        source=center_name,
                        target=neighbor_name,
                        relationship=conn.get("relationship", "RELATED_TO"),
                    )
                    # 去重
                    edge_key = (edge.source, edge.target, edge.relationship)
                    existing_keys = {(e.source, e.target, e.relationship) for e in all_edges}
                    if edge_key not in existing_keys:
                        all_edges.append(edge)

            # 限制最多 20 个节点
            if len(all_nodes) >= 20:
                break

        # 截断到 20 个节点（保留种子概念）
        if len(all_nodes) > 20:
            seed_set = set(seed_concepts)
            seed_nodes = {k: v for k, v in all_nodes.items() if k in seed_set}
            non_seed_nodes = {k: v for k, v in all_nodes.items() if k not in seed_set}
            remaining = 20 - len(seed_nodes)
            kept = dict(list(non_seed_nodes.items())[:max(0, remaining)])
            all_nodes = {**seed_nodes, **kept}
            # 过滤掉引用已删除节点的边
            kept_ids = set(all_nodes.keys())
            all_edges = [e for e in all_edges if e.source in kept_ids and e.target in kept_ids]

        return list(all_nodes.values()), all_edges

    def _build_subgraph_from_sqlite(
        self, seed_concepts: List[str], user_id: str
    ) -> tuple:
        """从 SQLite 构建种子概念的 tag 共现子图

        使用 SQL 聚合查询替代 list_entries(limit=10000) 全表扫描。
        """
        if not self._sqlite:
            return [], []

        # 标准化种子概念用于匹配
        seed_set_lower = {c.lower() for c in seed_concepts}

        result = self._sqlite.get_tag_stats_for_subgraph(seed_concepts, user_id=user_id)

        # 构建节点，限制 20 个（种子概念优先）
        nodes = []
        sorted_tags = sorted(
            result["tags"],
            key=lambda x: (x["name"].lower() in seed_set_lower, x["entry_count"]),
            reverse=True,
        )
        for tag_info in sorted_tags[:20]:
            mastery = self._calculate_mastery_from_stats(
                entry_count=tag_info["entry_count"],
                recent_count=tag_info["recent_count"],
                note_count=tag_info["note_count"],
            )
            nodes.append(MapNode(
                id=tag_info["name"],
                name=tag_info["name"],
                category="tag",
                mastery=mastery,
                entry_count=tag_info["entry_count"],
            ))

        # 构建边（只保留在节点集合内的边）
        node_ids = {n.id for n in nodes}
        edges = []
        for source, target in result["co_occurrence_pairs"]:
            if source in node_ids and target in node_ids:
                edges.append(MapEdge(
                    source=source,
                    target=target,
                    relationship="CO_OCCURS",
                ))

        return nodes, edges
