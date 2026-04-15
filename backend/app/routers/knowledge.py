"""知识图谱 API 路由"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.deps import get_knowledge_service, get_current_user
from app.models.user import User
from app.services.knowledge_service import (
    ConceptNode,
    ConceptRelation,
    KnowledgeGraphResponse,
    RelatedConceptsResponse,
    LearningPathResponse,
    KnowledgeMapResponse,
    ConceptStatsResponse,
    ConceptSearchResponse,
    ConceptTimelineResponse,
    MasteryDistributionResponse,
)

router = APIRouter(tags=["knowledge"])


@router.get("/knowledge-graph/{concept}", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    concept: str,
    depth: int = Query(2, ge=1, le=3, description="关系深度"),
    user: User = Depends(get_current_user),
):
    """获取概念的知识图谱"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_knowledge_graph(concept, depth, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/related-concepts/{concept}", response_model=RelatedConceptsResponse)
async def get_related_concepts(concept: str, user: User = Depends(get_current_user)):
    """获取相关概念"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_related_concepts(concept, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/learning-path/{concept}", response_model=LearningPathResponse)
async def get_learning_path(concept: str, user: User = Depends(get_current_user)):
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
        return await knowledge_service.get_learning_path(concept, user_id=user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/knowledge-map", response_model=KnowledgeMapResponse)
async def get_knowledge_map(
    depth: int = Query(2, ge=1, le=3, description="关系深度"),
    view: str = Query("domain", regex="^(domain|mastery|project)$", description="视图模式"),
    user: User = Depends(get_current_user),
):
    """获取全局知识图谱

    返回所有概念节点及其关系，支持按掌握度/领域/项目分组查看。
    """
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_knowledge_map(depth=depth, view=view, user_id=user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/knowledge/stats", response_model=ConceptStatsResponse)
async def get_knowledge_stats(user: User = Depends(get_current_user)):
    """获取知识概念统计

    返回概念总数、关系总数、类别分布和热门概念。
    """
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_knowledge_stats(user_id=user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/knowledge/search", response_model=ConceptSearchResponse)
async def search_concepts(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="最大返回数"),
    user: User = Depends(get_current_user),
):
    """搜索概念（Neo4j 优先，SQLite tags 降级）"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.search_concepts(q, limit=limit, user_id=user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/knowledge/concepts/{name}/timeline", response_model=ConceptTimelineResponse)
async def get_concept_timeline(
    name: str,
    days: int = Query(90, ge=1, le=365, description="最近 N 天"),
    user: User = Depends(get_current_user),
):
    """概念学习时间线"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_concept_timeline(name, days=days, user_id=user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/knowledge/mastery-distribution", response_model=MasteryDistributionResponse)
async def get_mastery_distribution(user: User = Depends(get_current_user)):
    """掌握度分布统计"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_mastery_distribution(user_id=user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
