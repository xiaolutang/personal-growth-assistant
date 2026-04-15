"""MCP Tool Handler 实现"""
import uuid
from datetime import datetime, date
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


def _entry_belongs_to_user(entry, user_id: str) -> bool:
    """检查条目是否属于指定用户（SQLite dict 或 Task 对象）"""
    # Task 对象
    if hasattr(entry, "user_id"):
        return entry.user_id == user_id
    # SQLite dict
    if isinstance(entry, dict) and "user_id" in entry:
        return entry["user_id"] == user_id
    # 无法判断归属时允许访问（Markdown 回退场景）
    return True


async def handle_list_entries(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
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
            user_id=user_id,
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


async def handle_get_entry(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 get_entry"""
    entry_id = args["id"]
    entry = storage.markdown.read_entry(entry_id)

    if not entry:
        return [TextContent(type="text", text=f"找不到条目: {entry_id}")]

    # 用户隔离检查：SQLite 中验证归属
    if storage.sqlite:
        db_entry = storage.sqlite.get_entry(entry_id)
        if db_entry and db_entry.get("user_id") and db_entry["user_id"] != user_id:
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


async def handle_create_entry(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
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

    # 同步到 SQLite + Neo4j + Qdrant（传递 user_id 进行隔离）
    if storage.sqlite:
        storage.sqlite.upsert_entry(entry, user_id=user_id)
    await storage.sync_entry(entry)

    return [TextContent(
        type="text",
        text=f"已创建条目: {entry_id}\n标题: {title}\n类型: {entry_type.value}\n状态: {status.value}\n优先级: {priority.value}",
    )]


async def handle_update_entry(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 update_entry"""
    entry_id = args["id"]

    # 用户隔离检查
    if storage.sqlite:
        db_entry = storage.sqlite.get_entry(entry_id)
        if db_entry and db_entry.get("user_id") and db_entry["user_id"] != user_id:
            return [TextContent(type="text", text=f"找不到条目: {entry_id}")]

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
        storage.sqlite.upsert_entry(entry, user_id=user_id)
    await storage.sync_entry(entry)

    return [TextContent(type="text", text=f"已更新条目: {entry_id}")]


async def handle_delete_entry(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 delete_entry"""
    entry_id = args["id"]

    # 用户隔离检查
    if storage.sqlite:
        db_entry = storage.sqlite.get_entry(entry_id)
        if db_entry and db_entry.get("user_id") and db_entry["user_id"] != user_id:
            return [TextContent(type="text", text=f"删除失败: {entry_id}")]

    # 删除
    success = await storage.delete_entry(entry_id)

    if success:
        return [TextContent(type="text", text=f"已删除条目: {entry_id}")]
    else:
        return [TextContent(type="text", text=f"删除失败: {entry_id}")]


async def handle_search_entries(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
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


async def handle_get_knowledge_graph(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 get_knowledge_graph"""
    concept = args["concept"]
    depth = args.get("depth", 2)

    graph = await storage.neo4j.get_knowledge_graph(concept, depth, user_id=user_id)

    if not graph["center"]:
        return [TextContent(type="text", text=f"找不到概念: {concept}")]

    result = f"# 知识图谱: {concept}\n\n"
    result += "## 相关节点\n\n"

    for conn in graph["connections"]:
        node = conn.get("node", {})
        if node:
            result += f"- {node.get('name', 'Unknown')} ({node.get('category', '')})\n"

    return [TextContent(type="text", text=result)]


async def handle_get_related_concepts(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 get_related_concepts"""
    concept = args["concept"]

    related = await storage.neo4j.get_related_concepts(concept, user_id=user_id)

    if not related:
        return [TextContent(type="text", text=f"没有找到相关概念: {concept}")]

    result = f"# 相关概念: {concept}\n\n"
    for c in related:
        result += f"- {c['name']} ({c.get('category', '')})\n"

    return [TextContent(type="text", text=result)]


async def handle_get_project_progress(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 get_project_progress - 获取项目进度"""
    project_id = args["project_id"]

    # 检查项目是否存在
    entry = storage.markdown.read_entry(project_id)
    if not entry:
        return [TextContent(type="text", text=f"找不到条目: {project_id}")]

    # 用户隔离检查
    if storage.sqlite:
        db_entry = storage.sqlite.get_entry(project_id)
        if db_entry and db_entry.get("user_id") and db_entry["user_id"] != user_id:
            return [TextContent(type="text", text=f"找不到条目: {project_id}")]

    # 使用 SQLite 获取子任务
    if not storage.sqlite:
        return [TextContent(type="text", text="SQLite 索引不可用，无法计算进度")]

    child_entries = storage.sqlite.list_entries(parent_id=project_id, limit=MAX_CHILD_TASKS, user_id=user_id)

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
        child_status = child.get("status", "doing")
        status_counts[child_status] = status_counts.get(child_status, 0) + 1
        if child_status == TaskStatus.COMPLETE.value:
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
    for s, count in sorted(status_counts.items()):
        lines.append(f"- {s}: {count}\n")
    lines.append("\n## 子任务列表\n\n")
    for child in child_entries[:MAX_DISPLAY_TASKS]:
        status_icon = "done" if child.get("status") == TaskStatus.COMPLETE.value else "doing"
        lines.append(f"- [{status_icon}] {child.get('title', 'N/A')} ({child.get('status', 'doing')})\n")
    if total > MAX_DISPLAY_TASKS:
        lines.append(f"\n... 还有 {total - MAX_DISPLAY_TASKS} 个任务")

    return [TextContent(type="text", text="".join(lines))]


async def handle_get_review_summary(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 get_review_summary — 获取回顾统计（日报或周报）"""
    from app.services.review_service import ReviewService

    period = args.get("period", "daily")
    target_date_str = args.get("target_date")

    if not storage.sqlite:
        return [TextContent(type="text", text="SQLite 索引不可用，无法生成回顾")]

    review_svc = ReviewService(sqlite_storage=storage.sqlite)

    if period == "weekly":
        target = ReviewService.parse_date(target_date_str) if target_date_str else None
        report = review_svc.get_weekly_report(week_start=target, user_id=user_id)
        lines = [
            f"# 周报: {report.start_date} ~ {report.end_date}\n\n",
            f"## 任务统计\n",
            f"- 总任务数: {report.task_stats.total}\n",
            f"- 已完成: {report.task_stats.completed}\n",
            f"- 进行中: {report.task_stats.doing}\n",
            f"- 待开始: {report.task_stats.wait_start}\n",
            f"- 完成率: {report.task_stats.completion_rate}%\n\n",
            f"## 笔记统计\n",
            f"- 笔记总数: {report.note_stats.total}\n",
        ]
        if report.ai_summary:
            lines.append(f"\n## AI 总结\n\n{report.ai_summary}\n")
        return [TextContent(type="text", text="".join(lines))]
    else:
        target = ReviewService.parse_date(target_date_str) if target_date_str else None
        report = review_svc.get_daily_report(target_date=target, user_id=user_id)
        lines = [
            f"# 日报: {report.date}\n\n",
            f"## 任务统计\n",
            f"- 总任务数: {report.task_stats.total}\n",
            f"- 已完成: {report.task_stats.completed}\n",
            f"- 进行中: {report.task_stats.doing}\n",
            f"- 待开始: {report.task_stats.wait_start}\n",
            f"- 完成率: {report.task_stats.completion_rate}%\n\n",
            f"## 笔记统计\n",
            f"- 笔记总数: {report.note_stats.total}\n",
        ]
        if report.ai_summary:
            lines.append(f"\n## AI 总结\n\n{report.ai_summary}\n")
        return [TextContent(type="text", text="".join(lines))]


async def handle_get_knowledge_stats(storage: SyncService, args: dict, user_id: str) -> list[TextContent]:
    """处理 get_knowledge_stats — 获取知识概念统计"""
    from app.services.knowledge_service import KnowledgeService

    svc = KnowledgeService(
        neo4j_client=storage.neo4j if storage.neo4j else None,
        sqlite_storage=storage.sqlite if storage.sqlite else None,
    )

    stats = await svc.get_knowledge_stats(user_id=user_id)

    lines = [
        "# 知识概念统计\n\n",
        f"- 概念总数: {stats.concept_count}\n",
        f"- 关系总数: {stats.relation_count}\n\n",
    ]
    if stats.category_distribution:
        lines.append("## 分类分布\n\n")
        for cat, count in sorted(stats.category_distribution.items()):
            lines.append(f"- {cat}: {count}\n")
    if stats.top_concepts:
        lines.append("\n## 热门概念\n\n")
        for c in stats.top_concepts[:10]:
            lines.append(f"- {c.get('name', '')} ({c.get('entry_count', 0)} 条目)\n")

    return [TextContent(type="text", text="".join(lines))]
