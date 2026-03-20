"""通用响应模型"""
from typing import List

from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool
    message: str = ""


class ProjectProgressResponse(BaseModel):
    """项目进度响应"""
    project_id: str
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
    status_distribution: dict
