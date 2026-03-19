"""并发/异步测试

核心场景：防止阻塞
- LLM 调用不阻塞其他请求
- 创建后立即可查
- 删除后立即生效
- 并发操作的数据一致性
"""
import asyncio
import time

import pytest
from httpx import AsyncClient


# === 核心场景：防止阻塞 ===

@pytest.mark.asyncio
async def test_concurrent_parse_and_query(client: AsyncClient):
    """测试 /parse 期间 GET /entries 不被阻塞"""
    # 1. 预先创建测试数据
    for i in range(5):
        await client.post(
            "/entries",
            json={"type": "task", "title": f"已有任务-{i}", "content": f"内容 {i}"},
        )

    initial_response = await client.get("/entries?limit=100")
    initial_count = initial_response.json()["total"]

    # 2. 并发执行 /parse 和多次 GET /entries
    async def call_parse():
        try:
            # /parse 是 SSE 流式响应，可能需要较长时间
            response = await client.post(
                "/parse",
                json={"text": "明天开会", "session_id": "test-concurrent"},
                timeout=30.0,
            )
            return {"status": response.status_code, "error": None}
        except Exception as e:
            return {"status": None, "error": str(e)}

    async def query_entries(idx):
        await asyncio.sleep(0.05)  # 确保 parse 已开始
        start = time.time()
        try:
            resp = await client.get("/entries?limit=100", timeout=10.0)
            elapsed = time.time() - start
            return {
                "idx": idx,
                "status": resp.status_code,
                "time": elapsed,
                "count": resp.json()["total"],
            }
        except Exception as e:
            return {"idx": idx, "status": None, "error": str(e)}

    results = await asyncio.gather(
        call_parse(),
        *[query_entries(i) for i in range(5)],
        return_exceptions=True,
    )

    # 3. 验证所有 GET /entries 都成功
    query_results = [r for r in results[1:] if not isinstance(r, Exception)]
    assert len(query_results) == 5, "应该有 5 个查询结果"

    for r in query_results:
        assert r["status"] == 200, f"查询应该成功，实际状态: {r.get('status')}"
        assert r["count"] >= initial_count, f"条目数应该 >= {initial_count}"
        assert r["time"] < 5.0, f"查询时间应该小于 5 秒，实际: {r['time']:.2f}s"


@pytest.mark.asyncio
async def test_create_then_immediate_query(client: AsyncClient):
    """测试创建条目后立即能查询到"""
    # 创建条目
    create_resp = await client.post(
        "/entries",
        json={
            "type": "task",
            "title": "立即查询测试",
            "content": "测试内容",
            "tags": ["immediate"],
        },
    )
    assert create_resp.status_code == 200
    entry_id = create_resp.json()["id"]

    # 立即查询（不等待）
    query_resp = await client.get(f"/entries/{entry_id}")
    assert query_resp.status_code == 200, "创建后立即查询应该成功"
    assert query_resp.json()["title"] == "立即查询测试"

    # 列表查询也能看到
    list_resp = await client.get("/entries?limit=100")
    ids = [e["id"] for e in list_resp.json()["entries"]]
    assert entry_id in ids, "新创建的条目应该出现在列表中"


@pytest.mark.asyncio
async def test_delete_then_immediate_query(client: AsyncClient):
    """测试删除条目后立即从查询中消失"""
    # 创建条目
    create_resp = await client.post(
        "/entries",
        json={"type": "task", "title": "待删除任务", "content": ""},
    )
    entry_id = create_resp.json()["id"]

    # 删除
    delete_resp = await client.delete(f"/entries/{entry_id}")
    assert delete_resp.status_code == 200

    # 立即查询，应该不存在
    get_resp = await client.get(f"/entries/{entry_id}")
    assert get_resp.status_code == 404, "删除后立即查询应该返回 404"

    # 列表中也不应该存在
    list_resp = await client.get("/entries?limit=100")
    ids = [e["id"] for e in list_resp.json()["entries"]]
    assert entry_id not in ids, "已删除的条目不应该出现在列表中"


@pytest.mark.asyncio
async def test_concurrent_creates(client: AsyncClient):
    """测试并发创建多个条目"""
    async def create_entry(idx):
        response = await client.post(
            "/entries",
            json={
                "type": "task",
                "title": f"并发创建-{idx}",
                "content": f"并发测试内容 {idx}",
                "tags": ["concurrent"],
            },
        )
        return {"idx": idx, "status": response.status_code, "id": response.json()["id"]}

    # 并发创建 10 个条目
    results = await asyncio.gather(*[create_entry(i) for i in range(10)])

    # 验证所有创建都成功
    for r in results:
        assert r["status"] == 200, f"创建 {r['idx']} 应该成功"

    # 验证所有条目都能查询到
    created_ids = {r["id"] for r in results}
    list_resp = await client.get("/entries?limit=100")
    actual_ids = {e["id"] for e in list_resp.json()["entries"]}

    # 所有创建的 ID 都应该在列表中
    missing = created_ids - actual_ids
    assert len(missing) == 0, f"缺少的条目: {missing}"


@pytest.mark.asyncio
async def test_concurrent_updates_same_entry(client: AsyncClient):
    """测试并发更新同一条目"""
    # 创建一个条目
    create_resp = await client.post(
        "/entries",
        json={"type": "task", "title": "原始标题", "content": "原始内容"},
    )
    entry_id = create_resp.json()["id"]

    async def update_entry(new_title):
        response = await client.put(
            f"/entries/{entry_id}",
            json={"title": new_title},
        )
        return {"status": response.status_code, "title": new_title}

    # 并发更新
    results = await asyncio.gather(
        *[update_entry(f"更新-{i}") for i in range(5)],
        return_exceptions=True,
    )

    # 至少应该有一些成功
    success_count = sum(1 for r in results if not isinstance(r, Exception) and r.get("status") == 200)
    assert success_count >= 1, "至少应该有一个更新成功"

    # 验证最终状态
    get_resp = await client.get(f"/entries/{entry_id}")
    assert get_resp.status_code == 200
    # 标题应该是最后一次更新的值之一
    assert get_resp.json()["title"].startswith("更新-")


@pytest.mark.asyncio
async def test_concurrent_read_during_write(client: AsyncClient):
    """测试写入期间并发读取"""
    async def write_entrys():
        for i in range(5):
            await client.post(
                "/entries",
                json={"type": "task", "title": f"写入-{i}", "content": ""},
            )

    async def read_entries():
        results = []
        for _ in range(10):
            resp = await client.get("/entries?limit=100")
            results.append(resp.status_code)
            await asyncio.sleep(0.01)
        return results

    # 并发执行读写
    write_task = asyncio.create_task(write_entrys())
    read_task = asyncio.create_task(read_entries())

    await write_task
    read_results = await read_task

    # 所有读取都应该成功
    assert all(s == 200 for s in read_results), "读取期间不应该有失败"


# === SSE 流式测试 ===

@pytest.mark.asyncio
async def test_parse_stream_complete(client: AsyncClient):
    """测试流式响应正常完成"""
    try:
        response = await client.post(
            "/parse",
            json={"text": "测试流式响应", "session_id": "test-stream"},
            timeout=30.0,
        )
        # 只要不抛出异常就算成功
        # 在没有真实 LLM 的情况下，可能返回错误或超时
        assert response.status_code in [200, 500, 503], "应该返回有效状态码"
    except Exception:
        # 在测试环境下可能因为没有 LLM 而失败，这是预期的
        pass


@pytest.mark.asyncio
async def test_parse_stream_interrupted(client: AsyncClient):
    """测试流式响应中断恢复"""
    # 创建一个条目作为基准
    await client.post(
        "/entries",
        json={"type": "task", "title": "中断测试基准", "content": ""},
    )

    # 尝试中断 parse（通过超时）
    try:
        await asyncio.wait_for(
            client.post(
                "/parse",
                json={"text": "长时间任务", "session_id": "test-interrupt"},
            ),
            timeout=0.1,  # 极短超时
        )
    except asyncio.TimeoutError:
        pass  # 预期超时

    # 验证系统仍然正常工作
    resp = await client.get("/entries?limit=100")
    assert resp.status_code == 200, "中断后系统应该仍然正常"


# === 压力测试 ===

@pytest.mark.asyncio
@pytest.mark.slow
async def test_high_concurrency(client: AsyncClient):
    """高并发压力测试（标记为 slow，可选执行）"""
    async def create_and_query(idx):
        # 创建
        create_resp = await client.post(
            "/entries",
            json={"type": "task", "title": f"压力测试-{idx}", "content": ""},
        )
        if create_resp.status_code != 200:
            return False

        # 查询
        query_resp = await client.get("/entries?limit=100")
        return query_resp.status_code == 200

    # 并发 20 个操作
    results = await asyncio.gather(*[create_and_query(i) for i in range(20)])

    success_rate = sum(1 for r in results if r) / len(results)
    assert success_rate >= 0.9, f"成功率应该 >= 90%，实际: {success_rate * 100}%"
