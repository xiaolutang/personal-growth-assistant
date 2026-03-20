"""日志业务服务"""

from datetime import datetime
from typing import Optional

from app.infrastructure.logging.storage import LogEntry, LogStats, LogStorage


class LogService:
    """日志业务服务"""

    def __init__(self, storage: LogStorage):
        self.storage = storage

    def query_logs(
        self,
        level: Optional[str] = None,
        request_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LogEntry]:
        """查询日志"""
        return self.storage.query_logs(
            level=level,
            request_id=request_id,
            keyword=keyword,
            start_time=start_time,
            end_time=end_time,
            limit=min(limit, 1000),  # 最大 1000 条
            offset=offset,
        )

    def count_logs(
        self,
        level: Optional[str] = None,
        request_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """统计日志数量"""
        return self.storage.count_logs(
            level=level,
            request_id=request_id,
            keyword=keyword,
            start_time=start_time,
            end_time=end_time,
        )

    def cleanup_old_logs(self, retention_days: int) -> int:
        """清理过期日志"""
        return self.storage.cleanup_old_logs(retention_days)

    def get_stats(self) -> LogStats:
        """获取日志统计信息"""
        return self.storage.get_stats()
