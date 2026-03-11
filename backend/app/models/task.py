from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Category(str, Enum):
    """任务分类"""
    TASK = "task"      # 可执行任务
    INBOX = "inbox"    # 灵感收集
    NOTE = "note"      # 学习笔记
    PROJECT = "project"  # 项目（可拆解为多个任务）


class TaskStatus(str, Enum):
    """任务状态"""
    WAIT_START = "waitStart"  # 待开始
    DOING = "doing"           # 进行中
    COMPLETE = "complete"     # 已完成


class Task(BaseModel):
    """任务模型"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    category: Category
    status: TaskStatus
    created_at: Optional[datetime] = None
    planned_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_id: Optional[int] = None  # 父任务/父项目


class ParsedTaskInput(BaseModel):
    """LLM 解析结果"""
    tasks: List[Task]
