"""存储工厂 - 按用户创建隔离的存储实例"""

import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from app.infrastructure.storage.markdown import MarkdownStorage, _INBOX_FILE_RE

_MAX_CACHE_SIZE = 50


class StorageFactory:
    """按 user_id 创建和缓存 MarkdownStorage 实例

    数据目录结构：
        data/users/{user_id}/tasks/
        data/users/{user_id}/notes/
        data/users/{user_id}/projects/
        data/users/{user_id}/inbox.md
        data/users/{user_id}/inbox-{id}.md

    缓存策略：LRU 淘汰，最多保留 50 个用户实例。
    """

    def __init__(self, base_data_dir: str):
        self._base_dir = Path(base_data_dir) / "users"
        self._cache: OrderedDict[str, MarkdownStorage] = OrderedDict()

    def get_markdown_storage(self, user_id: str) -> MarkdownStorage:
        """获取指定用户的 MarkdownStorage（带 LRU 缓存）"""
        if user_id in self._cache:
            self._cache.move_to_end(user_id)
            return self._cache[user_id]

        user_dir = self._base_dir / user_id
        self._ensure_user_dirs(user_dir)

        storage = MarkdownStorage(data_dir=str(user_dir))
        self._cache[user_id] = storage

        if len(self._cache) > _MAX_CACHE_SIZE:
            self._cache.popitem(last=False)

        return storage

    def _ensure_user_dirs(self, user_dir: Path):
        """确保用户目录结构存在"""
        for subdir in ["tasks", "notes", "projects"]:
            (user_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _copy_user_md_files(self, src_dir: Path, dst_dir: Path) -> tuple[int, int]:
        """复制用户 Markdown 文件（子目录 + inbox 文件）

        Returns:
            (copied_count, skipped_count)
        """
        copied = 0
        skipped = 0

        for subdir in ["tasks", "notes", "projects"]:
            src_sub = src_dir / subdir
            if not src_sub.exists():
                continue

            dst_sub = dst_dir / subdir
            dst_sub.mkdir(parents=True, exist_ok=True)

            for md_file in src_sub.glob("*.md"):
                dst_file = dst_sub / md_file.name
                if dst_file.exists():
                    skipped += 1
                    continue
                shutil.copy2(md_file, dst_file)
                copied += 1

        # 复制根目录 inbox 文件（使用与 MarkdownStorage 一致的正则）
        if src_dir.is_dir():
            for f in src_dir.iterdir():
                if _INBOX_FILE_RE.match(f.name):
                    dst_file = dst_dir / f.name
                    if dst_file.exists():
                        skipped += 1
                    else:
                        shutil.copy2(f, dst_file)
                        copied += 1

        return copied, skipped

    def migrate_default_user(self, original_data_dir: str) -> int:
        """将现有 data/ 目录迁移到 data/users/_default/

        Returns:
            迁移的文件数量
        """
        src_dir = Path(original_data_dir)
        dst_dir = self._base_dir / "_default"

        if not src_dir.exists():
            return 0

        dst_dir.mkdir(parents=True, exist_ok=True)
        copied, _ = self._copy_user_md_files(src_dir, dst_dir)
        return copied

    def claim_default_user(self, target_user_id: str) -> tuple[int, int]:
        """将 data/users/_default/ 下的历史文件复制到目标用户目录

        Returns:
            (copied_count, skipped_count)
        """
        if not target_user_id or target_user_id == "_default":
            return 0, 0

        src_dir = self._base_dir / "_default"
        dst_dir = self._base_dir / target_user_id

        if not src_dir.exists():
            return 0, 0

        self._ensure_user_dirs(dst_dir)
        return self._copy_user_md_files(src_dir, dst_dir)

    def list_user_ids(self) -> list[str]:
        """列出已存在的用户目录"""
        if not self._base_dir.exists():
            return []
        return sorted(
            entry.name for entry in self._base_dir.iterdir() if entry.is_dir()
        )
