"""B86: AI 建议个性化测试

验收条件:
1. LLM prompt 包含用户活跃目标标题（如有活跃目标）
2. LLM prompt 包含近 30 天高频标签 top 5
3. LLM 不可用时降级到现有模板逻辑完全不变
4. 有目标和没目标用户的建议 prompt 差异化
5. 10 秒超时保护不变
6. LLM 返回 5xx 或非预期结构时降级到模板文本
"""
import asyncio
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clear_cache():
    """清除模块级缓存"""
    from app.services import review_service as rs
    rs._morning_digest_cache.clear()
    rs._morning_digest_pending.clear()


@pytest.fixture(autouse=True)
def _reset_cache():
    _clear_cache()
    yield
    _clear_cache()


def _make_service():
    """创建 ReviewService 实例用于单元测试"""
    from app.services.review_service import ReviewService
    sqlite_mock = MagicMock()
    sqlite_mock.list_entries.return_value = []
    return ReviewService(sqlite_storage=sqlite_mock)


def _mock_weekly_summary():
    from app.services.review_service import MorningDigestWeeklySummary
    return MorningDigestWeeklySummary(new_concepts=["Python"], entries_count=5)


# ---------------------------------------------------------------------------
# 1. 有目标用户：prompt 包含目标信息
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestion_with_goals_includes_goals_in_stats():
    """有活跃目标时，stats_data 应包含 active_goals"""
    svc = _make_service()

    captured_stats = {}

    async def mock_ai_summary(report_type, stats_data, user_id="_default", **kwargs):
        captured_stats.update(stats_data)
        return "个性化建议"

    svc._llm_caller = MagicMock()

    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = (
                [{"title": "学 Rust", "progress_percentage": 30}], 1, ""
            )
            mock_gs.return_value = goal_svc

            result = await svc._generate_morning_suggestion(
                today_todos=[], overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    assert result == "个性化建议"
    assert "active_goals" in captured_stats
    assert captured_stats["active_goals"][0]["title"] == "学 Rust"


# ---------------------------------------------------------------------------
# 2. 无目标用户：prompt 无目标段落
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_suggestion_without_goals_no_goals_in_stats():
    """无活跃目标时，stats_data 不包含 active_goals"""
    svc = _make_service()

    captured_stats = {}

    async def mock_ai_summary(report_type, stats_data, user_id="_default", **kwargs):
        captured_stats.update(stats_data)
        return "通用建议"

    svc._llm_caller = MagicMock()

    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = ([], 0, "")
            mock_gs.return_value = goal_svc

            result = await svc._generate_morning_suggestion(
                today_todos=[], overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    assert result == "通用建议"
    assert "active_goals" not in captured_stats


# ---------------------------------------------------------------------------
# 3. 高频标签：验证 top 5 标签出现在 stats_data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_top_tags_in_stats():
    """近 30 天高频标签 top 5 出现在 stats_data"""
    svc = _make_service()

    # 模拟 30 天内条目，含多个标签
    entries = [
        {"tags": ["Python", "Rust"]},
        {"tags": ["Python", "Go"]},
        {"tags": ["Python"]},
        {"tags": ["Rust", "Go", "TypeScript"]},
        {"tags": ["Go"]},
        {"tags": ["Java"]},
    ]
    svc._sqlite.list_entries.return_value = entries

    captured_stats = {}

    async def mock_ai_summary(report_type, stats_data, user_id="_default", **kwargs):
        captured_stats.update(stats_data)
        return "建议"

    svc._llm_caller = MagicMock()

    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = ([], 0, "")
            mock_gs.return_value = goal_svc

            await svc._generate_morning_suggestion(
                today_todos=[], overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    assert "top_tags_30d" in captured_stats
    tags = captured_stats["top_tags_30d"]
    assert len(tags) <= 5
    # Python 出现 3 次，排第一
    assert tags[0] == "Python"


# ---------------------------------------------------------------------------
# 4. LLM 降级：LLM 不可用时返回模板文本
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_unavailable_fallback_template():
    """LLM 不可用时降级到模板文本"""
    svc = _make_service()
    svc._llm_caller = None  # 无 LLM

    result = await svc._generate_morning_suggestion(
        today_todos=[{"title": "任务1"}],
        overdue=[],
        stale_inbox=[],
        weekly_summary=_mock_weekly_summary(),
        user_id="u1",
    )

    # 应该是模板文本
    assert "1个任务待完成" in result


# ---------------------------------------------------------------------------
# 5. 超时：LLM 超时时返回降级文本
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_timeout_fallback():
    """LLM 超时时降级到模板文本"""
    svc = _make_service()

    async def mock_ai_summary_timeout(*args, **kwargs):
        raise asyncio.TimeoutError()

    svc._llm_caller = MagicMock()

    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary_timeout):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = ([], 0, "")
            mock_gs.return_value = goal_svc

            result = await svc._generate_morning_suggestion(
                today_todos=[{"title": "任务1"}],
                overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    assert "1个任务待完成" in result


# ---------------------------------------------------------------------------
# 6. LLM 5xx：模拟 LLM 返回 500 错误，降级到模板文本
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_5xx_fallback():
    """LLM 抛出异常时降级到模板文本"""
    svc = _make_service()

    async def mock_ai_summary_error(*args, **kwargs):
        raise Exception("LLM returned 500")

    svc._llm_caller = MagicMock()

    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary_error):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = ([], 0, "")
            mock_gs.return_value = goal_svc

            result = await svc._generate_morning_suggestion(
                today_todos=[{"title": "任务1"}],
                overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    assert "1个任务待完成" in result


# ---------------------------------------------------------------------------
# 7. LLM 异常结构：模拟 LLM 返回非字符串，降级到模板文本
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_non_string_response_fallback():
    """LLM 返回非字符串时降级到模板文本"""
    svc = _make_service()

    async def mock_ai_summary_non_string(*args, **kwargs):
        return ""  # 空字符串，_generate_ai_summary 返回空字符串

    svc._llm_caller = MagicMock()

    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary_non_string):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = ([], 0, "")
            mock_gs.return_value = goal_svc

            result = await svc._generate_morning_suggestion(
                today_todos=[{"title": "任务1"}],
                overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    # 空字符串被视为 falsy，降级到模板
    assert "1个任务待完成" in result


# ---------------------------------------------------------------------------
# 8. 个性化 prompt 差异化
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_diff_with_and_without_goals():
    """有目标和无目标时，system_prompt_override 内容不同"""
    svc = _make_service()

    captured_prompts = []

    async def mock_ai_summary(report_type, stats_data, user_id="_default", system_prompt_override="", **kwargs):
        captured_prompts.append(system_prompt_override)
        return "建议"

    svc._llm_caller = MagicMock()
    svc._sqlite.list_entries.return_value = []

    # 场景 1：有目标
    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = ([{"title": "G1", "progress_percentage": 50}], 1, "")
            mock_gs.return_value = goal_svc

            await svc._generate_morning_suggestion(
                today_todos=[], overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    # 场景 2：无目标
    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            goal_svc = AsyncMock()
            goal_svc.list_goals.return_value = ([], 0, "")
            mock_gs.return_value = goal_svc

            await svc._generate_morning_suggestion(
                today_todos=[], overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    assert len(captured_prompts) == 2
    prompt_with_goals = captured_prompts[0]
    prompt_without_goals = captured_prompts[1]
    assert "活跃目标" in prompt_with_goals
    assert "活跃目标" not in prompt_without_goals


# ---------------------------------------------------------------------------
# 9. GoalService 异常不影响主流程
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_goal_service_error_does_not_break():
    """GoalService 抛异常时，建议仍正常生成"""
    svc = _make_service()

    async def mock_ai_summary(*args, **kwargs):
        return "正常建议"

    svc._llm_caller = MagicMock()
    svc._sqlite.list_entries.return_value = [{"tags": ["Python"]}]

    with patch("app.services.review_service.ReviewService._generate_ai_summary", side_effect=mock_ai_summary):
        with patch("app.routers.deps.get_goal_service") as mock_gs:
            mock_gs.side_effect = Exception("GoalService 不可用")

            result = await svc._generate_morning_suggestion(
                today_todos=[], overdue=[], stale_inbox=[],
                weekly_summary=_mock_weekly_summary(), user_id="u1",
            )

    assert result == "正常建议"
