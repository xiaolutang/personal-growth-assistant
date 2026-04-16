"""B47: tag_auto 目标进度自动追踪触发测试"""
import uuid as _uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.goal_service import GoalService


def _make_goal_row(goal_id, user_id, auto_tags, target_value=5, status="active",
                   metric_type="tag_auto", start_date=None, end_date=None):
    """构建 goal 数据库行"""
    import json
    return {
        "id": goal_id,
        "user_id": user_id,
        "title": f"目标-{goal_id[:6]}",
        "description": None,
        "metric_type": metric_type,
        "target_value": target_value,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "auto_tags": json.dumps(auto_tags) if auto_tags else None,
        "checklist_items": None,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }


@pytest.fixture
def mock_sqlite():
    """Mock SQLite 存储"""
    return MagicMock()


@pytest.fixture
def goal_service(mock_sqlite):
    """GoalService 实例"""
    return GoalService(sqlite_storage=mock_sqlite)


class TestRecalculateTagAutoGoals:
    """GoalService.recalculate_tag_auto_goals 测试"""

    @pytest.mark.asyncio
    async def test_recalculate_matching_goal(self, goal_service, mock_sqlite):
        """匹配的 tag_auto 目标进度更新"""
        user_id = "user-1"
        goal_id = "g1"
        goal_row = _make_goal_row(goal_id, user_id, ["react", "hooks"])

        mock_sqlite.list_goals_by_status.return_value = [goal_row]
        mock_sqlite.count_goal_entries.return_value = 0
        mock_sqlite.count_entries_by_tags.return_value = 3

        await goal_service.recalculate_tag_auto_goals(user_id, ["react"])

        # 验证 count_entries_by_tags 被调用计算进度
        mock_sqlite.count_entries_by_tags.assert_called_once_with(["react", "hooks"], user_id)

    @pytest.mark.asyncio
    async def test_no_matching_goals(self, goal_service, mock_sqlite):
        """tags 不匹配任何目标时不触发重算"""
        user_id = "user-1"
        goal_row = _make_goal_row("g1", user_id, ["python"])

        mock_sqlite.list_goals_by_status.return_value = [goal_row]

        await goal_service.recalculate_tag_auto_goals(user_id, ["react"])

        # count_entries_by_tags 不应被调用
        mock_sqlite.count_entries_by_tags.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_tags_no_op(self, goal_service, mock_sqlite):
        """空 tags 列表不触发操作"""
        await goal_service.recalculate_tag_auto_goals("user-1", [])

        mock_sqlite.list_goals_by_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_complete_at_100_percent(self, goal_service, mock_sqlite):
        """进度 100% 时自动标记 completed"""
        user_id = "user-1"
        goal_id = "g1"
        goal_row = _make_goal_row(goal_id, user_id, ["react"], target_value=3)

        mock_sqlite.list_goals_by_status.return_value = [goal_row]
        mock_sqlite.count_goal_entries.return_value = 0
        mock_sqlite.count_entries_by_tags.return_value = 3

        await goal_service.recalculate_tag_auto_goals(user_id, ["react"])

        # 验证状态被更新为 completed
        mock_sqlite.update_goal_status.assert_called_once_with(goal_id, user_id, "completed")

    @pytest.mark.asyncio
    async def test_no_auto_complete_already_completed(self, goal_service, mock_sqlite):
        """completed 目标不再重复触发 auto-complete"""
        user_id = "user-1"
        goal_id = "g1"
        goal_row = _make_goal_row(goal_id, user_id, ["react"], target_value=3, status="completed")

        mock_sqlite.list_goals_by_status.return_value = [goal_row]
        mock_sqlite.count_goal_entries.return_value = 0
        mock_sqlite.count_entries_by_tags.return_value = 5

        await goal_service.recalculate_tag_auto_goals(user_id, ["react"])

        # status 已是 completed，不应再调用 update_goal_status
        mock_sqlite.update_goal_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_count_type_goals(self, goal_service, mock_sqlite):
        """count 类型目标被跳过"""
        user_id = "user-1"
        goal_row = _make_goal_row("g1", user_id, [], metric_type="count")

        mock_sqlite.list_goals_by_status.return_value = [goal_row]

        await goal_service.recalculate_tag_auto_goals(user_id, ["react"])

        mock_sqlite.count_entries_by_tags.assert_not_called()

    @pytest.mark.asyncio
    async def test_recalc_failure_does_not_raise(self, goal_service, mock_sqlite):
        """重算失败不抛异常"""
        mock_sqlite.list_goals_by_status.side_effect = Exception("DB error")

        # 不应抛异常
        await goal_service.recalculate_tag_auto_goals("user-1", ["react"])

    @pytest.mark.asyncio
    async def test_partial_failure_continues(self, goal_service, mock_sqlite):
        """部分目标重算失败不影响其他目标"""
        user_id = "user-1"
        goal1 = _make_goal_row("g1", user_id, ["react"])
        goal2 = _make_goal_row("g2", user_id, ["python"])

        mock_sqlite.list_goals_by_status.return_value = [goal1, goal2]
        mock_sqlite.count_goal_entries.return_value = 0

        # goal1 抛异常，goal2 正常
        call_count = [0]
        def side_effect(tags, uid):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("DB error for g1")
            return 2
        mock_sqlite.count_entries_by_tags.side_effect = side_effect

        # 不应抛异常
        await goal_service.recalculate_tag_auto_goals(user_id, ["react", "python"])

        # g2 的 count 应被调用
        assert mock_sqlite.count_entries_by_tags.call_count == 2


class TestEntryServiceTrigger:
    """EntryService 中的 tag_auto 触发测试"""

    @pytest.mark.asyncio
    async def test_create_entry_triggers_recalc(self, client, storage):
        """创建带 tag 的条目后触发 tag_auto 目标进度重算"""
        # 先创建 tag_auto 目标
        resp = await client.post("/goals", json={
            "title": "React 学习",
            "metric_type": "tag_auto",
            "auto_tags": ["react"],
            "target_value": 5,
        })
        assert resp.status_code == 201
        goal_id = resp.json()["id"]

        # 验证初始进度为 0
        resp = await client.get(f"/goals/{goal_id}")
        assert resp.json()["progress_percentage"] == 0.0

        # 创建带 react tag 的条目
        resp = await client.post("/entries", json={
            "title": "学习 React Hooks",
            "content": "学习内容",
            "category": "task",
            "tags": ["react", "hooks"],
        })
        assert resp.status_code == 200

        # 等待异步重算完成
        import asyncio
        await asyncio.sleep(0.3)

        # 验证目标进度已更新
        resp = await client.get(f"/goals/{goal_id}")
        assert resp.json()["progress_percentage"] == 20.0  # 1/5 = 20%

    @pytest.mark.asyncio
    async def test_update_entry_tags_triggers_recalc(self, client, storage):
        """更新条目 tags 后触发重算（含 old_tags ∪ new_tags）"""
        # 创建 tag_auto 目标
        resp = await client.post("/goals", json={
            "title": "Python 学习",
            "metric_type": "tag_auto",
            "auto_tags": ["python"],
            "target_value": 3,
        })
        assert resp.status_code == 201
        goal_id = resp.json()["id"]

        # 创建带 react tag 的条目
        resp = await client.post("/entries", json={
            "title": "学习 React",
            "content": "React 内容",
            "category": "task",
            "tags": ["react"],
        })
        assert resp.status_code == 200
        entry_id = resp.json()["id"]

        import asyncio
        await asyncio.sleep(0.2)

        # 进度应为 0
        resp = await client.get(f"/goals/{goal_id}")
        assert resp.json()["progress_percentage"] == 0.0

        # 更新条目 tags 为 python
        resp = await client.put(f"/entries/{entry_id}", json={
            "tags": ["python"],
        })
        assert resp.status_code == 200

        await asyncio.sleep(0.3)

        # 进度应更新为 33.3% (1/3)
        resp = await client.get(f"/goals/{goal_id}")
        assert resp.json()["progress_percentage"] == 33.3

    @pytest.mark.asyncio
    async def test_update_remove_tag_triggers_recalc(self, client, storage):
        """移除匹配 tag 后进度回退（old_tags ∪ new_tags 覆盖）"""
        # 创建 tag_auto 目标
        resp = await client.post("/goals", json={
            "title": "React 目标",
            "metric_type": "tag_auto",
            "auto_tags": ["react"],
            "target_value": 2,
        })
        goal_id = resp.json()["id"]

        # 创建带 react tag 的条目
        resp = await client.post("/entries", json={
            "title": "React 入门",
            "content": "内容",
            "category": "task",
            "tags": ["react"],
        })
        entry_id = resp.json()["id"]

        import asyncio
        await asyncio.sleep(0.2)

        # 进度应为 50% (1/2)
        resp = await client.get(f"/goals/{goal_id}")
        assert resp.json()["progress_percentage"] == 50.0

        # 移除 react tag
        resp = await client.put(f"/entries/{entry_id}", json={
            "tags": ["python"],
        })
        assert resp.status_code == 200

        await asyncio.sleep(0.3)

        # 进度应降回 0%
        resp = await client.get(f"/goals/{goal_id}")
        assert resp.json()["progress_percentage"] == 0.0

    @pytest.mark.asyncio
    async def test_entry_no_tags_no_trigger(self, client, storage):
        """无 tags 的条目不触发重算"""
        with patch("app.services.entry_service.EntryService._trigger_tag_auto_recalc",
                    new_callable=AsyncMock) as mock_recalc:
            # 创建无 tag 条目
            resp = await client.post("/entries", json={
                "title": "无标签条目",
                "content": "内容",
                "category": "task",
                "tags": [],
            })
            assert resp.status_code == 200

            import asyncio
            await asyncio.sleep(0.1)

            # _trigger_tag_auto_recalc 不应被调用（空 tags）
            mock_recalc.assert_not_called()

    @pytest.mark.asyncio
    async def test_recalc_failure_does_not_block_entry(self, client, storage):
        """重算失败不影响条目操作"""
        # 创建 tag_auto 目标
        resp = await client.post("/goals", json={
            "title": "目标",
            "metric_type": "tag_auto",
            "auto_tags": ["test"],
            "target_value": 5,
        })
        assert resp.status_code == 201

        # 正常创建条目，即使目标重算可能失败，条目操作仍应成功
        with patch(
            "app.services.goal_service.GoalService.recalculate_tag_auto_goals",
            new_callable=AsyncMock,
            side_effect=Exception("recalc error"),
        ):
            resp = await client.post("/entries", json={
                "title": "测试条目",
                "content": "内容",
                "category": "task",
                "tags": ["test"],
            })
            # 条目创建应成功
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_non_tag_field_no_recalc(self, client, storage):
        """更新非 tags 字段不触发重算"""
        resp = await client.post("/entries", json={
            "title": "原始标题",
            "content": "内容",
            "category": "task",
            "tags": ["react"],
        })
        entry_id = resp.json()["id"]

        with patch("app.services.entry_service.EntryService._trigger_tag_auto_recalc",
                    new_callable=AsyncMock) as mock_recalc:
            # 只更新 title
            resp = await client.put(f"/entries/{entry_id}", json={
                "title": "新标题",
            })
            assert resp.status_code == 200

            import asyncio
            await asyncio.sleep(0.1)

            # 不应触发 tag_auto 重算
            mock_recalc.assert_not_called()
