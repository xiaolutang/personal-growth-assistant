"""条目管理 API 路由"""

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    SearchResult,
    SuccessResponse,
    ProjectProgressResponse,
)
from app.routers.deps import get_entry_service, get_storage

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("", response_model=EntryListResponse)
async def list_entries(
    type: str | None = Query(None, description="条目类型: project/task/note/inbox"),
    status: str | None = Query(None, description="状态: waitStart/doing/complete/paused/cancelled"),
    tags: str | None = Query(None, description="标签筛选（逗号分隔）"),
    parent_id: str | None = Query(None, description="父条目ID（用于获取子任务）"),
    start_date: str | None = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """列出条目（优先从 SQLite 索引读取）"""
    service = get_entry_service()
    return await service.list_entries(
        type=type,
        status=status,
        tags=tags,
        parent_id=parent_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: str):
    """获取单个条目"""
    service = get_entry_service()
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")
    return entry


@router.post("", response_model=EntryResponse)
async def create_entry(request: EntryCreate):
    """创建条目"""
    service = get_entry_service()
    try:
        return await service.create_entry(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entry_id}", response_model=SuccessResponse)
async def update_entry(entry_id: str, request: EntryUpdate):
    """更新条目"""
    service = get_entry_service()
    try:
        success, message = await service.update_entry(entry_id, request)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return SuccessResponse(success=success, message=message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search/query", response_model=SearchResult)
async def search_entries(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
):
    """全文搜索条目（使用 SQLite FTS5）"""
    service = get_entry_service()
    try:
        return await service.search_entries(q, limit)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/{entry_id}", response_model=SuccessResponse)
async def delete_entry(entry_id: str):
    """删除条目"""
    service = get_entry_service()
    success, message = await service.delete_entry(entry_id)
    if not success:
        raise HTTPException(status_code=404 if "不存在" in message else 500, detail=message)
    return SuccessResponse(success=success, message=message)


@router.get("/{entry_id}/progress", response_model=ProjectProgressResponse)
async def get_project_progress(entry_id: str):
    """获取项目进度（子任务完成率）"""
    service = get_entry_service()
    try:
        return await service.get_project_progress(entry_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/admin/sync-vectors", response_model=SuccessResponse)
async def sync_vectors():
    """同步所有条目到向量数据库（Qdrant）"""
    storage = get_storage()
    if not storage.qdrant:
        raise HTTPException(status_code=503, detail="向量数据库未配置")

    try:
        result = await storage.sync_all()
        return SuccessResponse(
            success=True,
            message=f"同步完成: {result['success']} 条成功, {result['failed']} 条失败"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")
