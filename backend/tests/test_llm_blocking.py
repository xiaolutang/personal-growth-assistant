"""测试 LLM 对话期间的阻塞问题

问题描述：
- 通过 LLM 对话（/parse）后，整个页面获取不到数据
- 包括以前存在的数据也获取不到
- 需要等待一段时间才能恢复

测试目标：
1. 模拟 /parse 调用期间，验证 GET /entries 是否被阻塞
2. 验证 /parse 完成后，GET /entries 是否能正常返回
"""
import asyncio
import time
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport


async def test_llm_parse_blocking():
    """测试 LLM 解析期间是否会阻塞其他请求"""
    from app.main import app
    from app.storage import init_storage
    from app.routers import deps

    # 创建临时目录
    test_dir = tempfile.mkdtemp(prefix="pga_test_")
    print(f"测试数据目录: {test_dir}")

    # 初始化存储服务（不使用 LLM caller，模拟无 LLM 场景）
    storage = await init_storage(
        data_dir=test_dir,
        neo4j_uri=None,
        qdrant_url=None,
        llm_caller=None,
    )
    deps.storage = storage
    print("存储服务初始化完成")

    # 先创建一些测试数据
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client:
        # 创建 5 条测试数据
        print("\n=== 准备测试数据 ===")
        for i in range(5):
            response = await client.post(
                "/entries",
                json={"type": "task", "title": f"已有任务-{i}", "content": f"内容 {i}"}
            )
            assert response.status_code == 200

        # 验证数据已存在
        response = await client.get("/entries?limit=100")
        data = response.json()
        initial_count = len(data["entries"])
        print(f"初始条目数: {initial_count}")
        assert initial_count >= 5, "测试数据创建失败"

        print("\n=== 测试: 模拟 /parse 长时间运行 ===")
        print("注意: 由于测试环境没有真实 LLM，/parse 会失败")
        print("我们测试的是: 即使 /parse 失败/超时，GET /entries 是否能正常工作")

        # 测试 1: 并发发送 /parse 请求和多个 GET /entries 请求
        print("\n--- 测试 1: 并发 /parse 和 GET /entries ---")

        results = {"parse_done": False, "entries_results": []}

        async def call_parse():
            """调用 /parse API"""
            start = time.time()
            try:
                # /parse 是 SSE 流式响应，可能需要较长时间
                response = await client.post(
                    "/parse",
                    json={"text": "明天下午3点开会", "session_id": "test-session"},
                    timeout=30.0
                )
                elapsed = time.time() - start
                results["parse_done"] = True
                return {"status": response.status_code, "time": elapsed, "error": None}
            except Exception as e:
                elapsed = time.time() - start
                results["parse_done"] = True
                return {"status": None, "time": elapsed, "error": str(e)}

        async def get_entries_during_parse(index):
            """在 parse 期间尝试获取条目"""
            # 稍微延迟一下，确保 parse 已经开始
            await asyncio.sleep(0.1)
            start = time.time()
            try:
                response = await client.get("/entries?limit=100", timeout=10.0)
                elapsed = time.time() - start
                data = response.json()
                count = len(data.get("entries", []))
                results["entries_results"].append({
                    "index": index,
                    "status": response.status_code,
                    "time": elapsed,
                    "count": count,
                })
                return {"index": index, "status": response.status_code, "time": elapsed, "count": count}
            except Exception as e:
                elapsed = time.time() - start
                return {"index": index, "status": None, "time": elapsed, "error": str(e)}

        # 并发执行
        start_time = time.time()
        tasks = [call_parse()]
        for i in range(5):
            tasks.append(get_entries_during_parse(i))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        print(f"\n总耗时: {total_time:.3f}s")
        print(f"\n各请求结果:")

        parse_result = results_list[0]
        entries_results = results_list[1:]

        if isinstance(parse_result, Exception):
            print(f"  /parse: 异常 - {parse_result}")
        else:
            print(f"  /parse: 状态={parse_result.get('status')}, 耗时={parse_result.get('time', 0):.3f}s")
            if parse_result.get("error"):
                print(f"          错误: {parse_result['error']}")

        for r in entries_results:
            if isinstance(r, Exception):
                print(f"  GET /entries: 异常 - {r}")
            else:
                print(f"  GET /entries[{r.get('index')}]: 状态={r.get('status')}, "
                      f"条目数={r.get('count')}, 耗时={r.get('time', 0):.3f}s")
                if r.get("error"):
                    print(f"          错误: {r['error']}")

        # 验证 GET /entries 是否正常
        entries_ok = all(
            r.get("status") == 200 and r.get("count", 0) >= initial_count
            for r in entries_results
            if not isinstance(r, Exception)
        )

        if entries_ok:
            print("\n✅ 测试通过: GET /entries 在 /parse 期间正常工作")
        else:
            print("\n❌ 测试失败: GET /entries 被阻塞或返回异常数据")
            print(f"   期望条目数 >= {initial_count}")

        # 测试 2: 验证 /parse 完成后，GET /entries 是否正常
        print("\n--- 测试 2: /parse 完成后 GET /entries ---")
        response = await client.get("/entries?limit=100")
        data = response.json()
        final_count = len(data["entries"])
        print(f"最终条目数: {final_count}")
        assert final_count >= initial_count, f"条目数异常减少: {initial_count} -> {final_count}"
        print("✅ 测试 2 通过")

    # 清理
    shutil.rmtree(test_dir, ignore_errors=True)
    return entries_ok


async def test_parse_creates_entry_then_query():
    """测试完整的 LLM 对话 -> 创建条目 -> 查询流程"""
    from app.main import app
    from app.storage import init_storage
    from app.routers import deps
    from app.callers import APICaller

    test_dir = tempfile.mkdtemp(prefix="pga_test_")
    print(f"\n测试数据目录: {test_dir}")

    # 使用真实的 LLM caller（如果环境变量配置了）
    llm_caller = None
    api_key = os.getenv("LLM_API_KEY")
    if api_key:
        print("检测到 LLM_API_KEY，使用真实 LLM")
        llm_caller = APICaller()

    storage = await init_storage(
        data_dir=test_dir,
        neo4j_uri=None,
        qdrant_url=None,
        llm_caller=llm_caller,
    )
    deps.storage = storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as client:
        # 创建一些已有数据
        print("\n=== 准备已有数据 ===")
        for i in range(3):
            await client.post(
                "/entries",
                json={"type": "task", "title": f"已有任务-{i}", "content": f"内容 {i}"}
            )

        response = await client.get("/entries?limit=100")
        initial_count = len(response.json()["entries"])
        print(f"初始条目数: {initial_count}")

        # 模拟用户操作: /parse -> 创建条目 -> 刷新页面
        print("\n=== 模拟用户操作流程 ===")

        # 1. 调用 /parse
        print("1. 调用 /parse...")
        parse_start = time.time()
        try:
            parse_response = await client.post(
                "/parse",
                json={"text": "明天下午3点开会讨论项目进度", "session_id": "test-flow"},
                timeout=30.0
            )
            parse_time = time.time() - parse_start
            print(f"   /parse 完成: 状态={parse_response.status_code}, 耗时={parse_time:.3f}s")
        except Exception as e:
            parse_time = time.time() - parse_start
            print(f"   /parse 异常: {e}, 耗时={parse_time:.3f}s")

        # 2. 立即刷新页面（GET /entries）
        print("2. 立即刷新页面...")
        query_start = time.time()
        query_response = await client.get("/entries?limit=100")
        query_time = time.time() - query_start
        data = query_response.json()
        entries_count = len(data["entries"])

        print(f"   GET /entries: 状态={query_response.status_code}, "
              f"条目数={entries_count}, 耗时={query_time:.3f}s")

        # 3. 验证
        if query_response.status_code == 200 and entries_count >= initial_count:
            print(f"\n✅ 测试通过: 页面刷新正常，条目数 {entries_count} >= 初始 {initial_count}")
            result = True
        else:
            print(f"\n❌ 测试失败: 状态={query_response.status_code}, 条目数={entries_count}, 期望>={initial_count}")
            result = False

    shutil.rmtree(test_dir, ignore_errors=True)
    return result


async def main():
    print("=" * 60)
    print("测试 LLM 对话阻塞问题")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("测试 1: 并发 /parse 和 GET /entries")
    print("=" * 60)
    result1 = await test_llm_parse_blocking()

    print("\n" + "=" * 60)
    print("测试 2: 完整用户操作流程")
    print("=" * 60)
    result2 = await test_parse_creates_entry_then_query()

    print("\n" + "=" * 60)
    if result1 and result2:
        print("所有测试通过 ✅")
    else:
        print("部分测试失败 ❌")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
