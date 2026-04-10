"""MCP Tool Handler 实现"""
import uuid
from datetime import datetime
from typing import Optional

from mcp.types import TextContent

from app.models import Task, Category, TaskStatus, Priority
from app.services import SyncService
from app.infrastructure.storage.markdown import MarkdownStorage


# === 常量 ===
ENTRY_ID_LENGTH = 8
MAX_CHILD_TASKS = 1000
MAX_DISPLAY_TASKS = 10


def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """解析 ISO 格式日期字符串"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '').split('+')[0])
    except ValueError:
        return None


async def handle_list_entries(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 list_entries"""
    category = Category(args["type"]) if args.get("type") else None
    status = TaskStatus(args["status"]) if args.get("status") else None
    tags = args.get("tags")
    parent_id = args.get("parent_id")
    limit = args.get("limit", 10)

    # 优先使用 SQLite 索引（支持更多筛选）
    if storage.sqlite:
        entries = storage.sqlite.list_entries(
            type=category.value if category else None,
            status=status.value if status else None,
            tags=tags,
            parent_id=parent_id,
            limit=limit,
        )

        if not entries:
            return [TextContent(type="text", text="没有找到条目")]

        lines = ["# 条目列表\n"]
        for entry in entries:
            lines.append(f"\n## {entry.get('title', 'N/A')}\n")
            lines.append(f"- ID: {entry['id']}\n")
            lines.append(f"- 类型: {entry.get('type', 'N/A')}\n")
            lines.append(f"- 状态: {entry.get('status', 'N/A')}\n")
            lines.append(f"- 优先级: {entry.get('priority', 'medium')}\n")
            lines.append(f"- 标签: {', '.join(entry.get('tags', [])) or '无'}\n")
            lines.append(f"- 父项目: {entry.get('parent_id') or '无'}\n")
            lines.append(f"- 计划日期: {entry.get('planned_date') or '未设置'}\n")
            lines.append(f"- 更新时间: {entry.get('updated_at', 'N/A')}\n")

        return [TextContent(type="text", text="".join(lines))]

    # 回退到 Markdown 直接读取
    entries = storage.markdown.list_entries(
        category=category,
        status=status,
        limit=limit,
    )

    if not entries:
        return [TextContent(type="text", text="没有找到条目")]

    lines = ["# 条目列表\n"]
    for entry in entries:
        lines.append(f"\n## {entry.title}\n")
        lines.append(f"- ID: {entry.id}\n")
        lines.append(f"- 类型: {entry.category.value}\n")
        lines.append(f"- 状态: {entry.status.value}\n")
        lines.append(f"- 标签: {', '.join(entry.tags) or '无'}\n")
        lines.append(f"- 更新时间: {entry.updated_at.strftime('%Y-%m-%d %H:%M')}\n")

    return [TextContent(type="text", text="".join(lines))]


async def handle_get_entry(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 get_entry"""
    entry_id = args["id"]
    entry = storage.markdown.read_entry(entry_id)

    if not entry:
        return [TextContent(type="text", text=f"找不到条目: {entry_id}")]

    lines = [
        f"# {entry.title}\n\n",
        f"- ID: {entry.id}\n",
        f"- 类型: {entry.category.value}\n",
        f"- 状态: {entry.status.value}\n",
        f"- 优先级: {entry.priority.value if hasattr(entry, 'priority') and entry.priority else 'medium'}\n",
        f"- 标签: {', '.join(entry.tags) or '无'}\n",
        f"- 父项目: {entry.parent_id or '无'}\n",
        f"- 计划日期: {entry.planned_date.strftime('%Y-%m-%d') if entry.planned_date else '未设置'}\n",
        f"- 耗时: {f'{entry.time_spent}分钟' if entry.time_spent else '未记录'}\n",
        f"- 创建时间: {entry.created_at.strftime('%Y-%m-%d %H:%M')}\n",
        f"- 更新时间: {entry.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n",
        "---\n\n",
        entry.content,
    ]

    return [TextContent(type="text", text="".join(lines))]


async def handle_create_entry(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 create_entry"""
    entry_type = Category(args["type"])
    title = args["title"]
    content = args["content"]
    tags = args.get("tags", [])
    parent_id = args.get("parent_id")

    # 解析字段
    status = TaskStatus(args["status"]) if args.get("status") else TaskStatus.WAIT_START
    priority = Priority(args["priority"]) if args.get("priority") else Priority.MEDIUM
    planned_date = parse_iso_date(args.get("planned_date"))
    time_spent = args.get("time_spent")

    # 生成 ID
    entry_id = f"{entry_type.value}-{uuid.uuid4().hex[:ENTRY_ID_LENGTH]}"

    # 复用 MarkdownStorage 的目录映射
    dir_name = MarkdownStorage.CATEGORY_DIRS.get(entry_type, "notes")
    file_path = f"{dir_name}/{entry_id}.md" if dir_name else f"{entry_id}.md"

    # 创建条目
    entry = Task(
        id=entry_id,
        title=title,
        content=content,
        category=entry_type,
        status=status,
        priority=priority,
        tags=tags,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        parent_id=parent_id,
        file_path=file_path,
        planned_date=planned_date,
        time_spent=time_spent,
    )

    # 写入 Markdown
    storage.markdown.write_entry(entry)

    # 同步到 SQLite + Neo4j + Qdrant
    if storage.sqlite:
        storage.sqlite.upsert_entry(entry)
    await storage.sync_entry(entry)

    return [TextContent(
        type="text",
        text=f"已创建条目: {entry_id}\n标题: {title}\n类型: {entry_type.value}\n状态: {status.value}\n优先级: {priority.value}",
    )]


async def handle_update_entry(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 update_entry"""
    entry_id = args["id"]
    entry = storage.markdown.read_entry(entry_id)

    if not entry:
        return [TextContent(type="text", text=f"找不到条目: {entry_id}")]

    # 更新字段
    if "title" in args:
        entry.title = args["title"]
    if "content" in args:
        entry.content = args["content"]
    if "status" in args:
        entry.status = TaskStatus(args["status"])
    if "priority" in args:
        entry.priority = Priority(args["priority"])
    if "tags" in args:
        entry.tags = args["tags"]
    if "parent_id" in args:
        entry.parent_id = args["parent_id"]
    if "planned_date" in args:
        entry.planned_date = parse_iso_date(args["planned_date"])
    if "time_spent" in args:
        entry.time_spent = args["time_spent"]
    if "completed_at" in args:
        entry.completed_at = parse_iso_date(args["completed_at"])

    entry.updated_at = datetime.now()

    # 写入 Markdown
    storage.markdown.write_entry(entry)

    # 同步到 SQLite + Neo4j + Qdrant
    if storage.sqlite:
        storage.sqlite.upsert_entry(entry)
    await storage.sync_entry(entry)

    return [TextContent(type="text", text=f"已更新条目: {entry_id}")]


async def handle_delete_entry(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 delete_entry"""
    entry_id = args["id"]

    # 删除
    success = await storage.delete_entry(entry_id)

    if success:
        return [TextContent(type="text", text=f"已删除条目: {entry_id}")]
    else:
        return [TextContent(type="text", text=f"删除失败: {entry_id}")]


async def handle_search_entries(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 search_entries"""
    query = args["query"]
    limit = args.get("limit", 5)

    # 向量搜索
    results = await storage.qdrant.search(query, limit)

    if not results:
        return [TextContent(type="text", text="没有找到相关内容")]

    result = "# 搜索结果\n\n"
    for i, hit in enumerate(results, 1):
        payload = hit.payload
        result += f"## {i}. {payload['title']}\n"
        result += f"- ID: {hit.id}\n"
        result += f"- 类型: {payload['type']}\n"
        result += f"- 相似度: {hit.score:.2f}\n"
        result += f"- 标签: {', '.join(payload.get('tags', []))}\n\n"

    return [TextContent(type="text", text=result)]


async def handle_get_knowledge_graph(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 get_knowledge_graph"""
    concept = args["concept"]
    depth = args.get("depth", 2)

    graph = await storage.neo4j.get_knowledge_graph(concept, depth)

    if not graph["center"]:
        return [TextContent(type="text", text=f"找不到概念: {concept}")]

    result = f"# 知识图谱: {concept}\n\n"
    result += "## 相关节点\n\n"

    for conn in graph["connections"]:
        node = conn.get("node", {})
        if node:
            result += f"- {node.get('name', 'Unknown')} ({node.get('category', '')})\n"

    return [TextContent(type="text", text=result)]


async def handle_get_related_concepts(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 get_related_concepts"""
    concept = args["concept"]

    related = await storage.neo4j.get_related_concepts(concept)

    if not related:
        return [TextContent(type="text", text=f"没有找到相关概念: {concept}")]

    result = f"# 相关概念: {concept}\n\n"
    for c in related:
        result += f"- {c['name']} ({c.get('category', '')})\n"

    return [TextContent(type="text", text=result)]


async def handle_get_project_progress(storage: SyncService, args: dict) -> list[TextContent]:
    """处理 get_project_progress - 获取项目进度"""
    project_id = args["project_id"]

    # 检查项目是否存在
    entry = storage.markdown.read_entry(project_id)
    if not entry:
        return [TextContent(type="text", text=f"找不到条目: {project_id}")]

    # 使用 SQLite 获取子任务
    if not storage.sqlite:
        return [TextContent(type="text", text="SQLite 索引不可用，无法计算进度")]

    child_entries = storage.sqlite.list_entries(parent_id=project_id, limit=MAX_CHILD_TASKS)

    total = len(child_entries)
    if total == 0:
        return [TextContent(
            type="text",
            text=f"项目进度: {project_id}\n\n该项目下暂无子任务"
        )]

    # 统计各状态数量
    status_counts: dict[str, int] = {}
    completed = 0
    for child in child_entries:
        status = child.get("status", "doing")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == TaskStatus.COMPLETE.value:
            completed += 1

    progress = (completed / total) * 100 if total > 0 else 0

    lines = [
        f"# 项目进度: {entry.title}\n\n",
        f"- 项目ID: {project_id}\n",
        f"- 总任务数: {total}\n",
        f"- 已完成: {completed}\n",
        f"- 完成率: {round(progress, 1)}%\n\n",
        "## 状态分布\n\n",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}\n")
    lines.append("\n## 子任务列表\n\n")
    for child in child_entries[:MAX_DISPLAY_TASKS]:
        status_icon = "✅" if child.get("status") == TaskStatus.COMPLETE.value else "⏳"
        lines.append(f"- {status_icon} {child.get('title', 'N/A')} ({child.get('status', 'doing')})\n")
    if total > MAX_DISPLAY_TASKS:
        lines.append(f"\n... 还有 {total - MAX_DISPLAY_TASKS} 个任务")

    return [TextContent(type="text", text="".join(lines))]
