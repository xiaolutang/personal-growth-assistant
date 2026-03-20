"""日志存储层 - SQLite 实现"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class LogEntry(BaseModel):
    """日志条目模型"""

    id: Optional[int] = None
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
    extra: Optional[dict[str, Any]] = None


class LogStats(BaseModel):
    """日志统计信息"""

    total_count: int
    count_by_level: dict[str, int]
    oldest_log: Optional[datetime]
    newest_log: Optional[datetime]
    db_size_mb: float


class LogStorage:
    """日志存储层"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self):
        """确保日志表存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    logger_name TEXT,
                    timestamp DATETIME NOT NULL,
                    request_id TEXT,
                    method TEXT,
                    path TEXT,
                    status_code INTEGER,
                    process_time_ms INTEGER,
                    client_ip TEXT,
                    exception_type TEXT,
                    exception_message TEXT,
                    stack_trace TEXT,
                    extra TEXT
                )
            """)
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_request_id ON logs(request_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_logger_name ON logs(logger_name)")
            conn.commit()

    def insert_logs(self, logs: list[dict[str, Any]]) -> int:
        """批量插入日志"""
        if not logs:
            return 0

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO logs (
                    level, message, logger_name, timestamp, request_id,
                    method, path, status_code, process_time_ms, client_ip,
                    exception_type, exception_message, stack_trace, extra
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._log_to_tuple(log) for log in logs],
            )
            conn.commit()
            return cursor.rowcount

    def _log_to_tuple(self, log: dict[str, Any]) -> tuple:
        """将日志字典转换为数据库元组"""
        return (
            log.get("level"),
            log.get("message"),
            log.get("logger_name"),
            log.get("timestamp"),
            log.get("request_id"),
            log.get("method"),
            log.get("path"),
            log.get("status_code"),
            log.get("process_time_ms"),
            log.get("client_ip"),
            log.get("exception_type"),
            log.get("exception_message"),
            log.get("stack_trace"),
            json.dumps(log.get("extra")) if log.get("extra") else None,
        )

    def _build_query_conditions(
        self,
        level: Optional[str] = None,
        request_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[list[str], list[Any]]:
        """构建查询条件，返回 (conditions, params)"""
        conditions = []
        params = []

        if level:
            conditions.append("level = ?")
            params.append(level.upper())
        if request_id:
            conditions.append("request_id = ?")
            params.append(request_id)
        if keyword:
            conditions.append("message LIKE ?")
            params.append(f"%{keyword}%")
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())

        return conditions, params

    def query_logs(
        self,
        level: Optional[str] = None,
        request_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",  # desc 或 asc
    ) -> list[LogEntry]:
        """查询日志"""
        conditions, params = self._build_query_conditions(
            level, request_id, keyword, start_time, end_time
        )
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_clause = "DESC" if order.lower() == "desc" else "ASC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT * FROM logs
                WHERE {where_clause}
                ORDER BY timestamp {order_clause}
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            )
            rows = cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]

    def count_logs(
        self,
        level: Optional[str] = None,
        request_id: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """统计日志数量"""
        conditions, params = self._build_query_conditions(
            level, request_id, keyword, start_time, end_time
        )
        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM logs WHERE {where_clause}", params)
            return cursor.fetchone()[0]

    def cleanup_old_logs(self, retention_days: int) -> int:
        """清理过期日志"""
        cutoff = datetime.now() - timedelta(days=retention_days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM logs WHERE timestamp < ?",
                (cutoff.isoformat(),),
            )
            deleted = cursor.rowcount
            # 优化数据库空间
            cursor.execute("VACUUM")
            conn.commit()
            return deleted

    def get_stats(self) -> LogStats:
        """获取日志统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 总数
            cursor.execute("SELECT COUNT(*) FROM logs")
            total_count = cursor.fetchone()[0]

            # 按级别统计
            cursor.execute("SELECT level, COUNT(*) as count FROM logs GROUP BY level")
            count_by_level = {row["level"]: row["count"] for row in cursor.fetchall()}

            # 时间范围
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM logs")
            row = cursor.fetchone()
            oldest_log = datetime.fromisoformat(row[0]) if row[0] else None
            newest_log = datetime.fromisoformat(row[1]) if row[1] else None

            # 数据库大小
            db_size_mb = Path(self.db_path).stat().st_size / (1024 * 1024) if Path(self.db_path).exists() else 0

            return LogStats(
                total_count=total_count,
                count_by_level=count_by_level,
                oldest_log=oldest_log,
                newest_log=newest_log,
                db_size_mb=round(db_size_mb, 2),
            )

    def _row_to_entry(self, row: sqlite3.Row) -> LogEntry:
        """将数据库行转换为 LogEntry"""
        return LogEntry(
            id=row["id"],
            level=row["level"],
            message=row["message"],
            logger_name=row["logger_name"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            request_id=row["request_id"],
            method=row["method"],
            path=row["path"],
            status_code=row["status_code"],
            process_time_ms=row["process_time_ms"],
            client_ip=row["client_ip"],
            exception_type=row["exception_type"],
            exception_message=row["exception_message"],
            stack_trace=row["stack_trace"],
            extra=json.loads(row["extra"]) if row["extra"] else None,
        )
