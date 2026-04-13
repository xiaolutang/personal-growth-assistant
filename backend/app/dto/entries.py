"""条目相关 DTO"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models import Task, TaskStatus, Priority


# === 请求模型 ===

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
    category: Optional[str] = Field(None, description="条目分类: project/task/note/inbox")
    status: Optional[str] = Field(None, description="新状态: waitStart/doing/complete/paused/cancelled")
    priority: Optional[str] = Field(None, description="新优先级: high/medium/low")
    tags: Optional[List[str]] = Field(None, description="新标签")
    parent_id: Optional[str] = Field(None, description="父条目ID")
    planned_date: Optional[str] = Field(None, description="计划日期")
    time_spent: Optional[int] = Field(None, description="耗时（分钟）")
    completed_at: Optional[str] = Field(None, description="完成时间")


# === 响应模型 ===

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


class ProjectProgressResponse(BaseModel):
    """项目进度响应"""
    project_id: str
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
    status_distribution: dict


# === 转换函数 ===

def task_to_response(task: Task) -> EntryResponse:
    """Task 模型转响应模型"""
    if isinstance(task, Task):
        return EntryResponse(
            id=task.id,
            title=task.title,
            content=task.content,
            category=task.category.value,
            status=task.status.value,
            priority=task.priority.value if task.priority else "medium",
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
    return dict_to_response(task)


def dict_to_response(data: dict) -> EntryResponse:
    """字典转响应模型（来自 SQLite）"""
    return EntryResponse(
        id=data["id"],
        title=data.get("title", ""),
        content=data.get("content", ""),
        category=data.get("category") or data.get("type", "note"),
        status=data.get("status", "doing"),
        priority=data.get("priority", "medium"),
        tags=data.get("tags", []),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        planned_date=data.get("planned_date"),
        completed_at=data.get("completed_at"),
        time_spent=data.get("time_spent"),
        parent_id=data.get("parent_id"),
        file_path=data.get("file_path", ""),
    )
