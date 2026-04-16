"""
B41: API 性能基线测试

验证核心 API 响应时间在合理范围内。
标记为 @pytest.mark.benchmark，不包含在默认测试运行中。
运行方式：uv run pytest tests/performance/ -m benchmark
"""
import pytest
import time


@pytest.mark.benchmark
class TestAPIPerformance:
    """API 响应时间基线测试"""

    async def test_health_response_time(self, client):
        """GET /health < 50ms"""
        start = time.perf_counter()
        resp = await client.get("/health")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert resp.status_code == 200
        assert elapsed_ms < 50, f"/health took {elapsed_ms:.1f}ms (> 50ms)"

    async def test_entries_list_response_time(self, client):
        """GET /entries < 200ms"""
        start = time.perf_counter()
        resp = await client.get("/entries")
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert resp.status_code == 200
        assert elapsed_ms < 200, f"/entries took {elapsed_ms:.1f}ms (> 200ms)"

    async def test_create_entry_response_time(self, client):
        """POST /entries < 300ms"""
        start = time.perf_counter()
        resp = await client.post("/entries", json={
            "type": "task",
            "title": "perf-test-task",
            "content": "",
            "status": "pending",
            "tags": [],
        })
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert resp.status_code in (200, 201)
        assert elapsed_ms < 300, f"POST /entries took {elapsed_ms:.1f}ms (> 300ms)"

    async def test_search_response_time(self, client):
        """POST /search < 300ms (允许 503 当向量服务不可用时)"""
        start = time.perf_counter()
        resp = await client.post("/search", json={
            "query": "perf-test",
            "limit": 10,
        })
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert resp.status_code in (200, 503)
        assert elapsed_ms < 300, f"/search took {elapsed_ms:.1f}ms (> 300ms)"
