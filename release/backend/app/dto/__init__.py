"""
向后兼容模块 - 重新导出 api.schemas 和 mappers

警告：此模块已弃用，请使用：
- app.api.schemas 替代 DTO
- app.mappers.entry_mapper.EntryMapper 替代转换函数
"""
import warnings

# 发出弃用警告
warnings.warn(
    "app.dto 模块已弃用，请使用 app.api.schemas 和 app.mappers.entry_mapper",
    DeprecationWarning,
    stacklevel=2
)

# 从新位置重新导出
from app.api.schemas import (
    EntryCreate,
    EntryUpdate,
    EntryResponse,
    EntryListResponse,
    SearchResult,
    SuccessResponse,
    ProjectProgressResponse,
)
from app.mappers.entry_mapper import EntryMapper

# 提供向后兼容的函数
def task_to_response(task):
    """向后兼容函数 - 使用 EntryMapper.task_to_response"""
    return EntryMapper.task_to_response(task)

def dict_to_response(data):
    """向后兼容函数 - 使用 EntryMapper.dict_to_response"""
    return EntryMapper.dict_to_response(data)


__all__ = [
    "EntryCreate",
    "EntryUpdate",
    "EntryResponse",
    "EntryListResponse",
    "SearchResult",
    "SuccessResponse",
    "ProjectProgressResponse",
    "task_to_response",
    "dict_to_response",
]
