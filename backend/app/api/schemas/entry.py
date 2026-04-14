"""条目相关 Schema (DTO) - 使用 category 统一命名"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, AliasChoices


# === 请求模型 ===

class EntryCreate(BaseModel):
    """创建条目请求"""
    category: str = Field(
        ...,
        description="条目分类: project/task/note/inbox",
        validation_alias=AliasChoices('category', 'type')
    )
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
