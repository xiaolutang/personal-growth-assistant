"""反馈 API 测试"""
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

MODULE_PATH = Path(__file__).resolve().parents[3] / "app" / "routers" / "feedback.py"
SPEC = importlib.util.spec_from_file_location("feedback_router_module", MODULE_PATH)
feedback_module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(feedback_module)
router = feedback_module.router


@pytest.fixture
async def client():
    app = FastAPI()
    app.include_router(router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


class TestFeedbackAPI:
    async def test_submit_feedback_success(self, client):
        with patch.object(feedback_module, "report_issue", return_value={
            "id": 101,
            "title": "搜索功能响应慢",
            "status": "open",
            "created_at": "2026-04-12T10:00:00Z",
        }) as mock_report_issue:
            response = await client.post("/feedback", json={
                "title": "搜索功能响应慢",
                "description": "任务列表存在卡顿",
                "severity": "medium",
            })

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "issue": {
                "id": 101,
                "title": "搜索功能响应慢",
                "status": "open",
                "created_at": "2026-04-12T10:00:00Z",
            },
        }
        mock_report_issue.assert_called_once()
        args, kwargs = mock_report_issue.call_args
        assert args[0] == "http://localhost:8001"
        assert args[1] == "搜索功能响应慢"
        assert args[2] == "personal-growth-assistant"
        assert kwargs["description"] == "任务列表存在卡顿"
        assert kwargs["severity"] == "medium"
        assert kwargs["component"] == "frontend"

    async def test_submit_feedback_returns_503_when_sdk_fails(self, client):
        with patch.object(feedback_module, "report_issue", side_effect=RuntimeError("sdk unavailable")):
            response = await client.post("/feedback", json={
                "title": "服务不可用",
                "severity": "high",
            })

        assert response.status_code == 503
        assert response.json()["detail"] == "反馈服务暂时不可用，请稍后重试"

    async def test_submit_feedback_returns_422_for_empty_title(self, client):
        response = await client.post("/feedback", json={
            "title": "   ",
            "severity": "low",
        })

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail[0]["loc"] == ["body", "title"]

    async def test_submit_feedback_returns_422_for_invalid_severity(self, client):
        response = await client.post("/feedback", json={
            "title": "严重级别错误",
            "severity": "urgent",
        })

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail[0]["loc"] == ["body", "severity"]
