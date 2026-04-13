#!/usr/bin/env python3
"""检查并回填 `_default` 历史数据。"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
from typing import Optional

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.infrastructure.storage.sqlite import SQLiteStorage
from app.infrastructure.storage.storage_factory import StorageFactory
from app.infrastructure.storage.user_storage import UserStorage
from app.services.session_meta_store import SessionMetaStore
from app.services.sync_service import SyncService


@dataclass
class DataSnapshot:
    users_count: int
    default_entries: int
    default_markdown_files: int
    default_sessions: int
    target_user_id: str = ""
    target_username: str = ""
    target_entries: int = 0
    target_markdown_files: int = 0
    target_sessions: int = 0


def _count_markdown_files(data_dir: Path, user_id: str) -> int:
    user_dir = data_dir / "users" / user_id
    if not user_dir.exists():
        return 0

    count = 0
    for subdir in ["tasks", "notes", "projects"]:
        path = user_dir / subdir
        if path.exists():
            count += len(list(path.glob("*.md")))
    if (user_dir / "inbox.md").exists():
        count += 1
    return count


def _build_snapshot(data_dir: Path, user_id: str = "", username: str = "") -> DataSnapshot:
    sqlite = SQLiteStorage(str(data_dir / "index.db"))
    users = UserStorage(str(data_dir / "users.db"))
    session_meta = SessionMetaStore(str(data_dir / "checkpoints_meta.db"))

    snapshot = DataSnapshot(
        users_count=users.count_users(),
        default_entries=sqlite.count_entries(user_id="_default"),
        default_markdown_files=_count_markdown_files(data_dir, "_default"),
        default_sessions=len(session_meta.get_all_sessions("_default")),
        target_user_id=user_id,
        target_username=username,
    )

    if user_id:
        snapshot.target_entries = sqlite.count_entries(user_id=user_id)
        snapshot.target_markdown_files = _count_markdown_files(data_dir, user_id)
        snapshot.target_sessions = len(session_meta.get_all_sessions(user_id))

    return snapshot


def _resolve_target_user(data_dir: Path, username: Optional[str], user_id: Optional[str]):
    if not username and not user_id:
        return None

    users = UserStorage(str(data_dir / "users.db"))
    if user_id:
        user = users.get_by_id(user_id)
    else:
        user = users.get_by_username(username)

    if user is None:
        raise SystemExit(f"未找到目标用户: username={username or '-'} user_id={user_id or '-'}")
    return user


def _print_snapshot(title: str, snapshot: DataSnapshot):
    print(title)
    for key, value in asdict(snapshot).items():
        print(f"- {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description="检查或回填 `_default` 历史数据")
    parser.add_argument("--data-dir", default="./data", help="数据目录，默认 ./data")
    parser.add_argument("--username", help="目标用户名")
    parser.add_argument("--user-id", help="目标 user_id")
    parser.add_argument("--apply", action="store_true", help="实际执行回填")
    parser.add_argument(
        "--fail-if-empty",
        action="store_true",
        help="若 `_default` 与目标用户都无内容，则返回非 0 退出码",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    target_user = _resolve_target_user(data_dir, args.username, args.user_id)
    snapshot_before = _build_snapshot(
        data_dir,
        user_id=target_user.id if target_user else "",
        username=target_user.username if target_user else "",
    )
    _print_snapshot("=== Data Snapshot (before) ===", snapshot_before)

    if args.fail_if_empty:
        if (
            snapshot_before.default_entries == 0
            and snapshot_before.default_markdown_files == 0
            and snapshot_before.target_entries == 0
            and snapshot_before.target_markdown_files == 0
        ):
            raise SystemExit(2)

    if not args.apply:
        return

    if target_user is None:
        raise SystemExit("--apply 需要配合 --username 或 --user-id")

    sqlite = SQLiteStorage(str(data_dir / "index.db"))
    storage_factory = StorageFactory(str(data_dir))
    sync_service = SyncService(
        markdown_storage=storage_factory.get_markdown_storage("_default"),
        storage_factory=storage_factory,
        sqlite_storage=sqlite,
    )
    result = sync_service.claim_default_data(target_user)
    print("=== Claim Result ===")
    for key, value in result.model_dump().items():
        print(f"- {key}: {value}")

    snapshot_after = _build_snapshot(
        data_dir,
        user_id=target_user.id,
        username=target_user.username,
    )
    _print_snapshot("=== Data Snapshot (after) ===", snapshot_after)


if __name__ == "__main__":
    main()
