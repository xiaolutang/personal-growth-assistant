"""成长回顾统计服务"""
import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from app.models.review import *  # noqa: F401,F403 — re-export for backward compat
from app.utils.mastery import calculate_mastery_from_stats
from app.services.review.morning_digest import (
    MorningDigestMixin,
    morning_digest_cache as _morning_digest_cache,
    morning_digest_lock as _morning_digest_lock,
    morning_digest_pending as _morning_digest_pending,
    MORNING_DIGEST_CACHE_MAX as _MORNING_DIGEST_CACHE_MAX,
)
from app.services.review.insights import InsightsMixin
if TYPE_CHECKING:
    from app.callers import APICaller

logger = logging.getLogger(__name__)

# Backward compat: 保持模块级缓存变量可被外部测试 import
__all__ = ["ReviewService", "_MORNING_DIGEST_CACHE_MAX", "_morning_digest_cache",
           "_morning_digest_lock", "_morning_digest_pending"]


class ReviewService(MorningDigestMixin, InsightsMixin):
    """成长回顾统计服务"""

    CATEGORY_LABELS = {"task": "任务", "note": "笔记", "inbox": "灵感", "project": "项目"}

    def __init__(self, sqlite_storage=None, neo4j_client=None):
        """
        初始化服务

        Args:
            sqlite_storage: SQLite 存储实例
            neo4j_client: Neo4j 客户端（可选，用于知识热力图增强）
        """
        self._sqlite = sqlite_storage
        self._neo4j_client = neo4j_client
        self._llm_caller: Optional["APICaller"] = None
        self._goal_service = None  # 通过 set_goal_service 注入
        self._knowledge_service = None  # 通过 set_knowledge_service 注入

    def set_sqlite_storage(self, storage):
        """设置 SQLite 存储"""
        self._sqlite = storage

    def set_llm_caller(self, caller: "APICaller"):
        """设置 LLM 调用器"""
        self._llm_caller = caller

    def set_goal_service(self, goal_service):
        """设置目标服务（由 deps.py 注入）"""
        self._goal_service = goal_service

    def set_knowledge_service(self, knowledge_service):
        """设置知识图谱服务（由 deps.py 注入）"""
        self._knowledge_service = knowledge_service

    @property
    def goal_service(self):
        """获取目标服务实例"""
        return self._goal_service

    @property
    def knowledge_service(self):
        """获取知识图谱服务实例"""
        return self._knowledge_service

    @staticmethod
    def calculate_task_stats(tasks: List[dict]) -> TaskStats:
        """计算任务统计"""
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("status") == "complete")
        doing = sum(1 for t in tasks if t.get("status") == "doing")
        wait_start = sum(1 for t in tasks if t.get("status") == "waitStart")

        completion_rate = (completed / total * 100) if total > 0 else 0

        return TaskStats(
            total=total,
            completed=completed,
            doing=doing,
            wait_start=wait_start,
            completion_rate=round(completion_rate, 1),
        )

    @staticmethod
    def calculate_note_stats(notes: List[dict]) -> NoteStats:
        """计算笔记统计"""
        return NoteStats(
            total=len(notes),
            recent_titles=[n.get("title", "")[:50] for n in notes[:5]],
        )

    async def get_daily_report(self, target_date: Optional[date] = None, user_id: Optional[str] = None) -> DailyReport:
        """获取日报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if target_date is None:
            target_date = date.today()

        date_str = target_date.isoformat()

        tasks = self._sqlite.list_entries(
            type="task",
            start_date=date_str,
            end_date=date_str,
            limit=1000,
            user_id=user_id,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=date_str,
            end_date=date_str,
            limit=1000,
            user_id=user_id,
        )

        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)
        completed_tasks = [t for t in tasks if t.get("status") == "complete"]

        # 生成 AI 总结
        ai_summary = None
        if self._llm_caller:
            stats_data = {
                "task_stats": task_stats.model_dump(),
                "note_stats": note_stats.model_dump(),
                "completed_tasks": [
                    {"id": t.get("id"), "title": t.get("title")}
                    for t in completed_tasks
                ],
                "recent_note_titles": note_stats.recent_titles,
            }
            ai_summary = await self._generate_ai_summary("daily", stats_data, user_id=user_id or "_default")

        return DailyReport(
            date=date_str,
            task_stats=task_stats,
            note_stats=note_stats,
            completed_tasks=completed_tasks,
            ai_summary=ai_summary,
        )

    async def get_weekly_report(self, week_start: Optional[date] = None, user_id: Optional[str] = None) -> WeeklyReport:
        """获取周报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        start_str = week_start.isoformat()
        end_str = week_end.isoformat()

        tasks = self._sqlite.list_entries(
            type="task",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)

        daily_breakdown = []
        # 从已获取的 tasks 中按日聚合，避免 N+1 查询
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_str = day.isoformat()
            day_tasks = [t for t in tasks if t.get("created_at", "")[:10] == day_str or t.get("updated_at", "")[:10] == day_str]
            completed = sum(1 for t in day_tasks if t.get("status") == "complete")
            daily_breakdown.append({
                "date": day_str,
                "total": len(day_tasks),
                "completed": completed,
            })

        # 生成 AI 总结
        ai_summary = None
        if self._llm_caller:
            stats_data = {
                "task_stats": task_stats.model_dump(),
                "note_stats": note_stats.model_dump(),
                "daily_breakdown": daily_breakdown,
                "recent_note_titles": note_stats.recent_titles,
            }
            ai_summary = await self._generate_ai_summary("weekly", stats_data, user_id=user_id or "_default")

        # 计算环比上周
        vs_last_week = self._calculate_weekly_vs_last_week(
            week_start, task_stats, user_id
        )

        return WeeklyReport(
            start_date=start_str,
            end_date=week_end.isoformat(),
            task_stats=task_stats,
            note_stats=note_stats,
            daily_breakdown=daily_breakdown,
            ai_summary=ai_summary,
            vs_last_week=vs_last_week,
        )

    def _calculate_weekly_vs_last_week(
        self, week_start: date, current_task_stats: TaskStats, user_id: Optional[str]
    ) -> Optional[VsLastPeriod]:
        """计算周环比差值"""
        last_week_start = week_start - timedelta(weeks=1)
        last_week_end = last_week_start + timedelta(days=6)

        last_tasks = self._sqlite.list_entries(
            type="task",
            start_date=last_week_start.isoformat(),
            end_date=last_week_end.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        last_total = len(last_tasks)
        last_completed = sum(1 for t in last_tasks if t.get("status") == "complete")
        last_completion_rate = (last_completed / last_total * 100) if last_total > 0 else 0.0

        if last_total == 0 and current_task_stats.total == 0:
            return VsLastPeriod(delta_completion_rate=None, delta_total=None)

        return VsLastPeriod(
            delta_completion_rate=round(current_task_stats.completion_rate - last_completion_rate, 1),
            delta_total=current_task_stats.total - last_total,
        )

    def _calculate_monthly_vs_last_month(
        self, month_start: date, current_task_stats: TaskStats, user_id: Optional[str]
    ) -> Optional[VsLastPeriod]:
        """计算月环比差值"""
        if month_start.month == 1:
            last_month_start = date(month_start.year - 1, 12, 1)
        else:
            last_month_start = date(month_start.year, month_start.month - 1, 1)

        if last_month_start.month == 12:
            last_month_end = date(last_month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_month_end = date(last_month_start.year, last_month_start.month + 1, 1) - timedelta(days=1)

        last_tasks = self._sqlite.list_entries(
            type="task",
            start_date=last_month_start.isoformat(),
            end_date=last_month_end.isoformat(),
            limit=1000,
            user_id=user_id,
        )

        last_total = len(last_tasks)
        last_completed = sum(1 for t in last_tasks if t.get("status") == "complete")
        last_completion_rate = (last_completed / last_total * 100) if last_total > 0 else 0.0

        if last_total == 0 and current_task_stats.total == 0:
            return VsLastPeriod(delta_completion_rate=None, delta_total=None)

        return VsLastPeriod(
            delta_completion_rate=round(current_task_stats.completion_rate - last_completion_rate, 1),
            delta_total=current_task_stats.total - last_total,
        )

    async def get_monthly_report(self, month_start: Optional[date] = None, user_id: Optional[str] = None) -> MonthlyReport:
        """获取月报"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if month_start is None:
            today = date.today()
            month_start = date(today.year, today.month, 1)

        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

        start_str = month_start.isoformat()
        end_str = month_end.isoformat()

        tasks = self._sqlite.list_entries(
            type="task",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        notes = self._sqlite.list_entries(
            type="note",
            start_date=start_str,
            end_date=end_str,
            limit=1000,
            user_id=user_id,
        )

        task_stats = self.calculate_task_stats(tasks)
        note_stats = self.calculate_note_stats(notes)

        weekly_breakdown = []
        current_week_start = month_start
        week_num = 1

        # 从已获取的 tasks 中按周聚合，避免 N+1 查询
        while current_week_start <= month_end:
            week_end = min(current_week_start + timedelta(days=6), month_end)
            ws_str = current_week_start.isoformat()
            we_str = week_end.isoformat()

            week_tasks = [
                t for t in tasks
                if ws_str <= (t.get("created_at", "")[:10]) <= we_str
                or ws_str <= (t.get("updated_at", "")[:10]) <= we_str
            ]

            completed = sum(1 for t in week_tasks if t.get("status") == "complete")
            weekly_breakdown.append({
                "week": f"第{week_num}周",
                "start_date": ws_str,
                "end_date": we_str,
                "total": len(week_tasks),
                "completed": completed,
            })

            current_week_start = week_end + timedelta(days=1)
            week_num += 1

        # 生成 AI 总结
        ai_summary = None
        if self._llm_caller:
            stats_data = {
                "task_stats": task_stats.model_dump(),
                "note_stats": note_stats.model_dump(),
                "weekly_breakdown": weekly_breakdown,
                "recent_note_titles": note_stats.recent_titles,
            }
            ai_summary = await self._generate_ai_summary("monthly", stats_data, user_id=user_id or "_default")

        # 计算环比上月
        vs_last_month = self._calculate_monthly_vs_last_month(
            month_start, task_stats, user_id
        )

        return MonthlyReport(
            month=month_start.strftime("%Y-%m"),
            task_stats=task_stats,
            note_stats=note_stats,
            weekly_breakdown=weekly_breakdown,
            ai_summary=ai_summary,
            vs_last_month=vs_last_month,
        )

    def get_trend_data(
        self,
        period: str = "daily",
        days: int = 7,
        weeks: int = 8,
        user_id: Optional[str] = None,
    ) -> TrendResponse:
        """获取趋势数据（单次聚合 SQL 替代 N+1 循环查询）"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        if period not in ("daily", "weekly"):
            raise ValueError("period 参数必须是 daily 或 weekly")

        if period == "daily":
            count = max(1, min(days, 365))
            today = date.today()
            start = today - timedelta(days=count - 1)
            end = today + timedelta(days=1)
            agg = self._sqlite.get_trend_aggregation(
                user_id=user_id,
                start_date=start.isoformat(),
                end_date=end.isoformat(),
            )
            return self._build_daily_trend(agg, start, count)
        else:  # weekly
            count = max(1, min(weeks, 52))
            today = date.today()
            current_week_start = today - timedelta(days=today.weekday())
            oldest_week_start = current_week_start - timedelta(weeks=count - 1)
            end = current_week_start + timedelta(days=7)
            agg = self._sqlite.get_trend_aggregation(
                user_id=user_id,
                start_date=oldest_week_start.isoformat(),
                end_date=end.isoformat(),
            )
            return self._build_weekly_trend(agg, current_week_start, count)

    def _build_daily_trend(
        self, agg: list[dict], start: date, count: int
    ) -> TrendResponse:
        """从聚合数据构建日趋势（内存 O(N) 分桶）"""
        from collections import defaultdict

        buckets: dict[str, dict] = defaultdict(
            lambda: {"task": 0, "task_complete": 0, "note": 0, "inbox": 0}
        )
        for row in agg:
            d = row["d"]
            cat = row["category"] or "task"
            status = row["status"] or ""
            cnt = row["cnt"]
            b = buckets[d]
            if cat == "task":
                b["task"] += cnt
                if status == "complete":
                    b["task_complete"] += cnt
            elif cat == "note":
                b["note"] += cnt
            elif cat == "inbox":
                b["inbox"] += cnt

        periods: List[TrendPeriod] = []
        for i in range(count):
            target = start + timedelta(days=i)
            ds = target.isoformat()
            b = buckets.get(ds, {"task": 0, "task_complete": 0, "note": 0, "inbox": 0})
            total = b["task"]
            completed = b["task_complete"]
            completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0
            periods.append(TrendPeriod(
                date=ds,
                total=total,
                completed=completed,
                completion_rate=completion_rate,
                notes_count=b["note"],
                task_count=total,
                inbox_count=b["inbox"],
            ))

        return TrendResponse(periods=periods)

    def _build_weekly_trend(
        self, agg: list[dict], current_week_start: date, count: int
    ) -> TrendResponse:
        """从聚合数据构建周趋势"""
        from collections import defaultdict

        def _week_key(d_str: str) -> str:
            """将日期字符串转为所属周的周一日期"""
            dt = datetime.strptime(d_str, "%Y-%m-%d").date()
            return (dt - timedelta(days=dt.weekday())).isoformat()

        buckets: dict[str, dict] = defaultdict(
            lambda: {"task": 0, "task_complete": 0, "note": 0, "inbox": 0}
        )
        for row in agg:
            wk = _week_key(row["d"])
            cat = row["category"] or "task"
            status = row["status"] or ""
            cnt = row["cnt"]
            b = buckets[wk]
            if cat == "task":
                b["task"] += cnt
                if status == "complete":
                    b["task_complete"] += cnt
            elif cat == "note":
                b["note"] += cnt
            elif cat == "inbox":
                b["inbox"] += cnt

        periods: List[TrendPeriod] = []
        for i in range(count):
            week_start = current_week_start - timedelta(weeks=i)
            ws = week_start.isoformat()
            b = buckets.get(ws, {"task": 0, "task_complete": 0, "note": 0, "inbox": 0})
            total = b["task"]
            completed = b["task_complete"]
            completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0
            periods.append(TrendPeriod(
                date=ws,
                total=total,
                completed=completed,
                completion_rate=completion_rate,
                notes_count=b["note"],
                task_count=total,
                inbox_count=b["inbox"],
            ))

        return TrendResponse(periods=periods)

    @staticmethod
    def parse_date(date_str: Optional[str]) -> date:
        """解析日期字符串"""
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("日期格式错误，应为 YYYY-MM-DD")
        return date.today()

    @staticmethod
    def parse_month(month_str: Optional[str]) -> date:
        """解析月份字符串"""
        if month_str:
            try:
                return datetime.strptime(month_str, "%Y-%m").date()
            except ValueError:
                raise ValueError("月份格式错误，应为 YYYY-MM")
        today = date.today()
        return date(today.year, today.month, 1)

    async def _generate_ai_summary(
        self, report_type: str, stats_data: dict, user_id: str = "_default",
        system_prompt_override: str = "",
    ) -> str:
        """
        使用 LLM 生成 AI 总结

        Args:
            report_type: 报告类型 (daily/weekly/monthly)
            stats_data: 统计数据
            user_id: 用户 ID
            system_prompt_override: 可选的自定义系统提示词

        Returns:
            AI 总结文本，失败时返回空字符串
        """
        if not self._llm_caller:
            return ""

        import json

        system_prompt = system_prompt_override or (
            "你是个人成长助手「日知」，请根据以下数据生成一段简短的中文总结（2-3句话），"
            "包含关键成就和建议。"
        )

        user_message = (
            f"报告类型：{report_type}\n"
            f"统计数据：\n{json.dumps(stats_data, ensure_ascii=False, indent=2)}"
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
            result = await asyncio.wait_for(
                self._llm_caller.call(messages),
                timeout=10.0,
            )
            return result.strip() if result else ""
        except asyncio.TimeoutError:
            logger.warning("AI 总结生成超时")
            return ""
        except Exception as e:
            logger.warning(f"AI 总结生成失败: {e}")
            return ""

    async def get_knowledge_heatmap(self, user_id: str = "_default") -> HeatmapResponse:
        """
        获取知识热力图

        优先使用 Neo4j get_all_concepts_with_stats() 获取数据，
        Neo4j 不可用时降级到 SQLite tags 现有逻辑。

        Args:
            user_id: 用户 ID

        Returns:
            HeatmapResponse: 知识热力图数据
        """
        # 尝试 Neo4j 路径
        if self._neo4j_client:
            try:
                concepts = await self._neo4j_client.get_all_concepts_with_stats(user_id)
                if concepts:
                    relationships = await self._neo4j_client.get_all_relationships(user_id)
                    rel_count_map = self._count_relationships_per_concept(relationships)
                    items = [
                        self._neo4j_concept_to_heatmap(c, rel_count_map)
                        for c in concepts
                    ]
                    # 按 mastery 分组排序
                    items.sort(key=lambda x: self._mastery_order(x.mastery))
                    return HeatmapResponse(items=items)
            except Exception:
                logger.warning("Neo4j 查询失败，降级到 SQLite", exc_info=True)

        # SQLite tags 降级路径
        return self._get_heatmap_from_sqlite(user_id)

    def _get_heatmap_from_sqlite(self, user_id: str) -> HeatmapResponse:
        """从 SQLite tags 获取热力图数据（降级路径，SQL 聚合）"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        stats = self._sqlite.get_tag_stats_for_knowledge_map(user_id=user_id)

        # 构建热力图项
        items: List[HeatmapItem] = []
        for tag_info in stats.get("tags", []):
            mastery = self._calculate_mastery_from_stats(
                entry_count=tag_info["entry_count"],
                recent_count=tag_info["recent_count"],
                note_count=tag_info["note_count"],
            )
            items.append(HeatmapItem(
                concept=tag_info["name"],
                mastery=mastery,
                entry_count=tag_info["entry_count"],
                category="tag",
            ))

        # 按 mastery 分组排序
        items.sort(key=lambda x: self._mastery_order(x.mastery))

        return HeatmapResponse(items=items)

    @staticmethod
    def _count_relationships_per_concept(
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """统计每个概念的关系数量"""
        rel_count: Dict[str, int] = {}
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_count[source] = rel_count.get(source, 0) + 1
            rel_count[target] = rel_count.get(target, 0) + 1
        return rel_count

    def _neo4j_concept_to_heatmap(
        self,
        concept: Dict[str, Any],
        rel_count_map: Dict[str, int],
    ) -> HeatmapItem:
        """将 Neo4j 概念统计转换为 HeatmapItem"""
        name = concept.get("name", "")
        entry_count = concept.get("entry_count", 0)
        mention_count = concept.get("mention_count", 0)
        category = concept.get("category")
        relationship_count = rel_count_map.get(name, 0)

        mastery = self._calculate_mastery_from_stats(
            entry_count=entry_count,
            relationship_count=relationship_count,
        )

        return HeatmapItem(
            concept=name,
            mastery=mastery,
            entry_count=entry_count,
            category=category,
            mention_count=mention_count,
        )

    @staticmethod
    def _mastery_order(mastery: str) -> int:
        """掌握度排序权重（值越小掌握度越高）"""
        order = {"advanced": 0, "intermediate": 1, "beginner": 2, "new": 3}
        return order.get(mastery, 99)

    def get_growth_curve(
        self, weeks: int = 8, user_id: str = "_default"
    ) -> GrowthCurveResponse:
        """
        获取成长曲线数据

        Args:
            weeks: 回溯周数 (1-52)
            user_id: 用户 ID

        Returns:
            GrowthCurveResponse: 成长曲线数据
        """
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        count = max(1, min(weeks, 52))
        today = date.today()
        current_week_start = today - timedelta(days=today.weekday())

        # 使用 SQL 聚合查询替代 list_entries(limit=10000)
        earliest_week_start = current_week_start - timedelta(weeks=count - 1)
        tag_stats = self._sqlite.get_growth_curve_tag_stats(
            user_id=user_id,
            start_date=earliest_week_start.isoformat(),
            end_date=today.isoformat(),
        )

        # 构建 year_week -> {tag_name -> {entry_count, note_count, recent_count}} 索引
        week_tag_map: Dict[str, Dict[str, Dict]] = {}
        for row in tag_stats:
            yw = row["year_week"]
            if yw not in week_tag_map:
                week_tag_map[yw] = {}
            week_tag_map[yw][row["tag_name"]] = {
                "entry_count": row["entry_count"],
                "note_count": row["note_count"],
                "recent_count": row["recent_count"],
            }

        points: List[GrowthCurvePoint] = []

        for i in range(count):
            week_start = current_week_start - timedelta(weeks=i)

            # 计算 year_week key：使用 strftime('%Y-%W') 格式
            # %W 是 Monday-based week number (00-53)，与 SQL 的 strftime('%Y-%W') 完全一致
            year_week_key = week_start.strftime("%Y-%W")

            # 获取该周的 tag 统计
            concept_map = week_tag_map.get(year_week_key, {})

            # 统计掌握度分布
            advanced_count = 0
            intermediate_count = 0
            beginner_count = 0

            for concept, info in concept_map.items():
                mastery = self._calculate_mastery_from_stats(
                    entry_count=info["entry_count"],
                    recent_count=info["recent_count"],
                    note_count=info["note_count"],
                )
                if mastery == "advanced":
                    advanced_count += 1
                elif mastery == "intermediate":
                    intermediate_count += 1
                elif mastery == "beginner":
                    beginner_count += 1

            # 恢复 ISO 周标签格式 (YYYY-WXX)，与 API 契约一致
            iso_calendar = week_start.isocalendar()
            week_label = f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"

            points.append(GrowthCurvePoint(
                week=week_label,
                total_concepts=len(concept_map),
                advanced_count=advanced_count,
                intermediate_count=intermediate_count,
                beginner_count=beginner_count,
            ))

        return GrowthCurveResponse(points=points)

    @staticmethod
    def _calculate_mastery_from_stats(
        entry_count: int,
        recent_count: int = 0,
        note_count: int = 0,
        relationship_count: int = 0,
    ) -> str:
        """根据统计数据计算掌握度（委托到共享模块）"""
        return calculate_mastery_from_stats(
            entry_count=entry_count,
            recent_count=recent_count,
            note_count=note_count,
            relationship_count=relationship_count,
        )

    def get_activity_heatmap(self, year: int, user_id: str) -> ActivityHeatmapResponse:
        """获取年度每日活动热力图数据（基于 created_at）"""
        from datetime import date as date_type

        start = date_type(year, 1, 1)
        end = date_type(year, 12, 31)
        start_str = start.isoformat()
        end_str = end.isoformat() + "T23:59:59"

        counts = self._sqlite.get_daily_activity_counts(user_id, start_str, end_str)

        items = []
        current = start
        while current <= end:
            items.append(ActivityHeatmapItem(
                date=current.isoformat(),
                count=counts.get(current.isoformat(), 0),
            ))
            current += timedelta(days=1)

        return ActivityHeatmapResponse(year=year, items=items)

    async def export_growth_report(self, user_id: str) -> str:
        """生成成长报告 Markdown 内容"""
        if not self._sqlite:
            raise ValueError("SQLite 存储未初始化")

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        # Section 1: 概览
        categories = ["task", "note", "inbox", "project", "decision", "reflection", "question"]
        category_labels = {
            "task": "任务", "note": "笔记", "inbox": "灵感", "project": "项目",
            "decision": "决策", "reflection": "复盘", "question": "待解问题",
        }
        counts = {cat: self._sqlite.count_entries(type=cat, user_id=user_id) for cat in categories}
        total = sum(counts.values())

        overview_lines = [
            "| 指标 | 数值 |",
            "|------|------|",
            f"| 总条目数 | {total} |",
        ]
        for cat in categories:
            overview_lines.append(f"| {category_labels[cat]} | {counts[cat]} |")

        # Section 2: 学习趋势
        trend_data = self.get_trend_data(period="weekly", weeks=4, user_id=user_id)
        trend_lines = []
        if trend_data and hasattr(trend_data, "periods") and trend_data.periods:
            from collections import defaultdict
            weekly_buckets = defaultdict(int)
            for item in trend_data.periods:
                d = item.date if hasattr(item, "date") else str(item.get("date", ""))
                cnt = item.total if hasattr(item, "total") else item.get("total", 0)
                try:
                    dt = date.fromisoformat(str(d))
                    ws = dt - timedelta(days=dt.weekday())
                    weekly_buckets[ws.isoformat()] += cnt
                except (ValueError, TypeError):
                    pass
            for ws in sorted(weekly_buckets.keys()):
                trend_lines.append(f"- {ws}: {weekly_buckets[ws]} 条")
        if not trend_lines:
            trend_lines = ["暂无数据"]

        # Section 3: 学习连续天数
        streak = self._calculate_learning_streak(user_id)

        # Section 4: 知识图谱概览
        knowledge_lines = []
        try:
            if self._knowledge_service:
                ks = self._knowledge_service
                stats = await ks.get_knowledge_stats(user_id)
            knowledge_lines = [
                f"| 指标 | 数值 |",
                f"|------|------|",
                f"| 概念数 | {stats.concept_count} |",
                f"| 关联数 | {stats.relation_count} |",
            ]
            if hasattr(stats, "category_distribution") and stats.category_distribution:
                dist_str = " / ".join(f"{k} {v}" for k, v in stats.category_distribution.items())
                knowledge_lines.append(f"| 掌握度分布 | {dist_str} |")
        except Exception:
            knowledge_lines = ["暂无数据"]

        return f"""# 📊 成长报告

> 生成时间：{date_str}
> 报告周期：全部数据

## 概览

{chr(10).join(overview_lines)}

## 学习趋势

{chr(10).join(trend_lines)}

## 学习连续天数

{streak} 天

## 知识图谱概览

{chr(10).join(knowledge_lines)}
"""
