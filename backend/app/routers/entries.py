"""条目管理 API 路由"""
from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models import Task, Category, TaskStatus, Priority
from app.routers.deps import get_storage

router = APIRouter(prefix="/entries", tags=["entries"])


# === 请求/响应模型 ===

class EntryCreate(BaseModel):
    """创建条目请求"""
    type: str = Field(..., description="条目类型: project/task/note/inbox")
    title: str = Field(..., min_length=1, description="标题")
    content: str = Field(default="", description="内容")
    tags: List[str] = Field(default_factory=list, description="标签")
    parent_id: Optional[str] = Field(None, description="父条目ID")
    status: Optional[str] = Field(None, description="状态: waitStart/doing/complete/paused/cancelled")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")
    planned_date: Optional[str] = Field(None, description="计划日期")
    time_spent: Optional[int] = Field(None, description="耗时（分钟）")


class EntryUpdate(BaseModel):
    """更新条目请求"""
    title: Optional[str] = Field(None, description="新标题")
    content: Optional[str] = Field(None, description="新内容")
    status: Optional[str] = Field(None, description="新状态: waitStart/doing/complete/paused/cancelled")
    priority: Optional[str] = Field(None, description="新优先级: high/medium/low")
    tags: Optional[List[str]] = Field(None, description="新标签")
    parent_id: Optional[str] = Field(None, description="父条目ID")
    planned_date: Optional[str] = Field(None, description="计划日期")
    time_spent: Optional[int] = Field(None, description="耗时（分钟）")
    completed_at: Optional[str] = Field(None, description="完成时间")


class EntryResponse(BaseModel):
    """条目响应"""
    id: str
    title: str
    content: str
    category: str
    status: str
    priority: str = "medium"
    tags: List[str]
    created_at: str
    updated_at: str
    planned_date: Optional[str] = None
    completed_at: Optional[str] = None
    time_spent: Optional[int] = None
    parent_id: Optional[str] = None
    file_path: str


class EntryListResponse(BaseModel):
    """条目列表响应"""
    entries: List[EntryResponse]
    total: int = 0


class SearchResult(BaseModel):
    """搜索结果"""
    entries: List[EntryResponse]
    query: str


class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool
    message: str = ""


def task_to_response(task: Task) -> EntryResponse:
    """Task 模型或字典转响应模型"""
    if isinstance(task, Task):
        return EntryResponse(
            id=task.id,
            title=task.title,
            content=task.content,
            category=task.category.value,
            status=task.status.value,
            priority=task.priority.value if hasattr(task, 'priority') and task.priority else "medium",
            tags=task.tags,
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            planned_date=task.planned_date.isoformat() if task.planned_date else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            time_spent=task.time_spent,
            parent_id=task.parent_id,
            file_path=task.file_path,
        )
    # 支持字典输入（来自 SQLite）
    return EntryResponse(
        id=task["id"],
        title=task.get("title", ""),
        content=task.get("content", ""),
        category=task.get("type", "note"),
        status=task.get("status", "doing"),
        priority=task.get("priority", "medium"),
        tags=task.get("tags", []),
        created_at=task.get("created_at", ""),
        updated_at=task.get("updated_at", ""),
        planned_date=task.get("planned_date"),
        completed_at=task.get("completed_at"),
        time_spent=task.get("time_spent"),
        parent_id=task.get("parent_id"),
        file_path=task.get("file_path", ""),
    )


# 保留别名以保持兼容性
dict_to_response = task_to_response


# === API 端点 ===

@router.get("", response_model=EntryListResponse)
async def list_entries(
    type: Optional[str] = Query(None, description="条目类型: project/task/note/inbox"),
    status: Optional[str] = Query(None, description="状态: waitStart/doing/complete/paused/cancelled"),
    tags: Optional[str] = Query(None, description="标签筛选（逗号分隔）"),
    parent_id: Optional[str] = Query(None, description="父条目ID（用于获取子任务）"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """列出条目（优先从 SQLite 索引读取）"""
    storage = get_storage()

    # 优先使用 SQLite 索引
    if storage.sqlite:
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        entries = storage.sqlite.list_entries(
            type=type,
            status=status,
            tags=tag_list,
            parent_id=parent_id,
            limit=limit,
            offset=offset,
        )
        total = storage.sqlite.count_entries(
            type=type,
            status=status,
            tags=tag_list,
            parent_id=parent_id,
        )
        return EntryListResponse(
            entries=[dict_to_response(e) for e in entries],
            total=total,
        )

    # 回退到 Markdown 直接读取
    category = Category(type) if type else None
    task_status = TaskStatus(status) if status else None

    entries = storage.markdown.list_entries(
        category=category,
        status=task_status,
        limit=limit,
    )

    return EntryListResponse(
        entries=[task_to_response(e) for e in entries]
    )


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(entry_id: str):
    """获取单个条目"""
    storage = get_storage()

    entry = storage.markdown.read_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")

    return task_to_response(entry)


@router.post("", response_model=EntryResponse)
async def create_entry(request: EntryCreate):
    """创建条目"""
    storage = get_storage()

    try:
        category = Category(request.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的条目类型: {request.type}")

    # 生成 ID 和文件路径
    entry_id = f"{category.value}-{uuid.uuid4().hex[:8]}"
    now = datetime.now()

    # 复用 MarkdownStorage 的目录映射
    from app.storage.markdown import MarkdownStorage
    dir_name = MarkdownStorage.CATEGORY_DIRS.get(category, "notes")
    file_path = f"{dir_name}/{entry_id}.md" if dir_name else f"{entry_id}.md"

    # 解析状态（如果提供了的话）
    if request.status:
        try:
            status = TaskStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {request.status}")
    else:
        status = TaskStatus.DOING

    # 解析优先级
    if request.priority:
        try:
            priority = Priority(request.priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的优先级: {request.priority}")
    else:
        priority = Priority.MEDIUM

    # 解析计划日期
    planned_date = None
    if request.planned_date:
        try:
            planned_date = datetime.fromisoformat(request.planned_date.replace('Z', '').split('+')[0])
        except ValueError:
            pass

    # 创建条目
    entry = Task(
        id=entry_id,
        title=request.title,
        content=request.content,
        category=category,
        status=status,
        priority=priority,
        tags=request.tags,
        created_at=now,
        updated_at=now,
        parent_id=request.parent_id,
        file_path=file_path,
        planned_date=planned_date,
        time_spent=request.time_spent,
    )

    # 写入 Markdown
    storage.markdown.write_entry(entry)

    # 异步同步到 Neo4j + Qdrant（不阻塞响应）
    try:
        await storage.sync_entry(entry)
    except Exception as e:
        # 同步失败不影响创建
        print(f"同步失败: {e}")

    return task_to_response(entry)


@router.put("/{entry_id}", response_model=SuccessResponse)
async def update_entry(entry_id: str, request: EntryUpdate):
    """更新条目"""
    storage = get_storage()

    entry = storage.markdown.read_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")

    # 更新字段
    updated = False
    if request.title is not None:
        entry.title = request.title
        updated = True
    if request.content is not None:
        entry.content = request.content
        updated = True
    if request.status is not None:
        try:
            entry.status = TaskStatus(request.status)
            updated = True
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态: {request.status}")
    if request.priority is not None:
        try:
            entry.priority = Priority(request.priority)
            updated = True
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的优先级: {request.priority}")
    if request.tags is not None:
        entry.tags = request.tags
        updated = True
    if request.parent_id is not None:
        entry.parent_id = request.parent_id
        updated = True
    if request.planned_date is not None:
        try:
            entry.planned_date = datetime.fromisoformat(request.planned_date.replace('Z', '').split('+')[0])
            updated = True
        except ValueError:
            pass
    if request.time_spent is not None:
        entry.time_spent = request.time_spent
        updated = True
    if request.completed_at is not None:
        try:
            entry.completed_at = datetime.fromisoformat(request.completed_at.replace('Z', '').split('+')[0])
            updated = True
        except ValueError:
            pass

    if not updated:
        return SuccessResponse(success=True, message="无更新")

    entry.updated_at = datetime.now()

    # 写入 Markdown
    storage.markdown.write_entry(entry)

    # 异步同步
    try:
        await storage.sync_entry(entry)
    except Exception as e:
        print(f"同步失败: {e}")

    return SuccessResponse(success=True, message=f"已更新条目: {entry_id}")


@router.get("/search/query", response_model=SearchResult)
async def search_entries(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
):
    """全文搜索条目（使用 SQLite FTS5）"""
    storage = get_storage()

    if not storage.sqlite:
        raise HTTPException(status_code=503, detail="SQLite 索引不可用")

    results = storage.sqlite.search(q, limit=limit)

    return SearchResult(
        entries=[dict_to_response(e) for e in results],
        query=q,
    )


@router.delete("/{entry_id}", response_model=SuccessResponse)
async def delete_entry(entry_id: str):
    """删除条目"""
    storage = get_storage()

    # 检查条目是否存在
    entry = storage.markdown.read_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")

    # 删除
    success = await storage.delete_entry(entry_id)

    if success:
        return SuccessResponse(success=True, message=f"已删除条目: {entry_id}")
    else:
        raise HTTPException(status_code=500, detail="删除失败")


class ProjectProgressResponse(BaseModel):
    """项目进度响应"""
    project_id: str
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
    status_distribution: dict


@router.get("/{entry_id}/progress", response_model=ProjectProgressResponse)
async def get_project_progress(entry_id: str):
    """获取项目进度（子任务完成率）"""
    storage = get_storage()

    # 检查项目是否存在
    entry = storage.markdown.read_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"条目不存在: {entry_id}")

    if not storage.sqlite:
        raise HTTPException(status_code=503, detail="SQLite 索引不可用")

    # 获取所有子任务
    child_entries = storage.sqlite.list_entries(parent_id=entry_id, limit=1000)

    total = len(child_entries)
    if total == 0:
        return ProjectProgressResponse(
            project_id=entry_id,
            total_tasks=0,
            completed_tasks=0,
            progress_percentage=0.0,
            status_distribution={}
        )

    # 统计各状态数量
    status_counts = {}
    completed = 0
    for child in child_entries:
        status = child.get("status", "doing")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "complete":
            completed += 1

    progress = (completed / total) * 100 if total > 0 else 0

    return ProjectProgressResponse(
        project_id=entry_id,
        total_tasks=total,
        completed_tasks=completed,
        progress_percentage=round(progress, 1),
        status_distribution=status_counts
    )

