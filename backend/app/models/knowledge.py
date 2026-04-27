"""知识图谱相关 Pydantic 模型"""
from typing import Dict, List, Any, Literal, Optional

from pydantic import BaseModel, Field


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
