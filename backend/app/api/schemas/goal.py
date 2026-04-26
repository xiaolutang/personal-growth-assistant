"""Goal 相关 Schema (DTO)"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# === 请求模型 ===

class GoalCreate(BaseModel):
    """创建目标请求"""
    title: str = Field(..., min_length=1, description="目标标题")
    description: Optional[str] = Field(None, description="目标描述")
    metric_type: Literal["count", "checklist", "tag_auto", "milestone"] = Field(
        ..., description="衡量方式: count(手动计数)/checklist(检查清单)/tag_auto(基于tag自动追踪)/milestone(里程碑)"
    )
    target_value: int = Field(..., ge=1, description="目标值（必须 >= 1）")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    auto_tags: Optional[List[str]] = Field(None, description="自动追踪的标签列表（tag_auto 类型必填）")
    checklist_items: Optional[List[str]] = Field(None, description="检查清单项标题列表（checklist 类型必填）")

    @model_validator(mode="after")
    def validate_metric_fields(self):
        """根据 metric_type 校验条件必填字段"""
        if self.metric_type == "tag_auto" and (not self.auto_tags or len(self.auto_tags) == 0):
            raise ValueError("tag_auto 类型必须提供 auto_tags")
        if self.metric_type == "checklist" and (not self.checklist_items or len(self.checklist_items) == 0):
            raise ValueError("checklist 类型必须提供 checklist_items")
        return self


class GoalUpdate(BaseModel):
    """更新目标请求"""
    title: Optional[str] = Field(None, min_length=1, description="目标标题")
    description: Optional[str] = Field(None, description="目标描述")
    target_value: Optional[int] = Field(None, ge=1, description="目标值（必须 >= 1）")
    status: Optional[Literal["active", "completed", "abandoned"]] = Field(None, description="目标状态")
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")


# === 响应模型 ===

class ChecklistItem(BaseModel):
    """检查清单项"""
    id: str
    title: str
    checked: bool = False


class GoalResponse(BaseModel):
    """目标响应"""
    id: str
    title: str
    description: Optional[str] = None
    metric_type: str
    target_value: int
    current_value: int = 0
    status: str = "active"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    auto_tags: Optional[List[str]] = None
    checklist_items: Optional[List[ChecklistItem]] = None
    progress_percentage: float = 0.0
    created_at: str
    updated_at: str


class GoalListResponse(BaseModel):
    """目标列表响应"""
    goals: List[GoalResponse]


class GoalDetailResponse(GoalResponse):
    """目标详情响应（含关联条目数）"""
    linked_entries_count: int = 0


# === 条目关联 ===

class GoalEntryCreate(BaseModel):
    """创建目标-条目关联请求"""
    entry_id: str = Field(..., min_length=1, description="条目 ID")


class EntryInfo(BaseModel):
    """关联条目简要信息"""
    id: str
    title: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    created_at: Optional[str] = None


class GoalEntryResponse(BaseModel):
    """目标-条目关联响应"""
    id: str
    goal_id: str
    entry_id: str
    created_at: str
    entry: EntryInfo


class GoalEntryLinkResponse(BaseModel):
    """目标-条目关联创建响应（含更新后的目标）"""
    id: str
    goal_id: str
    entry_id: str
    created_at: str
    entry: EntryInfo
    goal: GoalDetailResponse


class GoalEntryListResponse(BaseModel):
    """目标-条目关联列表响应"""
    entries: List[GoalEntryResponse]


# === Checklist 切换 ===

class ChecklistItemToggle(BaseModel):
    """检查清单项切换请求"""
    checked: bool = Field(..., description="是否勾选")


# === 进度汇总 ===

class ProgressItem(BaseModel):
    """进度单项"""
    id: str
    title: str
    progress_percentage: float
    progress_delta: Optional[float] = None


class ProgressSummaryResponse(BaseModel):
    """进度汇总响应"""
    active_count: int
    completed_count: int
    goals: List[ProgressItem]


# === 进度历史快照 ===

class ProgressSnapshotItem(BaseModel):
    """进度快照项"""
    id: str
    goal_id: str
    current_value: int
    target_value: int
    percentage: float
    snapshot_date: str
    created_at: str


class ProgressHistoryResponse(BaseModel):
    """进度历史响应"""
    snapshots: List[ProgressSnapshotItem]


# === 里程碑 ===

class MilestoneCreate(BaseModel):
    """创建里程碑请求"""
    title: str = Field(..., min_length=1, description="里程碑标题")
    description: Optional[str] = Field(None, description="里程碑描述")
    due_date: Optional[str] = Field(None, description="截止日期 (YYYY-MM-DD)")


class MilestoneUpdate(BaseModel):
    """更新里程碑请求"""
    title: Optional[str] = Field(None, min_length=1, description="里程碑标题")
    description: Optional[str] = Field(None, description="里程碑描述")
    due_date: Optional[str] = Field(None, description="截止日期 (YYYY-MM-DD)")
    status: Optional[Literal["pending", "completed"]] = Field(None, description="里程碑状态")


class MilestoneResponse(BaseModel):
    """里程碑响应"""
    id: str
    goal_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[str] = None
    status: str = "pending"
    sort_order: int = 0
    created_at: str
    updated_at: str


class MilestoneReorderRequest(BaseModel):
    """里程碑重排序请求"""
    milestone_ids: List[str] = Field(..., min_length=1, description="按新顺序排列的里程碑 ID 列表")


class MilestoneListResponse(BaseModel):
    """里程碑列表响应"""
    milestones: List[MilestoneResponse]
