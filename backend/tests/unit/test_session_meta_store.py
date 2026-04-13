"""SessionMetaStore 用户隔离测试"""
import tempfile
import os
from pathlib import Path

from app.services.session_meta_store import SessionMetaStore


def _make_store(tmp_dir: str) -> SessionMetaStore:
    db_path = str(Path(tmp_dir) / "session_meta.db")
    return SessionMetaStore(db_path)


def test_create_session_with_user_id():
    """创建会话关联 user_id"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        meta = store.create_session("s1", "测试", user_id="user_a")
        assert meta.id == "s1"
        assert meta.title == "测试"


def test_list_sessions_filters_by_user():
    """list_sessions 只返回当前用户的会话"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.create_session("s1", "A的会话", user_id="user_a")
        store.create_session("s2", "B的会话", user_id="user_b")
        store.create_session("s3", "A的会话2", user_id="user_a")

        a_sessions = store.get_all_sessions(user_id="user_a")
        assert len(a_sessions) == 2
        assert {s.title for s in a_sessions} == {"A的会话", "A的会话2"}

        b_sessions = store.get_all_sessions(user_id="user_b")
        assert len(b_sessions) == 1
        assert b_sessions[0].title == "B的会话"


def test_get_session_respects_user_id():
    """get_session 按 user_id 过滤"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.create_session("s1", "A的会话", user_id="user_a")

        # 正确 user_id 能拿到
        assert store.get_session("s1", user_id="user_a") is not None
        # 错误 user_id 拿不到
        assert store.get_session("s1", user_id="user_b") is None


def test_update_title_respects_user_id():
    """update_title 只影响同用户的会话"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.create_session("s1", "原标题", user_id="user_a")

        # 错误 user_id 更新不了
        assert store.update_title("s1", "新标题", user_id="user_b") is False
        # 正确 user_id 可以更新
        assert store.update_title("s1", "新标题", user_id="user_a") is True
        assert store.get_session("s1", user_id="user_a").title == "新标题"


def test_delete_session_respects_user_id():
    """delete_session 只删除同用户的会话"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.create_session("s1", "A的会话", user_id="user_a")

        # 错误 user_id 删不了
        assert store.delete_session("s1", user_id="user_b") is False
        assert store.session_exists("s1", user_id="user_a") is True

        # 正确 user_id 可以删
        assert store.delete_session("s1", user_id="user_a") is True
        assert store.session_exists("s1", user_id="user_a") is False


def test_session_exists_respects_user_id():
    """session_exists 按 user_id 过滤"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.create_session("s1", "测试", user_id="user_a")

        assert store.session_exists("s1", user_id="user_a") is True
        assert store.session_exists("s1", user_id="user_b") is False


def test_default_user_migration():
    """已有数据迁移到 _default 用户"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        # 使用 _default 创建（模拟旧数据）
        store.create_session("s1", "旧会话", user_id="_default")

        # _default 用户能看到
        assert store.session_exists("s1", user_id="_default") is True
        # 其他用户看不到
        assert store.session_exists("s1", user_id="user_a") is False


def test_touch_session_respects_user_id():
    """touch_session 只影响同用户的会话"""
    with tempfile.TemporaryDirectory() as tmp:
        store = _make_store(tmp)
        store.create_session("s1", "测试", user_id="user_a")

        assert store.touch_session("s1", user_id="user_b") is False
        assert store.touch_session("s1", user_id="user_a") is True
