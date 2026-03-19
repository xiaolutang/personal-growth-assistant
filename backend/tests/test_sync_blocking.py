"""测试 OpenAI 同步客户端阻塞问题

问题：
- APICaller 使用同步的 OpenAI 客户端
- 同步调用会阻塞 asyncio 事件循环
- 导致 LLM 调用期间，所有其他请求都无法处理

验证方法：
1. 模拟一个长时间的同步调用
2. 验证在同步调用期间，其他请求是否被阻塞
"""
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_sync_vs_async_blocking():
    """测试同步调用是否会阻塞事件循环"""

    results = {"sync_done": False, "async_results": []}

    def sync_long_operation(duration: float):
        """模拟同步的长时间操作（如 LLM API 调用）"""
        time.sleep(duration)  # 同步阻塞
        return f"sync done after {duration}s"

    async def async_operation(index: int):
        """异步操作，应该不受同步操作影响"""
        start = time.time()
        await asyncio.sleep(0.01)  # 很短的异步等待
        elapsed = time.time() - start
        results["async_results"].append({
            "index": index,
            "elapsed": elapsed,
            "sync_done_at_start": results["sync_done"],
        })
        return elapsed

    async def run_sync_in_async():
        """在异步函数中运行同步操作"""
        start = time.time()
        # 这是问题所在：直接调用同步函数会阻塞事件循环
        result = sync_long_operation(1.0)
        elapsed = time.time() - start
        results["sync_done"] = True
        return result, elapsed

    print("=== 测试: 同步操作阻塞事件循环 ===")
    print("预期: 如果同步操作阻塞了事件循环，async_operation 会在同步操作完成后才执行")
    print()

    # 同时启动同步操作和多个异步操作
    start_time = time.time()

    tasks = [
        run_sync_in_async(),
        async_operation(0),
        async_operation(1),
        async_operation(2),
    ]

    await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(f"总耗时: {total_time:.3f}s")
    print()

    print("异步操作结果:")
    for r in results["async_results"]:
        timing = "同步操作完成后" if r["sync_done_at_start"] else "同步操作进行中"
        print(f"  操作 {r['index']}: 耗时 {r['elapsed']:.3f}s, 开始时同步状态: {timing}")

    # 如果所有异步操作都在同步操作完成后才开始，说明事件循环被阻塞了
    all_after_sync = all(r["sync_done_at_start"] for r in results["async_results"])

    if all_after_sync:
        print("\n❌ 确认问题: 同步操作阻塞了事件循环")
        print("   所有异步操作都等到同步操作完成后才执行")
    else:
        print("\n✅ 没有阻塞: 异步操作在同步操作进行期间就执行了")

    return all_after_sync


async def test_to_thread_fix():
    """测试使用 asyncio.to_thread 解决阻塞问题"""

    results = {"sync_done": False, "async_results": []}

    def sync_long_operation(duration: float):
        """模拟同步的长时间操作"""
        time.sleep(duration)
        return f"sync done after {duration}s"

    async def async_operation(index: int):
        """异步操作"""
        start = time.time()
        await asyncio.sleep(0.01)
        elapsed = time.time() - start
        results["async_results"].append({
            "index": index,
            "elapsed": elapsed,
            "sync_done_at_start": results["sync_done"],
        })
        return elapsed

    async def run_sync_with_to_thread():
        """使用 to_thread 在线程池中运行同步操作"""
        start = time.time()
        # 解决方案：使用 to_thread 在单独的线程中运行同步操作
        result = await asyncio.to_thread(sync_long_operation, 1.0)
        elapsed = time.time() - start
        results["sync_done"] = True
        return result, elapsed

    print("\n=== 测试: 使用 asyncio.to_thread 解决阻塞 ===")
    print()

    start_time = time.time()

    tasks = [
        run_sync_with_to_thread(),
        async_operation(0),
        async_operation(1),
        async_operation(2),
    ]

    await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(f"总耗时: {total_time:.3f}s")
    print()

    print("异步操作结果:")
    for r in results["async_results"]:
        timing = "同步操作完成后" if r["sync_done_at_start"] else "同步操作进行中"
        print(f"  操作 {r['index']}: 耗时 {r['elapsed']:.3f}s, 开始时同步状态: {timing}")

    # 如果异步操作在同步操作进行期间就完成了，说明问题解决了
    any_during_sync = any(not r["sync_done_at_start"] for r in results["async_results"])

    if any_during_sync:
        print("\n✅ 问题解决: 异步操作在同步操作进行期间就执行了")
    else:
        print("\n❌ 仍然阻塞: 异步操作等到同步操作完成后才执行")

    return any_during_sync


async def check_apicaller_implementation():
    """检查 APICaller 的实现"""
    print("\n=== 检查 APICaller 实现 ===")

    try:
        from app.callers import APICaller
        import inspect

        # 检查 call 方法是否是异步的
        call_method = APICaller.call
        is_async = inspect.iscoroutinefunction(call_method)
        print(f"APICaller.call 是异步方法: {is_async}")

        # 检查源码
        source_file = inspect.getfile(APICaller)
        print(f"源文件: {source_file}")

        # 检查是否使用了同步的 OpenAI 客户端
        source = inspect.getsource(APICaller)
        uses_sync_openai = "from openai import OpenAI" in source and "AsyncOpenAI" not in source
        uses_async_openai = "AsyncOpenAI" in source

        print(f"使用同步 OpenAI 客户端: {uses_sync_openai}")
        print(f"使用异步 AsyncOpenAI 客户端: {uses_async_openai}")

        if uses_sync_openai and is_async:
            print("\n⚠️ 问题确认: APICaller.call 是异步方法，但内部使用同步的 OpenAI 客户端")
            print("   这会导致事件循环被阻塞！")
            return False
        elif uses_async_openai:
            print("\n✅ APICaller 使用异步客户端")
            return True
        else:
            print("\n❓ 无法确定")
            return None

    except Exception as e:
        print(f"检查失败: {e}")
        return None


async def main():
    print("=" * 60)
    print("测试: 同步 LLM 调用阻塞问题")
    print("=" * 60)

    # 测试 1: 验证同步操作会阻塞事件循环
    blocking_confirmed = await test_sync_vs_async_blocking()

    # 测试 2: 验证 to_thread 可以解决问题
    fix_works = await test_to_thread_fix()

    # 测试 3: 检查 APICaller 实现
    apicaller_ok = await check_apicaller_implementation()

    print("\n" + "=" * 60)
    print("测试结论:")
    print("=" * 60)

    if blocking_confirmed:
        print("1. ✅ 确认问题: 同步操作会阻塞 asyncio 事件循环")
    else:
        print("1. ❓ 未确认阻塞问题")

    if fix_works:
        print("2. ✅ 解决方案有效: asyncio.to_thread 可以解决阻塞")
    else:
        print("2. ❌ to_thread 方案无效")

    if apicaller_ok is False:
        print("3. ⚠️ APICaller 使用同步 OpenAI 客户端，会阻塞事件循环")
    elif apicaller_ok is True:
        print("3. ✅ APICaller 使用异步客户端")
    else:
        print("3. ❓ 无法检查 APICaller")


if __name__ == "__main__":
    asyncio.run(main())
