"""B23: MCP Server 认证增强 — JWT + 用户隔离 + 新工具 测试"""
import os
import jwt
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# 辅助：创建/验证 JWT
# ---------------------------------------------------------------------------

_SECRET = "test-mcp-secret-key"
_ALGORITHM = "HS256"


def _make_token(user_id: str, secret: str = _SECRET, exp_offset_days: int = 7) -> str:
    """创建一个有效 JWT token"""
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=exp_offset_days),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


# ===========================================================================
# 认证测试
# ===========================================================================

class TestVerifyToken:
    """_verify_token 在各种 token 情况下的行为"""

    def test_valid_token_returns_user_id(self):
        """有效 token -> 返回 user_id"""
        from app.mcp.server import _verify_token

        token = _make_token("user-abc")
        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": token}), \
             patch("app.services.auth_service.decode_access_token") as mock_decode:
            mock_decode.return_value = MagicMock(sub="user-abc")
            uid = _verify_token()
            assert uid == "user-abc"

    def test_missing_token_raises_system_exit(self):
        """空 token -> SystemExit"""
        from app.mcp.server import _verify_token

        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": ""}, clear=False):
            os.environ["MCP_AUTH_TOKEN"] = ""
            with pytest.raises(SystemExit):
                _verify_token()

    def test_invalid_token_raises_system_exit(self):
        """无效 token -> SystemExit"""
        from app.mcp.server import _verify_token

        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": "invalid.jwt.token"}), \
             patch("app.services.auth_service.decode_access_token", side_effect=jwt.InvalidTokenError("bad")):
            with pytest.raises(SystemExit):
                _verify_token()

    def test_expired_token_raises_system_exit(self):
        """过期 token -> SystemExit"""
        from app.mcp.server import _verify_token

        expired_token = _make_token("user-x", exp_offset_days=-1)
        with patch.dict(os.environ, {"MCP_AUTH_TOKEN": expired_token}), \
             patch("app.services.auth_service.decode_access_token", side_effect=jwt.ExpiredSignatureError):
            with pytest.raises(SystemExit):
                _verify_token()


# ===========================================================================
# call_tool 传递 user_id
# ===========================================================================

class TestCallToolWithAuth:
    """call_tool 正确将 authenticated_user_id 传递给 handler"""

    @pytest.mark.asyncio
    async def test_call_tool_passes_user_id(self):
        """handler 接收到正确的 user_id 参数"""
        from app.mcp.server import call_tool

        mock_storage = MagicMock()
        mock_handler = AsyncMock(return_value=[])

        with patch("app.mcp.server.storage", mock_storage), \
             patch("app.mcp.server.authenticated_user_id", "user-42"), \
             patch("app.mcp.server.TOOL_HANDLERS", {"list_entries": mock_handler}):
            await call_tool("list_entries", {"limit": 5})
            mock_handler.assert_called_once_with(mock_storage, {"limit": 5}, "user-42")


# ===========================================================================
# 新工具路由测试
# ===========================================================================

class TestNewToolsRouting:
    """get_review_summary 和 get_knowledge_stats 可路由"""

    def test_get_review_summary_routable(self):
        from app.mcp.server import TOOL_HANDLERS
        assert "get_review_summary" in TOOL_HANDLERS
        assert callable(TOOL_HANDLERS["get_review_summary"])

    def test_get_knowledge_stats_routable(self):
        from app.mcp.server import TOOL_HANDLERS
        assert "get_knowledge_stats" in TOOL_HANDLERS
        assert callable(TOOL_HANDLERS["get_knowledge_stats"])


# ===========================================================================
# Handler 功能测试
# ===========================================================================

class TestHandleGetReviewSummary:
    """get_review_summary handler 测试"""

    @pytest.mark.asyncio
    async def test_daily_report_returns_data(self):
        """日报返回数据"""
        from app.mcp.handlers import handle_get_review_summary

        mock_storage = MagicMock()
        mock_report = MagicMock(
            date="2026-04-15",
            task_stats=MagicMock(total=5, completed=3, doing=1, wait_start=1, completion_rate=60.0),
            note_stats=MagicMock(total=2),
            ai_summary=None,
        )
        mock_review_svc = MagicMock()
        mock_review_svc.get_daily_report.return_value = mock_report

        with patch("app.services.review_service.ReviewService", return_value=mock_review_svc):
            result = await handle_get_review_summary(mock_storage, {"period": "daily"}, "user-1")
            assert len(result) == 1
            assert "日报" in result[0].text
            assert "2026-04-15" in result[0].text

    @pytest.mark.asyncio
    async def test_weekly_report_returns_data(self):
        """周报返回数据"""
        from app.mcp.handlers import handle_get_review_summary

        mock_storage = MagicMock()
        mock_report = MagicMock(
            start_date="2026-04-13",
            end_date="2026-04-19",
            task_stats=MagicMock(total=10, completed=7, doing=2, wait_start=1, completion_rate=70.0),
            note_stats=MagicMock(total=3),
            ai_summary=None,
        )
        mock_review_svc = MagicMock()
        mock_review_svc.get_weekly_report.return_value = mock_report

        with patch("app.services.review_service.ReviewService", return_value=mock_review_svc):
            result = await handle_get_review_summary(mock_storage, {"period": "weekly"}, "user-1")
            assert len(result) == 1
            assert "周报" in result[0].text

    @pytest.mark.asyncio
    async def test_no_sqlite_returns_error(self):
        """SQLite 不可用时返回提示"""
        from app.mcp.handlers import handle_get_review_summary

        mock_storage = MagicMock()
        mock_storage.sqlite = None
        result = await handle_get_review_summary(mock_storage, {}, "user-1")
        assert "不可用" in result[0].text


class TestHandleGetKnowledgeStats:
    """get_knowledge_stats handler 测试"""

    @pytest.mark.asyncio
    async def test_returns_stats(self):
        """返回统计数据"""
        from app.mcp.handlers import handle_get_knowledge_stats

        mock_storage = MagicMock()
        mock_stats = MagicMock(
            concept_count=15,
            relation_count=8,
            category_distribution={"技术": 10, "概念": 5},
            top_concepts=[{"name": "Python", "entry_count": 5}, {"name": "Rust", "entry_count": 3}],
        )

        with patch("app.services.knowledge_service.KnowledgeService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_knowledge_stats = AsyncMock(return_value=mock_stats)
            result = await handle_get_knowledge_stats(mock_storage, {}, "user-1")
            assert len(result) == 1
            assert "15" in result[0].text
            assert "8" in result[0].text
            assert "Python" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_stats(self):
        """空统计也能返回"""
        from app.mcp.handlers import handle_get_knowledge_stats

        mock_storage = MagicMock()
        mock_stats = MagicMock(
            concept_count=0,
            relation_count=0,
            category_distribution={},
            top_concepts=[],
        )

        with patch("app.services.knowledge_service.KnowledgeService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_knowledge_stats = AsyncMock(return_value=mock_stats)
            result = await handle_get_knowledge_stats(mock_storage, {}, "user-1")
            assert len(result) == 1
            assert "0" in result[0].text


# ===========================================================================
# 用户隔离测试
# ===========================================================================

class TestUserIsolation:
    """不同 user_id 数据不互通"""

    @pytest.mark.asyncio
    async def test_list_entries_isolated_by_user(self):
        """list_entries 传递 user_id 给 SQLite"""
        from app.mcp.handlers import handle_list_entries

        mock_storage = MagicMock()
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []
        mock_storage.sqlite = mock_sqlite

        await handle_list_entries(mock_storage, {"limit": 10}, "user-A")

        mock_sqlite.list_entries.assert_called_once()
        call_kwargs = mock_sqlite.list_entries.call_args
        assert call_kwargs.kwargs.get("user_id") == "user-A"

    @pytest.mark.asyncio
    async def test_get_entry_rejects_other_user(self):
        """get_entry 拒绝访问其他用户的条目"""
        from app.mcp.handlers import handle_get_entry

        mock_storage = MagicMock()
        mock_storage.markdown.read_entry.return_value = MagicMock(title="test", id="task-abc")
        mock_sqlite = MagicMock()
        mock_sqlite.get_entry.return_value = {"id": "task-abc", "user_id": "user-B"}
        mock_storage.sqlite = mock_sqlite

        result = await handle_get_entry(mock_storage, {"id": "task-abc"}, "user-A")
        assert "找不到" in result[0].text

    @pytest.mark.asyncio
    async def test_update_entry_rejects_other_user(self):
        """update_entry 拒绝修改其他用户的条目"""
        from app.mcp.handlers import handle_update_entry

        mock_storage = MagicMock()
        mock_sqlite = MagicMock()
        mock_sqlite.get_entry.return_value = {"id": "task-abc", "user_id": "user-B"}
        mock_storage.sqlite = mock_sqlite

        result = await handle_update_entry(mock_storage, {"id": "task-abc"}, "user-A")
        assert "找不到" in result[0].text

    @pytest.mark.asyncio
    async def test_delete_entry_rejects_other_user(self):
        """delete_entry 拒绝删除其他用户的条目"""
        from app.mcp.handlers import handle_delete_entry

        mock_storage = MagicMock()
        mock_sqlite = MagicMock()
        mock_sqlite.get_entry.return_value = {"id": "task-abc", "user_id": "user-B"}
        mock_storage.sqlite = mock_sqlite

        result = await handle_delete_entry(mock_storage, {"id": "task-abc"}, "user-A")
        assert "删除失败" in result[0].text

    @pytest.mark.asyncio
    async def test_create_entry_passes_user_id_to_sync_entry(self):
        """create_entry 将 user_id 传递给 sync_entry"""
        from app.mcp.handlers import handle_create_entry

        mock_storage = MagicMock()
        mock_storage.markdown.write_entry = MagicMock()
        mock_sqlite = MagicMock()
        mock_storage.sqlite = mock_sqlite
        mock_storage.sync_entry = AsyncMock()

        result = await handle_create_entry(
            mock_storage,
            {"type": "task", "title": "测试", "content": "内容"},
            "user-C",
        )
        assert "已创建" in result[0].text
        # 验证 sync_entry 传入了 user_id（不再直接调用 sqlite.upsert_entry）
        mock_storage.sync_entry.assert_called_once()
        call_kwargs = mock_storage.sync_entry.call_args
        assert call_kwargs.kwargs.get("user_id") == "user-C"


# ===========================================================================
# 回归：现有 9 个工具仍可调用
# ===========================================================================

class TestExistingToolsRegression:
    """确保原有 9 个工具 handler 签名更新后仍正常工作"""

    @pytest.mark.asyncio
    async def test_all_9_handlers_accept_user_id(self):
        """所有原有 handler 接受 user_id 参数（不报错）"""
        from app.mcp.handlers import (
            handle_list_entries,
            handle_get_entry,
            handle_create_entry,
            handle_update_entry,
            handle_delete_entry,
            handle_search_entries,
            handle_get_knowledge_graph,
            handle_get_related_concepts,
            handle_get_project_progress,
        )

        mock_storage = MagicMock()
        # 最小 mock：使每个 handler 能快速返回
        mock_storage.sqlite = None
        mock_storage.markdown.list_entries.return_value = []
        mock_storage.markdown.read_entry.return_value = None
        # get_markdown_storage 返回的 mock 也需要配置
        mock_user_md = MagicMock()
        mock_user_md.list_entries.return_value = []
        mock_user_md.read_entry.return_value = None
        mock_storage.get_markdown_storage.return_value = mock_user_md
        mock_storage.qdrant = AsyncMock()
        mock_storage.qdrant.search = AsyncMock(return_value=[])
        mock_storage.neo4j = AsyncMock()
        mock_storage.neo4j.get_knowledge_graph = AsyncMock(return_value={"center": None, "connections": []})
        mock_storage.neo4j.get_related_concepts = AsyncMock(return_value=[])
        mock_storage.delete_entry = AsyncMock(return_value=False)

        uid = "user-test"

        # list_entries
        r = await handle_list_entries(mock_storage, {}, uid)
        assert r[0].type == "text"

        # get_entry
        r = await handle_get_entry(mock_storage, {"id": "x"}, uid)
        assert "找不到" in r[0].text

        # delete_entry
        r = await handle_delete_entry(mock_storage, {"id": "x"}, uid)
        assert "删除失败" in r[0].text

        # search_entries
        r = await handle_search_entries(mock_storage, {"query": "test"}, uid)
        assert r[0].type == "text"

        # get_knowledge_graph
        r = await handle_get_knowledge_graph(mock_storage, {"concept": "Python"}, uid)
        assert "找不到" in r[0].text

        # get_related_concepts
        r = await handle_get_related_concepts(mock_storage, {"concept": "Python"}, uid)
        assert "没有找到" in r[0].text
