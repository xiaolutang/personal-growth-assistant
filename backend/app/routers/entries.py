"""条目管理 API 路由"""

import re
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from app.api.schemas import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    SearchResult,
    SuccessResponse,
    ProjectProgressResponse,
    RelatedEntriesResponse,
    EntrySummaryResponse,
    EntryLinkCreate,
    EntryLinkResponse,
    EntryLinkListResponse,
    KnowledgeContextResponse,
    BacklinksResponse,
    BacklinkItem,
    EntryTemplateListResponse,
)
from app.routers.deps import get_entry_service, get_current_user, get_knowledge_service
from app.models.user import User

router = APIRouter(prefix="/entries", tags=["entries"])

_VALID_EXPORT_TYPES = {"inbox", "task", "note", "project", "decision", "reflection", "question"}
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@router.get("", response_model=EntryListResponse)
async def list_entries(
    type: str | None = Query(None, description="条目类型: project/task/note/inbox/decision/reflection/question"),
    status: str | None = Query(None, description="状态: waitStart/doing/complete/paused/cancelled"),
    tags: str | None = Query(None, description="标签筛选（逗号分隔）"),
    parent_id: str | None = Query(None, description="父条目ID（用于获取子任务）"),
    start_date: str | None = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
    due: str | None = Query(None, description="到期过滤: today(今日到期) / overdue(已过期)"),
    priority: str | None = Query(None, description="优先级筛选: high/medium/low"),
    sort_by: str | None = Query(None, description="排序字段: priority"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user: User = Depends(get_current_user),
):
    """列出条目（优先从 SQLite 索引读取）"""
    if due is not None and due not in ("today", "overdue"):
        raise HTTPException(status_code=422, detail="due 参数必须是 today 或 overdue")

    service = get_entry_service()
    return await service.list_entries(
        type=type,
        status=status,
        tags=tags,
        parent_id=parent_id,
        start_date=start_date,
        end_date=end_date,
        due=due,
        priority=priority,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
        user_id=user.id,
    )


@router.get("/templates", response_model=EntryTemplateListResponse)
async def list_templates(
    category: str | None = Query(None, description="按类型过滤模板（如 note）"),
    user: User = Depends(get_current_user),
):
    """获取可用模板列表"""
    service = get_entry_service()
    templates = service.get_templates(category)
    return {"templates": templates}


@router.get("/export")
async def export_entries(
    format: str = Query("markdown", description="导出格式: markdown 或 json"),
    type: str | None = Query(None, description="条目类型: project/task/note/inbox/decision/reflection/question"),
    start_date: str | None = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="结束日期 (YYYY-MM-DD)"),
    user: User = Depends(get_current_user),
):
    """导出条目数据"""
    if format not in ("markdown", "json"):
        raise HTTPException(status_code=422, detail="format 参数必须是 markdown 或 json")

    # 参数校验: type
    if type is not None and type not in _VALID_EXPORT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"type 参数必须是 {', '.join(sorted(_VALID_EXPORT_TYPES))} 之一",
        )

    # 参数校验: start_date / end_date 格式
    for param_name, param_val in [("start_date", start_date), ("end_date", end_date)]:
        if param_val is not None:
            if not _ISO_DATE_RE.match(param_val):
                raise HTTPException(
                    status_code=422,
                    detail=f"{param_name} 格式无效，必须为 YYYY-MM-DD",
                )
            try:
                date.fromisoformat(param_val)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"{param_name} 不是合法日期: {param_val}",
                )

    service = get_entry_service()

    if format == "markdown":
        return StreamingResponse(
            service.export_markdown_stream(
                type=type,
                start_date=start_date,
                end_date=end_date,
                user_id=user.id,
            ),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=entries_export.zip"},
        )

    # json 格式
    data = await service.export_json(
        type=type,
        start_date=start_date,
        end_date=end_date,
        user_id=user.id,
    )
    return JSONResponse(content=data)


@router.get("/search/query", response_model=SearchResult)
async def search_entries(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    user: User = Depends(get_current_user),
):
    """全文搜索条目（使用 SQLite FTS5）"""
    service = get_entry_service()
    try:
        return await service.search_entries(q, limit, user_id=user.id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/{entry_id}/related", response_model=RelatedEntriesResponse)
async def get_related_entries(entry_id: str, user: User = Depends(get_current_user)):
    """获取条目的关联推荐"""
    service = get_entry_service()
    result = await service.get_related_entries(entry_id, user_id=user.id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")
    return result


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: str, user: User = Depends(get_current_user)):
    """获取单个条目"""
    service = get_entry_service()
    entry = await service.get_entry(entry_id, user_id=user.id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")
    return entry


@router.get("/{entry_id}/backlinks", response_model=BacklinksResponse)
async def get_backlinks(entry_id: str, user: User = Depends(get_current_user)):
    """获取条目的反向引用列表（谁引用了这个条目）"""
    service = get_entry_service()
    # 先验证条目存在且属于当前用户
    if not service._verify_entry_owner(entry_id, user.id):
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")

    backlinks = await service.get_backlinks(entry_id, user_id=user.id)
    return BacklinksResponse(
        backlinks=[BacklinkItem(**bl) for bl in backlinks]
    )


@router.get("/{entry_id}/export")
async def export_single_entry(entry_id: str, user: User = Depends(get_current_user)):
    """导出单条目 Markdown 文件"""
    service = get_entry_service()

    # 验证条目存在且属于当前用户
    entry = await service.get_entry(entry_id, user_id=user.id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")

    # 获取 Markdown 文件路径
    md_storage = service.get_markdown_storage(user.id)
    file_path = None
    from app.models import Category
    for cat in [Category.NOTE, Category.PROJECT, Category.TASK, Category.INBOX,
                Category.DECISION, Category.REFLECTION, Category.QUESTION]:
        fp = md_storage.get_file_path(entry_id, cat)
        if fp.exists():
            file_path = fp
            break

    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"条目文件不存在: {entry_id}")

    # 文件名：标题中的特殊字符替换为 _
    safe_title = re.sub(r'[^\w\s-]', '_', entry.title or "entry").strip()
    filename = f"{safe_title}.md"
    encoded_filename = quote(filename)

    return FileResponse(
        path=str(file_path),
        media_type="text/markdown; charset=utf-8",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"},
    )


@router.post("", response_model=EntryResponse)
async def create_entry(request: EntryCreate, user: User = Depends(get_current_user)):
    """创建条目"""
    service = get_entry_service()
    try:
        return await service.create_entry(request, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{entry_id}", response_model=SuccessResponse)
async def update_entry(entry_id: str, request: EntryUpdate, user: User = Depends(get_current_user)):
    """更新条目"""
    service = get_entry_service()
    try:
        success, message = await service.update_entry(entry_id, request, user_id=user.id)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return SuccessResponse(success=success, message=message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{entry_id}", response_model=SuccessResponse)
async def delete_entry(entry_id: str, user: User = Depends(get_current_user)):
    """删除条目"""
    service = get_entry_service()
    success, message = await service.delete_entry(entry_id, user_id=user.id)
    if not success:
        raise HTTPException(status_code=404 if "不存在" in message else 500, detail=message)
    return SuccessResponse(success=success, message=message)


@router.get("/{entry_id}/progress", response_model=ProjectProgressResponse)
async def get_project_progress(entry_id: str, user: User = Depends(get_current_user)):
    """获取项目进度（子任务完成率）"""
    service = get_entry_service()
    try:
        return await service.get_project_progress(entry_id, user_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# NOTE: sync-vectors 端点已移除（B64 安全加固）。
# 全量向量同步应通过内部脚本或管理 CLI 触发，不应作为公开 API 暴露。


@router.post("/{entry_id}/ai-summary", response_model=EntrySummaryResponse)
async def generate_ai_summary(entry_id: str, user: User = Depends(get_current_user)):
    """为条目生成 AI 摘要（200字以内），结果缓存到 SQLite"""
    service = get_entry_service()
    try:
        result = await service.generate_summary(entry_id, user_id=user.id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")
    return result


@router.post("/{entry_id}/links", response_model=EntryLinkResponse, status_code=201)
async def create_entry_link(
    entry_id: str,
    request: EntryLinkCreate,
    user: User = Depends(get_current_user),
):
    """创建条目关联（双向）"""
    service = get_entry_service()
    result, status_code, message = await service.create_entry_link(
        entry_id, request, user_id=user.id
    )
    if result is None:
        raise HTTPException(status_code=status_code, detail=message)
    return result


@router.get("/{entry_id}/links", response_model=EntryLinkListResponse)
async def list_entry_links(
    entry_id: str,
    direction: str = Query("both", description="关联方向: in/out/both"),
    user: User = Depends(get_current_user),
):
    """列出条目关联"""
    service = get_entry_service()
    result, status_code, message = await service.list_entry_links(
        entry_id, user_id=user.id, direction=direction
    )
    if result is None:
        raise HTTPException(status_code=status_code, detail=message)
    return result


@router.delete("/{entry_id}/links/{link_id}", status_code=204)
async def delete_entry_link(
    entry_id: str,
    link_id: str,
    user: User = Depends(get_current_user),
):
    """删除条目关联（双向）"""
    service = get_entry_service()
    success, status_code, message = await service.delete_entry_link(
        entry_id, link_id, user_id=user.id
    )
    if not success:
        raise HTTPException(status_code=status_code, detail=message)


@router.get("/{entry_id}/knowledge-context", response_model=KnowledgeContextResponse)
async def get_entry_knowledge_context(
    entry_id: str,
    user: User = Depends(get_current_user),
):
    """获取条目的知识图谱子图上下文（基于条目标签的 1-hop 子图）"""
    # 验证条目存在且属于当前用户
    service = get_entry_service()
    entry = await service.get_entry(entry_id, user_id=user.id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")

    ks = get_knowledge_service()
    return await ks.get_entry_knowledge_context(entry_id, user_id=user.id)
