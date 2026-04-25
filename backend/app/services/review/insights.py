"""深度洞察方法组 — 从 ReviewService 拆分"""
import asyncio
import json
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional

from app.models.review import (
    BehaviorPattern,
    CapabilityChange,
    DeepInsights,
    GrowthSuggestion,
    InsightsResponse,
)

logger = logging.getLogger(__name__)


class InsightsMixin:
    """深度洞察相关方法，供 ReviewService 继承"""

    async def get_insights(
        self, period: str = "weekly", user_id: Optional[str] = None
    ) -> InsightsResponse:
        """
        获取 AI 深度洞察

        Args:
            period: 统计周期 (weekly|monthly)
            user_id: 用户 ID

        Returns:
            InsightsResponse 结构化洞察
        """
        if period not in ("weekly", "monthly"):
            raise ValueError(f"不支持的统计 period: {period}")

        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        today = date.today()

        # 计算时间范围
        if period == "weekly":
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        else:  # monthly
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year, 12, 31)
            else:
                next_month = date(today.year, today.month + 1, 1)
                end_date = next_month - timedelta(days=1)

        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # 获取周期内条目
        entries = self._sqlite.list_entries(
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        # 获取前一个周期的条目（用于对比）
        if period == "weekly":
            prev_start = start_date - timedelta(days=7)
            prev_end = start_date - timedelta(days=1)
        else:
            if today.month == 1:
                prev_start = date(today.year - 1, 12, 1)
            else:
                prev_start = date(today.year, today.month - 1, 1)
            prev_end = start_date - timedelta(days=1)

        prev_entries = self._sqlite.list_entries(
            start_date=prev_start.isoformat(),
            end_date=prev_end.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        # 尝试 LLM 生成深度洞察
        insights, source = await self._generate_deep_insights(
            period=period,
            entries=entries,
            prev_entries=prev_entries,
            start_date=start_str,
            end_date=end_str,
            user_id=user_id or "_default",
        )

        return InsightsResponse(
            period=period,
            start_date=start_str,
            end_date=end_str,
            insights=insights,
            source=source,
        )

    async def _generate_deep_insights(
        self,
        period: str,
        entries: List[dict],
        prev_entries: List[dict],
        start_date: str,
        end_date: str,
        user_id: str,
    ) -> tuple:
        """
        生成深度洞察

        优先使用 LLM 生成结构化洞察，LLM 不可用时降级为规则分析。
        """
        # 先尝试 LLM
        if self._llm_caller:
            try:
                _, _, curr_tasks, curr_notes, curr_inbox = self._analyze_category_distribution(entries)
                curr_completed = sum(1 for t in curr_tasks if t.get("status") == "complete")
                curr_completion_rate = (curr_completed / len(curr_tasks) * 100) if curr_tasks else 0

                _, _, prev_tasks, _, _ = self._analyze_category_distribution(prev_entries)
                prev_completed = sum(1 for t in prev_tasks if t.get("status") == "complete")
                prev_completion_rate = (prev_completed / len(prev_tasks) * 100) if prev_tasks else 0

                curr_tags = []
                for e in entries:
                    curr_tags.extend(e.get("tags", []))

                stats_data = {
                    "period": period,
                    "start_date": start_date,
                    "end_date": end_date,
                    "current": {
                        "total_entries": len(entries),
                        "tasks": len(curr_tasks),
                        "completed": curr_completed,
                        "completion_rate": round(curr_completion_rate, 1),
                        "notes": len(curr_notes),
                        "inbox": len(curr_inbox),
                        "top_tags": list(set(curr_tags))[:10],
                    },
                    "previous": {
                        "total_entries": len(prev_entries),
                        "tasks": len(prev_tasks),
                        "completed": prev_completed,
                        "completion_rate": round(prev_completion_rate, 1),
                    },
                }

                system_prompt = (
                    "你是个人成长助手「日知」，请根据用户数据生成深度洞察。"
                    "必须返回 JSON 格式，包含三个字段：\n"
                    "1. behavior_patterns: 行为模式数组，每项含 pattern(描述), frequency(次数), trend(improving/stable/declining)\n"
                    "2. growth_suggestions: 成长建议数组，每项含 suggestion(建议), priority(high/medium/low), related_area(领域)\n"
                    "3. capability_changes: 能力变化数组，每项含 capability(能力名), previous_level(0-1), current_level(0-1), change(变化值)\n"
                    "每个数组最多3项。只返回 JSON，不要其他内容。"
                )

                user_message = (
                    f"周期类型：{period}\n"
                    f"统计数据：\n{json.dumps(stats_data, ensure_ascii=False, indent=2)}\n\n"
                    f"请生成深度洞察。"
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
                result = await asyncio.wait_for(
                    self._llm_caller.call(messages),
                    timeout=10.0,
                )

                if result:
                    parsed = self._parse_llm_json(result)
                    if parsed and isinstance(parsed, dict):
                        insights = DeepInsights(
                            behavior_patterns=[
                                BehaviorPattern(**bp)
                                for bp in parsed.get("behavior_patterns", [])[:3]
                            ],
                            growth_suggestions=[
                                GrowthSuggestion(**gs)
                                for gs in parsed.get("growth_suggestions", [])[:3]
                            ],
                            capability_changes=[
                                CapabilityChange(**cc)
                                for cc in parsed.get("capability_changes", [])[:3]
                            ],
                        )
                        return insights, "llm"

            except asyncio.TimeoutError:
                logger.warning("LLM 深度洞察生成超时，降级为规则分析")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"LLM 深度洞察 JSON 解析失败，降级为规则分析: {e}")
            except Exception as e:
                logger.warning(f"LLM 深度洞察生成失败，降级为规则分析: {e}")

        # 降级为规则分析
        insights = self._generate_rule_based_insights(
            period, entries, prev_entries
        )
        return insights, "rule_based"

    def _analyze_category_distribution(
        self, entries: List[dict]
    ) -> tuple:
        """分析条目分类分布，返回 (total, category_counts, curr_tasks, curr_notes, curr_inbox)"""
        curr_tasks = [e for e in entries if e.get("type") == "task"]
        curr_notes = [e for e in entries if e.get("type") == "note"]
        curr_inbox = [e for e in entries if e.get("type") == "inbox"]

        category_counts: Dict[str, int] = {}
        for entry in entries:
            entry_type = entry.get("type", "task")
            category_counts[entry_type] = category_counts.get(entry_type, 0) + 1

        return len(entries), category_counts, curr_tasks, curr_notes, curr_inbox

    def _generate_rule_based_insights(
        self,
        period: str,
        entries: List[dict],
        prev_entries: List[dict],
    ) -> DeepInsights:
        """
        基于规则的洞察生成（LLM 不可用时的降级方案）

        Args:
            period: 周期 (weekly|monthly)
            entries: 本周期条目
            prev_entries: 上周期条目

        Returns:
            DeepInsights 结构化洞察
        """
        behavior_patterns: List[BehaviorPattern] = []
        growth_suggestions: List[GrowthSuggestion] = []
        capability_changes: List[CapabilityChange] = []

        total, category_counts, curr_tasks, curr_notes, curr_inbox = (
            self._analyze_category_distribution(entries)
        )

        period_label = "本周" if period == "weekly" else "本月"

        # --- 行为模式：分类分布 ---
        if total > 0:
            for cat_type, count in category_counts.items():
                ratio = count / total
                if ratio > 0.6 and total >= 5:
                    behavior_patterns.append(BehaviorPattern(
                        pattern=f"{period_label}更倾向于创建{self.CATEGORY_LABELS.get(cat_type, cat_type)}，占比{int(ratio * 100)}%",
                        frequency=count,
                        trend="stable",
                    ))

        # --- 行为模式：完成率趋势 ---
        curr_completed = sum(1 for t in curr_tasks if t.get("status") == "complete")
        curr_rate = (curr_completed / len(curr_tasks) * 100) if curr_tasks else 0

        prev_tasks = [e for e in prev_entries if e.get("type") == "task"]
        prev_completed = sum(1 for t in prev_tasks if t.get("status") == "complete")
        prev_rate = (prev_completed / len(prev_tasks) * 100) if prev_tasks else 0

        if curr_tasks and prev_tasks:
            diff = curr_rate - prev_rate
            if abs(diff) >= 15:
                trend = "improving" if diff > 0 else "declining"
                direction = "提升" if diff > 0 else "下降"
                behavior_patterns.append(BehaviorPattern(
                    pattern=f"{period_label}任务完成率比上期{direction}了{int(abs(diff))}%",
                    frequency=len(curr_tasks),
                    trend=trend,
                ))

        # --- 成长建议 ---
        inbox_count = len(curr_inbox)
        if inbox_count >= 3:
            growth_suggestions.append(GrowthSuggestion(
                suggestion=f"有{inbox_count}个灵感尚未转化为行动，建议及时整理",
                priority="medium",
                related_area="灵感管理",
            ))

        if curr_rate < 50 and len(curr_tasks) >= 3:
            growth_suggestions.append(GrowthSuggestion(
                suggestion=f"{period_label}任务完成率较低，建议减少并行任务数量",
                priority="high",
                related_area="任务管理",
            ))

        if len(curr_notes) == 0 and total >= 3:
            growth_suggestions.append(GrowthSuggestion(
                suggestion=f"{period_label}没有记录学习笔记，建议养成记录习惯",
                priority="medium",
                related_area="学习记录",
            ))

        # --- 能力变化（基于标签活跃度） ---
        curr_tags: Dict[str, int] = {}
        for entry in entries:
            for tag in entry.get("tags", []):
                curr_tags[tag] = curr_tags.get(tag, 0) + 1

        prev_tags: Dict[str, int] = {}
        for entry in prev_entries:
            for tag in entry.get("tags", []):
                prev_tags[tag] = prev_tags.get(tag, 0) + 1

        all_tags = set(curr_tags.keys()) | set(prev_tags.keys())
        for tag in sorted(all_tags, key=lambda t: curr_tags.get(t, 0), reverse=True)[:3]:
            curr_count = curr_tags.get(tag, 0)
            prev_count = prev_tags.get(tag, 0)
            curr_level = min(curr_count / 5.0, 1.0)
            prev_level = min(prev_count / 5.0, 1.0)
            if abs(curr_level - prev_level) > 0.01:
                capability_changes.append(CapabilityChange(
                    capability=tag,
                    previous_level=round(prev_level, 2),
                    current_level=round(curr_level, 2),
                    change=round(curr_level - prev_level, 2),
                ))

        return DeepInsights(
            behavior_patterns=behavior_patterns[:3],
            growth_suggestions=growth_suggestions[:3],
            capability_changes=capability_changes[:3],
        )
