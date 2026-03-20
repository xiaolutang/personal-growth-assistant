#!/usr/bin/env python3
"""
迁移脚本：为现有 Markdown 文件添加 YAML Front Matter

用法：
    cd backend
    python scripts/migrate_frontmatter.py
"""
import re
import sys
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml


def extract_title(content: str) -> str:
    """从内容中提取标题"""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled"


def extract_tags(content: str) -> list:
    """从内容中提取标签"""
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


def extract_created_at(content: str, file_path: Path) -> datetime:
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


def migrate_file(file_path: Path, entry_type: str) -> bool:
    """为单个文件添加 Front Matter"""
    content = file_path.read_text(encoding='utf-8')

    # 跳过已有 Front Matter 的文件
    if content.startswith('---'):
        print(f"跳过（已有）: {file_path}")
        return False

    # 提取元数据
    title = extract_title(content)
    tags = extract_tags(content)
    created_at = extract_created_at(content, file_path)

    metadata = {
        'id': file_path.stem,
        'type': entry_type,
        'title': title,
        'status': 'doing',
        'created_at': created_at.isoformat(),
        'updated_at': datetime.now().isoformat(),
        'tags': tags,
    }

    # 生成新内容
    yaml_str = yaml.dump(metadata, allow_unicode=True, sort_keys=False, default_flow_style=False)
    new_content = f"---\n{yaml_str}---\n\n{content}"

    # 写回文件
    file_path.write_text(new_content, encoding='utf-8')
    print(f"已迁移: {file_path}")
    return True


def main():
    """主函数"""
    # 确定数据目录
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    data_dir = backend_dir / "data"

    if not data_dir.exists():
        print(f"数据目录不存在: {data_dir}")
        sys.exit(1)

    print(f"数据目录: {data_dir}")
    print("-" * 40)

    migrated = 0
    skipped = 0

    # 迁移各目录
    migrations = [
        ("projects", "project"),
        ("tasks", "task"),
        ("notes", "note"),
    ]

    for dir_name, entry_type in migrations:
        dir_path = data_dir / dir_name
        if not dir_path.exists():
            continue

        for md_file in sorted(dir_path.glob("*.md")):
            if migrate_file(md_file, entry_type):
                migrated += 1
            else:
                skipped += 1

    # 处理 inbox.md
    inbox_path = data_dir / "inbox.md"
    if inbox_path.exists():
        if migrate_file(inbox_path, "inbox"):
            migrated += 1
        else:
            skipped += 1

    print("-" * 40)
    print(f"完成: 迁移 {migrated} 个文件, 跳过 {skipped} 个文件")


if __name__ == '__main__':
    main()
