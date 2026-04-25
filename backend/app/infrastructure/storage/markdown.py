"""Markdown 文件存储层 - 支持 YAML Front Matter"""
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from app.models import Task, Category, TaskStatus, Priority

# inbox 文件匹配正则：inbox.md 或 inbox-{hexid}.md
# 与 EntryService._generate_entry_id 生成的 inbox-{hex} 格式一致
_INBOX_FILE_RE = re.compile(r"^inbox(-[a-f0-9]+)?\.md$")


class MarkdownStorage:
    """Markdown 文件存储 - 支持 YAML Front Matter"""

    # 目录映射
    CATEGORY_DIRS = {
        Category.PROJECT: "projects",
        Category.TASK: "tasks",
        Category.NOTE: "notes",
        Category.INBOX: "",  # inbox.md 在根目录
        Category.DECISION: "decisions",
        Category.REFLECTION: "reflections",
        Category.QUESTION: "questions",
    }

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录存在"""
        for category_dir in ["projects", "tasks", "notes", "decisions", "reflections", "questions"]:
            (self.data_dir / category_dir).mkdir(parents=True, exist_ok=True)

    def _safe_relative_path(self, file_path: Path) -> str:
        """安全获取相对路径，回退到文件名"""
        try:
            return str(file_path.relative_to(self.data_dir))
        except ValueError:
            return file_path.name

    def _get_file_path(self, entry_id: str, category: Category) -> Path:
        """获取文件路径"""
        dir_name = self.CATEGORY_DIRS.get(category, "notes")
        if dir_name:
            return self.data_dir / dir_name / f"{entry_id}.md"
        else:
            return self.data_dir / f"{entry_id}.md"

    def get_file_path(self, entry_id: str, category: Category) -> Path:
        """获取文件路径（公共接口，替代外部直接调用 _get_file_path）"""
        return self._get_file_path(entry_id, category)

    # === 旧格式提取方法（兼容用）===

    def _extract_title(self, content: str) -> str:
        """从内容中提取标题（第一个 # 标题）"""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def _extract_tags(self, content: str) -> List[str]:
        """从内容中提取标签（#标签 格式）"""
        tags = re.findall(r"#([\u4e00-\u9fa5\w-]+)", content)
        lines = content.split("\n")
        title_line = None
        for line in lines:
            if line.startswith("# ") and not line.startswith("## "):
                title_line = line
                break
        if title_line:
            title_tags = re.findall(r"#([\u4e00-\u9fa5\w-]+)", title_line)
            tags = [t for t in tags if t not in title_tags]
        return list(set(tags))

    def _extract_created_at(self, content: str, file_path: Path) -> datetime:
        """提取创建时间"""
        match = re.search(r"^>\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                pass
        try:
            stat = file_path.stat()
            return datetime.fromtimestamp(stat.st_ctime)
        except (OSError, AttributeError):
            return datetime.now()

    def _category_from_path(self, file_path: Path) -> Category:
        """从路径推断分类"""
        relative_path = file_path.relative_to(self.data_dir)
        parts = relative_path.parts

        if len(parts) > 1:
            dir_name = parts[0]
            if dir_name == "projects":
                return Category.PROJECT
            elif dir_name == "tasks":
                return Category.TASK
            elif dir_name == "notes":
                return Category.NOTE
            elif dir_name == "decisions":
                return Category.DECISION
            elif dir_name == "reflections":
                return Category.REFLECTION
            elif dir_name == "questions":
                return Category.QUESTION

        if _INBOX_FILE_RE.match(file_path.name):
            return Category.INBOX

        return Category.NOTE

    # === YAML Front Matter 支持 ===

    def _parse_front_matter(self, content: str) -> Tuple[dict, str]:
        """解析 YAML Front Matter，返回 (metadata, body)"""
        if not content.startswith('---'):
            return {}, content

        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content

        try:
            metadata = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return {}, content

        body = parts[2].strip()
        return metadata, body

    def _serialize_front_matter(self, task: Task, body: str) -> str:
        """序列化为带 YAML Front Matter 的 Markdown"""
        metadata = {
            'id': task.id,
            'type': task.category.value,
            'title': task.title,
            'status': task.status.value,
            'priority': task.priority.value if hasattr(task, 'priority') and task.priority else 'medium',
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'tags': task.tags,
        }

        # 可选字段
        if task.parent_id:
            metadata['parent_id'] = task.parent_id
        if task.planned_date:
            metadata['planned_date'] = task.planned_date.isoformat()
        if task.time_spent is not None:
            metadata['time_spent'] = task.time_spent
        if task.completed_at:
            metadata['completed_at'] = task.completed_at.isoformat()

        yaml_str = yaml.dump(metadata, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return f"---\n{yaml_str}---\n\n{body}"

    def _parse_datetime(self, value) -> Optional[datetime]:
        """解析 ISO 格式的日期时间（支持字符串或 datetime 对象）"""
        if not value:
            return None

        # YAML 可能已经解析为 datetime 对象
        if isinstance(value, datetime):
            return value

        # 处理字符串
        if isinstance(value, str):
            try:
                # 尝试 ISO 格式（去掉时区后缀）
                clean_value = value.replace('Z', '').split('+')[0].split('.')[0]
                return datetime.fromisoformat(clean_value)
            except (ValueError, AttributeError):
                pass
            try:
                # 尝试日期格式
                return datetime.strptime(value, '%Y-%m-%d')
            except (ValueError, AttributeError):
                pass

        return None

    def _extract_body(self, content: str, title: str) -> str:
        """从内容中提取正文（去掉旧的标题和日期行）"""
        lines = content.strip().split('\n')
        body_lines = []
        skip_title = True
        skip_date = True

        for line in lines:
            # 跳过标题行
            if skip_title and line.strip().startswith('# ') and title in line:
                skip_title = False
                continue
            # 跳过日期行（> 2026-03-14 格式）
            if skip_date and re.match(r'^>\s*\d{4}-\d{2}-\d{2}', line):
                skip_date = False
                continue
            # 跳过标题后的空行
            if not body_lines and not line.strip():
                continue
            body_lines.append(line)

        return '\n'.join(body_lines).strip()

    # === 公共 API ===

    def read_entry(self, entry_id: str, category: Optional[Category] = None) -> Optional[Task]:
        """读取条目，带 data/ 根目录回退兜底"""
        if category:
            file_path = self._get_file_path(entry_id, category)
            if file_path.exists():
                return self._parse_file(file_path)
        else:
            for cat in [Category.NOTE, Category.PROJECT, Category.TASK, Category.INBOX, Category.DECISION, Category.REFLECTION, Category.QUESTION]:
                file_path = self._get_file_path(entry_id, cat)
                if file_path.exists():
                    return self._parse_file(file_path)

        # 兜底：尝试从 data/ 根目录查找（R003 迁移遗漏文件）
        # data_dir 在用户态为 data/users/{uid}，需要走两级到 data/
        project_data_root = self.data_dir.parent.parent
        root_file = project_data_root / f"{entry_id}.md"
        if root_file.exists():
            return self._parse_file(root_file)

        return None

    def _parse_file(self, file_path: Path) -> Task:
        """解析文件为 Task"""
        content = file_path.read_text(encoding="utf-8")
        metadata, body = self._parse_front_matter(content)

        if metadata:
            # 新格式：从 YAML Front Matter 读取
            # 解析 priority，兼容旧数据
            priority_str = metadata.get('priority', 'medium')
            try:
                priority = Priority(priority_str)
            except ValueError:
                priority = Priority.MEDIUM

            return Task(
                id=metadata.get('id', file_path.stem),
                title=metadata.get('title', 'Untitled'),
                content=body,
                category=Category(metadata.get('type', 'note')),
                status=TaskStatus(metadata.get('status', 'doing')),
                priority=priority,
                tags=metadata.get('tags', []),
                created_at=self._parse_datetime(metadata.get('created_at')) or datetime.now(),
                updated_at=self._parse_datetime(metadata.get('updated_at')) or datetime.now(),
                planned_date=self._parse_datetime(metadata.get('planned_date')),
                completed_at=self._parse_datetime(metadata.get('completed_at')),
                time_spent=metadata.get('time_spent'),
                parent_id=metadata.get('parent_id'),
                file_path=self._safe_relative_path(file_path),
            )
        else:
            # 旧格式：从正文提取元数据
            title = self._extract_title(content)
            tags = self._extract_tags(content)
            category = self._category_from_path(file_path)
            created_at = self._extract_created_at(content, file_path)

            return Task(
                id=file_path.stem,
                title=title,
                content=content,
                category=category,
                status=TaskStatus.DOING,
                priority=Priority.MEDIUM,
                tags=tags,
                created_at=created_at,
                updated_at=datetime.now(),
                file_path=self._safe_relative_path(file_path),
            )

    def write_entry(self, entry: Task) -> str:
        """写入条目，返回文件路径"""
        file_path = self._get_file_path(entry.id, entry.category)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 提取正文（去掉旧的标题和日期）
        body = self._extract_body(entry.content, entry.title)

        # 如果正文为空，添加标题
        if not body.strip():
            body = f"# {entry.title}\n"

        # 序列化为 YAML Front Matter 格式
        content = self._serialize_front_matter(entry, body)
        file_path.write_text(content, encoding="utf-8")

        return str(file_path)

    def delete_entry(self, entry_id: str, category: Optional[Category] = None) -> bool:
        """删除条目"""
        entry = self.read_entry(entry_id, category)
        if entry:
            file_path = self.data_dir / entry.file_path
            if file_path.exists():
                file_path.unlink()
                return True
        return False

    def list_entries(
        self,
        category: Optional[Category] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
    ) -> List[Task]:
        """列出条目"""
        entries = []

        if category:
            dirs = [self.CATEGORY_DIRS.get(category, "notes")]
        else:
            dirs = ["projects", "tasks", "notes", "decisions", "reflections", "questions"]

        for dir_name in dirs:
            if not dir_name:
                continue
            dir_path = self.data_dir / dir_name
            if not dir_path.exists():
                continue

            for file_path in dir_path.glob("*.md"):
                try:
                    entry = self._parse_file(file_path)
                    if status is None or entry.status == status:
                        entries.append(entry)
                except Exception:
                    continue

        # 处理根目录 inbox 文件（使用共享正则 _INBOX_FILE_RE）
        if category is None or category == Category.INBOX:
            for f in self.data_dir.iterdir():
                if _INBOX_FILE_RE.match(f.name):
                    try:
                        entry = self._parse_file(f)
                        if status is None or entry.status == status:
                            entries.append(entry)
                    except Exception:
                        continue

        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[:limit]

    def scan_all(self) -> List[Task]:
        """扫描所有文件"""
        return self.list_entries(limit=1000)
