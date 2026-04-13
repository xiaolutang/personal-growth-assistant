"""搜索 API 路由"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.routers.deps import get_storage, get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])


# === 请求/响应模型 ===

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    limit: int = Field(5, ge=1, le=20, description="返回数量")


class SearchResult(BaseModel):
    """搜索结果项"""
    id: str
    title: str
    score: float
    type: str
    tags: List[str]
    file_path: str


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResult]


# === API 端点 ===

@router.post("/search", response_model=SearchResponse)
async def search_entries(request: SearchRequest, user: User = Depends(get_current_user)):
    """语义搜索条目"""
    storage = get_storage()

    # 检查 Qdrant 是否可用
    if not storage.qdrant:
        raise HTTPException(status_code=503, detail="搜索服务未配置")

    try:
        # 向量搜索
        hits = await storage.qdrant.search(request.query, request.limit, user_id=user.id)

        results = []
        for hit in hits:
            payload = hit.get("payload", {})
            results.append(SearchResult(
                id=hit.get("id", ""),
                title=payload.get("title", ""),
                score=hit.get("score", 0),
                type=payload.get("type", "note"),
                tags=payload.get("tags", []),
                file_path=payload.get("file_path", ""),
            ))

        return SearchResponse(results=results)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
