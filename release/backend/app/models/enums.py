"""枚举类型定义"""
from enum import Enum


class Category(str, Enum):
    """条目分类"""
    PROJECT = "project"  # 项目（可拆解为多个任务）
    TASK = "task"        # 可执行任务
    NOTE = "note"        # 学习笔记
    INBOX = "inbox"      # 灵感收集


class TaskStatus(str, Enum):
    """任务状态"""
    WAIT_START = "waitStart"  # 待开始
    DOING = "doing"           # 进行中
    COMPLETE = "complete"     # 已完成
    PAUSED = "paused"         # 挂起
    CANCELLED = "cancelled"   # 已取消


class Priority(str, Enum):
    """任务优先级"""
    HIGH = "high"       # 高优先级
    MEDIUM = "medium"   # 中优先级
    LOW = "low"         # 低优先级
