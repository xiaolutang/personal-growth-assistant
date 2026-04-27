"""晨报方法组 — 从 ReviewService 拆分"""
import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, TYPE_CHECKING

from app.models.review import (
    DailyFocus,
    MorningDigestResponse,
    MorningDigestOverdue,
    MorningDigestStaleInbox,
    MorningDigestTodo,
    MorningDigestWeeklySummary,
)

if TYPE_CHECKING:
    from app.callers import APICaller

logger = logging.getLogger(__name__)

# B85: 晨报缓存 — 单进程 best-effort
MORNING_DIGEST_CACHE_MAX = 1000
morning_digest_cache: dict[str, tuple[dict, str]] = {}  # key -> (response_dict, cached_at)
morning_digest_lock = asyncio.Lock()
morning_digest_pending: set[str] = set()  # single-flight: 正在计算的 key


class MorningDigestMixin:
    """晨报相关方法，供 ReviewService 继承"""

    def _calculate_learning_streak(self, user_id: str) -> int:
        """
        计算学习连续天数（从今天开始往前数连续有记录的天数）

        Args:
            user_id: 用户 ID

        Returns:
            连续天数，无条目时返回 0
        """
        if not self._sqlite:
            return 0

        active_dates = self._sqlite.get_active_dates(user_id, days=90)

        if not active_dates:
            return 0

        date_set = set(active_dates)
        today = date.today()
        streak = 0
        current = today
        while current.isoformat() in date_set:
            streak += 1
            current -= timedelta(days=1)

        return streak

    def _compute_30d_tag_stats(self, user_id: str, days: int = 30, top_n: int = 10) -> list[tuple[str, int]]:
        """统计近 N 天条目的标签频次 top N（SQL 聚合）"""
        if not self._sqlite:
            return []
        today = date.today()
        start = (today - timedelta(days=days)).isoformat()
        return self._sqlite.get_tag_stats_in_range(
            user_id=user_id, start_date=start, end_date=today.isoformat(), top_n=top_n,
        )

    async def _generate_pattern_insights_llm(self, user_id: str) -> Optional[List[str]]:
        """B87: 使用 LLM 生成模式洞察。返回 None 表示 LLM 不可用/失败（需降级），返回列表表示 LLM 成功。"""
        if not self._sqlite or not self._llm_caller:
            return None

        today = date.today()
        start_30 = (today - timedelta(days=30)).isoformat()
        recent_entries = self._sqlite.list_entries(
            start_date=start_30,
            end_date=today.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        if not recent_entries:
            return []

        total = len(recent_entries)
        cat_counts: dict[str, int] = {}
        task_completed = 0
        task_total = 0
        weekday_counts: dict[str, int] = {}
        for entry in recent_entries:
            cat = entry.get("type", entry.get("category", "unknown"))
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            if cat == "task":
                task_total += 1
                if entry.get("status") == "complete":
                    task_completed += 1
            created = entry.get("created_at", "")
            if created:
                try:
                    wd = datetime.fromisoformat(created).strftime("%A")
                    weekday_counts[wd] = weekday_counts.get(wd, 0) + 1
                except (ValueError, TypeError):
                    pass

        top_tags = self._compute_30d_tag_stats(user_id, days=30, top_n=10)
        stats = {
            "total_entries": total,
            "category_distribution": cat_counts,
            "task_completion_rate": round(task_completed / task_total * 100, 1) if task_total > 0 else 0,
            "top_tags": top_tags,
            "weekday_activity": weekday_counts,
        }

        system_prompt = (
            "你是个人成长助手「日知」，请分析用户近 30 天的行为数据，"
            "生成最多 5 条有价值的中文洞察。每条洞察为一句简洁的描述。"
            "请直接返回一个 JSON 数组，例如 [\"洞察1\", \"洞察2\"]。"
            "不要返回其他内容。如果数据不足以生成洞察，返回空数组 []。"
        )

        user_message = f"用户近 30 天数据：\n{json.dumps(stats, ensure_ascii=False, indent=2)}"

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            result = await asyncio.wait_for(
                self._llm_caller.call(messages),
                timeout=10.0,
            )
            if not result:
                return []
            result = result.strip()
            parsed = json.loads(result)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if isinstance(item, (str, int, float))][:5]
            return []
        except asyncio.TimeoutError:
            logger.warning("B87: 模式洞察 LLM 超时，将降级到规则引擎")
            return None
        except (json.JSONDecodeError, ValueError):
            logger.warning("B87: 模式洞察 LLM 返回非预期结构，将降级到规则引擎")
            return None
        except Exception as e:
            logger.warning("B87: 模式洞察 LLM 失败: %s，将降级到规则引擎", e)
            return None

    def _generate_pattern_insights(self, user_id: str) -> List[str]:
        """
        分析最近 30 天的行为模式，生成洞察

        Args:
            user_id: 用户 ID

        Returns:
            最多 3 条洞察字符串
        """
        if not self._sqlite:
            return []

        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        seven_days_ago = today - timedelta(days=7)

        recent_entries = self._sqlite.list_entries(
            start_date=thirty_days_ago.isoformat(),
            end_date=today.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        if not recent_entries:
            return []

        insights: List[str] = []

        total_count, category_counts, _, _, _ = self._analyze_category_distribution(recent_entries)

        if total_count > 0:
            top_category = max(category_counts, key=category_counts.get)
            top_ratio = category_counts[top_category] / total_count

            top_label = self.CATEGORY_LABELS.get(top_category, top_category)

            if top_ratio > 0.6 and total_count >= 5:
                insights.append(
                    f"你最近 30 天更倾向于创建{top_label}，"
                    f"占比 {int(top_ratio * 100)}%"
                )

        recent_7_entries = [
            e for e in recent_entries
            if e.get("type") == "task"
            and self._parse_entry_date(e.get("created_at")) is not None
            and self._parse_entry_date(e.get("created_at")) >= seven_days_ago
        ]
        older_entries = [
            e for e in recent_entries
            if e.get("type") == "task"
            and self._parse_entry_date(e.get("created_at")) is not None
            and self._parse_entry_date(e.get("created_at")) < seven_days_ago
        ]

        if recent_7_entries and older_entries:
            recent_completed = sum(1 for e in recent_7_entries if e.get("status") == "complete")
            recent_rate = recent_completed / len(recent_7_entries) * 100

            older_completed = sum(1 for e in older_entries if e.get("status") == "complete")
            older_rate = older_completed / len(older_entries) * 100

            diff = recent_rate - older_rate
            if abs(diff) >= 15:
                direction = "提升" if diff > 0 else "下降"
                insights.append(
                    f"你的任务完成率比上周{direction}了 {int(abs(diff))}%"
                )

        inbox_count = category_counts.get("inbox", 0)
        if inbox_count >= 3:
            insights.append(
                f"你有 {inbox_count} 个灵感尚未转化为行动"
            )

        return insights[:3]

    @staticmethod
    def _parse_entry_date(val) -> Optional[date]:
        """解析条目的日期字段"""
        if not val:
            return None
        if isinstance(val, date):
            return val
        try:
            return datetime.fromisoformat(str(val).replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            try:
                return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return None

    @staticmethod
    def _parse_llm_json(text: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON（可能包含在 markdown 代码块中）"""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

    async def _generate_daily_focus(
        self,
        user_id: str,
        overdue: list,
        learning_streak: int,
        recent_activity: list,
    ) -> Optional[DailyFocus]:
        """
        生成每日聚焦建议

        优先使用 LLM 生成个性化建议，LLM 不可用时降级为模板。

        Args:
            user_id: 用户 ID
            overdue: 逾期任务列表
            learning_streak: 学习连续天数
            recent_activity: 近期活动列表

        Returns:
            DailyFocus 或 None
        """
        if self._llm_caller:
            try:
                system_prompt = (
                    "你是个人成长助手「日知」，请为用户推荐今天最值得关注的一件事。"
                    "返回 JSON 格式：{\"title\": \"标题\", \"description\": \"描述\", \"target_entry_id\": \"id或null\"}"
                )
                context_data = {
                    "overdue_tasks": [
                        {"id": t.get("id"), "title": t.get("title"), "priority": t.get("priority")}
                        for t in overdue[:3]
                    ],
                    "learning_streak": learning_streak,
                    "recent_titles": [e.get("title", "") for e in recent_activity[:5]],
                }
                user_message = (
                    f"用户学习连续天数：{learning_streak}\n"
                    f"逾期任务：{json.dumps(context_data['overdue_tasks'], ensure_ascii=False)}\n"
                    f"近期活动：{json.dumps(context_data['recent_titles'], ensure_ascii=False)}\n\n"
                    f"请推荐今天最应该聚焦的一件事。"
                )
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
                result = await asyncio.wait_for(self._llm_caller.call(messages), timeout=10.0)
                if result:
                    try:
                        parsed = self._parse_llm_json(result)
                        if parsed and isinstance(parsed, dict) and "title" in parsed:
                            return DailyFocus(
                                title=str(parsed["title"]),
                                description=str(parsed.get("description", "")),
                                target_entry_id=parsed.get("target_entry_id"),
                            )
                    except (json.JSONDecodeError, KeyError, TypeError):
                        logger.debug("LLM daily_focus JSON 解析失败，降级为模板")
                        return DailyFocus(
                            title=result[:50].strip(),
                            description=result.strip(),
                        )
            except (asyncio.TimeoutError, Exception) as e:
                logger.debug(f"LLM daily_focus 生成失败: {e}")

        # 降级为模板
        if overdue:
            t = overdue[0]
            return DailyFocus(
                title=f"处理逾期任务：{t.get('title', '未命名')}",
                description=f"该任务已逾期，优先级为 {t.get('priority', 'medium')}，建议今天优先完成。",
                target_entry_id=t.get("id"),
            )

        if recent_activity:
            entry = recent_activity[0]
            if entry.get("status") != "complete":
                return DailyFocus(
                    title=f"继续推进：{entry.get('title', '未命名')}",
                    description="这是你最近在做的任务，保持节奏继续前进。",
                    target_entry_id=entry.get("id"),
                )

        return None

    async def get_morning_digest(self, user_id: str) -> MorningDigestResponse:
        """
        获取 AI 晨报数据

        聚合：今日待办 + 拖延任务 + 未跟进灵感 + 本周学习摘要

        Args:
            user_id: 用户 ID

        Returns:
            MorningDigestResponse
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        today = date.today()
        today_str = today.isoformat()
        cache_key = f"{user_id}:{today_str}"

        # --- B85: 缓存检查 + single-flight ---
        while True:
            async with morning_digest_lock:
                if cache_key in morning_digest_cache:
                    cached_data = morning_digest_cache.pop(cache_key)
                    morning_digest_cache[cache_key] = cached_data
                    cached_dict, cached_at = cached_data
                    response = MorningDigestResponse(**cached_dict)
                    response.cached_at = cached_at
                    logger.debug("晨报缓存命中: %s", cache_key)
                    return response
                if cache_key in morning_digest_pending:
                    pass
                else:
                    morning_digest_pending.add(cache_key)
                    break
            await asyncio.sleep(0.01)

        try:
            tomorrow_str = (today + timedelta(days=1)).isoformat()

            # 1. 今日待办
            all_active_tasks = self._sqlite.list_entries(
                type="task", status="doing", limit=200, user_id=user_id,
            )
            all_wait_tasks = self._sqlite.list_entries(
                type="task", status="waitStart", limit=200, user_id=user_id,
            )
            active_tasks = all_active_tasks + all_wait_tasks

            today_todos = [
                t for t in active_tasks
                if self._parse_entry_date(t.get("planned_date")) == today
            ]

            priority_order = {"high": 0, "medium": 1, "low": 2}
            today_todos.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

            # 2. 拖延任务
            past_tasks = self._sqlite.list_entries(
                type="task", end_date=today_str, limit=200, user_id=user_id,
            )
            overdue = [
                t for t in past_tasks
                if t.get("status") in ("waitStart", "doing")
                and t.get("planned_date")
                and self._parse_entry_date(t.get("planned_date")) is not None
                and self._parse_entry_date(t.get("planned_date")) < today
            ]
            overdue.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 1))

            # 3. 未跟进灵感
            three_days_ago = today - timedelta(days=3)
            old_inbox = self._sqlite.list_entries(
                type="inbox", end_date=three_days_ago.isoformat(), limit=200, user_id=user_id,
            )
            stale_inbox = [
                i for i in old_inbox
                if i.get("status") in ("waitStart", "pending")
            ]

            # 4. 本周学习摘要
            week_start = today - timedelta(days=today.weekday())
            week_end_str = (week_start + timedelta(days=6)).isoformat()
            week_start_str = week_start.isoformat()

            week_entries = self._sqlite.list_entries(
                start_date=week_start_str,
                end_date=week_end_str,
                limit=1000,
                user_id=user_id,
            )

            new_concepts_set: set = set()
            for entry in week_entries:
                for tag in entry.get("tags", []):
                    new_concepts_set.add(tag)

            weekly_summary = MorningDigestWeeklySummary(
                new_concepts=sorted(new_concepts_set)[:10],
                entries_count=len(week_entries),
            )

            # 5. 构建 AI 建议
            ai_suggestion = await self._generate_morning_suggestion(
                today_todos=today_todos,
                overdue=overdue,
                stale_inbox=stale_inbox,
                weekly_summary=weekly_summary,
                user_id=user_id,
            )

            # 6. 新增增强字段
            learning_streak = self._calculate_learning_streak(user_id)
            pattern_insights = await self._generate_pattern_insights_llm(user_id)
            if pattern_insights is None:
                pattern_insights = self._generate_pattern_insights(user_id)
            daily_focus = await self._generate_daily_focus(
                user_id=user_id,
                overdue=overdue,
                learning_streak=learning_streak,
                recent_activity=today_todos[:5] + overdue[:5],
            )

            # 7. 知识推荐（B115）
            knowledge_recommendations = None
            try:
                if self._knowledge_service is not None:
                    from app.routers import deps
                    rec_svc = deps.get_recommendation_service()
                    rec_resp = await rec_svc.get_recommendations(user_id=user_id)
                    knowledge_recommendations = rec_resp.model_dump()
            except Exception:
                logger.debug("B115: 晨报知识推荐获取失败，跳过", exc_info=True)

            response = MorningDigestResponse(
                date=today_str,
                ai_suggestion=ai_suggestion,
                todos=[
                    MorningDigestTodo(
                        id=t.get("id", ""),
                        title=t.get("title", ""),
                        priority=t.get("priority", "medium"),
                        planned_date=t.get("planned_date"),
                    )
                    for t in today_todos[:5]
                ],
                overdue=[
                    MorningDigestOverdue(
                        id=t.get("id", ""),
                        title=t.get("title", ""),
                        priority=t.get("priority", "medium"),
                        planned_date=t.get("planned_date"),
                    )
                    for t in overdue[:5]
                ],
                stale_inbox=[
                    MorningDigestStaleInbox(
                        id=i.get("id", ""),
                        title=i.get("title", ""),
                        created_at=i.get("created_at", ""),
                    )
                    for i in stale_inbox[:5]
                ],
                weekly_summary=weekly_summary,
                learning_streak=learning_streak,
                daily_focus=daily_focus,
                pattern_insights=pattern_insights,
                knowledge_recommendations=knowledge_recommendations,
                cached_at=None,
            )

            # --- B85: 写入缓存 ---
            async with morning_digest_lock:
                keys_to_remove = [k for k in morning_digest_cache if not k.endswith(f":{today_str}")]
                for k in keys_to_remove:
                    del morning_digest_cache[k]
                if keys_to_remove:
                    logger.debug("晨报缓存跨日清理: 删除 %d 条旧缓存", len(keys_to_remove))

                morning_digest_cache[cache_key] = (
                    response.model_dump(),
                    datetime.now(timezone.utc).isoformat(),
                )
                if len(morning_digest_cache) > MORNING_DIGEST_CACHE_MAX:
                    oldest_key = next(iter(morning_digest_cache))
                    del morning_digest_cache[oldest_key]
                    logger.debug("晨报缓存淘汰: %s", oldest_key)
                morning_digest_pending.discard(cache_key)

            return response
        except Exception:
            async with morning_digest_lock:
                morning_digest_pending.discard(cache_key)
            raise

    async def _generate_morning_suggestion(
        self,
        today_todos: list,
        overdue: list,
        stale_inbox: list,
        weekly_summary: MorningDigestWeeklySummary,
        user_id: str,
    ) -> str:
        """生成晨报建议文本，LLM 不可用时降级为模板"""
        todo_count = len(today_todos)
        overdue_count = len(overdue)
        stale_count = len(stale_inbox)
        concepts_count = len(weekly_summary.new_concepts)
        entries_count = weekly_summary.entries_count

        if self._llm_caller:
            try:
                stats_data = {
                    "todo_count": todo_count,
                    "overdue_count": overdue_count,
                    "stale_inbox_count": stale_count,
                    "week_new_concepts": weekly_summary.new_concepts[:5],
                    "week_entries_count": entries_count,
                    "todos": [t.get("title", "") for t in today_todos[:3]],
                    "overdue_titles": [t.get("title", "") for t in overdue[:3]],
                }

                # B86: 注入活跃目标
                try:
                    if self._goal_service:
                        goals, _, _ = await self._goal_service.list_goals(user_id, status="active")
                        if goals:
                            stats_data["active_goals"] = [
                                {"title": g.get("title", ""), "progress": g.get("progress_percentage", 0)}
                                for g in goals[:5]
                            ]
                except Exception:
                    logger.debug("B86: GoalService 不可用，跳过目标注入", exc_info=True)

                # B86: 注入近 30 天高频标签 top 5
                try:
                    top_tags = self._compute_30d_tag_stats(user_id, days=30, top_n=5)
                    if top_tags:
                        stats_data["top_tags_30d"] = [t[0] for t in top_tags]
                except Exception:
                    logger.debug("B86: 标签统计失败，跳过标签注入", exc_info=True)

                # B86: 个性化晨报 prompt
                has_goals = "active_goals" in stats_data
                has_tags = "top_tags_30d" in stats_data
                morning_prompt = (
                    "你是个人成长助手「日知」，请根据以下数据为用户生成一段个性化的早安建议（2-3句话）。"
                    "建议应具体、可执行，直接关联用户的目标和近期关注领域。"
                )
                if has_goals:
                    morning_prompt += "请结合用户的活跃目标，给出与目标相关的具体行动建议。"
                if has_tags:
                    morning_prompt += "请参考用户近期高频关注的话题方向，让建议更贴合实际。"

                suggestion = await self._generate_ai_summary(
                    "morning_digest", stats_data, user_id=user_id,
                    system_prompt_override=morning_prompt,
                )
                if suggestion:
                    return suggestion
            except Exception:
                logger.debug("B86: LLM 晨报建议生成失败，降级为模板", exc_info=True)

        # 降级为模板文本
        parts = []
        if todo_count > 0:
            parts.append(f"你有{todo_count}个任务待完成")
            if overdue_count > 0:
                parts[0] += f"，其中{overdue_count}个已逾期"
        elif overdue_count > 0:
            parts.append(f"你有{overdue_count}个逾期任务需要处理")
        else:
            parts.append("今天没有待办任务，适合学习新知识")

        if stale_count > 0:
            parts.append(f"有{stale_count}个灵感超过3天未跟进")

        if concepts_count > 0:
            parts.append(f"本周学习了{concepts_count}个新概念")

        return "，".join(parts) + "。"
