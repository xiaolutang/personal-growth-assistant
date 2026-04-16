"""条目类型转换器 - 处理 DTO 与 Domain 模型之间的转换"""
from datetime import datetime
from typing import Any, Dict, Optional, Union

from app.models import Task
from app.models.enums import Category, Priority, TaskStatus


class EntryMapper:
    """条目转换器 - 统一处理类型转换逻辑"""

    # 类型字符串到枚举的映射
    CATEGORY_MAP = {
        "project": Category.PROJECT,
        "task": Category.TASK,
        "note": Category.NOTE,
        "inbox": Category.INBOX,
        "decision": Category.DECISION,
        "reflection": Category.REFLECTION,
        "question": Category.QUESTION,
    }

    STATUS_MAP = {
        "waitStart": TaskStatus.WAIT_START,
        "doing": TaskStatus.DOING,
        "complete": TaskStatus.COMPLETE,
        "paused": TaskStatus.PAUSED,
        "cancelled": TaskStatus.CANCELLED,
    }

    PRIORITY_MAP = {
        "high": Priority.HIGH,
        "medium": Priority.MEDIUM,
        "low": Priority.LOW,
    }

    @classmethod
    def str_to_category(cls, value: str) -> Category:
        """字符串转 Category 枚举"""
        if value in cls.CATEGORY_MAP:
            return cls.CATEGORY_MAP[value]
        # 兼容 type 字段（旧命名）
        return cls.CATEGORY_MAP.get(value, Category.NOTE)

    @classmethod
    def str_to_status(cls, value: Optional[str]) -> TaskStatus:
        """字符串转 TaskStatus 枚举"""
        if not value:
            return TaskStatus.DOING
        return cls.STATUS_MAP.get(value, TaskStatus.DOING)

    @classmethod
    def str_to_priority(cls, value: Optional[str]) -> Priority:
        """字符串转 Priority 枚举"""
        if not value:
            return Priority.MEDIUM
        return cls.PRIORITY_MAP.get(value, Priority.MEDIUM)

    @classmethod
    def parse_datetime(cls, value: Optional[str]) -> Optional[datetime]:
        """解析日期时间字符串"""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    @classmethod
    def task_to_response(cls, task: Union[Task, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Task 模型或字典转响应字典

        Args:
            task: Task 模型实例或字典（来自 SQLite）

        Returns:
            响应字典
        """
        if isinstance(task, Task):
            return {
                "id": task.id,
                "title": task.title,
                "content": task.content,
                "category": task.category.value,
                "status": task.status.value,
                "priority": task.priority.value if task.priority else "medium",
                "tags": task.tags,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "planned_date": task.planned_date.isoformat() if task.planned_date else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "time_spent": task.time_spent,
                "parent_id": task.parent_id,
                "file_path": task.file_path,
            }
        return cls.dict_to_response(task)

    @classmethod
    def dict_to_response(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        字典转响应字典（来自 SQLite）

        Args:
            data: SQLite 返回的字典

        Returns:
            响应字典
        """
        # 兼容 type 和 category 字段
        category = data.get("category") or data.get("type", "note")

        return {
            "id": data["id"],
            "title": data.get("title", ""),
            "content": data.get("content", ""),
            "category": category,
            "status": data.get("status", "doing"),
            "priority": data.get("priority", "medium"),
            "tags": data.get("tags", []),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "planned_date": data.get("planned_date"),
            "completed_at": data.get("completed_at"),
            "time_spent": data.get("time_spent"),
            "parent_id": data.get("parent_id"),
            "file_path": data.get("file_path", ""),
        }
