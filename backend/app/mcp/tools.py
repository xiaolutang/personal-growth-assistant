"""MCP Tool Schema 定义"""
from mcp.types import Tool

TOOLS: tuple[Tool, ...] = (
    Tool(
        name="list_entries",
        description="查询条目列表",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["project", "task", "note", "inbox"],
                    "description": "条目类型",
                },
                "status": {
                    "type": "string",
                    "enum": ["waitStart", "doing", "complete", "paused", "cancelled"],
                    "description": "条目状态",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "按标签筛选",
                },
                "parent_id": {
                    "type": "string",
                    "description": "按父项目ID筛选（获取子任务）",
                },
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "description": "返回数量限制",
                },
            },
        },
    ),
    Tool(
        name="get_entry",
        description="获取单个条目的完整内容",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "条目ID（文件名）",
                },
            },
            "required": ["id"],
        },
    ),
    Tool(
        name="create_entry",
        description="创建新条目",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["project", "task", "note", "inbox"],
                    "description": "条目类型",
                },
                "title": {
                    "type": "string",
                    "description": "标题",
                },
                "content": {
                    "type": "string",
                    "description": "内容",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "标签",
                },
                "parent_id": {
                    "type": "string",
                    "description": "父条目ID",
                },
                "status": {
                    "type": "string",
                    "enum": ["waitStart", "doing", "complete", "paused", "cancelled"],
                    "default": "waitStart",
                    "description": "状态",
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "default": "medium",
                    "description": "优先级",
                },
                "planned_date": {
                    "type": "string",
                    "description": "计划日期 (YYYY-MM-DD 格式)",
                },
                "time_spent": {
                    "type": "number",
                    "description": "耗时（分钟）",
                },
            },
            "required": ["type", "title", "content"],
        },
    ),
    Tool(
        name="update_entry",
        description="更新条目",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "条目ID",
                },
                "title": {
                    "type": "string",
                    "description": "新标题",
                },
                "content": {
                    "type": "string",
                    "description": "新内容",
                },
                "status": {
                    "type": "string",
                    "enum": ["waitStart", "doing", "complete", "paused", "cancelled"],
                    "description": "新状态",
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "新优先级",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "新标签",
                },
                "parent_id": {
                    "type": "string",
                    "description": "父条目ID",
                },
                "planned_date": {
                    "type": "string",
                    "description": "计划日期 (YYYY-MM-DD 格式)",
                },
                "time_spent": {
                    "type": "number",
                    "description": "耗时（分钟）",
                },
                "completed_at": {
                    "type": "string",
                    "description": "完成时间 (ISO 格式)",
                },
            },
            "required": ["id"],
        },
    ),
    Tool(
        name="delete_entry",
        description="删除条目",
        inputSchema={
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "条目ID",
                },
            },
            "required": ["id"],
        },
    ),
    Tool(
        name="search_entries",
        description="语义搜索条目",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询",
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "返回数量",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_knowledge_graph",
        description="获取某个概念的知识图谱",
        inputSchema={
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "概念名称",
                },
                "depth": {
                    "type": "integer",
                    "default": 2,
                    "description": "关系深度",
                },
            },
            "required": ["concept"],
        },
    ),
    Tool(
        name="get_related_concepts",
        description="获取相关概念",
        inputSchema={
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "概念名称",
                },
            },
            "required": ["concept"],
        },
    ),
    Tool(
        name="get_project_progress",
        description="获取项目进度，包括子任务统计和完成率",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "项目ID",
                },
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="get_review_summary",
        description="获取成长回顾统计（日报或周报）",
        inputSchema={
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["daily", "weekly"],
                    "default": "daily",
                    "description": "报告周期：daily（日报）或 weekly（周报）",
                },
                "target_date": {
                    "type": "string",
                    "description": "目标日期（YYYY-MM-DD 格式），不填则使用当天/本周",
                },
            },
        },
    ),
    Tool(
        name="get_knowledge_stats",
        description="获取知识概念统计数据，包括概念数量、关系数量、分类分布等",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
)
