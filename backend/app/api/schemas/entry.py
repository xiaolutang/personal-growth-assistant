"""条目相关 Schema (DTO) - 使用 category 统一命名"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, AliasChoices


# === 请求模型 ===

class EntryCreate(BaseModel):
    """创建条目请求"""
    category: str = Field(
        ...,
        description="条目分类: project/task/note/inbox/decision/reflection/question",
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
    category: Optional[str] = Field(None, description="条目分类: project/task/note/inbox/decision/reflection/question")
    status: Optional[str] = Field(None, description="新状态: waitStart/doing/complete/paused/cancelled")
    priority: Optional[str] = Field(None, description="新优先级: high/medium/low")
    tags: Optional[List[str]] = Field(None, description="新标签")
    parent_id: Optional[str] = Field(None, description="父条目ID")
    planned_date: Optional[str] = Field(None, description="计划日期")
    time_spent: Optional[int] = Field(None, description="耗时（分钟）")
    completed_at: Optional[str] = Field(None, description="完成时间")


class EntryLinkCreate(BaseModel):
    """创建条目关联请求"""
    target_id: str = Field(..., min_length=1, description="目标条目 ID")
    relation_type: Literal["related", "depends_on", "derived_from", "references"] = Field(
        ..., description="关联类型: related/depends_on/derived_from/references"
    )


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


class RelatedEntry(BaseModel):
    """关联条目"""
    id: str
    title: str
    category: str
    relevance_reason: str


class RelatedEntriesResponse(BaseModel):
    """关联条目列表响应"""
    related: List[RelatedEntry]


class EntrySummaryResponse(BaseModel):
    """AI 摘要响应"""
    summary: Optional[str] = None
    generated_at: Optional[str] = None
    cached: bool = False


class LinkTargetEntry(BaseModel):
    """关联目标条目摘要"""
    id: str
    title: str
    category: str


class EntryLinkResponse(BaseModel):
    """条目关联响应（创建时返回）"""
    id: str
    source_id: str
    target_id: str
    relation_type: str
    created_at: str
    target_entry: LinkTargetEntry


class EntryLinkItem(BaseModel):
    """条目关联列表项"""
    id: str
    target_id: str
    target_entry: LinkTargetEntry
    relation_type: str
    direction: str
    created_at: str


class EntryLinkListResponse(BaseModel):
    """条目关联列表响应"""
    links: List[EntryLinkItem]


# === 知识上下文 ===

class KnowledgeContextNode(BaseModel):
    """知识上下文节点"""
    id: str
    name: str
    category: Optional[str] = None
    mastery: Optional[str] = None
    entry_count: int = 0


class KnowledgeContextEdge(BaseModel):
    """知识上下文边"""
    source: str
    target: str
    relationship: str = "RELATED_TO"


class KnowledgeContextResponse(BaseModel):
    """条目知识上下文响应"""
    nodes: List[KnowledgeContextNode] = []
    edges: List[KnowledgeContextEdge] = []
    center_concepts: List[str] = []


class BacklinkItem(BaseModel):
    """反向引用条目"""
    id: str
    title: str
    category: str


class BacklinksResponse(BaseModel):
    """反向引用列表响应"""
    backlinks: List[BacklinkItem]
