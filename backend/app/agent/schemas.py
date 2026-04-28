"""Agent Tools 的 Pydantic Input/Output Schema 定义

每个 tool 都有独立的 Input 和 Output schema，与现有 models 保持一致的命名风格。
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# === 通用 ===

class ToolResult(BaseModel):
    """Tool 执行结果的通用包装。

    所有 tool 返回都通过此结构包装，确保错误不向上抛异常。
    success=True 时 data 有值，success=False 时 error 有值。
    """
    success: bool = Field(..., description="执行是否成功")
    data: Optional[Any] = Field(None, description="成功时的返回数据")
    error: Optional[str] = Field(None, description="失败时的错误信息")


# === create_entry ===

class CreateEntryInput(BaseModel):
    """创建条目输入"""
    category: str = Field(
        ...,
        description="条目分类: project/task/note/inbox/decision/reflection/question",
    )
    title: str = Field(..., min_length=1, description="标题")
    content: str = Field(default="", description="内容")
    tags: List[str] = Field(default_factory=list, description="标签")
    parent_id: Optional[str] = Field(None, description="父条目ID")
    status: Optional[str] = Field(None, description="状态: waitStart/doing/complete/paused/cancelled")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")
    planned_date: Optional[str] = Field(None, description="计划日期 (YYYY-MM-DD)")
    time_spent: Optional[int] = Field(None, description="耗时（分钟）")


class CreateEntryOutput(BaseModel):
    """创建条目输出"""
    id: str = Field(..., description="创建的条目ID")
    title: str = Field(..., description="标题")
    category: str = Field(..., description="分类")
    status: str = Field(..., description="状态")


# === update_entry ===

class UpdateEntryInput(BaseModel):
    """更新条目输入"""
    entry_id: str = Field(..., min_length=1, description="条目ID")
    title: Optional[str] = Field(None, description="新标题")
    content: Optional[str] = Field(None, description="新内容")
    category: Optional[str] = Field(None, description="新分类")
    status: Optional[str] = Field(None, description="新状态")
    priority: Optional[str] = Field(None, description="新优先级")
    tags: Optional[List[str]] = Field(None, description="新标签")
    parent_id: Optional[str] = Field(None, description="父条目ID")
    planned_date: Optional[str] = Field(None, description="计划日期 (YYYY-MM-DD)")
    time_spent: Optional[int] = Field(None, description="耗时（分钟）")
    completed_at: Optional[str] = Field(None, description="完成时间 (ISO 格式)")


class UpdateEntryOutput(BaseModel):
    """更新条目输出"""
    entry_id: str = Field(..., description="更新的条目ID")
    message: str = Field(..., description="操作结果消息")


# === delete_entry ===

class DeleteEntryInput(BaseModel):
    """删除条目输入"""
    entry_id: str = Field(..., min_length=1, description="条目ID")


class DeleteEntryOutput(BaseModel):
    """删除条目输出"""
    entry_id: str = Field(..., description="删除的条目ID")
    message: str = Field(..., description="操作结果消息")


# === search_entries ===

class SearchEntriesInput(BaseModel):
    """搜索条目输入"""
    query: str = Field(..., min_length=1, description="搜索关键词")
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制")


class SearchEntriesOutput(BaseModel):
    """搜索条目输出"""
    entries: List[Dict[str, Any]] = Field(default_factory=list, description="搜索结果列表")
    query: str = Field(..., description="搜索关键词")
    total: int = Field(default=0, description="结果总数")


# === get_entry ===

class GetEntryInput(BaseModel):
    """获取条目输入"""
    entry_id: str = Field(..., min_length=1, description="条目ID")


class GetEntryOutput(BaseModel):
    """获取条目输出"""
    id: str = Field(..., description="条目ID")
    title: str = Field(..., description="标题")
    content: str = Field(default="", description="内容")
    category: str = Field(..., description="分类")
    status: str = Field(..., description="状态")
    priority: str = Field(default="medium", description="优先级")
    tags: List[str] = Field(default_factory=list, description="标签")
    created_at: str = Field(default="", description="创建时间")
    updated_at: str = Field(default="", description="更新时间")
    planned_date: Optional[str] = Field(None, description="计划日期")
    completed_at: Optional[str] = Field(None, description="完成时间")
    time_spent: Optional[int] = Field(None, description="耗时（分钟）")
    parent_id: Optional[str] = Field(None, description="父条目ID")


# === get_review_summary ===

class GetReviewSummaryInput(BaseModel):
    """获取成长回顾统计输入"""
    period: Literal["daily", "weekly"] = Field(
        default="daily",
        description="报告周期: daily（日报）或 weekly（周报）",
    )
    target_date: Optional[str] = Field(
        None,
        description="目标日期 (YYYY-MM-DD)，不填则使用当天/本周",
    )


class GetReviewSummaryOutput(BaseModel):
    """获取成长回顾统计输出"""
    period: str = Field(..., description="报告周期")
    date_range: str = Field(..., description="日期范围")
    task_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="任务统计: total/completed/doing/wait_start/completion_rate",
    )
    note_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="笔记统计: total",
    )
    ai_summary: Optional[str] = Field(None, description="AI 总结")


# === ask_user ===

class AskUserInput(BaseModel):
    """向用户提问输入

    返回 {type:'ask', question:'...'} 结构后，
    ReAct 图条件边将路由到 END，中断 Agent 循环。
    """
    question: str = Field(..., min_length=1, description="向用户提出的问题")


class AskUserOutput(BaseModel):
    """向用户提问输出

    固定返回 {type:'ask', question:'...'} 结构，
    触发 ReAct 图条件边路由到 END，中断 Agent 循环。
    """
    type: Literal["ask"] = Field(default="ask", description="类型标识，固定为 'ask'")
    question: str = Field(..., description="向用户提出的问题")
