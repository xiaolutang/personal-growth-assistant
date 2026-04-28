"""搜索 API 路由"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Set

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.schemas.entry import EntryResponse
from app.routers.deps import (
    get_entry_service, get_hybrid_search_service, get_storage, get_current_user,
)
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])


# === 请求/响应模型 ===

class SearchRequest(BaseModel):
    """搜索请求"""
    query: Optional[str] = Field("", description="搜索查询（空时走列表+过滤模式）")
    limit: int = Field(10, ge=1, le=20, description="返回数量")
    filter_type: Optional[str] = Field(None, description="按类型过滤")
    start_time: Optional[str] = Field(None, description="ISO 格式起始时间")
    end_time: Optional[str] = Field(None, description="ISO 格式结束时间")
    tags: Optional[List[str]] = Field(None, description="标签数组筛选")


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


# === 辅助函数 ===

def _snippet(content: str, max_len: int = 100) -> str:
    """截取内容前 max_len 字符作为摘要"""
    if not content:
        return ""
    text = content.replace("\n", " ").strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    """安全解析 ISO 时间字符串，统一返回 naive UTC datetime"""
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return _normalize_datetime(datetime.fromisoformat(normalized))
    except (ValueError, TypeError):
        return None


def _normalize_datetime(value: datetime) -> datetime:
    """统一转换为 naive UTC datetime，避免 aware/naive 混用。"""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _matches_time_window(
    created_at: str,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> bool:
    """检查 created_at 是否落在时间过滤闭区间内。"""
    try:
        created = _normalize_datetime(datetime.fromisoformat(created_at))
    except (ValueError, TypeError):
        return True  # 无法解析时间时不过滤

    if start_time and created < start_time:
        return False
    if end_time and created > end_time:
        return False
    return True


def _matches_tags(entry_tags: List[str], tags: Optional[Set[str]]) -> bool:
    """检查条目 tags 是否与过滤 tag 集合有交集。"""
    if not tags:
        return True
    return bool(set(entry_tags) & tags)


def _entry_matches_filters(
    entry: EntryResponse,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    tags: Optional[Set[str]],
) -> bool:
    """检查 EntryResponse 是否匹配时间和标签过滤条件"""
    if (start_time or end_time) and not _matches_time_window(entry.created_at, start_time, end_time):
        return False

    return _matches_tags(entry.tags or [], tags)


def _filter_entries(
    entries: List[EntryResponse],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    tags: Optional[Set[str]],
) -> List[EntryResponse]:
    """对 EntryResponse 列表应用时间和标签后过滤"""
    if not start_time and not end_time and not tags:
        return entries
    return [e for e in entries if _entry_matches_filters(e, start_time, end_time, tags)]


def _raw_matches_filters(
    raw: dict,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    tags: Optional[Set[str]],
) -> bool:
    """检查原始 dict 结果是否匹配过滤条件（SQLite 降级路径）"""
    if (start_time or end_time) and not _matches_time_window(raw.get("created_at", ""), start_time, end_time):
        return False

    entry_tags = raw.get("tags", [])
    if isinstance(entry_tags, str):
        entry_tags = [t.strip() for t in entry_tags.split(",") if t.strip()]

    return _matches_tags(entry_tags, tags)


# === API 端点 ===

@router.post("/search", response_model=SearchResponse)
async def search_entries(request: SearchRequest, user: User = Depends(get_current_user)):
    """混合搜索条目（向量 + 全文），支持时间和标签过滤，空 query 走列表+过滤模式"""
    return await _search_entries_impl(request, user)

async def _search_entries_impl(request: SearchRequest, user: User):
    storage = get_storage()
    query = request.query or ""
    start_dt = _parse_time(request.start_time)
    end_dt = _parse_time(request.end_time)
    tag_set = set(request.tags) if request.tags else None

    # === 空 query 路径：getEntries + 后过滤 ===
    if not query:
        entry_service = get_entry_service()
        list_response = await entry_service.list_entries(
            type=request.filter_type,
            limit=100,
            offset=0,
            user_id=user.id,
        )
        filtered = _filter_entries(
            list_response.entries, start_dt, end_dt, tag_set,
        )
        filtered = filtered[:request.limit]
        results = [
            SearchResult(
                id=e.id, title=e.title, content_snippet=_snippet(e.content),
                category=e.category, status=e.status, tags=e.tags or [],
                file_path=e.file_path, score=1.0,
            )
            for e in filtered
        ]
        return SearchResponse(results=results, query=query)

    # === 非空 query：混合搜索 + 后过滤 ===
    if storage.qdrant or storage.sqlite:
        try:
            hybrid = get_hybrid_search_service()
            entries = await hybrid.search(
                query, user_id=user.id, limit=request.limit * 2,
                filter_type=request.filter_type,
                start_time=start_dt, end_time=end_dt,
                tags=request.tags,
            )
            # 路由层后过滤（兜底，确保过滤总是生效）
            if request.filter_type:
                entries = [e for e in entries if e.category == request.filter_type]
            entries = _filter_entries(
                entries, start_dt, end_dt, tag_set,
            )
            entries = entries[:request.limit]
            results = [
                SearchResult(
                    id=e.id, title=e.title, content_snippet=_snippet(e.content),
                    category=e.category, status=e.status, tags=e.tags or [],
                    file_path=e.file_path, score=1.0,
                )
                for e in entries
            ]
            return SearchResponse(results=results, query=query)
        except Exception as exc:
            logger.warning(f"混合搜索失败，降级到纯全文: {exc}", exc_info=True)

    # === SQLite 降级 ===
    if storage.sqlite:
        raw = storage.sqlite.search(query, limit=request.limit * 2, user_id=user.id)
        if request.filter_type:
            raw = [r for r in raw if r.get("type") == request.filter_type]
        if request.start_time or request.end_time or request.tags:
            raw = [r for r in raw if _raw_matches_filters(
                r, start_dt, end_dt, tag_set,
            )]
        raw = raw[:request.limit]
        results = [
            SearchResult(
                id=r.get("id", ""), title=r.get("title", ""),
                content_snippet=_snippet(r.get("content", "")),
                category=r.get("type", "note"), status=r.get("status", "doing"),
                tags=r.get("tags", []), file_path=r.get("file_path", ""),
                score=1.0,
            )
            for r in raw
        ]
        return SearchResponse(results=results, query=query)

    # 无任何搜索后端可用
    return SearchResponse(results=[], query=query)
