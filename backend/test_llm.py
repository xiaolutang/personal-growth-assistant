"""测试 LLM 通信"""
import asyncio

from app.callers import APICaller, MockCaller
from app.services import TaskParser


async def test_api_caller():
    """测试真实 API 调用"""
    print("=== 测试 APICaller ===")
    caller = APICaller()
    parser = TaskParser(caller=caller)

    result = await parser.parse("明天下午3点开会，讨论项目进度")
    print(f"解析结果: {result}")
    return result


async def test_mock_caller():
    """测试 Mock 调用"""
    print("\n=== 测试 MockCaller ===")
    mock_response = '{"tasks": [{"name": "测试任务", "category": "task", "status": "waitStart"}]}'
    caller = MockCaller(response=mock_response)
    parser = TaskParser(caller=caller)

    result = await parser.parse("随便输入")
    print(f"解析结果: {result}")
    return result


if __name__ == "__main__":
    # 先测试 Mock（不需要网络）
    asyncio.run(test_mock_caller())

    # 再测试真实 API（需要网络和 API Key）
    asyncio.run(test_api_caller())
