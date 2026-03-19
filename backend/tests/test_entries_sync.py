"""测试条目创建和查询的同步问题

问题描述：
- 通过 LLM 对话创建任务后，整个页面获取不到数据
- 需要等待一段时间才能恢复

测试目标：
1. 验证创建条目后立即查询是否能获取到数据
2. 验证并发请求是否会阻塞
3. 验证 SQLite 同步是否正常
"""
import asyncio
import time
import sys
import os
import tempfile
import shutil

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="module")
def test_storage():
    """创建测试存储环境"""
    # 创建临时目录
    test_dir = tempfile.mkdtemp(prefix="pga_test_")
    print(f"\n测试数据目录: {test_dir}")

    # 初始化存储服务
    from app.storage import init_storage

    async def setup():
        storage = await init_storage(
            data_dir=test_dir,
            neo4j_uri=None,  # 不使用 Neo4j
            qdrant_url=None,  # 不使用 Qdrant
            llm_caller=None,  # 不使用 LLM
        )
        return storage

    storage = asyncio.run(setup())

    # 注入到 deps
    from app.routers import deps
    deps.storage = storage

    yield storage

    # 清理
    shutil.rmtree(test_dir, ignore_errors=True)


class TestEntriesSync:
    """条目同步测试"""

    @pytest.fixture
    async def client(self, test_storage):
        """创建测试客户端"""
        from app.main import app
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            yield client

    @pytest.mark.asyncio
    async def test_create_and_query_immediately(self, client):
        """测试1: 创建条目后立即查询"""
        print("\n=== 测试1: 创建条目后立即查询 ===")

        # 创建条目
        create_start = time.time()
        create_response = await client.post(
            "/entries",
            json={
                "type": "task",
                "title": f"测试任务-{int(time.time())}",
                "content": "测试内容",
            }
        )
        create_time = time.time() - create_start

        print(f"创建响应状态: {create_response.status_code}")
        print(f"创建耗时: {create_time:.3f}s")

        assert create_response.status_code == 200, f"创建失败: {create_response.text}"
        created = create_response.json()
        entry_id = created["id"]
        print(f"创建的条目ID: {entry_id}")

        # 立即查询所有条目
        query_start = time.time()
        query_response = await client.get("/entries?limit=100")
        query_time = time.time() - query_start

        print(f"查询响应状态: {query_response.status_code}")
        print(f"查询耗时: {query_time:.3f}s")

        assert query_response.status_code == 200, f"查询失败: {query_response.text}"
        data = query_response.json()
        entries = data["entries"]
        print(f"查询到的条目数: {len(entries)}")

        # 验证新创建的条目在结果中
        found = any(e["id"] == entry_id for e in entries)
        assert found, f"新创建的条目 {entry_id} 未在查询结果中找到"

        print("✅ 测试1通过: 创建后立即查询成功")

    @pytest.mark.asyncio
    async def test_concurrent_create_and_query(self, client):
        """测试2: 并发创建和查询"""
        print("\n=== 测试2: 并发创建和查询 ===")

        async def create_entry(index):
            start = time.time()
            response = await client.post(
                "/entries",
                json={
                    "type": "task",
                    "title": f"并发测试任务-{index}-{int(time.time())}",
                    "content": f"并发测试内容 {index}",
                }
            )
            elapsed = time.time() - start
            return {"index": index, "status": response.status_code, "time": elapsed}

        async def query_entries():
            start = time.time()
            response = await client.get("/entries?limit=100")
            elapsed = time.time() - start
            return {"status": response.status_code, "time": elapsed, "count": len(response.json()["entries"])}

        # 同时发起 3 个创建请求和 5 个查询请求
        print("发起并发请求: 3个创建 + 5个查询")
        start_time = time.time()

        tasks = []
        # 创建任务
        for i in range(3):
            tasks.append(create_entry(i))
        # 查询任务
        for i in range(5):
            tasks.append(query_entries())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        print(f"总耗时: {total_time:.3f}s")

        # 分析结果
        create_results = [r for r in results if isinstance(r, dict) and "index" in r]
        query_results = [r for r in results if isinstance(r, dict) and "count" in r]
        exceptions = [r for r in results if isinstance(r, Exception)]

        print(f"\n创建结果:")
        for r in create_results:
            print(f"  任务{r['index']}: 状态={r['status']}, 耗时={r['time']:.3f}s")

        print(f"\n查询结果:")
        for i, r in enumerate(query_results):
            print(f"  查询{i}: 状态={r['status']}, 条目数={r['count']}, 耗时={r['time']:.3f}s")

        if exceptions:
            print(f"\n异常:")
            for e in exceptions:
                print(f"  {type(e).__name__}: {e}")

        # 验证
        assert len(exceptions) == 0, f"有 {len(exceptions)} 个请求失败"
        assert all(r["status"] == 200 for r in create_results), "部分创建请求失败"
        assert all(r["status"] == 200 for r in query_results), "部分查询请求失败"

        # 检查是否有请求被阻塞超过 5 秒
        max_query_time = max(r["time"] for r in query_results)
        print(f"\n最大查询耗时: {max_query_time:.3f}s")
        assert max_query_time < 5.0, f"查询被阻塞，耗时 {max_query_time:.3f}s 超过 5 秒"

        print("✅ 测试2通过: 并发请求正常")

    @pytest.mark.asyncio
    async def test_query_response_time(self, client):
        """测试3: 查询响应时间"""
        print("\n=== 测试3: 查询响应时间 ===")

        times = []
        for i in range(10):
            start = time.time()
            response = await client.get("/entries?limit=100")
            elapsed = time.time() - start
            times.append(elapsed)
            assert response.status_code == 200

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        print(f"查询次数: {len(times)}")
        print(f"平均耗时: {avg_time:.3f}s")
        print(f"最大耗时: {max_time:.3f}s")
        print(f"最小耗时: {min_time:.3f}s")

        assert max_time < 2.0, f"最大查询耗时 {max_time:.3f}s 超过 2 秒"
        print("✅ 测试3通过: 查询响应时间正常")


async def run_tests():
    """手动运行测试"""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    import tempfile
    import shutil

    # 创建临时目录
    test_dir = tempfile.mkdtemp(prefix="pga_test_")
    print(f"测试数据目录: {test_dir}")

    # 初始化存储服务
    from app.storage import init_storage
    from app.routers import deps

    storage = await init_storage(
        data_dir=test_dir,
        neo4j_uri=None,
        qdrant_url=None,
        llm_caller=None,
    )
    deps.storage = storage
    print("存储服务初始化完成")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
        test = TestEntriesSync()

        print("=" * 60)
        print("开始测试条目同步问题")
        print("=" * 60)

        try:
            await test.test_create_and_query_immediately(client)
        except AssertionError as e:
            print(f"❌ 测试1失败: {e}")
            shutil.rmtree(test_dir, ignore_errors=True)
            return False

        try:
            await test.test_concurrent_create_and_query(client)
        except AssertionError as e:
            print(f"❌ 测试2失败: {e}")
            shutil.rmtree(test_dir, ignore_errors=True)
            return False

        try:
            await test.test_query_response_time(client)
        except AssertionError as e:
            print(f"❌ 测试3失败: {e}")
            shutil.rmtree(test_dir, ignore_errors=True)
            return False

        print("\n" + "=" * 60)
        print("所有测试通过 ✅")
        print("=" * 60)

    # 清理
    shutil.rmtree(test_dir, ignore_errors=True)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
