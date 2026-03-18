from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


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


class Task(BaseModel):
    """统一条目模型 - 对应一个 Markdown 文件"""
    # 核心字段
    id: str = Field(..., description="条目ID（文件名，不含扩展名）")
    title: str = Field(..., description="标题（从 Markdown # 标题提取）")
    content: str = Field(default="", description="正文内容")
    category: Category = Field(..., description="分类")
    status: TaskStatus = Field(default=TaskStatus.DOING, description="状态")

    # 元数据
    tags: List[str] = Field(default_factory=list, description="标签列表")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # Task 专用字段
    planned_date: Optional[datetime] = Field(default=None, description="计划完成日期")
    completed_at: Optional[datetime] = Field(default=None, description="实际完成时间")
    time_spent: Optional[int] = Field(default=None, description="耗时（分钟）")

    # 关联关系
    parent_id: Optional[str] = Field(default=None, description="父条目ID（文件名）")
    file_path: str = Field(..., description="文件路径")

    # 优先级
    priority: Priority = Field(default=Priority.MEDIUM, description="优先级")


class ParsedTaskInput(BaseModel):
    """LLM 解析结果"""
    tasks: List[Task]


class Concept(BaseModel):
    """知识图谱概念"""
    name: str = Field(..., description="概念名称")
    description: Optional[str] = Field(default=None, description="概念描述")
    category: Optional[str] = Field(default=None, description="概念分类（技术/方法/工具）")


class ConceptRelation(BaseModel):
    """概念关系"""
    from_concept: str = Field(..., description="源概念")
    to_concept: str = Field(..., description="目标概念")
    relation_type: str = Field(..., description="关系类型（PART_OF/RELATED_TO/PREREQUISITE）")


class ExtractedKnowledge(BaseModel):
    """LLM 提取的知识结构"""
    tags: List[str] = Field(default_factory=list, description="标签")
    concepts: List[Concept] = Field(default_factory=list, description="概念列表")
    relations: List[ConceptRelation] = Field(default_factory=list, description="概念关系")
