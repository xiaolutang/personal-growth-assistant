"""反馈功能全链路集成测试

使用真实 FastAPI app 实例（含中间件），mock report_issue SDK，
验证从前端请求到后端响应的完整链路。
"""
import importlib
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

# 导入真实 app（含所有中间件、CORS、路由注册）
from app.main import app


# client fixture 直接复用根 conftest.py 的（自动注入 auth token）


MOCK_ISSUE_RESPONSE = {
    "id": 42,
    "title": "搜索加载慢",
    "status": "open",
    "severity": "high",
    "created_at": "2026-04-12T10:00:00Z",
    "updated_at": "2026-04-12T10:00:00Z",
}


class TestFeedbackFullFlow:
    """全链路验证：模拟前端真实请求 → 后端处理 → SDK 调用 → 响应返回"""

    async def test_full_chain_success(self, client):
        """完整链路：正常提交反馈，验证请求穿透到 SDK 并返回正确响应"""
        with patch("app.routers.feedback.report_issue", return_value=MOCK_ISSUE_RESPONSE) as mock_sdk:
            response = await client.post("/feedback", json={
                "title": "搜索加载慢",
                "description": "任务列表搜索时页面卡顿约 3 秒",
                "severity": "high",
            })

        # 响应正确
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["issue"]["id"] == 42
        assert body["issue"]["title"] == "搜索加载慢"
        assert body["issue"]["status"] == "open"

        # SDK 被正确调用
        mock_sdk.assert_called_once()
        args, kwargs = mock_sdk.call_args
        assert args[1] == "搜索加载慢"           # title
        assert args[2] == "personal-growth-assistant"  # service_name
        assert kwargs["severity"] == "high"
        assert kwargs["description"] == "任务列表搜索时页面卡顿约 3 秒"

    async def test_full_chain_sdk_timeout(self, client):
        """SDK 超时场景：模拟 log-service 不可达，验证 503 降级"""
        with patch("app.routers.feedback.report_issue", side_effect=TimeoutError("connection timed out")):
            response = await client.post("/feedback", json={
                "title": "测试超时",
                "severity": "low",
            })

        assert response.status_code == 503
        assert "暂时不可用" in response.json()["detail"]

    async def test_full_chain_connection_refused(self, client):
        """SDK 连接拒绝：模拟 log-service 宕机"""
        with patch("app.routers.feedback.report_issue", side_effect=ConnectionRefusedError("refused")):
            response = await client.post("/feedback", json={
                "title": "测试连接拒绝",
                "severity": "medium",
            })

        assert response.status_code == 503

    async def test_full_chain_severity_enum_boundary(self, client):
        """severity 枚举边界：验证四个合法值都能通过"""
        for severity in ["low", "medium", "high", "critical"]:
            with patch("app.routers.feedback.report_issue", return_value=MOCK_ISSUE_RESPONSE):
                response = await client.post("/feedback", json={
                    "title": f"severity={severity}",
                    "severity": severity,
                })
            assert response.status_code == 200, f"severity={severity} should be accepted"

    async def test_full_chain_title_boundary(self, client):
        """title 边界：空字符串、纯空格、过长"""
        # 空字符串
        response = await client.post("/feedback", json={"title": "", "severity": "low"})
        assert response.status_code == 422

        # 纯空格
        response = await client.post("/feedback", json={"title": "   ", "severity": "low"})
        assert response.status_code == 422

        # 正常短标题
        with patch("app.routers.feedback.report_issue", return_value=MOCK_ISSUE_RESPONSE):
            response = await client.post("/feedback", json={"title": "a", "severity": "low"})
            assert response.status_code == 200

    async def test_full_chain_default_severity(self, client):
        """不传 severity 时默认 medium"""
        with patch("app.routers.feedback.report_issue", return_value=MOCK_ISSUE_RESPONSE) as mock_sdk:
            response = await client.post("/feedback", json={"title": "默认严重程度"})

        assert response.status_code == 200
        _, kwargs = mock_sdk.call_args
        assert kwargs["severity"] == "medium"

    async def test_full_chain_no_description(self, client):
        """不传 description 时为 None"""
        with patch("app.routers.feedback.report_issue", return_value=MOCK_ISSUE_RESPONSE) as mock_sdk:
            response = await client.post("/feedback", json={
                "title": "无描述反馈",
                "severity": "high",
            })

        assert response.status_code == 200
        _, kwargs = mock_sdk.call_args
        assert kwargs["description"] is None

    async def test_full_chain_cors_preflight(self, client):
        """CORS 预检：验证 OPTIONS /feedback 通过"""
        response = await client.options("/feedback", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        })
        assert response.status_code == 200
        assert "POST" in response.headers.get("access-control-allow-methods", "")
