"""ReviewService 服务级测试 — S16 回顾增强测试收口

覆盖：
- get_insights: period 校验、时间范围计算、前后周期查询、LLM/rule-based 路径
- _generate_deep_insights: LLM 成功/超时/解析失败/不可用/payload 校验
- _generate_rule_based_insights: 分类分布、完成率趋势、成长建议、能力变化、阈值边界
- _analyze_category_distribution: 共享 helper
"""
import asyncio
import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.review_service import (
    ReviewService,
    DeepInsights,
    BehaviorPattern,
    GrowthSuggestion,
    CapabilityChange,
    InsightsResponse,
)


@pytest.fixture
def mock_sqlite():
    """模拟 SQLite 存储"""
    storage = MagicMock()
    storage.list_entries.return_value = []
    return storage


@pytest.fixture
def service(mock_sqlite):
    """创建 ReviewService 实例"""
    svc = ReviewService(sqlite_storage=mock_sqlite)
    return svc


def _make_entry(
    entry_type="task",
    status="complete",
    tags=None,
    created_at=None,
    user_id="user1",
    entry_id="entry-1",
    title="测试条目",
):
    """构建测试条目"""
    if tags is None:
        tags = []
    if created_at is None:
        created_at = date.today().isoformat()
    return {
        "id": entry_id,
        "type": entry_type,
        "status": status,
        "tags": tags,
        "title": title,
        "created_at": created_at,
        "updated_at": created_at,
        "user_id": user_id,
    }


class TestGetInsights:
    """测试 get_insights 方法"""

    @pytest.mark.asyncio
    async def test_invalid_period_raises(self, service):
        """非法 period 参数抛出 ValueError"""
        with pytest.raises(ValueError, match="period"):
            await service.get_insights(period="daily", user_id="user1")

    @pytest.mark.asyncio
    async def test_no_sqlite_raises(self):
        """SQLite 未初始化抛出 ValueError"""
        svc = ReviewService(sqlite_storage=None)
        with pytest.raises(ValueError, match="SQLite"):
            await svc.get_insights(period="weekly", user_id="user1")

    @pytest.mark.asyncio
    async def test_weekly_queries_both_periods(self, service, mock_sqlite):
        """weekly 周期查询当前和前一个周期的 list_entries"""
        await service.get_insights(period="weekly", user_id="user1")

        calls = mock_sqlite.list_entries.call_args_list
        assert len(calls) == 2  # current period + previous period

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        prev_start = week_start - timedelta(days=7)
        prev_end = week_start - timedelta(days=1)

        # 第一次调用：当前周期
        curr_call = calls[0]
        assert curr_call.kwargs.get("user_id") == "user1"
        assert curr_call.kwargs.get("start_date") == week_start.isoformat()

        # 第二次调用：前一个周期
        prev_call = calls[1]
        assert prev_call.kwargs.get("start_date") == prev_start.isoformat()
        assert prev_call.kwargs.get("end_date") == prev_end.isoformat()

    @pytest.mark.asyncio
    async def test_monthly_queries_both_periods(self, service, mock_sqlite):
        """monthly 周期查询当前和前一个周期"""
        await service.get_insights(period="monthly", user_id="user1")

        calls = mock_sqlite.list_entries.call_args_list
        assert len(calls) == 2

        today = date.today()
        month_start = date(today.year, today.month, 1)

        # 第一次调用起始日期
        assert calls[0].kwargs.get("start_date") == month_start.isoformat()

        # 第二次调用：上一个月
        if today.month == 1:
            expected_prev_start = date(today.year - 1, 12, 1)
        else:
            expected_prev_start = date(today.year, today.month - 1, 1)
        assert calls[1].kwargs.get("start_date") == expected_prev_start.isoformat()

    @pytest.mark.asyncio
    @patch("app.services.review.insights.date")
    async def test_january_monthly_prev_december(self, mock_date, service, mock_sqlite):
        """1 月 monthly 的前一个周期是去年 12 月"""
        mock_date.today.return_value = date(2026, 1, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        await service.get_insights(period="monthly", user_id="user1")

        calls = mock_sqlite.list_entries.call_args_list
        # 前一个月应该是 2025-12-01
        prev_call = calls[1]
        assert prev_call.kwargs.get("start_date") == "2025-12-01"

    @pytest.mark.asyncio
    async def test_empty_entries_returns_rule_based(self, service, mock_sqlite):
        """空条目返回 rule_based 降级洞察"""
        mock_sqlite.list_entries.return_value = []

        result = await service.get_insights(period="weekly", user_id="user1")

        assert result.source == "rule_based"
        assert isinstance(result.insights, DeepInsights)

    @pytest.mark.asyncio
    async def test_user_id_passed_to_all_queries(self, service, mock_sqlite):
        """user_id 正确传递到所有 SQLite 查询"""
        await service.get_insights(period="weekly", user_id="user42")

        for call in mock_sqlite.list_entries.call_args_list:
            assert call.kwargs.get("user_id") == "user42"


class TestGenerateDeepInsights:
    """测试 _generate_deep_insights 方法"""

    def _make_llm_caller(self, return_value):
        """创建模拟 LLM caller（call 方法返回指定值）"""
        caller = MagicMock()
        caller.call = AsyncMock(return_value=return_value)
        return caller

    @pytest.mark.asyncio
    async def test_llm_success(self, service):
        """LLM 成功返回结构化洞察"""
        llm_response = json.dumps({
            "behavior_patterns": [
                {"pattern": "偏向创建任务", "frequency": 5, "trend": "stable"},
            ],
            "growth_suggestions": [
                {"suggestion": "多记笔记", "priority": "medium", "related_area": "学习"},
            ],
            "capability_changes": [
                {"capability": "Python", "previous_level": 0.3, "current_level": 0.6, "change": 0.3},
            ],
        })

        caller = self._make_llm_caller(llm_response)
        service.set_llm_caller(caller)

        entries = [_make_entry(tags=["Python"])]
        prev_entries = [_make_entry(tags=["Python"])]

        insights, source = await service._generate_deep_insights(
            period="weekly",
            entries=entries,
            prev_entries=prev_entries,
            start_date="2026-04-20",
            end_date="2026-04-26",
            user_id="user1",
        )

        assert source == "llm"
        assert len(insights.behavior_patterns) == 1
        assert insights.behavior_patterns[0].pattern == "偏向创建任务"
        assert len(insights.growth_suggestions) == 1
        assert len(insights.capability_changes) == 1

        # 验证 LLM caller.call 被调用一次且 await
        caller.call.assert_awaited_once()
        # 验证传入的 messages 结构
        call_args = caller.call.call_args
        messages = call_args[0][0]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "weekly" in messages[1]["content"]
        assert "2026-04-20" in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_llm_timeout_fallback(self, service):
        """LLM 超时降级为规则分析"""
        caller = MagicMock()
        caller.call = AsyncMock(side_effect=asyncio.TimeoutError())
        service.set_llm_caller(caller)

        entries = [_make_entry(), _make_entry()]
        prev_entries = [_make_entry()]

        insights, source = await service._generate_deep_insights(
            period="weekly",
            entries=entries,
            prev_entries=prev_entries,
            start_date="2026-04-20",
            end_date="2026-04-26",
            user_id="user1",
        )

        assert source == "rule_based"
        assert isinstance(insights, DeepInsights)

    @pytest.mark.asyncio
    async def test_llm_invalid_json_fallback(self, service):
        """LLM 返回非法 JSON 降级为规则分析"""
        service.set_llm_caller(self._make_llm_caller("this is not json"))

        entries = [_make_entry()]
        prev_entries = []

        insights, source = await service._generate_deep_insights(
            period="weekly",
            entries=entries,
            prev_entries=prev_entries,
            start_date="2026-04-20",
            end_date="2026-04-26",
            user_id="user1",
        )

        assert source == "rule_based"

    @pytest.mark.asyncio
    async def test_llm_returns_json_in_code_block(self, service):
        """LLM 返回 markdown 代码块包裹的 JSON"""
        llm_response = '```json\n{"behavior_patterns":[],"growth_suggestions":[],"capability_changes":[]}\n```'
        service.set_llm_caller(self._make_llm_caller(llm_response))

        insights, source = await service._generate_deep_insights(
            period="weekly",
            entries=[],
            prev_entries=[],
            start_date="2026-04-20",
            end_date="2026-04-26",
            user_id="user1",
        )

        assert source == "llm"
        assert len(insights.behavior_patterns) == 0

    @pytest.mark.asyncio
    async def test_no_llm_caller_fallback(self, service):
        """无 LLM caller 直接走规则分析"""
        entries = [_make_entry()]
        prev_entries = []

        insights, source = await service._generate_deep_insights(
            period="weekly",
            entries=entries,
            prev_entries=prev_entries,
            start_date="2026-04-20",
            end_date="2026-04-26",
            user_id="user1",
        )

        assert source == "rule_based"

    @pytest.mark.asyncio
    async def test_llm_overlong_arrays_capped(self, service):
        """LLM 返回超过 3 项的数组被截断"""
        patterns = [{"pattern": f"模式{i}", "frequency": i, "trend": "stable"} for i in range(5)]
        llm_response = json.dumps({
            "behavior_patterns": patterns,
            "growth_suggestions": [],
            "capability_changes": [],
        })
        service.set_llm_caller(self._make_llm_caller(llm_response))

        insights, source = await service._generate_deep_insights(
            period="weekly",
            entries=[_make_entry()],
            prev_entries=[],
            start_date="2026-04-20",
            end_date="2026-04-26",
            user_id="user1",
        )

        assert source == "llm"
        assert len(insights.behavior_patterns) == 3

    @pytest.mark.asyncio
    async def test_llm_invalid_schema_field_fallback(self, service):
        """LLM 返回的字段类型不匹配（如 trend 无效值）降级为规则分析"""
        llm_response = json.dumps({
            "behavior_patterns": [
                {"pattern": "测试", "frequency": 1, "trend": "invalid_trend"},
            ],
            "growth_suggestions": [],
            "capability_changes": [],
        })
        service.set_llm_caller(self._make_llm_caller(llm_response))

        insights, source = await service._generate_deep_insights(
            period="weekly",
            entries=[_make_entry()],
            prev_entries=[],
            start_date="2026-04-20",
            end_date="2026-04-26",
            user_id="user1",
        )

        # Pydantic Literal 验证失败应降级
        assert source == "rule_based"

    @pytest.mark.asyncio
    async def test_llm_payload_contains_stats(self, service):
        """验证 LLM 调用 payload 包含正确的统计数据"""
        caller = self._make_llm_caller('{"behavior_patterns":[],"growth_suggestions":[],"capability_changes":[]}')
        service.set_llm_caller(caller)

        entries = [
            _make_entry(entry_type="task", status="complete", tags=["Python"]),
            _make_entry(entry_type="task", status="doing"),
            _make_entry(entry_type="note"),
        ]
        prev_entries = [_make_entry(entry_type="task", status="complete")]

        await service._generate_deep_insights(
            period="monthly",
            entries=entries,
            prev_entries=prev_entries,
            start_date="2026-04-01",
            end_date="2026-04-30",
            user_id="user1",
        )

        call_args = caller.call.call_args
        messages = call_args[0][0]
        user_msg = messages[1]["content"]
        # 验证 payload 包含周期类型和关键统计数据
        assert "monthly" in user_msg
        assert "2026-04-01" in user_msg
        assert "Python" in user_msg


class TestGenerateRuleBasedInsights:
    """测试 _generate_rule_based_insights 方法"""

    def test_empty_entries(self, service):
        """空条目返回空洞察"""
        insights = service._generate_rule_based_insights("weekly", [], [])

        assert isinstance(insights, DeepInsights)
        assert len(insights.behavior_patterns) == 0
        assert len(insights.growth_suggestions) == 0
        assert len(insights.capability_changes) == 0

    def test_category_distribution_pattern(self, service):
        """分类占比 >60% 且总数>=5 时生成行为模式"""
        entries = [_make_entry(entry_type="task") for _ in range(7)]
        entries.append(_make_entry(entry_type="note"))
        entries.append(_make_entry(entry_type="note"))

        insights = service._generate_rule_based_insights("weekly", entries, [])

        task_patterns = [p for p in insights.behavior_patterns if "任务" in p.pattern]
        assert len(task_patterns) >= 1
        assert task_patterns[0].frequency == 7

    def test_category_below_threshold_no_pattern(self, service):
        """分类占比 <=60% 不生成分布行为模式"""
        # 5 task + 5 note = 各 50%，都不超 60%
        entries = [_make_entry(entry_type="task") for _ in range(5)]
        entries += [_make_entry(entry_type="note") for _ in range(5)]

        insights = service._generate_rule_based_insights("weekly", entries, [])

        category_patterns = [p for p in insights.behavior_patterns if "倾向于" in p.pattern]
        assert len(category_patterns) == 0

    def test_category_total_below_5_no_pattern(self, service):
        """总数 <5 即使占比 >60% 也不生成分布模式"""
        # 3 task + 1 note = task 75%，但总数只有 4
        entries = [_make_entry(entry_type="task") for _ in range(3)]
        entries.append(_make_entry(entry_type="note"))

        insights = service._generate_rule_based_insights("weekly", entries, [])

        category_patterns = [p for p in insights.behavior_patterns if "倾向于" in p.pattern]
        assert len(category_patterns) == 0

    def test_monthly_period_label(self, service):
        """monthly 周期使用"本月"标签"""
        entries = [_make_entry(entry_type="task") for _ in range(7)]
        entries.append(_make_entry(entry_type="note"))

        insights = service._generate_rule_based_insights("monthly", entries, [])

        all_texts = (
            [p.pattern for p in insights.behavior_patterns]
            + [s.suggestion for s in insights.growth_suggestions]
        )
        weekly_labels = [t for t in all_texts if "本周" in t]
        assert len(weekly_labels) == 0

    def test_completion_rate_trend(self, service):
        """完成率变化 >=15% 生成趋势洞察"""
        curr = [
            _make_entry(entry_type="task", status="complete") for _ in range(4)
        ] + [_make_entry(entry_type="task", status="doing")]

        prev = [
            _make_entry(entry_type="task", status="complete")
        ] + [_make_entry(entry_type="task", status="doing") for _ in range(4)]

        insights = service._generate_rule_based_insights("weekly", curr, prev)

        trend_patterns = [p for p in insights.behavior_patterns if "提升" in p.pattern or "下降" in p.pattern]
        assert len(trend_patterns) >= 1

    def test_completion_rate_below_threshold_no_trend(self, service):
        """完成率变化 <15% 不生成趋势洞察"""
        # 当前 60%，之前 50%，差 10%
        curr = [
            _make_entry(entry_type="task", status="complete") for _ in range(3)
        ] + [_make_entry(entry_type="task", status="doing") for _ in range(2)]

        prev = [
            _make_entry(entry_type="task", status="complete")
        ] + [_make_entry(entry_type="task", status="doing")

        ]

        insights = service._generate_rule_based_insights("weekly", curr, prev)

        trend_patterns = [p for p in insights.behavior_patterns if "提升" in p.pattern or "下降" in p.pattern]
        assert len(trend_patterns) == 0

    def test_inbox_suggestion(self, service):
        """>=3 个灵感时生成整理建议"""
        entries = [_make_entry(entry_type="inbox") for _ in range(3)]
        entries.append(_make_entry(entry_type="task"))

        insights = service._generate_rule_based_insights("weekly", entries, [])

        inbox_suggestions = [s for s in insights.growth_suggestions if "灵感" in s.suggestion]
        assert len(inbox_suggestions) >= 1

    def test_inbox_below_threshold_no_suggestion(self, service):
        """<3 个灵感不生成整理建议"""
        entries = [_make_entry(entry_type="inbox") for _ in range(2)]
        entries.append(_make_entry(entry_type="task"))

        insights = service._generate_rule_based_insights("weekly", entries, [])

        inbox_suggestions = [s for s in insights.growth_suggestions if "灵感" in s.suggestion]
        assert len(inbox_suggestions) == 0

    def test_low_completion_rate_suggestion(self, service):
        """完成率 <50% 且任务>=3 生成高优先级建议"""
        entries = [_make_entry(entry_type="task", status="doing") for _ in range(5)]

        insights = service._generate_rule_based_insights("weekly", entries, [])

        rate_suggestions = [s for s in insights.growth_suggestions if "完成率" in s.suggestion]
        assert len(rate_suggestions) >= 1
        assert rate_suggestions[0].priority == "high"

    def test_low_completion_rate_few_tasks_no_suggestion(self, service):
        """任务<3 即使完成率低也不生成建议"""
        entries = [_make_entry(entry_type="task", status="doing") for _ in range(2)]

        insights = service._generate_rule_based_insights("weekly", entries, [])

        rate_suggestions = [s for s in insights.growth_suggestions if "完成率" in s.suggestion]
        assert len(rate_suggestions) == 0

    def test_no_notes_suggestion(self, service):
        """无笔记且总条目>=3 生成笔记建议"""
        entries = [_make_entry(entry_type="task") for _ in range(3)]

        insights = service._generate_rule_based_insights("weekly", entries, [])

        note_suggestions = [s for s in insights.growth_suggestions if "笔记" in s.suggestion]
        assert len(note_suggestions) >= 1

    def test_has_notes_no_suggestion(self, service):
        """有笔记时不生成笔记建议"""
        entries = [
            _make_entry(entry_type="task"),
            _make_entry(entry_type="task"),
            _make_entry(entry_type="note"),
        ]

        insights = service._generate_rule_based_insights("weekly", entries, [])

        note_suggestions = [s for s in insights.growth_suggestions if "笔记" in s.suggestion]
        assert len(note_suggestions) == 0

    def test_capability_changes_from_tags(self, service):
        """标签活跃度变化生成能力变化"""
        curr = [_make_entry(tags=["Python", "AI"]) for _ in range(4)]
        prev = [_make_entry(tags=["Python"]) for _ in range(1)]

        insights = service._generate_rule_based_insights("weekly", curr, prev)

        assert len(insights.capability_changes) >= 1
        python_changes = [c for c in insights.capability_changes if c.capability == "Python"]
        assert len(python_changes) >= 1
        assert python_changes[0].current_level > python_changes[0].previous_level

    def test_unchanged_tags_no_capability_change(self, service):
        """标签活跃度不变不生成能力变化"""
        curr = [_make_entry(tags=["Python"]) for _ in range(3)]
        prev = [_make_entry(tags=["Python"]) for _ in range(3)]

        insights = service._generate_rule_based_insights("weekly", curr, prev)

        # 3/5.0 = 0.6，前一期也是 0.6，change = 0，abs(0) > 0.01 为 False
        python_changes = [c for c in insights.capability_changes if c.capability == "Python"]
        assert len(python_changes) == 0

    def test_max_three_items_per_section(self, service):
        """每个维度最多 3 项"""
        entries = [_make_entry(entry_type="task") for _ in range(10)]
        entries += [_make_entry(entry_type="inbox") for _ in range(5)]
        entries += [_make_entry(entry_type="note") for _ in range(3)]

        prev = [_make_entry(entry_type="task", status="doing") for _ in range(5)]

        insights = service._generate_rule_based_insights("weekly", entries, prev)

        assert len(insights.behavior_patterns) <= 3
        assert len(insights.growth_suggestions) <= 3
        assert len(insights.capability_changes) <= 3


class TestAnalyzeCategoryDistribution:
    """测试 _analyze_category_distribution 共享 helper"""

    def test_mixed_entries(self, service):
        """混合条目正确分类"""
        entries = [
            _make_entry(entry_type="task"),
            _make_entry(entry_type="task"),
            _make_entry(entry_type="note"),
            _make_entry(entry_type="inbox"),
        ]

        total, counts, tasks, notes, inbox = service._analyze_category_distribution(entries)

        assert total == 4
        assert counts == {"task": 2, "note": 1, "inbox": 1}
        assert len(tasks) == 2
        assert len(notes) == 1
        assert len(inbox) == 1

    def test_empty_entries(self, service):
        """空列表返回零值"""
        total, counts, tasks, notes, inbox = service._analyze_category_distribution([])

        assert total == 0
        assert counts == {}
        assert tasks == []
        assert notes == []
        assert inbox == []

    def test_single_type_entries(self, service):
        """单一类型条目"""
        entries = [_make_entry(entry_type="task") for _ in range(3)]

        total, counts, tasks, notes, inbox = service._analyze_category_distribution(entries)

        assert total == 3
        assert counts == {"task": 3}
        assert len(tasks) == 3
        assert len(notes) == 0


# ===== B93: export_growth_report 依赖注入测试 =====


class TestB93KnowledgeServiceDI:
    """B93: export_growth_report 通过构造函数注入 knowledge_service"""

    def test_constructor_accepts_knowledge_service(self):
        """构造函数接收 knowledge_service 参数"""
        ks = MagicMock()
        service = ReviewService(sqlite_storage=MagicMock())
        service.set_knowledge_service(ks)
        assert service._knowledge_service is ks

    @pytest.mark.asyncio
    async def test_export_growth_report_uses_injected_service(self):
        """export_growth_report 使用注入的 knowledge_service，不调 deps"""
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []
        mock_sqlite.count_entries.return_value = 0

        ks = MagicMock()
        ks.get_knowledge_stats = AsyncMock(return_value=MagicMock(
            concept_count=10, relation_count=5, category_distribution={"beginner": 10}
        ))

        service = ReviewService(sqlite_storage=mock_sqlite)
        service.set_knowledge_service(ks)

        report = await service.export_growth_report("user1")
        assert "成长报告" in report
        ks.get_knowledge_stats.assert_called_once_with("user1")

    @pytest.mark.asyncio
    async def test_export_growth_report_no_knowledge_service_graceful(self):
        """knowledge_service 未注入时知识图谱 section 显示'暂无数据'"""
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []
        mock_sqlite.count_entries.return_value = 0

        service = ReviewService(sqlite_storage=mock_sqlite)
        # 不设置 knowledge_service

        report = await service.export_growth_report("user1")
        assert "成长报告" in report
        assert "知识图谱" in report


class TestB96TrendDataFieldFix:
    """B96: export_growth_report 趋势数据字段名修复（daily_data → periods）"""

    def _make_service(self):
        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []
        mock_sqlite.count_entries.return_value = 0
        service = ReviewService(sqlite_storage=mock_sqlite)
        return service

    @pytest.mark.asyncio
    async def test_trend_data_with_periods_renders_weekly(self):
        """有趋势数据时 export_growth_report 正确渲染周维度趋势"""
        from app.models.review import TrendResponse, TrendPeriod

        service = self._make_service()
        # 2026-04-20 是周一，属于 W17 周；2026-04-13 也是周一，属于 W16 周
        periods = [
            TrendPeriod(date="2026-04-20", total=5, completed=3),
            TrendPeriod(date="2026-04-13", total=2, completed=1),
        ]
        trend_response = TrendResponse(periods=periods)

        with patch.object(service, "get_trend_data", return_value=trend_response):
            report = await service.export_growth_report("user1")

        assert "学习趋势" in report
        # 验证具体周数据渲染：W17 有 5 条，W16 有 2 条
        assert "2026-04-20: 5 条" in report
        assert "2026-04-13: 2 条" in report
        # 不应 fallback 到"暂无数据"
        # 趋势数据段之后到下一个 section 之前，不应出现"暂无数据"
        lines = report.split("\n")
        trend_start = None
        for i, line in enumerate(lines):
            if "学习趋势" in line:
                trend_start = i
                break
        assert trend_start is not None
        # 趋势段后面的行应包含具体数据
        after_trend = "\n".join(lines[trend_start:trend_start + 10])
        assert "暂无数据" not in after_trend

    @pytest.mark.asyncio
    async def test_trend_data_empty_periods_fallback(self):
        """空 periods 时 fallback 到'暂无数据'"""
        from app.models.review import TrendResponse

        service = self._make_service()
        trend_response = TrendResponse(periods=[])

        with patch.object(service, "get_trend_data", return_value=trend_response):
            report = await service.export_growth_report("user1")

        assert "暂无数据" in report

    @pytest.mark.asyncio
    async def test_regression_other_report_sections_intact(self):
        """回归: 其他 report section 不受影响"""
        from app.models.review import TrendResponse

        mock_sqlite = MagicMock()
        mock_sqlite.list_entries.return_value = []
        mock_sqlite.count_entries.return_value = 10
        mock_sqlite.count_entries_by_type.return_value = {"task": 5, "note": 3, "inbox": 2}
        service = ReviewService(sqlite_storage=mock_sqlite)

        with patch.object(service, "get_trend_data", return_value=TrendResponse(periods=[])):
            report = await service.export_growth_report("user1")

        assert "成长报告" in report
        assert "概览" in report
