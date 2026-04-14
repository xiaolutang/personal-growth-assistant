"""知识图谱服务"""
import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, TYPE_CHECKING

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
        """从标签关联推荐下一步学习内容"""
        all_entries = self._sqlite.list_entries(limit=100, user_id=user_id)
        seen_concepts = set()

        for entry in all_entries:
            tags = entry.get("tags", [])
            # 查找有共同标签的其他概念
            if any(tag.lower() in concept.lower() or concept.lower() in tag.lower() for tag in tags):
                for tag in tags:
                    if tag.lower() != concept.lower() and tag not in seen_concepts:
                        seen_concepts.add(tag)
                        response.next_steps.append(ConceptNode(
                            name=tag,
                            category="tag",
                            description="相关标签",
                        ))
                        if len(response.next_steps) >= 5:
                            break
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
        nodes: List[MapNode] = []
        edges: List[MapEdge] = []

        if self.is_neo4j_available():
            nodes, edges = await self._build_map_from_neo4j(depth, user_id)
        elif self._sqlite:
            nodes, edges = self._build_map_from_sqlite(user_id)

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
            mastery = await self._calculate_mastery_with_neo4j(name, entry_count, user_id)
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

    async def _calculate_mastery_with_neo4j(
        self, concept_name: str, entry_count: int, user_id: str
    ) -> str:
        """基于 Neo4j 数据计算掌握度"""
        if entry_count == 0:
            return "new"

        # 获取提及该概念的条目详情
        try:
            entries = await self._neo4j.get_entries_by_concept(concept_name, user_id=user_id)
        except Exception:
            entries = []

        if not entries:
            return "new" if entry_count == 0 else "beginner"

        recent_count = 0
        note_count = 0
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)

        for e in entries:
            entry_type = e.get("type", "task")
            updated_str = e.get("updated_at", "")

            if entry_type == "note":
                note_count += 1

            # 检查是否在最近 30 天内更新
            try:
                if updated_str:
                    if isinstance(updated_str, str):
                        updated_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                    else:
                        updated_at = updated_str
                    if updated_at >= thirty_days_ago:
                        recent_count += 1
            except (ValueError, TypeError):
                pass

        note_ratio = note_count / len(entries) if entries else 0

        if entry_count >= 6 and note_ratio > 0.3:
            return "advanced"
        elif entry_count >= 3 and recent_count > 0:
            return "intermediate"
        elif entry_count >= 1:
            return "beginner"
        return "new"

    def _build_map_from_sqlite(self, user_id: str) -> tuple:
        """从 SQLite 构建图谱数据（Neo4j 不可用时的降级方案）"""
        all_entries = self._sqlite.list_entries(limit=200, user_id=user_id)

        # 从所有条目的 tags 中提取概念
        concept_map: Dict[str, Dict] = {}
        concept_pairs: set = set()

        for entry in all_entries:
            tags = entry.get("tags", [])
            entry_type = entry.get("type", "task")

            for tag in tags:
                if tag not in concept_map:
                    concept_map[tag] = {
                        "name": tag,
                        "category": "tag",
                        "entry_count": 0,
                        "recent_count": 0,
                        "note_count": 0,
                    }
                concept_map[tag]["entry_count"] += 1

                if entry_type == "note":
                    concept_map[tag]["note_count"] += 1

                # 检查是否在 30 天内更新
                updated_str = entry.get("updated_at", "")
                try:
                    if updated_str:
                        if isinstance(updated_str, str):
                            updated_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                        else:
                            updated_at = updated_str
                        if updated_at >= datetime.now() - timedelta(days=30):
                            concept_map[tag]["recent_count"] += 1
                except (ValueError, TypeError):
                    pass

            # 构建概念之间的关联边（共同出现在同一条目中的 tags）
            for i in range(len(tags)):
                for j in range(i + 1, len(tags)):
                    pair = tuple(sorted([tags[i], tags[j]]))
                    concept_pairs.add(pair)

        # 构建 nodes
        nodes = []
        for name, info in concept_map.items():
            mastery = self._calculate_mastery_from_stats(
                entry_count=info["entry_count"],
                recent_count=info["recent_count"],
                note_count=info["note_count"],
            )
            nodes.append(MapNode(
                id=name,
                name=name,
                category=info.get("category"),
                mastery=mastery,
                entry_count=info["entry_count"],
            ))

        # 构建 edges
        edges = []
        for source, target in concept_pairs:
            edges.append(MapEdge(
                source=source,
                target=target,
                relationship="CO_OCCURS",
            ))

        return nodes, edges

    def _calculate_mastery_from_stats(
        self, entry_count: int, recent_count: int, note_count: int
    ) -> str:
        """根据统计数据计算掌握度"""
        if entry_count == 0:
            return "new"

        note_ratio = note_count / entry_count if entry_count > 0 else 0

        if entry_count >= 6 and note_ratio > 0.3:
            return "advanced"
        elif entry_count >= 3 and recent_count > 0:
            return "intermediate"
        elif entry_count >= 1:
            return "beginner"
        return "new"

    def _calculate_mastery(self, concept_name: str, user_id: str = "_default") -> str:
        """计算概念的掌握度（基于 SQLite 数据）"""
        if not self._sqlite:
            return "new"

        # 搜索提及该概念的条目
        results = self._sqlite.search(concept_name, limit=50, user_id=user_id)

        if not results:
            return "new"

        entry_count = len(results)
        recent_count = 0
        note_count = 0
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)

        for entry in results:
            entry_type = entry.get("type", "task")
            if entry_type == "note":
                note_count += 1

            updated_str = entry.get("updated_at", "")
            try:
                if updated_str:
                    if isinstance(updated_str, str):
                        updated_at = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                    else:
                        updated_at = updated_str
                    if updated_at >= thirty_days_ago:
                        recent_count += 1
            except (ValueError, TypeError):
                pass

        return self._calculate_mastery_from_stats(entry_count, recent_count, note_count)

    async def get_knowledge_stats(self, user_id: str = "_default") -> ConceptStatsResponse:
        """
        获取知识概念统计

        Args:
            user_id: 用户 ID

        Returns:
            ConceptStatsResponse: 统计数据
        """
        if self.is_neo4j_available():
            return await self._stats_from_neo4j(user_id)
        elif self._sqlite:
            return self._stats_from_sqlite(user_id)
        return ConceptStatsResponse()

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
        """从 SQLite 获取统计"""
        all_entries = self._sqlite.list_entries(limit=200, user_id=user_id)

        concept_map: Dict[str, Dict] = {}

        for entry in all_entries:
            tags = entry.get("tags", [])
            for tag in tags:
                if tag not in concept_map:
                    concept_map[tag] = {"name": tag, "entry_count": 0, "category": "tag"}
                concept_map[tag]["entry_count"] += 1

        category_dist: Dict[str, int] = {}
        for info in concept_map.values():
            cat = info.get("category") or "tag"
            category_dist[cat] = category_dist.get(cat, 0) + 1

        # 计算共现边数（co-occur pairs）
        edge_count = 0
        pair_set: set = set()
        for entry in all_entries:
            tags = entry.get("tags", [])
            for i in range(len(tags)):
                for j in range(i + 1, len(tags)):
                    pair = tuple(sorted([tags[i], tags[j]]))
                    if pair not in pair_set:
                        pair_set.add(pair)
                        edge_count += 1

        sorted_concepts = sorted(concept_map.values(), key=lambda x: x["entry_count"], reverse=True)
        top_concepts = sorted_concepts[:10]

        return ConceptStatsResponse(
            concept_count=len(concept_map),
            relation_count=edge_count,
            category_distribution=category_dist,
            top_concepts=top_concepts,
        )
