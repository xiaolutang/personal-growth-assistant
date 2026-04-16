"""Goal 相关 Schema (DTO)"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# === 请求模型 ===

class GoalCreate(BaseModel):
    """创建目标请求"""
    title: str = Field(..., min_length=1, description="目标标题")
    description: Optional[str] = Field(None, description="目标描述")
    metric_type: Literal["count", "checklist", "tag_auto"] = Field(
        ..., description="衡量方式: count(手动计数)/checklist(检查清单)/tag_auto(基于tag自动追踪)"
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
