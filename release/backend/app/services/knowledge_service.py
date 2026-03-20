"""知识图谱服务"""
import json
import re
import logging
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

    async def get_knowledge_graph(self, concept: str, depth: int = 2) -> KnowledgeGraphResponse:
        """
        获取概念的知识图谱

        Args:
            concept: 概念名称
            depth: 关系深度 (1-3)

        Returns:
            KnowledgeGraphResponse: 知识图谱数据
        """
        if not self.is_neo4j_available():
            raise ValueError("知识图谱服务未配置")

        graph = await self._neo4j.get_knowledge_graph(concept, depth)

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

    async def get_related_concepts(self, concept: str) -> RelatedConceptsResponse:
        """
        获取相关概念

        Args:
            concept: 概念名称

        Returns:
            RelatedConceptsResponse: 相关概念数据
        """
        if not self.is_neo4j_available():
            raise ValueError("知识图谱服务未配置")

        related = await self._neo4j.get_related_concepts(concept)

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

    async def get_learning_path(self, concept: str) -> LearningPathResponse:
        """
        获取概念的学习路径

        Args:
            concept: 概念名称

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
                graph = await self._neo4j.get_knowledge_graph(concept, depth=2)

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
            response = self._analyze_sqlite_data(concept, response)

        return response

    def _analyze_sqlite_data(
        self,
        concept: str,
        response: LearningPathResponse
    ) -> LearningPathResponse:
        """分析 SQLite 数据来补充学习路径"""
        # 搜索包含该概念的条目
        results = self._sqlite.search(concept, limit=20)

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
            response = self._recommend_from_tags(concept, response)

        return response

    def _recommend_from_tags(
        self,
        concept: str,
        response: LearningPathResponse
    ) -> LearningPathResponse:
        """从标签关联推荐下一步学习内容"""
        all_entries = self._sqlite.list_entries(limit=100)
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
