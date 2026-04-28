"""Agent Tools 模块

为 LangGraph ReAct Agent 提供 7 个工具函数，封装现有 service 层调用。

Tools:
    - create_entry: 创建条目
    - update_entry: 更新条目
    - delete_entry: 删除条目
    - search_entries: 语义搜索条目
    - get_entry: 获取单个条目
    - get_review_summary: 获取成长回顾统计
    - ask_user: 向用户提问（中断 Agent 循环）

调用方向: Tools -> Services -> Infrastructure（严格单向）
"""

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
from app.agent.tools import (
    create_entry_tool,
    update_entry_tool,
    delete_entry_tool,
    search_entries_tool,
    get_entry_tool,
    get_review_summary_tool,
    ask_user_tool,
    AGENT_TOOLS,
)

__all__ = [
    # Schemas
    "CreateEntryInput",
    "CreateEntryOutput",
    "UpdateEntryInput",
    "UpdateEntryOutput",
    "DeleteEntryInput",
    "DeleteEntryOutput",
    "SearchEntriesInput",
    "SearchEntriesOutput",
    "GetEntryInput",
    "GetEntryOutput",
    "GetReviewSummaryInput",
    "GetReviewSummaryOutput",
    "AskUserInput",
    "AskUserOutput",
    "ToolResult",
    # Tools
    "create_entry_tool",
    "update_entry_tool",
    "delete_entry_tool",
    "search_entries_tool",
    "get_entry_tool",
    "get_review_summary_tool",
    "ask_user_tool",
    "AGENT_TOOLS",
]
