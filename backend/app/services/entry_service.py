"""条目业务服务层"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional, Tuple

from app.api.schemas import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    SearchResult,
    SuccessResponse,
    ProjectProgressResponse,
)
from app.mappers.entry_mapper import EntryMapper
from app.models import Task, Category, TaskStatus, Priority
from app.services.sync_service import SyncService
from app.storage.markdown import MarkdownStorage


class EntryService:
    """条目业务逻辑服务"""

    def __init__(self, storage: SyncService):
        self.storage = storage

    # === 辅助方法 ===

    def _parse_category(self, category_str: str) -> Category:
        """解析条目分类"""
        return EntryMapper.str_to_category(category_str)

    def _parse_status(self, status_str: Optional[str]) -> TaskStatus:
        """解析状态"""
        return EntryMapper.str_to_status(status_str)

    def _parse_priority(self, priority_str: Optional[str]) -> Priority:
        """解析优先级"""
        return EntryMapper.str_to_priority(priority_str)

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """解析日期时间字符串"""
        return EntryMapper.parse_datetime(date_str)

    def _generate_entry_id(self, category: Category) -> str:
        """生成条目 ID"""
        return f"{category.value}-{uuid.uuid4().hex[:8]}"

    def _get_file_path(self, category: Category, entry_id: str) -> str:
        """获取文件路径"""
        dir_name = MarkdownStorage.CATEGORY_DIRS.get(category, "notes")
        return f"{dir_name}/{entry_id}.md" if dir_name else f"{entry_id}.md"

    # === CRUD 操作 ===

    async def create_entry(self, request: EntryCreate) -> EntryResponse:
        """创建条目"""
        # 解析类型（兼容 type 和 category 字段）
        category_str = getattr(request, 'category', None) or getattr(request, 'type', None)
        category = self._parse_category(category_str)

        # 生成 ID 和文件路径
        entry_id = self._generate_entry_id(category)
        file_path = self._get_file_path(category, entry_id)
        now = datetime.now()

        # 解析状态和优先级
        status = self._parse_status(request.status)
        priority = self._parse_priority(request.priority)
        planned_date = self._parse_datetime(request.planned_date)

        # 创建条目对象
        entry = Task(
            id=entry_id,
            title=request.title,
            content=request.content,
            category=category,
            status=status,
            priority=priority,
            tags=request.tags,
            created_at=now,
            updated_at=now,
            parent_id=request.parent_id,
            file_path=file_path,
            planned_date=planned_date,
            time_spent=request.time_spent,
        )

        # 写入 Markdown
        self.storage.markdown.write_entry(entry)

        # SQLite 同步（同步执行）
        if self.storage.sqlite:
            self.storage.sqlite.upsert_entry(entry)

        # Neo4j + Qdrant 后台同步
        asyncio.create_task(self.storage.sync_to_graph_and_vector(entry))

        return EntryResponse(**EntryMapper.task_to_response(entry))

    async def get_entry(self, entry_id: str) -> Optional[EntryResponse]:
        """获取单个条目"""
        entry = self.storage.markdown.read_entry(entry_id)
        if not entry:
            return None
        return EntryResponse(**EntryMapper.task_to_response(entry))

    async def update_entry(self, entry_id: str, request: EntryUpdate) -> Tuple[bool, str]:
        """更新条目，返回 (成功, 消息)"""
        entry = self.storage.markdown.read_entry(entry_id)
        if not entry:
            return False, f"条目不存在: {entry_id}"

        # 更新字段
        updated = False

        if request.title is not None:
            entry.title = request.title
            updated = True

        if request.content is not None:
            entry.content = request.content
            updated = True

        if request.status is not None:
            entry.status = self._parse_status(request.status)
            updated = True

        if request.priority is not None:
            entry.priority = self._parse_priority(request.priority)
            updated = True

        if request.tags is not None:
            entry.tags = request.tags
            updated = True

        if request.parent_id is not None:
            entry.parent_id = request.parent_id
            updated = True

        if request.planned_date is not None:
            parsed_date = self._parse_datetime(request.planned_date)
            if parsed_date:
                entry.planned_date = parsed_date
                updated = True

        if request.time_spent is not None:
            entry.time_spent = request.time_spent
            updated = True

        if request.completed_at is not None:
            parsed_date = self._parse_datetime(request.completed_at)
            if parsed_date:
                entry.completed_at = parsed_date
                updated = True

        if not updated:
            return True, "无更新"

        entry.updated_at = datetime.now()

        # 写入 Markdown
        self.storage.markdown.write_entry(entry)

        # SQLite 同步
        if self.storage.sqlite:
            self.storage.sqlite.upsert_entry(entry)

        # Neo4j + Qdrant 后台同步
        asyncio.create_task(self.storage.sync_to_graph_and_vector(entry))

        return True, f"已更新条目: {entry_id}"

    async def delete_entry(self, entry_id: str) -> Tuple[bool, str]:
        """删除条目，返回 (成功, 消息)"""
        # 检查条目是否存在
        entry = self.storage.markdown.read_entry(entry_id)
        if not entry:
            return False, f"条目不存在: {entry_id}"

        # 删除
        success = await self.storage.delete_entry(entry_id)

        if success:
            return True, f"已删除条目: {entry_id}"
        else:
            return False, "删除失败"

    # === 查询操作 ===

    async def list_entries(
        self,
        type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[str] = None,
        parent_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> EntryListResponse:
        """列出条目"""
        # 优先使用 SQLite 索引
        if self.storage.sqlite:
            tag_list = [t.strip() for t in tags.split(",")] if tags else None
            entries = self.storage.sqlite.list_entries(
                type=type,
                status=status,
                tags=tag_list,
                parent_id=parent_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
            )
            total = self.storage.sqlite.count_entries(
                type=type,
                status=status,
                tags=tag_list,
                parent_id=parent_id,
                start_date=start_date,
                end_date=end_date,
            )
            return EntryListResponse(
                entries=[EntryResponse(**EntryMapper.dict_to_response(e)) for e in entries],
                total=total,
            )

        # 回退到 Markdown 直接读取
        category = Category(type) if type else None
        task_status = TaskStatus(status) if status else None

        entries = self.storage.markdown.list_entries(
            category=category,
            status=task_status,
            limit=limit,
        )

        return EntryListResponse(
            entries=[EntryResponse(**EntryMapper.task_to_response(e)) for e in entries]
        )

    async def search_entries(self, query: str, limit: int = 10) -> SearchResult:
        """搜索条目"""
        if not self.storage.sqlite:
            raise RuntimeError("SQLite 索引不可用")

        results = self.storage.sqlite.search(query, limit=limit)

        return SearchResult(
            entries=[EntryResponse(**EntryMapper.dict_to_response(e)) for e in results],
            query=query,
        )

    async def get_project_progress(self, entry_id: str) -> ProjectProgressResponse:
        """获取项目进度"""
        # 检查项目是否存在
        entry = self.storage.markdown.read_entry(entry_id)
        if not entry:
            raise ValueError(f"条目不存在: {entry_id}")

        if not self.storage.sqlite:
            raise RuntimeError("SQLite 索引不可用")

        # 获取所有子任务
        child_entries = self.storage.sqlite.list_entries(parent_id=entry_id, limit=1000)

        total = len(child_entries)
        if total == 0:
            return ProjectProgressResponse(
                project_id=entry_id,
                total_tasks=0,
                completed_tasks=0,
                progress_percentage=0.0,
                status_distribution={}
            )

        # 统计各状态数量
        status_counts = {}
        completed = 0
        for child in child_entries:
            status = child.get("status", "doing")
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == "complete":
                completed += 1

        progress = (completed / total) * 100 if total > 0 else 0

        return ProjectProgressResponse(
            project_id=entry_id,
            total_tasks=total,
            completed_tasks=completed,
            progress_percentage=round(progress, 1),
            status_distribution=status_counts
        )
