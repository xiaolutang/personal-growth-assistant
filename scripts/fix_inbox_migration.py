"""
修复 R003 迁移遗漏：对比 SQLite 索引与用户目录实际文件，复制遗漏的 Markdown 文件。

问题：R003 迁移时只更新了 SQLite entries.user_id，未复制 Markdown 文件。
导致 list_entries（走 SQLite 索引）能查到，但 get_entry/update_entry（走 Markdown 文件）返回 404。

覆盖范围：所有类别（inbox/task/note/project）。

使用方式：
    python3 scripts/fix_inbox_migration.py [--dry-run]
"""
import argparse
import shutil
import sqlite3
from pathlib import Path

CATEGORY_DIRS = {
    "inbox": "",
    "task": "tasks",
    "note": "notes",
    "project": "projects",
}


def get_project_root() -> Path:
    p = Path(__file__).resolve().parent.parent
    if (p / "backend").exists():
        return p
    return p.parent


def find_orphan_entries(index_db: Path, data_dir: Path) -> list[dict]:
    """找出 SQLite 中 user_id != '_default' 但 Markdown 文件不在用户目录的条目"""
    conn = sqlite3.connect(str(index_db))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT id, type, file_path, user_id FROM entries "
        "WHERE user_id != '_default'"
    ).fetchall()

    orphans = []
    for row in rows:
        entry_id = row["id"]
        entry_type = row["type"]
        file_path = row["file_path"]
        user_id = row["user_id"]

        user_dir = data_dir / "users" / user_id
        # 根据 category 确定目标路径
        cat_dir = CATEGORY_DIRS.get(entry_type, "")
        if cat_dir:
            target_file = user_dir / cat_dir / f"{entry_id}.md"
        else:
            target_file = user_dir / f"{entry_id}.md"

        if not target_file.exists():
            # 从 data/ 根目录尝试多种来源
            candidates = [
                data_dir / file_path,                          # file_path as-is
                data_dir / f"{entry_id}.md",                   # root level
            ]
            if cat_dir:
                candidates.append(data_dir / cat_dir / f"{entry_id}.md")

            source = None
            for c in candidates:
                if c.exists():
                    source = c
                    break

            if source:
                orphans.append({
                    "entry_id": entry_id,
                    "entry_type": entry_type,
                    "user_id": user_id,
                    "source": source,
                    "target": target_file,
                })
            else:
                print(f"  WARNING: {entry_id} ({entry_type}) no source file found, skipping")

    conn.close()
    return orphans


def fix_orphans(orphans: list[dict], dry_run: bool = False) -> int:
    fixed = 0
    for orphan in orphans:
        source = orphan["source"]
        target = orphan["target"]
        user_id = orphan["user_id"]
        entry_id = orphan["entry_id"]
        entry_type = orphan["entry_type"]

        if dry_run:
            print(f"  [DRY-RUN] [{entry_type}] {source} -> {target}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(target))
            print(f"  FIXED: [{entry_type}] {entry_id} for user={user_id}")
        fixed += 1

    return fixed


def main():
    parser = argparse.ArgumentParser(description="Fix R003 migration gap - copy missing Markdown files to user directories")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    args = parser.parse_args()

    root = get_project_root()
    data_dir = root / "data"
    index_db = data_dir / "index.db"

    if not index_db.exists():
        print(f"ERROR: {index_db} not found")
        return

    print("Scanning for orphan entries (all categories)...")
    orphans = find_orphan_entries(index_db, data_dir)

    if not orphans:
        print("No orphan entries found. Migration is complete.")
        return

    # 按类型分组统计
    by_type: dict[str, int] = {}
    for o in orphans:
        by_type[o["entry_type"]] = by_type.get(o["entry_type"], 0) + 1
    summary = ", ".join(f"{t}: {c}" for t, c in sorted(by_type.items()))
    print(f"Found {len(orphans)} orphan entries ({summary}):")

    fixed = fix_orphans(orphans, dry_run=args.dry_run)
    action = "Would fix" if args.dry_run else "Fixed"
    print(f"\n{action} {fixed} entries.")


if __name__ == "__main__":
    main()
