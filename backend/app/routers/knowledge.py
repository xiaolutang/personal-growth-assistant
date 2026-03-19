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


class LearningPathResponse(BaseModel):
    """学习路径响应"""
    concept: str
    prerequisites: List[ConceptNode] = []   # 前置知识
    current_level: str = "unknown"          # 掌握程度
    next_steps: List[ConceptNode] = []      # 下一步建议
    related_projects: List[str] = []        # 相关项目
    related_notes: List[str] = []           # 相关笔记


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


@router.get("/learning-path/{concept}", response_model=LearningPathResponse)
async def get_learning_path(concept: str):
    """获取概念的学习路径

    返回：
    - prerequisites: 前置知识（需要先学习的概念）
    - current_level: 当前掌握程度（基于相关笔记/任务数量推断）
    - next_steps: 下一步建议学习的内容
    - related_projects: 相关项目
    - related_notes: 相关笔记
    """
    storage = get_storage()

    # 初始化响应
    response = LearningPathResponse(concept=concept)

    try:
        # 1. 从 Neo4j 获取前置知识和后续概念（如果可用）
        if storage.neo4j and storage.neo4j.driver:
            try:
                graph = await storage.neo4j.get_knowledge_graph(concept, depth=2)

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
        if storage.sqlite:
            # 搜索包含该概念的条目
            results = storage.sqlite.search(concept, limit=20)

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
                # 查找相似标签的条目
                all_entries = storage.sqlite.list_entries(limit=100)
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
                                    description=f"相关标签",
                                ))
                                if len(response.next_steps) >= 5:
                                    break
                    if len(response.next_steps) >= 5:
                        break

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
