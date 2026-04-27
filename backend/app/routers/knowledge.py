"""知识图谱 API 路由"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.deps import get_knowledge_service, get_recommendation_service, get_current_user
from app.models.user import User
from app.models.knowledge import (
    ConceptNode,
    KnowledgeGraphResponse,
    RelatedConceptsResponse,
    LearningPathResponse,
    KnowledgeMapResponse,
    ConceptStatsResponse,
    ConceptSearchResponse,
    ConceptTimelineResponse,
    MasteryDistributionResponse,
    CapabilityMapResponse,
)
from app.services.recommendation_service import RecommendationResponse

router = APIRouter(tags=["knowledge"])

logger = logging.getLogger(__name__)


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
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/related-concepts/{concept}", response_model=RelatedConceptsResponse)
async def get_related_concepts(concept: str, user: User = Depends(get_current_user)):
    """获取相关概念"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_related_concepts(concept, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


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
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/knowledge-map", response_model=KnowledgeMapResponse)
async def get_knowledge_map(
    depth: int = Query(2, ge=1, le=3, description="关系深度"),
    view: str = Query("domain", regex="^(domain|mastery|project)$", description="视图模式"),
    user: User = Depends(get_current_user),
):
    """获取全局知识图谱

    返回所有概念节点及其关系，支持按掌握度/领域/项目分组查看。
    Neo4j 不可用时返回 200 + 空图谱（降级到 SQLite）。
    """
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_knowledge_map(depth=depth, view=view, user_id=user.id)
    except (ConnectionError, ValueError) as e:
        logger.warning(f"知识图谱查询降级返回空数据: {e}")
        return KnowledgeMapResponse()


@router.get("/knowledge/stats", response_model=ConceptStatsResponse)
async def get_knowledge_stats(user: User = Depends(get_current_user)):
    """获取知识概念统计

    返回概念总数、关系总数、类别分布和热门概念。
    Neo4j 不可用时返回 200 + 零值统计（降级到 SQLite）。
    """
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_knowledge_stats(user_id=user.id)
    except (ConnectionError, ValueError) as e:
        logger.warning(f"知识统计查询降级返回空数据: {e}")
        return ConceptStatsResponse()


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
        logger.error("搜索失败", exc_info=True)
        raise HTTPException(status_code=500, detail="搜索失败，请稍后重试")


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
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/knowledge/mastery-distribution", response_model=MasteryDistributionResponse)
async def get_mastery_distribution(user: User = Depends(get_current_user)):
    """掌握度分布统计"""
    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_mastery_distribution(user_id=user.id)
    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/knowledge/capability-map", response_model=CapabilityMapResponse)
async def get_capability_map(
    mastery_level: Optional[str] = Query(None, description="按掌握度过滤: new/beginner/intermediate/advanced"),
    user: User = Depends(get_current_user),
):
    """获取能力地图数据（按领域聚合的概念+掌握度）"""
    if mastery_level and mastery_level not in ("new", "beginner", "intermediate", "advanced"):
        raise HTTPException(status_code=422, detail="mastery_level 参数必须是 new/beginner/intermediate/advanced")

    knowledge_service = get_knowledge_service()

    try:
        return await knowledge_service.get_capability_map(mastery_level=mastery_level, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.get("/knowledge/recommendations", response_model=RecommendationResponse)
async def get_knowledge_recommendations(user: User = Depends(get_current_user)):
    """获取知识推荐

    返回三类推荐：
    - knowledge_gaps: 知识缺口（PREREQUISITE 关系链中未涉足的概念）
    - review_suggestions: 复习推荐（间隔重复策略，推荐近期未复习的概念）
    - related_concepts: 共现推荐（基于标签共现或概念中心度）
    """
    recommendation_service = get_recommendation_service()

    try:
        return await recommendation_service.get_recommendations(user_id=user.id)
    except Exception as e:
        logger.error("推荐查询失败", exc_info=True)
        raise HTTPException(status_code=500, detail="推荐查询失败，请稍后重试")
