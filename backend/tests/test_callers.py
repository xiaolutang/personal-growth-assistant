"""测试 LLM Callers"""
import pytest

from app.callers import APICaller, MockCaller
from app.services import TaskParser


class TestMockCaller:
    """MockCaller 单元测试"""

    @pytest.mark.asyncio
    async def test_returns_preset_response(self):
        """测试返回预设响应"""
        mock_response = '{"tasks": []}'
        caller = MockCaller(response=mock_response)

        result = await caller.call([{"role": "user", "content": "test"}])
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_ignores_response_format(self):
        """测试忽略 response_format 参数"""
        mock_response = '{"tasks": []}'
        caller = MockCaller(response=mock_response)

        result = await caller.call(
            [{"role": "user", "content": "test"}],
            response_format={"type": "json_object"}
        )
        assert result == mock_response


class TestAPICaller:
    """APICaller 集成测试（需要网络和 API Key）"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_api_call(self):
        """测试真实 API 调用"""
        caller = APICaller()
        parser = TaskParser(caller=caller)

        result = await parser.parse("明天下午3点开会，讨论项目进度")
        assert len(result) >= 1
        print(f"解析结果: {result}")
