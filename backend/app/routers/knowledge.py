"""知识图谱 API 路由"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.routers.deps import get_storage

router = APIRouter(tags=["knowledge"])


# === 响应模型 ===

class ConceptNode(BaseModel):
    """概念节点"""
    name: str
    category: Optional[str] = None
    description: Optional[str] = None


class ConceptRelation(BaseModel):
    """概念关系"""
    name: str
    relationship: str
    category: Optional[str] = None


class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应"""
    center: Optional[ConceptNode] = None
    connections: List[ConceptRelation] = []


class RelatedConceptsResponse(BaseModel):
    """相关概念响应"""
    concept: str
    related: List[ConceptNode]


# === API 端点 ===

@router.get("/knowledge-graph/{concept}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    concept: str,
    depth: int = Query(2, ge=1, le=3, description="关系深度"),
):
    """获取概念的知识图谱"""
    storage = get_storage()

    # 检查 Neo4j 是否可用
    if not storage.neo4j or not storage.neo4j.driver:
        raise HTTPException(status_code=503, detail="知识图谱服务未配置")

    try:
        graph = await storage.neo4j.get_knowledge_graph(concept, depth)

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
                connections.append(ConceptRelation(
                    name=node.get("name", ""),
                    relationship=conn.get("relationship", "RELATED_TO"),
                    category=node.get("category"),
                ))

        return KnowledgeGraphResponse(
            center=center,
            connections=connections,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/related-concepts/{concept}", response_model=RelatedConceptsResponse)
async def get_related_concepts(concept: str):
    """获取相关概念"""
    storage = get_storage()

    # 检查 Neo4j 是否可用
    if not storage.neo4j or not storage.neo4j.driver:
        raise HTTPException(status_code=503, detail="知识图谱服务未配置")

    try:
        related = await storage.neo4j.get_related_concepts(concept)

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
