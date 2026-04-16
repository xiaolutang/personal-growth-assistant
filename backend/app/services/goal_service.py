"""目标管理服务"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def _calculate_progress(current_value: int, target_value: int) -> float:
    """计算进度百分比，上限 100"""
    if target_value <= 0:
        return 0.0
    return min(100.0, round(current_value / target_value * 100, 1))


class GoalService:
    """目标 CRUD + 进度计算"""

    def __init__(self, sqlite_storage):
        self._sqlite = sqlite_storage

    def _row_to_response(self, row: dict[str, Any], linked_entries_count: int = 0) -> dict[str, Any]:
        """将数据库行转换为响应 dict，包含计算字段"""
        result = dict(row)

        # 解析 JSON 字段
        if result.get("auto_tags"):
            if isinstance(result["auto_tags"], str):
                result["auto_tags"] = json.loads(result["auto_tags"])
        else:
            result["auto_tags"] = None

        if result.get("checklist_items"):
            if isinstance(result["checklist_items"], str):
                result["checklist_items"] = json.loads(result["checklist_items"])
        else:
            result["checklist_items"] = None

        # 计算 current_value
        metric_type = result["metric_type"]
        if metric_type == "checklist":
            items = result.get("checklist_items") or []
            current_value = sum(1 for item in items if item.get("checked", False))
        elif metric_type == "tag_auto":
            tags = result.get("auto_tags") or []
            current_value = self._sqlite.count_entries_by_tags(tags, row["user_id"])
        else:
            # count 类型：使用关联条目数
            current_value = linked_entries_count

        result["current_value"] = current_value
        result["progress_percentage"] = _calculate_progress(current_value, result["target_value"])
        result["linked_entries_count"] = linked_entries_count

        return result

    async def create_goal(self, request, user_id: str) -> tuple[Optional[dict], int, str]:
        """创建目标，返回 (result, status_code, message)"""
        goal_id = uuid.uuid4().hex

        # 准备 JSON 字段
        auto_tags_json = None
        checklist_items_json = None

        if request.metric_type == "tag_auto":
            auto_tags_json = json.dumps(request.auto_tags)
        elif request.metric_type == "checklist":
            items = [
                {"id": uuid.uuid4().hex, "title": title, "checked": False}
                for title in request.checklist_items
            ]
            checklist_items_json = json.dumps(items)

        try:
            row = self._sqlite.create_goal(
                goal_id=goal_id,
                user_id=user_id,
                title=request.title,
                metric_type=request.metric_type,
                target_value=request.target_value,
                description=request.description,
                start_date=request.start_date,
                end_date=request.end_date,
                auto_tags=auto_tags_json,
                checklist_items=checklist_items_json,
            )
            result = self._row_to_response(row, linked_entries_count=0)
            return result, 201, "目标创建成功"
        except Exception as e:
            logger.error("创建目标失败: %s", e)
            return None, 500, f"创建目标失败: {e}"

    async def get_goal(self, goal_id: str, user_id: str) -> tuple[Optional[dict], int, str]:
        """获取目标详情"""
        row = self._sqlite.get_goal(goal_id, user_id)
        if not row:
            return None, 404, "目标不存在"

        linked_count = self._sqlite.count_goal_entries(goal_id, user_id)
        result = self._row_to_response(row, linked_entries_count=linked_count)
        return result, 200, "获取成功"

    async def list_goals(
        self, user_id: str, status: Optional[str] = None, limit: int = 20
    ) -> tuple[list[dict], int, str]:
        """列出目标"""
        rows = self._sqlite.list_goals(user_id, status=status, limit=limit)
        results = []
        for row in rows:
            linked_count = self._sqlite.count_goal_entries(row["id"], user_id)
            results.append(self._row_to_response(row, linked_entries_count=linked_count))
        return results, 200, "获取成功"

    async def update_goal(self, goal_id: str, request, user_id: str) -> tuple[Optional[dict], int, str]:
        """更新目标"""
        existing = self._sqlite.get_goal(goal_id, user_id)
        if not existing:
            return None, 404, "目标不存在"

        # 构建更新字段（排除 metric_type）
        fields = {}
        if request.title is not None:
            fields["title"] = request.title
        if request.description is not None:
            fields["description"] = request.description
        if request.target_value is not None:
            fields["target_value"] = request.target_value
        if request.status is not None:
            fields["status"] = request.status
        if request.start_date is not None:
            fields["start_date"] = request.start_date
        if request.end_date is not None:
            fields["end_date"] = request.end_date

        if not fields:
            # 没有字段需要更新，直接返回当前记录
            linked_count = self._sqlite.count_goal_entries(goal_id, user_id)
            result = self._row_to_response(existing, linked_entries_count=linked_count)
            return result, 200, "目标未变更"

        try:
            updated = self._sqlite.update_goal(goal_id, user_id, **fields)
            if not updated:
                return None, 404, "目标不存在"
            linked_count = self._sqlite.count_goal_entries(goal_id, user_id)
            result = self._row_to_response(updated, linked_entries_count=linked_count)
            return result, 200, "目标更新成功"
        except Exception as e:
            logger.error("更新目标失败: %s", e)
            return None, 500, f"更新目标失败: {e}"

    async def delete_goal(self, goal_id: str, user_id: str) -> tuple[Optional[dict], int, str]:
        """删除目标（仅 abandoned 状态可删除）"""
        existing = self._sqlite.get_goal(goal_id, user_id)
        if not existing:
            return None, 404, "目标不存在"

        if existing["status"] != "abandoned":
            return None, 400, "仅已放弃的目标可以删除"

        deleted = self._sqlite.delete_goal(goal_id, user_id)
        if not deleted:
            return None, 404, "目标删除失败"

        return {"id": goal_id}, 200, "目标已删除"

    # === 条目关联 ===

    async def link_entry(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> tuple[Optional[dict], int, str]:
        """关联条目到目标（仅 count 类型）"""
        goal = self._sqlite.get_goal(goal_id, user_id)
        if not goal:
            return None, 404, "目标不存在"

        if goal["metric_type"] != "count":
            return None, 400, "仅 count 类型目标支持手动关联条目"

        # 验证条目存在
        if not self._sqlite.entry_belongs_to_user(entry_id, user_id):
            return None, 404, "条目不存在"

        # 检查重复关联
        if self._sqlite.check_goal_entry_exists(goal_id, entry_id, user_id):
            return None, 409, "条目已关联该目标"

        try:
            link_row = self._sqlite.create_goal_entry(goal_id, entry_id, user_id)

            # 重新计算进度
            linked_count = self._sqlite.count_goal_entries(goal_id, user_id)
            progress = _calculate_progress(linked_count, goal["target_value"])

            # 自动完成：进度达到 100%
            if progress >= 100.0 and goal["status"] == "active":
                self._sqlite.update_goal_status(goal_id, user_id, "completed")

            # 获取最新的目标数据
            updated_goal = self._sqlite.get_goal(goal_id, user_id)
            result = self._row_to_response(updated_goal, linked_entries_count=linked_count)

            # 构建关联响应
            entry_info = self._sqlite.get_entry(entry_id, user_id)
            response = {
                "id": link_row["id"],
                "goal_id": goal_id,
                "entry_id": entry_id,
                "created_at": link_row["created_at"],
                "entry": {
                    "id": entry_id,
                    "title": entry_info.get("title") if entry_info else None,
                    "status": entry_info.get("status") if entry_info else None,
                    "category": entry_info.get("type") if entry_info else None,
                    "created_at": entry_info.get("created_at") if entry_info else None,
                },
                "goal": result,
            }
            return response, 201, "条目关联成功"
        except Exception as e:
            logger.error("关联条目失败: %s", e)
            return None, 500, f"关联条目失败: {e}"

    async def unlink_entry(
        self, goal_id: str, entry_id: str, user_id: str
    ) -> tuple[Optional[dict], int, str]:
        """取消关联条目"""
        goal = self._sqlite.get_goal(goal_id, user_id)
        if not goal:
            return None, 404, "目标不存在"

        deleted = self._sqlite.delete_goal_entry(goal_id, entry_id, user_id)
        if not deleted:
            return None, 404, "关联不存在"

        # 重新计算进度（但不自动回退状态）
        linked_count = self._sqlite.count_goal_entries(goal_id, user_id)
        updated_goal = self._sqlite.get_goal(goal_id, user_id)
        result = self._row_to_response(updated_goal, linked_entries_count=linked_count)

        return result, 200, "取消关联成功"

    async def list_goal_entries(
        self, goal_id: str, user_id: str
    ) -> tuple[Optional[list], int, str]:
        """列出目标关联的条目"""
        goal = self._sqlite.get_goal(goal_id, user_id)
        if not goal:
            return None, 404, "目标不存在"

        rows = self._sqlite.list_goal_entries(goal_id, user_id)
        entries = []
        for row in rows:
            entries.append({
                "id": row["id"],
                "goal_id": row["goal_id"],
                "entry_id": row["entry_id"],
                "created_at": row["linked_at"],
                "entry": {
                    "id": row["entry_id"],
                    "title": row["entry_title"],
                    "status": row["entry_status"],
                    "category": row["entry_category"],
                    "created_at": row["entry_created_at"],
                },
            })
        return entries, 200, "获取成功"

    # === Checklist 切换 ===

    async def toggle_checklist_item(
        self, goal_id: str, item_id: str, user_id: str
    ) -> tuple[Optional[dict], int, str]:
        """切换 checklist 项的勾选状态"""
        goal = self._sqlite.get_goal(goal_id, user_id)
        if not goal:
            return None, 404, "目标不存在"

        if goal["metric_type"] != "checklist":
            return None, 400, "仅 checklist 类型目标支持此操作"

        # 解析 checklist items
        items = json.loads(goal["checklist_items"]) if isinstance(goal["checklist_items"], str) else goal["checklist_items"]

        # 找到目标 item
        target_item = None
        for item in items:
            if item["id"] == item_id:
                target_item = item
                break

        if target_item is None:
            return None, 404, "检查项不存在"

        # 切换状态
        target_item["checked"] = not target_item["checked"]

        # 保存回数据库
        checklist_json = json.dumps(items)
        self._sqlite.update_goal(goal_id, user_id, checklist_items=checklist_json)

        # 计算进度
        checked_count = sum(1 for item in items if item.get("checked", False))
        progress = _calculate_progress(checked_count, goal["target_value"])

        # 自动完成
        if progress >= 100.0 and goal["status"] == "active":
            self._sqlite.update_goal_status(goal_id, user_id, "completed")

        # 返回更新后的目标
        updated_goal = self._sqlite.get_goal(goal_id, user_id)
        linked_count = self._sqlite.count_goal_entries(goal_id, user_id)
        result = self._row_to_response(updated_goal, linked_entries_count=linked_count)
        return result, 200, "检查项已更新"

    # === 进度汇总 ===

    async def get_progress_summary(
        self, user_id: str, period: Optional[str] = None
    ) -> tuple[dict, int, str]:
        """获取进度汇总"""
        active_goals = self._sqlite.list_goals_by_status(user_id, ["active"])
        completed_goals = self._sqlite.list_goals_by_status(user_id, ["completed"])

        all_goals = active_goals + completed_goals
        items = []
        for goal in all_goals:
            linked_count = self._sqlite.count_goal_entries(goal["id"], user_id)
            response = self._row_to_response(goal, linked_entries_count=linked_count)
            items.append({
                "id": response["id"],
                "title": response["title"],
                "progress_percentage": response["progress_percentage"],
                "progress_delta": None,
            })

        return {
            "active_count": len(active_goals),
            "completed_count": len(completed_goals),
            "goals": items,
        }, 200, "获取成功"
