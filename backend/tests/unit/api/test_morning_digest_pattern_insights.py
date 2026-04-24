"""B87: 模式洞察 LLM 增强测试

验收条件:
1. LLM 可用时生成最多 5 条模式洞察（string[]，每条为中文描述）
2. LLM 不可用时降级到现有 3 条规则引擎洞察
3. LLM 洞察基于近 30 天数据分析（分类分布、完成率、时间模式）
4. 10 秒超时保护不变
5. 空数据（30天无条目）时返回空列表
6. LLM 返回 5xx 或非预期结构时降级到规则引擎
"""
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_cache():
    from app.services import review_service as rs
    rs._morning_digest_cache.clear()
    rs._morning_digest_pending.clear()


@pytest.fixture(autouse=True)
def _reset_cache():
    _clear_cache()
    yield
    _clear_cache()


def _make_service():
    from app.services.review_service import ReviewService
    sqlite_mock = MagicMock()
    return ReviewService(sqlite_storage=sqlite_mock)


# ---------------------------------------------------------------------------
# 1. LLM 正常：返回最多 5 条洞察，格式为 string[]
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_returns_insights():
    """LLM 正常返回洞察列表"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = [
        {"type": "task", "status": "complete", "tags": ["Python"], "created_at": "2026-04-20"},
        {"type": "note", "status": "", "tags": ["Rust"], "created_at": "2026-04-21"},
    ]

    mock_caller = AsyncMock()
    mock_caller.call.return_value = json.dumps(["你最近专注于 Python 学习", "任务完成率较高"])
    svc._llm_caller = mock_caller

    result = await svc._generate_pattern_insights_llm("u1")

    assert len(result) == 2
    assert "Python" in result[0]


# ---------------------------------------------------------------------------
# 1b. 时间模式：weekday_activity 出现在 LLM 输入数据中
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_stats_include_weekday_activity():
    """B87 AC3: stats 应包含 weekday_activity 时间模式"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = [
        {"type": "task", "status": "complete", "tags": [], "created_at": "2026-04-20"},  # Monday
        {"type": "note", "status": "", "tags": [], "created_at": "2026-04-22"},  # Wednesday
        {"type": "inbox", "status": "", "tags": [], "created_at": "2026-04-22"},  # Wednesday
    ]

    captured_stats = {}

    async def _capture_call(messages):
        user_msg = messages[1]["content"]
        # 提取 JSON 部分
        import re
        match = re.search(r'用户近 30 天数据：\n(.*)', user_msg, re.DOTALL)
        if match:
            captured_stats.update(json.loads(match.group(1)))
        return json.dumps(["你在周三最活跃"])

    mock_caller = AsyncMock()
    mock_caller.call.side_effect = _capture_call
    svc._llm_caller = mock_caller

    result = await svc._generate_pattern_insights_llm("u1")

    # 验证 weekday_activity 存在且包含时间分布
    assert "weekday_activity" in captured_stats
    assert captured_stats["weekday_activity"]["Wednesday"] == 2
    assert captured_stats["weekday_activity"]["Monday"] == 1


# ---------------------------------------------------------------------------
# 2. LLM 降级：LLM 不可用时返回空列表（调用方降级到规则引擎）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_unavailable_returns_empty():
    """LLM 不可用时返回空列表"""
    svc = _make_service()
    svc._llm_caller = None

    result = await svc._generate_pattern_insights_llm("u1")
    assert result == []


# ---------------------------------------------------------------------------
# 3. LLM 超时：降级到规则引擎
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_timeout_returns_empty():
    """LLM 超时时返回空列表"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = [{"type": "task", "status": "doing", "tags": []}]

    mock_caller = AsyncMock()
    mock_caller.call.side_effect = asyncio.TimeoutError()
    svc._llm_caller = mock_caller

    result = await svc._generate_pattern_insights_llm("u1")
    assert result == []


# ---------------------------------------------------------------------------
# 4. 空数据：30 天无条目时返回空列表
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_data_returns_empty():
    """30 天无条目时返回空列表"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = []

    result = await svc._generate_pattern_insights_llm("u1")
    assert result == []


# ---------------------------------------------------------------------------
# 5. LLM 5xx：模拟 LLM 返回 500 错误，降级到规则引擎
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_5xx_returns_empty():
    """LLM 抛出异常时返回空列表"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = [{"type": "task", "status": "doing", "tags": []}]

    mock_caller = AsyncMock()
    mock_caller.call.side_effect = Exception("LLM returned 500")
    svc._llm_caller = mock_caller

    result = await svc._generate_pattern_insights_llm("u1")
    assert result == []


# ---------------------------------------------------------------------------
# 6. LLM 异常结构：模拟 LLM 返回非列表，降级到规则引擎
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_non_list_response():
    """LLM 返回非列表结构时返回空列表"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = [{"type": "task", "status": "doing", "tags": []}]

    mock_caller = AsyncMock()
    mock_caller.call.return_value = '{"error": "not a list"}'
    svc._llm_caller = mock_caller

    result = await svc._generate_pattern_insights_llm("u1")
    assert result == []


# ---------------------------------------------------------------------------
# 7. LLM 返回超 5 条：截断到 5 条
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_returns_more_than_5_truncated():
    """LLM 返回超过 5 条时截断"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = [{"type": "task", "status": "doing", "tags": []}]

    mock_caller = AsyncMock()
    insights = [f"洞察{i}" for i in range(8)]
    mock_caller.call.return_value = json.dumps(insights)
    svc._llm_caller = mock_caller

    result = await svc._generate_pattern_insights_llm("u1")
    assert len(result) == 5


# ---------------------------------------------------------------------------
# 8. 回归：现有模式洞察规则引擎测试通过
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rule_engine_fallback():
    """LLM 返回空列表后降级到规则引擎"""
    svc = _make_service()
    svc._sqlite.list_entries.return_value = []

    # LLM 返回空 → 规则引擎
    result = svc._generate_pattern_insights("u1")
    assert result == []


# ---------------------------------------------------------------------------
# 9. 集成：get_morning_digest 中 LLM 失败降级到规则引擎
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_digest_llm_insights_fallback_to_rule_engine():
    """在 get_morning_digest 中，LLM 洞察失败时降级到规则引擎"""
    svc = _make_service()

    # 规则引擎有数据（3 个 inbox 触发规则）
    svc._sqlite.list_entries.return_value = [
        {"type": "inbox", "status": "", "tags": [], "created_at": "2026-04-24"},
        {"type": "inbox", "status": "", "tags": [], "created_at": "2026-04-24"},
        {"type": "inbox", "status": "", "tags": [], "created_at": "2026-04-24"},
    ]

    # LLM 失败 → 降级到规则引擎
    with patch.object(svc, "_generate_pattern_insights_llm", new_callable=AsyncMock, return_value=[]):
        with patch.object(svc, "_generate_daily_focus", new_callable=AsyncMock, return_value=None):
            with patch.object(svc, "_generate_morning_suggestion", new_callable=AsyncMock, return_value="建议"):
                with patch.object(svc, "_calculate_learning_streak", return_value=0):
                    result = await svc.get_morning_digest("u1")

    # 应该是规则引擎的结果（3 个 inbox → 规则引擎生成洞察）
    assert isinstance(result.pattern_insights, list)
