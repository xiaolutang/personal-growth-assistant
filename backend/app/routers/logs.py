"""日志 API 路由"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from app.routers.deps import get_log_service

router = APIRouter(prefix="/logs", tags=["logs"])


# === 响应模型 ===


class LogEntryResponse(BaseModel):
    """日志条目响应"""

    id: int
    level: str
    message: str
    logger_name: Optional[str] = None
    timestamp: datetime
    request_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    process_time_ms: Optional[int] = None
    client_ip: Optional[str] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    extra: Optional[dict] = None


class LogStatsResponse(BaseModel):
    """日志统计响应"""

    total_count: int
    count_by_level: dict[str, int]
    oldest_log: Optional[datetime] = None
    newest_log: Optional[datetime] = None
    db_size_mb: float


class LogListResponse(BaseModel):
    """日志列表响应"""

    items: list[LogEntryResponse]
    total: int
    limit: int
    offset: int


class CleanupResponse(BaseModel):
    """清理响应"""

    deleted_count: int
    message: str


# === API 端点 ===


@router.get("", response_model=LogListResponse)
async def list_logs(
    level: Optional[str] = Query(None, description="日志级别筛选 (DEBUG/INFO/WARNING/ERROR/CRITICAL)"),
    request_id: Optional[str] = Query(None, description="请求 ID 筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    start_time: Optional[datetime] = Query(None, description="开始时间 (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="结束时间 (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    order: str = Query("desc", description="排序方式: desc(最新优先) 或 asc(最早优先)"),
    log_service=Depends(get_log_service),
):
    """
    查询日志列表

    支持筛选：
    - level: 日志级别
    - request_id: 请求追踪 ID
    - keyword: 消息关键词
    - start_time/end_time: 时间范围
    - order: 排序方式 (desc/asc)
    """
    if log_service is None:
        raise HTTPException(status_code=503, detail="日志服务未初始化")

    # 查询日志
    entries = log_service.query_logs(
        level=level,
        request_id=request_id,
        keyword=keyword,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
        order=order,
    )

    # 统计总数
    total = log_service.count_logs(
        level=level,
        request_id=request_id,
        keyword=keyword,
        start_time=start_time,
        end_time=end_time,
    )

    return LogListResponse(
        items=[
            LogEntryResponse(
                id=e.id,
                level=e.level,
                message=e.message,
                logger_name=e.logger_name,
                timestamp=e.timestamp,
                request_id=e.request_id,
                method=e.method,
                path=e.path,
                status_code=e.status_code,
                process_time_ms=e.process_time_ms,
                client_ip=e.client_ip,
                exception_type=e.exception_type,
                exception_message=e.exception_message,
                stack_trace=e.stack_trace,
                extra=e.extra,
            )
            for e in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(log_service=Depends(get_log_service)):
    """
    获取日志统计信息

    返回：
    - total_count: 总日志数
    - count_by_level: 按级别统计
    - oldest_log: 最早日志时间
    - newest_log: 最新日志时间
    - db_size_mb: 数据库大小 (MB)
    """
    if log_service is None:
        raise HTTPException(status_code=503, detail="日志服务未初始化")

    stats = log_service.get_stats()

    return LogStatsResponse(
        total_count=stats.total_count,
        count_by_level=stats.count_by_level,
        oldest_log=stats.oldest_log,
        newest_log=stats.newest_log,
        db_size_mb=stats.db_size_mb,
    )


@router.delete("/cleanup", response_model=CleanupResponse)
async def cleanup_logs(
    retention_days: int = Query(30, ge=1, le=365, description="保留天数"),
    log_service=Depends(get_log_service),
):
    """
    清理过期日志

    删除超过 retention_days 天的日志
    """
    if log_service is None:
        raise HTTPException(status_code=503, detail="日志服务未初始化")

    deleted_count = log_service.cleanup_old_logs(retention_days)

    return CleanupResponse(
        deleted_count=deleted_count,
        message=f"已清理 {deleted_count} 条超过 {retention_days} 天的日志",
    )
