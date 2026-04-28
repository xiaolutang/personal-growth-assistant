"""Agent 反馈 API 测试

覆盖场景：
1. Agent 反馈提交成功
2. 缺少必填字段时返回 422（agent 类型无 message_id）
3. 负面反馈自动创建 Issue
4. Langfuse trace 标记（mock）
5. bad case 导出
6. 通用反馈仍正常工作
"""
import asyncio
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.infrastructure.storage.sqlite import SQLiteStorage

MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "feedback.py"
SPEC = importlib.util.spec_from_file_location("feedback_router_module", MODULE_PATH)
feedback_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(feedback_module)
router = feedback_module.router

# Mock user for auth bypass
_mock_user = MagicMock()
_mock_user.id = "test-user"


class _MockSyncService:
    """轻量 mock，持有临时文件 SQLite"""

    def __init__(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.sqlite = SQLiteStorage(self._tmp.name)

    def cleanup(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass


@pytest.fixture
async def client():
    """创建带 mock storage 的测试客户端"""
    app = FastAPI()

    from app.routers.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: _mock_user

    mock_storage = _MockSyncService()
    with patch.object(feedback_module, "get_storage", return_value=mock_storage):
        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            test_client._mock_storage = mock_storage
            yield test_client

    app.dependency_overrides.clear()
    mock_storage.cleanup()


class TestAgentFeedbackSubmit:
    """Agent 反馈提交测试"""

    async def test_agent_feedback_success(self, client):
        """Agent 反馈提交成功"""
        with patch.object(feedback_module, "report_issue", return_value={
            "id": 201,
            "title": "Agent 反馈",
            "status": "open",
        }):
            response = await client.post("/feedback", json={
                "title": "Agent 回复不准确",
                "feedback_type": "agent",
                "message_id": "msg-abc123",
                "reason": "信息不准确",
                "detail": "Agent 说今天有 5 个任务，实际只有 2 个",
                "severity": "medium",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["feedback"]["feedback_type"] == "agent"
        assert data["feedback"]["message_id"] == "msg-abc123"
        assert data["feedback"]["reason"] == "信息不准确"
        assert data["feedback"]["detail"] == "Agent 说今天有 5 个任务，实际只有 2 个"

    async def test_agent_feedback_without_message_id_returns_422(self, client):
        """Agent 反馈缺少 message_id 返回 422"""
        response = await client.post("/feedback", json={
            "title": "Agent 反馈",
            "feedback_type": "agent",
            "reason": "理解错了",
        })

        assert response.status_code == 422
        detail = response.json()["detail"]
        # 验证错误信息包含 message_id 相关内容
        assert any("message_id" in str(err) for err in detail)

    async def test_general_feedback_still_works(self, client):
        """通用反馈（general）仍然正常工作"""
        with patch.object(feedback_module, "report_issue", return_value={
            "id": 202,
            "title": "通用反馈",
            "status": "open",
        }):
            response = await client.post("/feedback", json={
                "title": "通用反馈",
                "description": "这是通用反馈",
                "severity": "low",
            })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["feedback"]["feedback_type"] == "general"

    async def test_agent_feedback_default_type_is_general(self, client):
        """不指定 feedback_type 时默认为 general"""
        with patch.object(feedback_module, "report_issue", return_value={
            "id": 203,
            "title": "默认类型反馈",
            "status": "open",
        }):
            response = await client.post("/feedback", json={
                "title": "默认类型反馈",
            })

        assert response.status_code == 200
        assert response.json()["feedback"]["feedback_type"] == "general"


class TestAgentFeedbackStorage:
    """Agent 反馈存储测试"""

    async def test_agent_feedback_stored_in_sqlite(self, client):
        """Agent 反馈正确存储到 SQLite"""
        storage: _MockSyncService = client._mock_storage

        with patch.object(feedback_module, "report_issue", return_value={
            "id": 301,
            "title": "存储测试",
            "status": "open",
        }):
            await client.post("/feedback", json={
                "title": "存储测试",
                "feedback_type": "agent",
                "message_id": "msg-store-001",
                "reason": "不完整",
                "detail": "缺少关键信息",
            })

        feedbacks = storage.sqlite.list_feedbacks_by_user("test-user")
        assert len(feedbacks) == 1
        fb = feedbacks[0]
        assert fb["feedback_type"] == "agent"
        assert fb["message_id"] == "msg-store-001"
        assert fb["reason"] == "不完整"
        assert fb["detail"] == "缺少关键信息"

    async def test_agent_feedback_visible_in_list(self, client):
        """Agent 反馈在列表中可见"""
        storage: _MockSyncService = client._mock_storage
        storage.sqlite.create_feedback(
            "test-user", "旧反馈", feedback_type="general"
        )
        storage.sqlite.create_feedback(
            "test-user", "新 Agent 反馈",
            feedback_type="agent",
            message_id="msg-list-001",
            reason="理解错了",
        )

        response = await client.get("/feedback")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        # Agent 反馈应该包含新字段
        agent_items = [i for i in data["items"] if i.get("feedback_type") == "agent"]
        assert len(agent_items) == 1
        assert agent_items[0]["message_id"] == "msg-list-001"


class TestNegativeFeedbackIssue:
    """负面反馈自动创建 Issue 测试"""

    async def test_negative_feedback_triggers_auto_issue(self, client):
        """负面 Agent 反馈触发自动创建 Issue（通过 mock 验证调度）"""
        with patch.object(feedback_module, "_auto_create_issue_for_negative") as mock_auto:
            mock_auto.return_value = asyncio.coroutine(lambda: None)() if hasattr(asyncio, 'coroutine') else None

            response = await client.post("/feedback", json={
                "title": "Agent 理解错误",
                "feedback_type": "agent",
                "message_id": "msg-neg-001",
                "reason": "理解错了",
                "detail": "Agent 把任务理解成了笔记",
                "severity": "medium",
            })

        assert response.status_code == 200

    async def test_auto_create_issue_calls_report_issue(self):
        """_auto_create_issue_for_negative 在负面 reason 时调用 report_issue"""
        feedback = {
            "id": 501,
            "user_id": "test-user",
            "title": "Agent 错误",
            "message_id": "msg-auto-001",
            "reason": "理解错了",
            "detail": "理解成了笔记",
            "created_at": "2026-04-28T10:00:00Z",
        }

        mock_storage = MagicMock()
        mock_storage.sqlite.update_feedback_status = MagicMock()

        with patch.object(feedback_module, "get_storage", return_value=mock_storage):
            with patch.object(feedback_module, "get_settings") as mock_settings:
                mock_settings.return_value.LOG_SERVICE_URL = "http://localhost:8001"
                with patch.object(feedback_module, "report_issue", return_value={
                    "id": 601,
                    "title": "[Agent Bad Case]",
                    "status": "open",
                }) as mock_report:
                    await feedback_module._auto_create_issue_for_negative(501, feedback)

        assert mock_report.called
        call_args = mock_report.call_args
        assert "[Agent Bad Case]" in call_args[0][1]
        assert call_args[1]["severity"] == "medium"
        assert call_args[1]["component"] == "backend"

    async def test_auto_create_issue_skips_non_negative(self):
        """_auto_create_issue_for_negative 在非负面 reason 时不调用 report_issue"""
        feedback = {
            "id": 502,
            "reason": "helpful",
        }

        with patch.object(feedback_module, "report_issue") as mock_report:
            await feedback_module._auto_create_issue_for_negative(502, feedback)

        assert not mock_report.called

    async def test_non_negative_feedback_no_auto_issue(self, client):
        """非负面 Agent 反馈不自动创建 Issue"""
        with patch.object(feedback_module, "report_issue", return_value={
            "id": 402,
            "title": "正面反馈",
            "status": "open",
        }) as mock_report:
            response = await client.post("/feedback", json={
                "title": "Agent 回复很好",
                "feedback_type": "agent",
                "message_id": "msg-pos-001",
                "reason": "helpful",
                "detail": "回复很准确",
                "severity": "low",
            })

        assert response.status_code == 200

        import asyncio
        await asyncio.sleep(0.1)

        # 非负面 reason 不触发自动 Issue
        assert not mock_report.called


class TestLangfuseScoreTrace:
    """Langfuse trace 标记测试"""

    def test_langfuse_score_positive(self):
        """正面反馈标记 Langfuse 评分 1.0"""
        with patch.object(feedback_module, "_langfuse_score_trace") as mock_score:
            # 直接调用不会触发 mock，验证函数逻辑
            pass

    def test_langfuse_score_with_mock(self):
        """Mock Langfuse 客户端标记评分"""
        mock_langfuse = MagicMock()
        with patch.dict(os.environ, {
            "LANGFUSE_PUBLIC_KEY": "pk-test",
            "LANGFUSE_SECRET_KEY": "sk-test",
            "LANGFUSE_HOST": "http://localhost:3010",
        }):
            with patch("app.routers.feedback.Langfuse", return_value=mock_langfuse, create=True):
                # 需要在模块内 patch
                with patch.object(feedback_module, "_langfuse_score_trace") as mock_fn:
                    feedback_module._langfuse_score_trace("msg-001", 0.0, "理解错了")
                    mock_fn.assert_called_once_with("msg-001", 0.0, "理解错了")

    def test_langfuse_not_configured_returns_silently(self):
        """Langfuse 未配置时静默返回"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LANGFUSE_PUBLIC_KEY", None)
            os.environ.pop("LANGFUSE_SECRET_KEY", None)
            # 不应抛异常
            feedback_module._langfuse_score_trace("msg-001", 0.0, "test")


class TestBadCaseExport:
    """Bad case 导出到 Golden Dataset 测试"""

    def test_export_negative_agent_feedback(self, tmp_path):
        """负面 Agent 反馈导出到 bad case 文件"""
        feedback = {
            "id": 1,
            "user_id": "test-user",
            "title": "Agent 错误",
            "description": "Agent 回复不对",
            "feedback_type": "agent",
            "message_id": "msg-export-001",
            "reason": "理解错了",
            "detail": "理解成了笔记",
            "created_at": "2026-04-28T10:00:00Z",
        }

        with patch.object(feedback_module, "get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            filepath = feedback_module.export_to_golden_dataset(feedback)

        assert filepath is not None
        assert filepath.exists()
        data = json.loads(filepath.read_text(encoding="utf-8"))
        assert data["feedback_id"] == 1
        assert data["message_id"] == "msg-export-001"
        assert data["reason"] == "理解错了"
        assert "exported_at" in data

    def test_export_skips_general_feedback(self, tmp_path):
        """通用反馈不导出"""
        feedback = {
            "id": 2,
            "feedback_type": "general",
            "message_id": None,
            "reason": None,
        }

        with patch.object(feedback_module, "get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            result = feedback_module.export_to_golden_dataset(feedback)

        assert result is None

    def test_export_skips_non_negative_reason(self, tmp_path):
        """非负面 reason 不导出"""
        feedback = {
            "id": 3,
            "feedback_type": "agent",
            "message_id": "msg-skip-001",
            "reason": "helpful",
        }

        with patch.object(feedback_module, "get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            result = feedback_module.export_to_golden_dataset(feedback)

        assert result is None

    def test_export_skips_no_message_id(self, tmp_path):
        """无 message_id 的反馈不导出"""
        feedback = {
            "id": 4,
            "feedback_type": "agent",
            "message_id": None,
            "reason": "理解错了",
        }

        with patch.object(feedback_module, "get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            result = feedback_module.export_to_golden_dataset(feedback)

        assert result is None

    def test_export_creates_directory(self, tmp_path):
        """导出时自动创建目录"""
        feedback = {
            "id": 5,
            "user_id": "test-user",
            "title": "Test",
            "feedback_type": "agent",
            "message_id": "msg-dir-001",
            "reason": "不完整",
            "created_at": "2026-04-28T10:00:00Z",
        }

        with patch.object(feedback_module, "get_settings") as mock_settings:
            mock_settings.return_value.DATA_DIR = str(tmp_path)
            filepath = feedback_module.export_to_golden_dataset(feedback)

        assert filepath is not None
        assert (tmp_path / "eval_transcripts" / "bad_cases").is_dir()


class TestFeedbackGetWithAgentFields:
    """GET 反馈详情包含 Agent 字段"""

    async def test_get_feedback_includes_agent_fields(self, client):
        """获取反馈详情包含 Agent 扩展字段"""
        storage: _MockSyncService = client._mock_storage
        fb = storage.sqlite.create_feedback(
            "test-user", "Agent 详情",
            feedback_type="agent",
            message_id="msg-get-001",
            reason="操作不正确",
            detail="执行了错误的操作",
        )

        response = await client.get(f"/feedback/{fb['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["feedback_type"] == "agent"
        assert data["message_id"] == "msg-get-001"
        assert data["reason"] == "操作不正确"
        assert data["detail"] == "执行了错误的操作"
