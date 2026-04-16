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
