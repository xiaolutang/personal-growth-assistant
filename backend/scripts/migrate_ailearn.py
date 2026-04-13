"""
迁移 aiLearn 数据到 personal-growth-assistant

从 aiLearn 的 projects.md / todo.md / inbox.md / notes.md 中提取数据，
按确认的映射表创建条目（markdown 文件 + SQLite 索引）。

Usage:
    cd /Users/tangxiaolu/project/personal-growth-assistant/backend
    uv run python scripts/migrate_ailearn.py --dry-run   # 预览，不写入
    uv run python scripts/migrate_ailearn.py              # 执行迁移
"""

import argparse
import re
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

# ============================================================
# 路径配置
# ============================================================
AILEARN_DIR = Path("/Users/tangxiaolu/project/aiLearn")
PROJECT_DIR = Path("/Users/tangxiaolu/project/personal-growth-assistant")
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "index.db"

# ============================================================
# 工具函数
# ============================================================

def gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_source(name: str) -> str:
    return (AILEARN_DIR / name).read_text(encoding="utf-8")


def extract_section(text: str, start_heading: str, stop_headings: list[str] | None = None) -> str:
    """从 markdown 中提取从 start_heading 开始到同级/更高级标题为止的内容。"""
    lines = text.split("\n")
    result = []
    started = False
    start_level = 0

    for line in lines:
        m = re.match(r"^(#{1,6})\s", line)
        if m:
            level = len(m.group(1))
            if not started:
                if line.strip().startswith(start_heading) or start_heading in line:
                    started = True
                    start_level = level
                    result.append(line)
                    continue
            else:
                # 同级或更高级标题 = 结束
                if level <= start_level:
                    # 检查是否是 stop_headings 中的
                    if stop_headings and any(sh in line for sh in stop_headings):
                        break
                    # 否则继续收集（子标题）
                    if level < start_level:
                        break
                    result.append(line)
                    continue
        if started:
            result.append(line)

    return "\n".join(result).strip()


def extract_dated_sections(text: str) -> list[dict]:
    """提取 markdown 中按日期分段的条目（## 2026-03-04 标题 格式）。"""
    sections = []
    lines = text.split("\n")
    current_date = None
    current_title = None
    current_lines: list[str] = []

    for line in lines:
        m = re.match(r"^##\s+(\d{4}-\d{2}-\d{2})\s*(.*)", line)
        if m:
            if current_date and current_lines:
                sections.append({
                    "date": current_date,
                    "title": current_title or "",
                    "content": "\n".join(current_lines).strip(),
                })
            current_date = m.group(1)
            # 提取标题（去掉标签标记）
            current_title = re.sub(r"\s*#\S+(?:\s*#\S+)*$", "", m.group(2)).strip()
            current_lines = []
        elif current_date:
            current_lines.append(line)

    if current_date and current_lines:
        sections.append({
            "date": current_date,
            "title": current_title or "",
            "content": "\n".join(current_lines).strip(),
        })

    return sections


def split_inbox_items(section_text: str) -> list[dict]:
    """将一个日期段内的多个 inbox 条目拆分出来（以 - **粗体** 或 - 普通文字开头）。"""
    items = []
    # 匹配 "- **标题**" 或 "- 普通标题（非 --- 分隔线）"
    pattern = re.compile(r"^- (?:\*\*(.+?)\*\*|([^-\n][^\n]*?))\s*$", re.MULTILINE)
    matches = list(pattern.finditer(section_text))

    if not matches:
        return [{"title": section_text.strip().split("\n")[0][:50], "content": section_text.strip()}]

    for i, m in enumerate(matches):
        title = (m.group(1) or m.group(2) or "").strip()
        if not title or title == "-" * len(title):  # 跳过分隔线
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        content = section_text[start:end].strip()
        items.append({"title": title, "content": content})

    return items if items else [{"title": section_text.strip()[:50], "content": section_text.strip()}]


def extract_note_title(section_text: str, fallback_title: str = "") -> str:
    """从笔记内容中提取第一个有意义的标题，优先使用 fallback（来自日期标题行）。"""
    # 如果 fallback 标题足够好，直接用
    if fallback_title and len(fallback_title) > 5:
        return fallback_title

    lines = section_text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 优先取 ### 或 ## 标题
        m = re.match(r"^#{1,4}\s+(.+)", line)
        if m:
            title = m.group(1).strip()
            title = re.sub(r"\s*#\S+(?:\s*#\S+)*$", "", title).strip()
            if title and len(title) > 3:
                return title
        # 取粗体文字
        m = re.match(r"^\*\*(.+?)\*\*", line)
        if m:
            title = m.group(1).strip()
            if title and len(title) > 3:
                return title
    return lines[0][:50].strip() if lines else "未命名笔记"


# ============================================================
# 迁移数据定义
# ============================================================

# -- 项目 (Projects) --
PROJECTS_DEF = [
    {
        "title": "AI 应用开发转型",
        "status": "doing",
        "priority": "high",
        "tags": ["AI", "转型", "学习计划"],
        "content_source": "projects.md",  # 整个文件作为计划文档
        "content_extract": "full",  # full = 整个文件内容
    },
    {
        "title": "个人成长助手开发",
        "status": "doing",
        "priority": "high",
        "tags": ["个人成长助手", "产品", "开发"],
        "content_source": "inbox.md",
        # 从 inbox 中提取产品规划相关内容合并
        "content_inbox_ids": ["I5", "I9", "I11"],
        "content_extra": "projects.md",  # 从 projects.md 提取助手相关章节
        "content_extra_section": "项目一：个人成长助手",
    },
    {
        "title": "自媒体运营",
        "status": "waitStart",
        "priority": "medium",
        "tags": ["自媒体", "抖音", "掘金", "小红书"],
        "content_source": "inbox.md",
        "content_inbox_ids": ["I19"],
    },
    {
        "title": "教学辅助系统",
        "status": "waitStart",
        "priority": "low",
        "tags": ["教育", "教学", "AI应用"],
        "content_source": "inbox.md",
        "content_inbox_ids": ["I18"],
    },
]

# -- 任务 (Tasks) --
TASKS_DEF = [
    {
        "title": "XLFoundry 文章分享（掘金+抖音）",
        "status": "doing",
        "priority": "high",
        "tags": ["自媒体", "掘金"],
        "project_index": 2,  # P3 自媒体运营
        "source": "todo.md",
        "source_pattern": r"文章分享.*?XLFoundry",
    },
    {
        "title": "学习 Claude Code Subagent",
        "status": "waitStart",
        "priority": "medium",
        "tags": ["Claude Code", "学习"],
        "project_index": 0,  # P1 AI转型
        "source": "todo.md",
        "source_pattern": r"学习 Claude Code Subagent",
    },
    {
        "title": "聊天乱发信息 Bug",
        "status": "doing",
        "priority": "high",
        "tags": ["个人助手", "Bug"],
        "project_index": 1,  # P2 助手开发
        "source": "todo.md",
        "source_pattern": r"聊天乱发信息 Bug",
    },
    {
        "title": "日志系统",
        "status": "waitStart",
        "priority": "medium",
        "tags": ["个人助手", "日志"],
        "project_index": 1,
        "source": "todo.md",
        "source_pattern": r"日志系统",
    },
    {
        "title": "左侧对话记录列表",
        "status": "waitStart",
        "priority": "medium",
        "tags": ["个人助手", "前端"],
        "project_index": 1,
        "source": "todo.md",
        "source_pattern": r"左侧对话记录列表",
    },
    {
        "title": "发送消息携带页面状态",
        "status": "waitStart",
        "priority": "medium",
        "tags": ["个人助手", "前端"],
        "project_index": 1,
        "source": "todo.md",
        "source_pattern": r"发送消息携带页面状态",
    },
    {
        "title": "聊天→创建任务 API 调用优化",
        "status": "complete",
        "priority": "medium",
        "tags": ["个人助手", "API"],
        "project_index": 1,
        "source": "todo.md",
        "source_pattern": r"聊天→创建任务 API 调用优化",
    },
]


# ============================================================
# 核心：创建条目
# ============================================================

class Migrator:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.created_ids: dict[str, str] = {}  # 项目/条目编号 -> 实际 ID
        self.project_ids: list[str] = []  # 按顺序存储项目 ID

    def create_entry(
        self,
        category: str,
        title: str,
        content: str,
        status: str = "doing",
        priority: str = "medium",
        tags: list[str] | None = None,
        parent_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        entry_id = gen_id(category)
        now = created_at or now_iso()

        # 确定 markdown 文件路径
        if category == "project":
            path = DATA_DIR / "projects" / f"{entry_id}.md"
        elif category == "task":
            path = DATA_DIR / "tasks" / f"{entry_id}.md"
        elif category == "note":
            path = DATA_DIR / "notes" / f"{entry_id}.md"
        else:  # inbox
            path = DATA_DIR / f"{entry_id}.md"

        # 构建 YAML front matter
        fm_lines = [
            "---",
            f"id: {entry_id}",
            f"type: {category}",
            f"title: {title}",
            f"status: {status}",
            f"priority: {priority}",
            f"created_at: '{now}'",
            f"updated_at: '{now}'",
        ]

        if tags:
            fm_lines.append("tags:")
            for tag in tags:
                fm_lines.append(f"- {tag}")

        if parent_id:
            fm_lines.append(f"parent_id: {parent_id}")

        fm_lines.append("---")

        full_content = "\n".join(fm_lines) + "\n\n" + content + "\n"

        if self.dry_run:
            print(f"  [DRY] {category}/{entry_id}: {title}")
            print(f"        file: {path.relative_to(PROJECT_DIR)}")
            if parent_id:
                print(f"        parent: {parent_id}")
            if tags:
                print(f"        tags: {tags}")
            print(f"        content: {len(content)} chars")
            print()
        else:
            # 写 markdown 文件
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(full_content, encoding="utf-8")

            # 写 SQLite
            self._insert_db(
                entry_id=entry_id,
                category=category,
                title=title,
                status=status,
                priority=priority,
                file_path=str(path.relative_to(DATA_DIR)),
                content=content,
                tags=tags or [],
                parent_id=parent_id,
                created_at=now,
                updated_at=now,
            )

            print(f"  [OK] {category}/{entry_id}: {title}")

        return entry_id

    def _insert_db(
        self,
        entry_id: str,
        category: str,
        title: str,
        status: str,
        priority: str,
        file_path: str,
        content: str,
        tags: list[str],
        parent_id: str | None,
        created_at: str,
        updated_at: str,
    ):
        conn = sqlite3.connect(str(DB_PATH))
        try:
            # 插入 entries
            conn.execute(
                """INSERT OR IGNORE INTO entries
                   (id, type, title, status, priority, file_path, content,
                    parent_id, created_at, updated_at, user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '_default')""",
                (entry_id, category, title, status, priority, file_path, content,
                 parent_id, created_at, updated_at),
            )

            # 插入 tags
            for tag in tags:
                conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()
                if tag_row:
                    conn.execute(
                        "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                        (entry_id, tag_row[0]),
                    )

            conn.commit()
        finally:
            conn.close()


# ============================================================
# 迁移逻辑
# ============================================================

def migrate(dry_run: bool = False):
    migrator = Migrator(dry_run=dry_run)

    # 读取源文件
    projects_src = read_source("projects.md")
    todo_src = read_source("todo.md")
    inbox_src = read_source("inbox.md")
    notes_src = read_source("notes.md")

    # 解析 inbox 条目（按日期分段，再按粗体标题拆分）
    inbox_sections = extract_dated_sections(inbox_src)
    all_inbox_items: list[dict] = []
    for sec in inbox_sections:
        items = split_inbox_items(sec["content"])
        for item in items:
            item["date"] = sec["date"]
            all_inbox_items.append(item)

    # 解析 note 条目 — 每个日期段作为一条完整笔记
    note_sections = extract_dated_sections(notes_src)

    # ========================================
    # 1. 创建 Projects
    # ========================================
    print("=" * 60)
    print("Creating Projects...")
    print("=" * 60)

    # P1: AI 应用开发转型 - 完整的 projects.md 内容
    p1_id = migrator.create_entry(
        category="project",
        title="AI 应用开发转型",
        content=projects_src,
        status="doing",
        priority="high",
        tags=["AI", "转型", "学习计划"],
    )
    migrator.project_ids.append(p1_id)

    # P2: 个人成长助手开发 - 提取助手相关内容
    p2_content_parts = []
    # 从 projects.md 提取个人成长助手章节
    p2_section = extract_section(projects_src, "项目一：个人成长助手")
    if p2_section:
        p2_content_parts.append(p2_section)
    # 从 inbox 提取产品规划相关（I5, I9, I11）
    for item in all_inbox_items:
        if any(kw in item["title"] for kw in ["产品定位", "助手二期", "功能与交互"]):
            p2_content_parts.append(f"\n---\n\n## {item['title']}\n\n{item['content']}")

    p2_id = migrator.create_entry(
        category="project",
        title="个人成长助手开发",
        content="\n\n".join(p2_content_parts),
        status="doing",
        priority="high",
        tags=["个人成长助手", "产品", "开发"],
    )
    migrator.project_ids.append(p2_id)

    # P3: 自媒体运营 - 从 inbox 提取 I19
    p3_content_parts = []
    for item in all_inbox_items:
        if any(kw in item["title"] for kw in ["自媒体", "做自媒体"]):
            p3_content_parts.append(item["content"])
    # 也包含第一条视频脚本
    for item in all_inbox_items:
        if "视频脚本" in item["title"]:
            p3_content_parts.append(item["content"])

    p3_id = migrator.create_entry(
        category="project",
        title="自媒体运营",
        content="\n\n---\n\n".join(p3_content_parts) if p3_content_parts else "自媒体运营规划",
        status="waitStart",
        priority="medium",
        tags=["自媒体", "抖音", "掘金", "小红书"],
    )
    migrator.project_ids.append(p3_id)

    # P4: 教学辅助系统 - 从 inbox 提取 I18
    p4_content = ""
    for item in all_inbox_items:
        if "教学辅助" in item["title"]:
            p4_content = item["content"]
            break

    p4_id = migrator.create_entry(
        category="project",
        title="教学辅助系统",
        content=p4_content or "教学辅助系统规划",
        status="waitStart",
        priority="low",
        tags=["教育", "教学", "AI应用"],
    )
    migrator.project_ids.append(p4_id)

    # ========================================
    # 2. 创建 Tasks
    # ========================================
    print("\n" + "=" * 60)
    print("Creating Tasks...")
    print("=" * 60)

    # 从 todo.md 提取任务内容
    todo_lines = todo_src.split("\n")

    for task_def in TASKS_DEF:
        # 提取任务内容
        task_content = extract_task_content(todo_src, task_def["source_pattern"])
        parent_id = migrator.project_ids[task_def["project_index"]]

        migrator.create_entry(
            category="task",
            title=task_def["title"],
            content=task_content,
            status=task_def["status"],
            priority=task_def["priority"],
            tags=task_def.get("tags", []),
            parent_id=parent_id,
        )

    # ========================================
    # 3. 创建 Inbox 条目（纯灵感）
    # ========================================
    print("\n" + "=" * 60)
    print("Creating Inbox entries...")
    print("=" * 60)

    # 跳过的条目（I2 JoJoRead, I6 SSE, I8 dev-flow）
    skip_keywords = ["JoJoRead", "SSE 功能", "AI 代码开发流程标准化"]
    # 已合并到 project 的条目
    merged_keywords = ["产品定位与技术规划", "功能与交互设计", "助手二期",
                       "做自媒体", "视频脚本", "教学辅助"]
    # 应该转为 note 的条目（深度思考）
    note_keywords = ["AI 编程质量评估", "Vibe Coding"]

    for item in all_inbox_items:
        title = item["title"]

        # 跳过
        if any(kw in title for kw in skip_keywords):
            print(f"  [SKIP] {title}")
            continue

        # 已合并到 project
        if any(kw in title for kw in merged_keywords):
            print(f"  [MERGED→project] {title}")
            continue

        # 深度思考 → 转为 note
        if any(kw in title for kw in note_keywords):
            print(f"  [→NOTE] {title}")
            migrator.create_entry(
                category="note",
                title=title,
                content=item["content"],
                status="doing",
                priority="medium",
                tags=["思考", "方法论"],
                created_at=item.get("date") + "T10:00:00" if item.get("date") else None,
            )
            continue

        # 普通灵感 → inbox
        migrator.create_entry(
            category="inbox",
            title=title,
            content=item["content"],
            status="doing",
            priority="medium",
            created_at=item.get("date") + "T10:00:00" if item.get("date") else None,
        )

    # ========================================
    # 4. 创建 Note 条目
    # ========================================
    print("\n" + "=" * 60)
    print("Creating Notes...")
    print("=" * 60)

    for sec in note_sections:
        content = sec["content"].strip()
        if not content or len(content) < 10:
            continue

        # 跳过纯引用（"详细笔记已移至独立文档"）
        if content.startswith(">") and "移至独立文档" in content:
            print(f"  [SKIP] 引用链接，跳过")
            continue

        title = extract_note_title(content, fallback_title=sec.get("title", ""))

        # 跳过无用标题
        skip_titles = ["标签索引", "专题笔记索引", "今日总结", "待整理"]
        if any(st in title for st in skip_titles):
            print(f"  [SKIP] {title}")
            continue

        # 提取标签（排除 markdown 标题 # 符号）
        tags = []
        # 只从非标题行提取标签（以 # 开头后跟非空白的非标题行）
        for line in content[:500].split("\n"):
            if line.startswith("#"):
                # 从标题行末尾提取标签（## 标题 #标签1 #标签2 格式）
                trailing_tags = re.findall(r"\s#(\w+)", line)
                tags.extend(trailing_tags)
            else:
                inline_tags = re.findall(r"(?:^|\s)#(\w+)", line)
                tags.extend(inline_tags)

        if any(kw in content for kw in ["FastAPI", "Pydantic", "uvicorn"]):
            tags.append("FastAPI")
        if any(kw in content for kw in ["Prompt", "提示词", "CoT", "Few-shot"]):
            tags.append("Prompt工程")
        if any(kw in content for kw in ["Claude Code", "Subagent", "Skill"]):
            tags.append("Claude Code")
        if any(kw in content for kw in ["调试", "debug", "日志"]):
            tags.append("调试")

        tags = list(set(tags))[:5]

        migrator.create_entry(
            category="note",
            title=title,
            content=content,
            status="doing",
            priority="medium",
            tags=tags if tags else None,
            created_at=sec.get("date") + "T10:00:00" if sec.get("date") else None,
        )

    # ========================================
    # 总结
    # ========================================
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"  Projects created: 4")
    print(f"    P1: AI 应用开发转型 → {migrator.project_ids[0]}")
    print(f"    P2: 个人成长助手开发 → {migrator.project_ids[1]}")
    print(f"    P3: 自媒体运营 → {migrator.project_ids[2]}")
    print(f"    P4: 教学辅助系统 → {migrator.project_ids[3]}")
    print(f"  Tasks created: {len(TASKS_DEF)}")
    print(f"  Inbox/Notes created: from parsed content")
    if dry_run:
        print("\n  *** DRY RUN - no data written ***")
    else:
        print("\n  Done! Restart the backend or Docker to see changes.")


def extract_task_content(todo_src: str, pattern: str) -> str:
    """从 todo.md 中提取匹配 pattern 的任务内容。"""
    lines = todo_src.split("\n")
    result_lines = []
    capturing = False

    for line in lines:
        if re.search(pattern, line):
            capturing = True
            result_lines.append(line)
            continue
        if capturing:
            # 遇到下一个 - [ ] 或 - [x] 项停止
            if re.match(r"^- \[[ x]\] \*\*", line):
                break
            result_lines.append(line)

    content = "\n".join(result_lines).strip()
    # 去掉开头的 checkbox
    content = re.sub(r"^- \[[ x]\] \*\*(.+?)\*\*\s*", r"", content, count=1)
    return content if content else "待补充"


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate aiLearn data to personal-growth-assistant")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run)
