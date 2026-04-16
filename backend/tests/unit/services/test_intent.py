"""测试意图识别服务"""
import pytest
from unittest.mock import AsyncMock, patch

from app.routers.intent import (
    IntentRequest,
    IntentResponse,
    detect_intent_service,
)
from app.services.intent_service import IntentService, INTENT_TYPES


class TestIntentTypes:
    """意图类型常量测试"""

    def test_intent_types_defined(self):
        """测试意图类型定义完整"""
        expected_types = ["create", "read", "update", "delete", "knowledge", "review", "help"]
        assert INTENT_TYPES == expected_types


class TestIntentRequest:
    """IntentRequest DTO 测试"""

    def test_request_minimal(self):
        """测试最小化请求"""
        request = IntentRequest(text="测试输入")
        assert request.text == "测试输入"
        assert request.context is None

    def test_request_with_context(self):
        """测试带上下文的请求"""
        context = {"history": ["之前的消息"]}
        request = IntentRequest(text="测试输入", context=context)
        assert request.context == context


class TestIntentResponse:
    """IntentResponse DTO 测试"""

    def test_response_minimal(self):
        """测试最小化响应"""
        response = IntentResponse(intent="create")
        assert response.intent == "create"
        assert response.confidence == 1.0
        assert response.entities == {}
        assert response.query is None
        assert response.response_hint is None

    def test_response_full(self):
        """测试完整响应"""
        response = IntentResponse(
            intent="update",
            confidence=0.95,
            entities={"field": "status", "value": "complete"},
            query="测试任务",
            response_hint="已更新状态",
        )
        assert response.intent == "update"
        assert response.confidence == 0.95
        assert response.entities["field"] == "status"
        assert response.query == "测试任务"


class TestIntentServiceFallback:
    """IntentService 回退检测测试"""

    @pytest.fixture
    def service(self):
        """创建无 LLM caller 的服务实例"""
        return IntentService(llm_caller=None)

    def test_detect_help_intent(self, service):
        """测试检测帮助意图"""
        texts = ["帮助", "你能做什么", "怎么用这个系统"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "help"
            assert result.confidence == 0.8

    def test_detect_review_intent(self, service):
        """测试检测回顾意图"""
        texts = ["今天做了什么", "本周进度", "月报", "回顾一下"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "review"
            assert result.confidence == 0.8

    def test_detect_knowledge_intent(self, service):
        """测试检测知识图谱意图"""
        result = service._fallback_detection("MCP的知识图谱")
        assert result.intent == "knowledge"
        assert "MCP" in result.query

        result = service._fallback_detection("相关概念分析")
        assert result.intent == "knowledge"

    def test_detect_delete_intent(self, service):
        """测试检测删除意图"""
        texts = ["删除测试任务", "移除这条记录", "去掉这个"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "delete"
            assert result.confidence == 0.8

    def test_detect_update_intent(self, service):
        """测试检测更新意图"""
        texts = ["把任务标记为完成", "修改标题", "更新状态", "添加标签测试"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "update"
            assert result.confidence == 0.8

    def test_detect_read_intent(self, service):
        """测试检测查询意图"""
        texts = ["帮我找MCP的笔记", "搜索任务", "查找记录", "有没有关于X的内容"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "read"
            assert result.confidence == 0.8

    def test_detect_create_intent_default(self, service):
        """测试默认创建意图"""
        texts = ["明天开会", "学习Python", "一个新的想法"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "create"
            # 默认创建的置信度较低
            assert result.confidence == 0.6


class TestIntentServiceAsync:
    """IntentService 异步检测测试"""

    @pytest.mark.asyncio
    async def test_service_with_mock_llm(self, mock_llm_caller):
        """测试使用 Mock LLM 的意图检测"""
        service = IntentService(llm_caller=mock_llm_caller)

        result = await service.detect("帮我找MCP的笔记")

        assert result.intent in INTENT_TYPES
        assert result.confidence >= 0

    @pytest.mark.asyncio
    async def test_service_fallback_on_error(self):
        """测试错误时回退"""
        service = IntentService(llm_caller=None)

        result = await service.detect("帮我找MCP的笔记")

        assert result.intent == "read"
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_service_validates_intent_type(self):
        """测试验证意图类型"""
        from app.infrastructure.llm.mock_caller import MockCaller

        # Mock 返回无效意图
        mock = MockCaller(response='{"intent": "invalid_intent", "confidence": 0.9}')
        service = IntentService(llm_caller=mock)

        result = await service.detect("测试")

        # 应回退到默认 create
        assert result.intent == "create"


class TestIntentAPI:
    """意图识别 API 测试"""

    @pytest.mark.asyncio
    async def test_intent_endpoint(self, client):
        """测试意图识别 API 端点"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        # 重置服务缓存并设置 mock
        deps.reset_all_services()

        service = deps.get_intent_service()
        service.set_llm_caller(MockCaller(response='{"intent": "read", "confidence": 0.9, "query": "MCP"}'))

        response = await client.post(
            "/intent",
            json={"text": "帮我找MCP的笔记"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "intent" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_intent_endpoint_empty_text(self, client):
        """测试空文本请求"""
        response = await client.post(
            "/intent",
            json={"text": ""}
        )

        # 空文本应该返回 422 (validation error)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_intent_endpoint_with_context(self, client):
        """测试带上下文的请求"""
        from app.routers import deps
        from app.infrastructure.llm.mock_caller import MockCaller

        # 重置服务缓存并设置 mock
        deps.reset_all_services()

        service = deps.get_intent_service()
        service.set_llm_caller(MockCaller(response='{"intent": "create", "confidence": 0.95}'))

        response = await client.post(
            "/intent",
            json={
                "text": "明天开会",
                "context": {"history": ["今天做了什么"]}
            }
        )

        assert response.status_code == 200


class TestCategoryKeywordDetection:
    """B49: 条目类型关键词检测"""

    @pytest.fixture
    def service(self):
        return IntentService(llm_caller=None)

    def test_detect_decision_keyword(self, service):
        texts = ["记个决策：选了 Rust 而不是 Go", "做一个决定，选择方案A", "技术抉择记录"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "create"
            assert result.entities.get("category") == "decision", f"Failed for: {text}"

    def test_detect_reflection_keyword(self, service):
        texts = ["写个复盘：项目延期原因", "反思一下最近的学习方法"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "create"
            assert result.entities.get("category") == "reflection", f"Failed for: {text}"

    def test_detect_question_keyword(self, service):
        texts = ["记个疑问：为什么用 WebSocket", "一个待解问题：如何优化性能"]
        for text in texts:
            result = service._fallback_detection(text)
            assert result.intent == "create"
            assert result.entities.get("category") == "question", f"Failed for: {text}"

    def test_no_category_for_normal_create(self, service):
        result = service._fallback_detection("明天开会")
        assert result.intent == "create"
        assert result.entities.get("category") is None
