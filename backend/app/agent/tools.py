"""Agent Tool 函数实现

7 个 tool 封装现有 service 调用，通过依赖注入接收 service 实例。
所有 tool 的 error handling 包装为结构化 ToolResult，不向上抛异常。

调用方向: Tools -> Services -> Infrastructure（严格单向）
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool

from app.agent.schemas import (
    CreateEntryInput,
    CreateEntryOutput,
    UpdateEntryInput,
    UpdateEntryOutput,
    DeleteEntryInput,
    DeleteEntryOutput,
    SearchEntriesInput,
    SearchEntriesOutput,
    GetEntryInput,
    GetEntryOutput,
    GetReviewSummaryInput,
    GetReviewSummaryOutput,
    AskUserInput,
    AskUserOutput,
    ToolResult,
)

logger = logging.getLogger(__name__)


# === Tool 依赖注入容器 ===

class ToolDependencies:
    """Tool 依赖容器，通过 setter 注入 service 实例。

    使用方式:
        deps = ToolDependencies()
        deps.set_entry_service(entry_service)
        deps.set_review_service(review_service)
    """

    def __init__(self):
        self._entry_service = None
        self._review_service = None

    def set_entry_service(self, entry_service) -> None:
        """注入 EntryService 实例"""
        self._entry_service = entry_service

    def set_review_service(self, review_service) -> None:
        """注入 ReviewService 实例"""
        self._review_service = review_service

    @property
    def entry_service(self):
        """获取 EntryService 实例"""
        return self._entry_service

    @property
    def review_service(self):
        """获取 ReviewService 实例"""
        return self._review_service


# === Tool 实现函数 ===

async def _create_entry(
    category: str,
    title: str,
    content: str = "",
    tags: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    planned_date: Optional[str] = None,
    time_spent: Optional[int] = None,
    *,
    dependencies: ToolDependencies,
    user_id: str = "_default",
) -> Dict[str, Any]:
    """创建条目，封装 entry_service.create_entry()。

    Args:
        category: 条目分类 (project/task/note/inbox/decision/reflection/question)
        title: 标题
        content: 内容
        tags: 标签列表
        parent_id: 父条目ID
        status: 状态
        priority: 优先级
        planned_date: 计划日期
        time_spent: 耗时（分钟）
        dependencies: 依赖容器
        user_id: 用户ID

    Returns:
        ToolResult 包装的 CreateEntryOutput 字典
    """
    try:
        from app.api.schemas import EntryCreate

        if tags is None:
            tags = []

        request = EntryCreate(
            category=category,
            title=title,
            content=content,
            tags=tags,
            parent_id=parent_id,
            status=status,
            priority=priority,
            planned_date=planned_date,
            time_spent=time_spent,
        )

        entry_service = dependencies.entry_service
        if entry_service is None:
            return ToolResult(success=False, error="EntryService 未初始化").model_dump()

        result = await entry_service.create_entry(request, user_id=user_id)

        if result is None:
            return ToolResult(success=False, error="创建条目失败: service 返回 None").model_dump()

        output = CreateEntryOutput(
            id=result.id,
            title=result.title,
            category=result.category,
            status=result.status,
        )
        return ToolResult(success=True, data=output.model_dump()).model_dump()

    except Exception as e:
        logger.error("create_entry tool 异常: %s", e, exc_info=True)
        return ToolResult(success=False, error=f"创建条目失败: {str(e)}").model_dump()


async def _update_entry(
    entry_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    planned_date: Optional[str] = None,
    time_spent: Optional[int] = None,
    completed_at: Optional[str] = None,
    *,
    dependencies: ToolDependencies,
    user_id: str = "_default",
) -> Dict[str, Any]:
    """更新条目，封装 entry_service.update_entry()。

    Args:
        entry_id: 条目ID
        title: 新标题
        content: 新内容
        category: 新分类
        status: 新状态
        priority: 新优先级
        tags: 新标签
        parent_id: 父条目ID
        planned_date: 计划日期
        time_spent: 耗时（分钟）
        completed_at: 完成时间
        dependencies: 依赖容器
        user_id: 用户ID

    Returns:
        ToolResult 包装的 UpdateEntryOutput 字典
    """
    try:
        from app.api.schemas import EntryUpdate

        request = EntryUpdate(
            title=title,
            content=content,
            category=category,
            status=status,
            priority=priority,
            tags=tags,
            parent_id=parent_id,
            planned_date=planned_date,
            time_spent=time_spent,
            completed_at=completed_at,
        )

        entry_service = dependencies.entry_service
        if entry_service is None:
            return ToolResult(success=False, error="EntryService 未初始化").model_dump()

        success, message = await entry_service.update_entry(entry_id, request, user_id=user_id)

        output = UpdateEntryOutput(
            entry_id=entry_id,
            message=message,
        )
        return ToolResult(success=success, data=output.model_dump()).model_dump()

    except Exception as e:
        logger.error("update_entry tool 异常: %s", e, exc_info=True)
        return ToolResult(success=False, error=f"更新条目失败: {str(e)}").model_dump()


async def _delete_entry(
    entry_id: str,
    *,
    dependencies: ToolDependencies,
    user_id: str = "_default",
) -> Dict[str, Any]:
    """删除条目，封装 entry_service.delete_entry()。

    Args:
        entry_id: 条目ID
        dependencies: 依赖容器
        user_id: 用户ID

    Returns:
        ToolResult 包装的 DeleteEntryOutput 字典
    """
    try:
        entry_service = dependencies.entry_service
        if entry_service is None:
            return ToolResult(success=False, error="EntryService 未初始化").model_dump()

        success, message = await entry_service.delete_entry(entry_id, user_id=user_id)

        output = DeleteEntryOutput(
            entry_id=entry_id,
            message=message,
        )
        return ToolResult(success=success, data=output.model_dump()).model_dump()

    except Exception as e:
        logger.error("delete_entry tool 异常: %s", e, exc_info=True)
        return ToolResult(success=False, error=f"删除条目失败: {str(e)}").model_dump()


async def _search_entries(
    query: str,
    limit: int = 10,
    *,
    dependencies: ToolDependencies,
    user_id: str = "_default",
) -> Dict[str, Any]:
    """搜索条目，封装 entry_service.search_entries()。

    Args:
        query: 搜索关键词
        limit: 返回数量限制
        dependencies: 依赖容器
        user_id: 用户ID

    Returns:
        ToolResult 包装的 SearchEntriesOutput 字典
    """
    try:
        entry_service = dependencies.entry_service
        if entry_service is None:
            return ToolResult(success=False, error="EntryService 未初始化").model_dump()

        result = await entry_service.search_entries(query, limit=limit, user_id=user_id)

        entries_data = []
        if result and result.entries:
            for entry in result.entries:
                entries_data.append(entry.model_dump() if hasattr(entry, "model_dump") else entry)

        output = SearchEntriesOutput(
            entries=entries_data,
            query=query,
            total=len(entries_data),
        )
        return ToolResult(success=True, data=output.model_dump()).model_dump()

    except Exception as e:
        logger.error("search_entries tool 异常: %s", e, exc_info=True)
        return ToolResult(success=False, error=f"搜索条目失败: {str(e)}").model_dump()


async def _get_entry(
    entry_id: str,
    *,
    dependencies: ToolDependencies,
    user_id: str = "_default",
) -> Dict[str, Any]:
    """获取单个条目，封装 entry_service.get_entry()。

    Args:
        entry_id: 条目ID
        dependencies: 依赖容器
        user_id: 用户ID

    Returns:
        ToolResult 包装的 GetEntryOutput 字典
    """
    try:
        entry_service = dependencies.entry_service
        if entry_service is None:
            return ToolResult(success=False, error="EntryService 未初始化").model_dump()

        result = await entry_service.get_entry(entry_id, user_id=user_id)

        if result is None:
            return ToolResult(success=False, error=f"条目不存在: {entry_id}").model_dump()

        output = GetEntryOutput(
            id=result.id,
            title=result.title,
            content=result.content,
            category=result.category,
            status=result.status,
            priority=result.priority,
            tags=result.tags,
            created_at=result.created_at,
            updated_at=result.updated_at,
            planned_date=result.planned_date,
            completed_at=result.completed_at,
            time_spent=result.time_spent,
            parent_id=result.parent_id,
        )
        return ToolResult(success=True, data=output.model_dump()).model_dump()

    except Exception as e:
        logger.error("get_entry tool 异常: %s", e, exc_info=True)
        return ToolResult(success=False, error=f"获取条目失败: {str(e)}").model_dump()


async def _get_review_summary(
    period: str = "daily",
    target_date: Optional[str] = None,
    *,
    dependencies: ToolDependencies,
    user_id: str = "_default",
) -> Dict[str, Any]:
    """获取成长回顾统计，封装 review_service 的日报/周报方法。

    Args:
        period: 报告周期 (daily/weekly)
        target_date: 目标日期 (YYYY-MM-DD)
        dependencies: 依赖容器
        user_id: 用户ID

    Returns:
        ToolResult 包装的 GetReviewSummaryOutput 字典
    """
    try:
        from datetime import date as date_type

        review_service = dependencies.review_service
        if review_service is None:
            return ToolResult(success=False, error="ReviewService 未初始化").model_dump()

        # 解析日期
        parsed_date = None
        if target_date:
            parsed_date = date_type.fromisoformat(target_date)

        if period == "weekly":
            report = await review_service.get_weekly_report(
                week_start=parsed_date, user_id=user_id
            )
            output = GetReviewSummaryOutput(
                period="weekly",
                date_range=f"{report.start_date} ~ {report.end_date}",
                task_stats={
                    "total": report.task_stats.total,
                    "completed": report.task_stats.completed,
                    "doing": report.task_stats.doing,
                    "wait_start": report.task_stats.wait_start,
                    "completion_rate": report.task_stats.completion_rate,
                },
                note_stats={"total": report.note_stats.total},
                ai_summary=report.ai_summary,
            )
        else:
            report = await review_service.get_daily_report(
                target_date=parsed_date, user_id=user_id
            )
            output = GetReviewSummaryOutput(
                period="daily",
                date_range=report.date,
                task_stats={
                    "total": report.task_stats.total,
                    "completed": report.task_stats.completed,
                    "doing": report.task_stats.doing,
                    "wait_start": report.task_stats.wait_start,
                    "completion_rate": report.task_stats.completion_rate,
                },
                note_stats={"total": report.note_stats.total},
                ai_summary=report.ai_summary,
            )

        return ToolResult(success=True, data=output.model_dump()).model_dump()

    except Exception as e:
        logger.error("get_review_summary tool 异常: %s", e, exc_info=True)
        return ToolResult(success=False, error=f"获取回顾统计失败: {str(e)}").model_dump()


async def _ask_user(
    question: str,
    *,
    dependencies: ToolDependencies,
    user_id: str = "_default",
) -> Dict[str, Any]:
    """向用户提问，返回 {type:'ask', question:'...'} 结构。

    返回后触发 ReAct 图条件边路由到 END，中断 Agent 循环。
    Agent 在下一次被用户回复唤醒时，会收到用户的回答。

    Args:
        question: 向用户提出的问题
        dependencies: 依赖容器
        user_id: 用户ID

    Returns:
        AskUserOutput 字典 {type: 'ask', question: '...'}
    """
    try:
        output = AskUserOutput(question=question)
        return output.model_dump()
    except Exception as e:
        logger.error("ask_user tool 异常: %s", e, exc_info=True)
        return ToolResult(success=False, error=f"向用户提问失败: {str(e)}").model_dump()


# === StructuredTool 定义 ===
# 使用 LangChain StructuredTool 包装，支持 LangGraph ReAct Agent 集成。
# 注意：StructuredTool 通过 args_schema 做参数校验。
# dependencies 和 user_id 通过 tool 的 coroutine_kwargs 注入。

create_entry_tool = StructuredTool.from_function(
    coroutine=_create_entry,
    name="create_entry",
    description=(
        "创建新条目（任务/笔记/灵感/项目等）。"
        "需要提供 category（分类）和 title（标题），其他字段可选。"
    ),
    args_schema=CreateEntryInput,
)

update_entry_tool = StructuredTool.from_function(
    coroutine=_update_entry,
    name="update_entry",
    description=(
        "更新已有条目。需要提供 entry_id，"
        "其余字段仅传需要修改的。"
    ),
    args_schema=UpdateEntryInput,
)

delete_entry_tool = StructuredTool.from_function(
    coroutine=_delete_entry,
    name="delete_entry",
    description="删除条目。需要提供 entry_id。",
    args_schema=DeleteEntryInput,
)

search_entries_tool = StructuredTool.from_function(
    coroutine=_search_entries,
    name="search_entries",
    description="语义搜索条目。需要提供搜索关键词 query。",
    args_schema=SearchEntriesInput,
)

get_entry_tool = StructuredTool.from_function(
    coroutine=_get_entry,
    name="get_entry",
    description="获取单个条目的完整内容。需要提供 entry_id。",
    args_schema=GetEntryInput,
)

get_review_summary_tool = StructuredTool.from_function(
    coroutine=_get_review_summary,
    name="get_review_summary",
    description=(
        "获取成长回顾统计（日报或周报）。"
        "可选 period（daily/weekly）和 target_date。"
    ),
    args_schema=GetReviewSummaryInput,
)

ask_user_tool = StructuredTool.from_function(
    coroutine=_ask_user,
    name="ask_user",
    description=(
        "向用户提问。当 Agent 需要用户确认或补充信息时使用。"
        "调用后 Agent 循环会中断，等待用户回复后继续。"
        "需要提供 question 参数。"
    ),
    args_schema=AskUserInput,
)


# === Tool 注册表 ===

AGENT_TOOLS: List[StructuredTool] = [
    create_entry_tool,
    update_entry_tool,
    delete_entry_tool,
    search_entries_tool,
    get_entry_tool,
    get_review_summary_tool,
    ask_user_tool,
]

AGENT_TOOL_NAMES: set[str] = {t.name for t in AGENT_TOOLS}
