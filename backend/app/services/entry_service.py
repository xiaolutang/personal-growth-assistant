"""条目业务服务层"""

import asyncio
import logging
import os
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, List, Optional, Tuple, Any, Dict, Set

logger = logging.getLogger(__name__)

from app.api.schemas import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    SearchResult,
    SuccessResponse,
    ProjectProgressResponse,
    RelatedEntry,
    RelatedEntriesResponse,
    EntryLinkCreate,
    EntryLinkResponse,
    EntryLinkItem,
    EntryLinkListResponse,
    LinkTargetEntry,
)
from app.mappers.entry_mapper import EntryMapper
from app.models import Task, Category, TaskStatus, Priority
from app.services.sync_service import SyncService
from app.infrastructure.storage.markdown import MarkdownStorage
from app.services.hybrid_search import HybridSearchService


class EntryService:
    """条目业务逻辑服务"""

    def __init__(self, storage: SyncService):
        self.storage = storage

    async def _trigger_tag_auto_recalc(self, user_id: str, tags: list[str]):
        """异步触发 tag_auto 目标进度重算（fire-and-forget）"""
        if not tags:
            return
        try:
            from app.routers import deps
            goal_service = deps.get_goal_service()
            await goal_service.recalculate_tag_auto_goals(user_id, tags)
        except Exception as e:
            logger.warning("tag_auto 目标进度重算失败: %s", e)

    def _get_markdown_storage(self, user_id: str) -> MarkdownStorage:
        return self.storage.get_markdown_storage(user_id)

    def get_markdown_storage(self, user_id: str) -> MarkdownStorage:
        """获取 Markdown 存储（公共接口，替代外部直接调用 _get_markdown_storage）"""
        return self._get_markdown_storage(user_id)

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

    # === 类型模板 ===

    CATEGORY_TEMPLATES = {
        Category.DECISION: (
            "\n\n## 决策背景\n\n\n## 可选方案\n\n\n## 最终选择\n\n\n## 选择理由\n"
        ),
        Category.REFLECTION: (
            "\n\n## 回顾目标\n\n\n## 实际结果\n\n\n## 经验教训\n\n\n## 下一步行动\n"
        ),
        Category.QUESTION: (
            "\n\n## 问题描述\n\n\n## 相关背景\n\n\n## 思考方向\n"
        ),
    }

    def _apply_category_template(self, category: Category, content: str, title: str) -> str:
        """为新类型条目应用结构化模板"""
        template = self.CATEGORY_TEMPLATES.get(category)
        if not template:
            return content
        if content.strip():
            return f"# {title}\n\n{content}{template}"
        return f"# {title}{template}"

    # === CRUD 操作 ===

    async def create_entry(self, request: EntryCreate, user_id: str = "_default") -> EntryResponse:
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
        content = self._apply_category_template(category, request.content, request.title)
        entry = Task(
            id=entry_id,
            title=request.title,
            content=content,
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
        self._get_markdown_storage(user_id).write_entry(entry)

        # SQLite 同步（同步执行）
        if self.storage.sqlite:
            self.storage.sqlite.upsert_entry(entry, user_id=user_id)
            # 解析双链引用
            self._update_note_references(entry.id, content, user_id)

        # Neo4j + Qdrant 后台同步
        asyncio.create_task(self.storage.sync_to_graph_and_vector(entry, user_id=user_id))

        # tag_auto 目标进度重算
        if entry.tags:
            asyncio.create_task(self._trigger_tag_auto_recalc(user_id, entry.tags))

        return EntryResponse(**EntryMapper.task_to_response(entry))

    def _verify_entry_owner(self, entry_id: str, user_id: str) -> bool:
        """验证条目是否属于当前用户"""
        if not self.storage.sqlite:
            logger.warning("SQLite 不可用，拒绝访问 entry_id=%s user_id=%s", entry_id, user_id)
            return False  # 无 SQLite 时无法验证，安全优先拒绝
        return self.storage.sqlite.entry_belongs_to_user(entry_id, user_id)

    async def get_entry(self, entry_id: str, user_id: str = "_default") -> Optional[EntryResponse]:
        """获取单个条目"""
        if not self._verify_entry_owner(entry_id, user_id):
            return None
        entry = self._get_markdown_storage(user_id).read_entry(entry_id)
        if not entry:
            return None
        return EntryResponse(**EntryMapper.task_to_response(entry))

    async def get_related_entries(
        self, entry_id: str, user_id: str = "_default", limit: int = 5
    ) -> Optional[RelatedEntriesResponse]:
        """获取关联条目（同项目 > 标签重叠 > 搜索相关）"""
        if not self._verify_entry_owner(entry_id, user_id):
            return None
        entry = self._get_markdown_storage(user_id).read_entry(entry_id)
        if not entry:
            return None

        seen_ids: set[str] = {entry_id}
        results: list[RelatedEntry] = []

        # 级别 1：同项目（同 parent_id）的兄弟条目
        if entry.parent_id:
            siblings = await self.list_entries(
                parent_id=entry.parent_id, limit=20, user_id=user_id
            )
            for s in siblings.entries:
                if s.id not in seen_ids and len(results) < limit:
                    seen_ids.add(s.id)
                    results.append(RelatedEntry(
                        id=s.id, title=s.title, category=s.category,
                        relevance_reason="同项目",
                    ))

        # 级别 2：标签重叠
        if entry.tags and len(results) < limit:
            sqlite = self.storage.sqlite
            if sqlite:
                tag_related = sqlite.find_entries_by_tag_overlap(
                    entry_id=entry_id, tags=entry.tags, limit=limit * 2, user_id=user_id
                )
                for r in tag_related:
                    if r["id"] not in seen_ids and len(results) < limit:
                        seen_ids.add(r["id"])
                        results.append(RelatedEntry(
                            id=r["id"], title=r.get("title", ""),
                            category=r.get("category", ""),
                            relevance_reason="标签相关",
                        ))

        # 级别 3：搜索相关（混合搜索：向量 + 全文）
        if len(results) < limit:
            try:
                search_service = HybridSearchService(self.storage)
                search_results = await search_service.search(
                    query=entry.title or entry.content or "",
                    user_id=user_id,
                    limit=limit * 2,
                )
                for vr in search_results:
                    if vr.id not in seen_ids and len(results) < limit:
                        seen_ids.add(vr.id)
                        results.append(RelatedEntry(
                            id=vr.id, title=vr.title, category=vr.category,
                            relevance_reason="搜索相关",
                        ))
            except Exception:
                logger.warning("搜索关联失败，跳过第3层关联")

        return RelatedEntriesResponse(related=results)

    async def update_entry(self, entry_id: str, request: EntryUpdate, user_id: str = "_default") -> Tuple[bool, str]:
        """更新条目，返回 (成功, 消息)"""
        if not self._verify_entry_owner(entry_id, user_id):
            return False, f"条目不存在: {entry_id}"
        entry = self._get_markdown_storage(user_id).read_entry(entry_id)
        if not entry:
            return False, f"条目不存在: {entry_id}"

        # 更新字段
        updated = False
        old_tags = list(entry.tags) if entry.tags else []

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

        # Category 变更：文件迁移
        old_file_path = None
        if request.category is not None:
            try:
                new_category = Category(request.category)
            except ValueError:
                return False, f"无效的 category: {request.category}"

            if new_category != entry.category:
                old_file_path = entry.file_path
                entry.category = new_category
                # 更新 file_path 到新 category 目录
                entry.file_path = self._get_file_path(new_category, entry.id)
                updated = True

        if not updated:
            return True, "无更新"

        entry.updated_at = datetime.now()

        # 写入 Markdown（写入新 file_path 位置）
        md_storage = self._get_markdown_storage(user_id)
        md_storage.write_entry(entry)

        # Category 变更后移动旧文件（先尝试 rename，失败则删旧留新）
        if old_file_path:
            old_path = md_storage.data_dir / old_file_path
            new_path = md_storage.data_dir / entry.file_path
            if old_path.exists() and Path(old_path) != Path(new_path):
                try:
                    # 确保目标目录存在
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    if not new_path.exists():
                        old_path.rename(new_path)
                    else:
                        # 新文件已由 write_entry 写入，只需删除旧文件
                        old_path.unlink()
                except OSError:
                    logger.warning(
                        "文件迁移失败 old=%s new=%s，依赖 write_entry 的新副本",
                        old_path, new_path,
                    )
                    try:
                        old_path.unlink()
                    except OSError:
                        pass  # 旧文件清理失败不阻塞

        # SQLite 同步 + 清除 AI 摘要缓存（内容变更后旧摘要失效）
        if self.storage.sqlite:
            self.storage.sqlite.upsert_entry(entry, user_id=user_id)
            if request.title is not None or request.content is not None:
                self.storage.sqlite.save_ai_summary(entry_id, "", user_id=user_id)
            # 内容变更时更新双链引用
            if request.content is not None:
                self._update_note_references(entry_id, request.content, user_id)

        # Neo4j + Qdrant 后台同步
        asyncio.create_task(self.storage.sync_to_graph_and_vector(entry, user_id=user_id))

        # tag_auto 目标进度重算（使用 old_tags ∪ new_tags 覆盖"原来匹配现在不匹配"的场景）
        if request.tags is not None:
            all_tags = list(set(old_tags) | set(request.tags))
            if all_tags:
                asyncio.create_task(self._trigger_tag_auto_recalc(user_id, all_tags))

        return True, f"已更新条目: {entry_id}"

    async def delete_entry(self, entry_id: str, user_id: str = "_default") -> Tuple[bool, str]:
        """删除条目，返回 (成功, 消息)"""
        # 验证条目属于当前用户
        if not self._verify_entry_owner(entry_id, user_id):
            return False, f"条目不存在: {entry_id}"
        # 检查条目是否存在
        entry = self._get_markdown_storage(user_id).read_entry(entry_id)
        if not entry:
            return False, f"条目不存在: {entry_id}"

        # 级联删除条目关联
        if self.storage.sqlite:
            self.storage.sqlite.delete_entry_links_by_entry(entry_id, user_id)
            # 清理双链引用关系
            self.storage.sqlite.delete_note_references(entry_id, user_id)

        # 删除
        success = await self.storage.delete_entry(entry_id, user_id=user_id)

        if success:
            return True, f"已删除条目: {entry_id}"
        else:
            return False, "删除失败"

    async def batch_create_entries(
        self, requests: list[EntryCreate], user_id: str = "_default"
    ) -> list[EntryResponse]:
        """批量创建条目，复用 create_entry 的字段默认值逻辑

        确保批量创建与单个创建使用完全相同的 status/category 默认值：
        - status 缺失时默认 "doing"
        - category 缺失时默认 "note"
        """
        results: list[EntryResponse] = []
        for req in requests:
            resp = await self.create_entry(req, user_id=user_id)
            results.append(resp)
        return results

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
        user_id: str = "_default",
        due: Optional[str] = None,
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
                user_id=user_id,
                due=due,
            )
            total = self.storage.sqlite.count_entries(
                type=type,
                status=status,
                tags=tag_list,
                parent_id=parent_id,
                start_date=start_date,
                end_date=end_date,
                user_id=user_id,
                due=due,
            )
            return EntryListResponse(
                entries=[EntryResponse(**EntryMapper.dict_to_response(e)) for e in entries],
                total=total,
            )

        # 回退到 Markdown 直接读取
        category = Category(type) if type else None
        task_status = TaskStatus(status) if status else None

        entries = self._get_markdown_storage(user_id).list_entries(
            category=category,
            status=task_status,
            limit=limit,
        )

        return EntryListResponse(
            entries=[EntryResponse(**EntryMapper.task_to_response(e)) for e in entries]
        )

    async def search_entries(self, query: str, limit: int = 10, user_id: str = "_default") -> SearchResult:
        """搜索条目 - 使用混合搜索（向量 + 全文）"""

        # 优先使用混合搜索（需要 Qdrant 和 SQLite 都可用）
        if self.storage.qdrant and self.storage.sqlite:
            hybrid = HybridSearchService(self.storage)
            entries = await hybrid.search(query, user_id=user_id, limit=limit)
            return SearchResult(entries=entries, query=query)

        # 回退：仅 SQLite 全文搜索
        if self.storage.sqlite:
            results = self.storage.sqlite.search(query, limit=limit, user_id=user_id)
            return SearchResult(
                entries=[EntryResponse(**EntryMapper.dict_to_response(e)) for e in results],
                query=query,
            )

        raise RuntimeError("没有可用的搜索服务")

    async def get_project_progress(self, entry_id: str, user_id: str = "_default") -> ProjectProgressResponse:
        """获取项目进度"""
        # 验证条目属于当前用户
        if not self._verify_entry_owner(entry_id, user_id):
            raise ValueError(f"条目不存在: {entry_id}")
        # 检查项目是否存在
        entry = self._get_markdown_storage(user_id).read_entry(entry_id)
        if not entry:
            raise ValueError(f"条目不存在: {entry_id}")

        if not self.storage.sqlite:
            raise RuntimeError("SQLite 索引不可用")

        # 获取所有子任务
        child_entries = self.storage.sqlite.list_entries(parent_id=entry_id, limit=1000, user_id=user_id)

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

    # === 导出操作 ===

    async def export_markdown_stream(
        self,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: str = "_default",
    ) -> AsyncGenerator[bytes, None]:
        """流式导出为 Markdown zip 格式，分块 yield 字节数据"""
        md_storage = self._get_markdown_storage(user_id)
        _EXPORT_LIMIT = 100_000
        _CHUNK_SIZE = 8192

        # 从 SQLite 获取符合条件的条目列表
        if self.storage.sqlite:
            entries = self.storage.sqlite.list_entries(
                type=type,
                start_date=start_date,
                end_date=end_date,
                limit=_EXPORT_LIMIT,
                offset=0,
                user_id=user_id,
            )
        else:
            # 回退：直接遍历 Markdown 文件
            category = Category(type) if type else None
            tasks = md_storage.list_entries(category=category, limit=_EXPORT_LIMIT)
            entries = [EntryMapper.task_to_response(t) for t in tasks]

        if len(entries) >= _EXPORT_LIMIT:
            logger.warning(
                "export_markdown_stream 达到 limit=%d 上限，可能有数据被截断, user_id=%s",
                _EXPORT_LIMIT, user_id,
            )

        # 使用临时文件写 zip，然后分块读取流式返回
        fd, tmp_path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)

        try:
            # 逐条写入 zip entry
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for entry_data in entries:
                    entry_id = entry_data["id"] if isinstance(entry_data, dict) else entry_data.id
                    file_path = entry_data.get("file_path", "") if isinstance(entry_data, dict) else entry_data.file_path

                    # 从磁盘读取原始 Markdown 文件内容
                    md_path = md_storage.data_dir / file_path if file_path else None
                    if md_path and md_path.exists():
                        content = md_path.read_text(encoding="utf-8")
                        category = entry_data.get("category") or entry_data.get("type", "note") if isinstance(entry_data, dict) else entry_data.category.value
                        dir_name = MarkdownStorage.CATEGORY_DIRS.get(Category(category), "")
                        if not dir_name:
                            dir_name = category
                        arc_name = f"{dir_name}/{entry_id}.md"
                        zf.writestr(arc_name, content)

            # 分块读取临时文件并 yield
            with open(tmp_path, "rb") as f:
                while chunk := f.read(_CHUNK_SIZE):
                    yield chunk
        finally:
            os.unlink(tmp_path)

    async def export_json(
        self,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: str = "_default",
    ) -> list[dict]:
        """导出为 JSON 格式，返回条目列表"""
        _EXPORT_LIMIT = 100_000

        if self.storage.sqlite:
            entries = self.storage.sqlite.list_entries(
                type=type,
                start_date=start_date,
                end_date=end_date,
                limit=_EXPORT_LIMIT,
                offset=0,
                user_id=user_id,
            )
            if len(entries) >= _EXPORT_LIMIT:
                logger.warning(
                    "export_json 达到 limit=%d 上限，可能有数据被截断, user_id=%s",
                    _EXPORT_LIMIT, user_id,
                )
            return [EntryMapper.dict_to_response(e) for e in entries]

        # 回退：直接从 Markdown 读取
        md_storage = self._get_markdown_storage(user_id)
        category = Category(type) if type else None
        tasks = md_storage.list_entries(category=category, limit=_EXPORT_LIMIT)
        if len(tasks) >= _EXPORT_LIMIT:
            logger.warning(
                "export_json (markdown fallback) 达到 limit=%d 上限，可能有数据被截断, user_id=%s",
                _EXPORT_LIMIT, user_id,
            )
        return [EntryMapper.task_to_response(t) for t in tasks]

    # === AI 摘要 ===

    async def generate_summary(
        self, entry_id: str, user_id: str = "_default"
    ) -> Optional[dict[str, Any]]:
        """为条目生成 AI 摘要

        Returns:
            {"summary": str, "generated_at": str, "cached": bool}
            条目不存在返回 None
            条目不属于当前用户抛出 PermissionError
            无内容时返回 {"summary": null, "generated_at": null, "cached": False}
        """
        # 读取条目
        entry = self._get_markdown_storage(user_id).read_entry(entry_id)
        if not entry:
            # 检查是否属于其他用户
            if self.storage.sqlite:
                db_entry = self.storage.sqlite.get_entry(entry_id, user_id=user_id)
                if db_entry and db_entry.get("user_id") and db_entry["user_id"] != user_id:
                    raise PermissionError(f"无权访问条目: {entry_id}")
            return None

        # 空内容返回 null
        if not entry.content or not entry.content.strip():
            return {"summary": None, "generated_at": None, "cached": False}

        # 检查缓存
        if self.storage.sqlite:
            cached = self.storage.sqlite.get_ai_summary(entry_id, user_id=user_id)
            if cached:
                return {"summary": cached["summary"], "generated_at": cached["generated_at"], "cached": True}

        # 检查 LLM 是否可用
        llm_caller = self.storage.llm_caller
        if not llm_caller:
            raise RuntimeError("LLM 服务不可用")

        # 调用 LLM 生成摘要
        prompt = (
            "请用中文对以下条目内容进行总结，要求：\n"
            "1. 总结条目的核心内容（不超过200字）\n"
            "2. 提炼关键知识点\n"
            "3. 如果有行动项或待办事项，请一并列出\n\n"
            f"条目标题：{entry.title or '无标题'}\n\n"
            f"条目内容：\n{entry.content}"
        )
        messages = [
            {"role": "system", "content": "你是一个专业的内容总结助手。请简洁、准确地总结内容。"},
            {"role": "user", "content": prompt},
        ]
        try:
            summary = await llm_caller.call(messages)
        except Exception as e:
            logger.error("LLM 生成摘要失败: %s", e)
            raise RuntimeError(f"LLM 服务不可用: {e}") from e

        # 截断到 200 字
        if len(summary) > 200:
            summary = summary[:200]

        # 缓存到 SQLite
        generated_at = datetime.now().isoformat()
        if self.storage.sqlite:
            self.storage.sqlite.save_ai_summary(entry_id, summary, user_id=user_id, generated_at=generated_at)

        return {"summary": summary, "generated_at": generated_at, "cached": False}

    # === 条目关联操作 ===

    async def create_entry_link(
        self, entry_id: str, request: EntryLinkCreate, user_id: str = "_default"
    ) -> Tuple[Optional[EntryLinkResponse], int, str]:
        """创建条目关联（双向），返回 (响应, 状态码, 消息)"""
        sqlite = self.storage.sqlite
        if not sqlite:
            return None, 503, "SQLite 索引不可用"

        target_id = request.target_id
        relation_type = request.relation_type

        # 不允许自关联
        if entry_id == target_id:
            return None, 400, "不允许自关联: source_id 不能等于 target_id"

        # 验证 source 条目存在且属于当前用户
        if not sqlite.entry_belongs_to_user(entry_id, user_id):
            return None, 404, f"条目不存在: {entry_id}"

        # 验证 target 条目存在且属于当前用户
        if not sqlite.entry_belongs_to_user(target_id, user_id):
            return None, 404, f"目标条目不存在: {target_id}"

        # 检查是否已存在（任一方向）
        if sqlite.check_entry_link_exists(user_id, entry_id, target_id, relation_type):
            return None, 409, f"关联已存在: {entry_id} -> {target_id} ({relation_type})"

        # 创建双向关联
        try:
            sqlite.create_entry_links_pair(user_id, entry_id, target_id, relation_type)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                return None, 409, f"关联已存在: {entry_id} -> {target_id} ({relation_type})"
            raise

        # 获取 target 条目信息
        target_data = sqlite.get_entry(target_id, user_id)
        target_entry = LinkTargetEntry(
            id=target_id,
            title=target_data.get("title", "") if target_data else "",
            category=target_data.get("type", "") if target_data else "",
        )

        # 获取创建的正向记录
        links = sqlite.list_entry_links(entry_id, user_id, direction="out")
        fwd_link = None
        for lk in links:
            if lk["target_id"] == target_id and lk["relation_type"] == relation_type:
                fwd_link = lk
                break

        return EntryLinkResponse(
            id=fwd_link["id"],
            source_id=fwd_link["source_id"],
            target_id=fwd_link["target_id"],
            relation_type=fwd_link["relation_type"],
            created_at=fwd_link["created_at"],
            target_entry=target_entry,
        ), 201, "关联创建成功"

    async def list_entry_links(
        self, entry_id: str, user_id: str = "_default", direction: str = "both"
    ) -> Tuple[Optional[EntryLinkListResponse], int, str]:
        """列出条目关联"""
        sqlite = self.storage.sqlite
        if not sqlite:
            return None, 503, "SQLite 索引不可用"

        # 验证条目存在
        if not sqlite.entry_belongs_to_user(entry_id, user_id):
            return None, 404, f"条目不存在: {entry_id}"

        if direction not in ("in", "out", "both"):
            return None, 422, f"无效的 direction 参数: {direction}"

        raw_links = sqlite.list_entry_links(entry_id, user_id, direction=direction)

        # 去重（both 模式下，正向和反向可能指向同一对，需要用 id 去重）
        seen_ids: set[str] = set()
        items: list[EntryLinkItem] = []
        for lk in raw_links:
            if lk["id"] in seen_ids:
                continue
            seen_ids.add(lk["id"])

            # target_id 根据 direction 决定
            if lk["direction"] == "out":
                tid = lk["target_id"]
            else:
                tid = lk["source_id"]

            target_data = sqlite.get_entry(tid, user_id)
            target_entry = LinkTargetEntry(
                id=tid,
                title=target_data.get("title", "") if target_data else "",
                category=target_data.get("type", "") if target_data else "",
            )
            items.append(EntryLinkItem(
                id=lk["id"],
                target_id=tid,
                target_entry=target_entry,
                relation_type=lk["relation_type"],
                direction=lk["direction"],
                created_at=lk["created_at"],
            ))

        return EntryLinkListResponse(links=items), 200, ""

    async def delete_entry_link(
        self, entry_id: str, link_id: str, user_id: str = "_default"
    ) -> Tuple[bool, int, str]:
        """删除条目关联（双向），返回 (成功, 状态码, 消息)"""
        sqlite = self.storage.sqlite
        if not sqlite:
            return False, 503, "SQLite 索引不可用"

        # 验证条目存在
        if not sqlite.entry_belongs_to_user(entry_id, user_id):
            return False, 404, f"条目不存在: {entry_id}"

        # 验证 link 属于该条目
        link = sqlite.get_entry_link(link_id, user_id)
        if not link:
            return False, 404, f"关联不存在: {link_id}"
        if link["source_id"] != entry_id and link["target_id"] != entry_id:
            return False, 404, f"关联 {link_id} 不属于条目 {entry_id}"

        # 删除双向
        deleted = sqlite.delete_entry_link_pair(link_id, user_id)
        if not deleted:
            return False, 404, f"关联不存在: {link_id}"

        return True, 204, ""

    # === 笔记双链引用 ===

    def _update_note_references(self, source_id: str, content: str, user_id: str):
        """解析内容的双链语法并更新引用关系"""
        if not self.storage.sqlite:
            return
        from app.infrastructure.storage.sqlite import SQLiteStorage
        target_ids = SQLiteStorage.parse_wikilinks(content)
        # 过滤自引用（再次确认）
        target_ids.discard(source_id)
        # 过滤不存在的 target_id
        valid_targets: Set[str] = set()
        for tid in target_ids:
            if '-' not in tid:
                continue
            if self.storage.sqlite.entry_belongs_to_user(tid, user_id):
                valid_targets.add(tid)
        self.storage.sqlite.upsert_note_references(source_id, valid_targets, user_id)

    async def get_backlinks(self, entry_id: str, user_id: str = "_default") -> List[Dict[str, Any]]:
        """获取条目的反向引用列表。

        首次调用时自动触发 reindex_backlinks（延迟初始化）。
        """
        if not self.storage.sqlite:
            return []

        # 延迟初始化：首次查询时 reindex
        if not self.storage.sqlite.is_backlinks_indexed(user_id):
            await self.reindex_backlinks(user_id)

        return self.storage.sqlite.get_backlinks(entry_id, user_id)

    async def reindex_backlinks(self, user_id: str):
        """扫描用户所有笔记内容并重建引用关系（幂等）"""
        if not self.storage.sqlite:
            return

        from app.infrastructure.storage.sqlite import SQLiteStorage

        # 获取用户所有条目（包含 content）
        conn = self.storage.sqlite.get_connection()
        try:
            rows = conn.execute(
                "SELECT id, content FROM entries WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            entry_id = row["id"]
            content = row["content"] or ""
            target_ids = SQLiteStorage.parse_wikilinks(content)
            # 过滤自引用
            target_ids.discard(entry_id)
            # 过滤无效 ID
            valid_targets = {tid for tid in target_ids if '-' in tid}
            self.storage.sqlite.upsert_note_references(entry_id, valid_targets, user_id)

        # 标记已索引
        self.storage.sqlite.mark_backlinks_indexed(user_id)
