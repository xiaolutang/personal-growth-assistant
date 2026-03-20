"""知识图谱 API 路由"""
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.routers.deps import get_knowledge_service
from app.services.knowledge_service import (
    ConceptNode,
    ConceptRelation,
    KnowledgeGraphResponse,
    RelatedConceptsResponse,
    LearningPathResponse,
)

router = APIRouter(tags=["knowledge"])


@router.get("/knowledge-graph/{concept}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    concept: str,
    depth: int = Query(2, ge=1, le=3, description="关系深度"),
):
    """获取概念的知识图谱"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_knowledge_graph(concept, depth)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/related-concepts/{concept}", response_model=RelatedConceptsResponse)
async def get_related_concepts(concept: str):
    """获取相关概念"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_related_concepts(concept)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
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
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_learning_path(concept)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
