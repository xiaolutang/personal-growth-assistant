"""测试 LLM Callers"""
import pytest

from app.callers import APICaller, MockCaller


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
    """APICaller 单元测试"""

    @pytest.mark.asyncio
    async def test_call_structure(self):
        """测试 API 调用结构（不实际调用）"""
        caller = APICaller()
        # 验证实例创建成功
        assert caller is not None
