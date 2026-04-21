"""搜索 API 路由"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routers.deps import get_hybrid_search_service, get_storage, get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])


# === 请求/响应模型 ===

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    limit: int = Field(10, ge=1, le=20, description="返回数量")
    filter_type: Optional[str] = Field(None, description="按类型过滤")


class SearchResult(BaseModel):
    """搜索结果项"""
    id: str
    title: str
    content_snippet: str
    category: str
    status: str
    tags: List[str]
    file_path: str
    score: float


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResult]
    query: str


# === API 端点 ===

@router.post("/search", response_model=SearchResponse)
async def search_entries(request: SearchRequest, user: User = Depends(get_current_user)):
    """混合搜索条目（向量 + 全文），Qdrant 不可用时自动降级为纯全文"""
    storage = get_storage()

    def _snippet(content: str, max_len: int = 120) -> str:
        """截取内容前 max_len 字符作为摘要"""
        if not content:
            return ""
        text = content.replace("\n", " ").strip()
        return text[:max_len] + ("..." if len(text) > max_len else "")

    # 尝试混合搜索
    if storage.qdrant or storage.sqlite:
        try:
            hybrid = get_hybrid_search_service()
            entries = await hybrid.search(
                request.query, user_id=user.id, limit=request.limit, filter_type=request.filter_type,
            )
            results = []
            for e in entries:
                results.append(SearchResult(
                    id=e.id,
                    title=e.title,
                    content_snippet=_snippet(e.content),
                    category=e.category,
                    status=e.status,
                    tags=e.tags or [],
                    file_path=e.file_path,
                    score=1.0,
                ))
            return SearchResponse(results=results, query=request.query)
        except Exception as exc:
            logger.warning(f"混合搜索失败，降级到纯全文: {exc}")

    # 降级：仅 SQLite 全文搜索
    if storage.sqlite:
        raw = storage.sqlite.search(request.query, limit=request.limit, user_id=user.id)
        if request.filter_type:
            raw = [r for r in raw if r.get("type") == request.filter_type]
        results = [
            SearchResult(
                id=r.get("id", ""),
                title=r.get("title", ""),
                content_snippet=_snippet(r.get("content", "")),
                category=r.get("type", "note"),
                status=r.get("status", "doing"),
                tags=r.get("tags", []),
                file_path=r.get("file_path", ""),
                score=1.0,
            )
            for r in raw
        ]
        return SearchResponse(results=results, query=request.query)

    # 无任何搜索后端可用
    return SearchResponse(results=[], query=request.query)
