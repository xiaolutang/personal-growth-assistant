"""存储工厂 - 按用户创建隔离的存储实例"""

import shutil
from pathlib import Path
from typing import Dict, Optional

from app.infrastructure.storage.markdown import MarkdownStorage


class StorageFactory:
    """按 user_id 创建和缓存 MarkdownStorage 实例

    数据目录结构：
        data/users/{user_id}/tasks/
        data/users/{user_id}/notes/
        data/users/{user_id}/projects/
        data/users/{user_id}/inbox.md
    """

    def __init__(self, base_data_dir: str):
        self._base_dir = Path(base_data_dir) / "users"
        self._cache: Dict[str, MarkdownStorage] = {}

    def get_markdown_storage(self, user_id: str) -> MarkdownStorage:
        """获取指定用户的 MarkdownStorage（带缓存）"""
        if user_id in self._cache:
            return self._cache[user_id]

        user_dir = self._base_dir / user_id
        self._ensure_user_dirs(user_dir)

        storage = MarkdownStorage(data_dir=str(user_dir))
        self._cache[user_id] = storage
        return storage

    def _ensure_user_dirs(self, user_dir: Path):
        """确保用户目录结构存在"""
        for subdir in ["tasks", "notes", "projects"]:
            (user_dir / subdir).mkdir(parents=True, exist_ok=True)

    def migrate_default_user(self, original_data_dir: str) -> int:
        """将现有 data/ 目录迁移到 data/users/_default/

        Returns:
            迁移的文件数量
        """
        src_dir = Path(original_data_dir)
        dst_dir = self._base_dir / "_default"

        if not src_dir.exists():
            return 0

        count = 0
        for subdir in ["tasks", "notes", "projects"]:
            src_sub = src_dir / subdir
            if not src_sub.exists():
                continue

            dst_sub = dst_dir / subdir
            dst_sub.mkdir(parents=True, exist_ok=True)

            for md_file in src_sub.glob("*.md"):
                dst_file = dst_sub / md_file.name
                if not dst_file.exists():
                    shutil.copy2(md_file, dst_file)
                    count += 1

        # 迁移 inbox.md
        src_inbox = src_dir / "inbox.md"
        if src_inbox.exists():
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst_inbox = dst_dir / "inbox.md"
            if not dst_inbox.exists():
                shutil.copy2(src_inbox, dst_inbox)
                count += 1

        return count
