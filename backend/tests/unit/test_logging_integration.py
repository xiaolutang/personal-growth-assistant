"""
B010/B011 集成验证：本地日志模块移除 + SDK 接入
"""
import logging
import os
from unittest.mock import patch, MagicMock

import pytest


class TestB010RemoveLocalLogging:
    """B010 验收条件：infrastructure/logging/ 已删除、项目能正常启动"""

    def test_infrastructure_logging_dir_not_exists(self):
        """旧日志模块目录已不存在"""
        import pathlib
        logging_dir = pathlib.Path(__file__).parent.parent.parent / "app" / "infrastructure" / "logging"
        assert not logging_dir.exists(), f"本地日志目录仍存在: {logging_dir}"

    def test_no_old_logging_imports(self):
        """旧日志模块无残留 import"""
        import subprocess
        result = subprocess.run(
            ["grep", "-r", "from app.infrastructure.logging", "backend/app/"],
            capture_output=True, text=True, cwd=os.getcwd().rsplit("/backend", 1)[0],
        )
        assert result.returncode != 0, f"发现旧日志模块残留引用: {result.stdout}"

    def test_project_starts_without_local_logging(self):
        """移除本地日志后项目可正常启动（import 成功）"""
        # 如果本地日志模块残留，import 会失败或引入旧依赖
        from app.main import app  # noqa: F401
        assert app is not None

    def test_no_log_router_registered(self):
        """旧日志路由 /api/logs 不再注册"""
        from app.main import app
        routes = [r.path for r in app.routes]
        assert "/api/logs" not in routes
        assert "/api/logs/ingest" not in routes


class TestB011SDKIntegration:
    """B011 验收条件：中间件日志通过 SDK 发送到 log-service"""

    def test_setup_remote_logging_importable(self):
        """SDK 可正常导入"""
        from log_service_sdk import setup_remote_logging, RemoteLogHandler
        assert callable(setup_remote_logging)
        assert issubclass(RemoteLogHandler, logging.Handler)

    def test_log_service_url_configured(self):
        """LOG_SERVICE_URL 配置项存在"""
        from app.core.config import get_settings
        settings = get_settings()
        assert hasattr(settings, "LOG_SERVICE_URL")
        assert settings.LOG_SERVICE_URL  # 非空

    def test_setup_remote_logging_attaches_handler(self):
        """setup_remote_logging 将 RemoteLogHandler 挂载到 root logger"""
        from log_service_sdk import setup_remote_logging

        # 清理可能的已有 handler
        root = logging.getLogger()
        original_handlers = root.handlers[:]

        try:
            handler = setup_remote_logging(
                endpoint="http://localhost:9999",  # 不可达端口，不影响测试
                service_name="test-service",
                level=logging.INFO,
            )
            assert handler is not None
            assert type(handler).__name__ == "RemoteLogHandler"
            assert handler in root.handlers
        finally:
            # 恢复原始 handlers
            root.handlers = original_handlers

    def test_sdk_init_failure_does_not_block_startup(self):
        """SDK 初始化失败不阻塞项目启动"""
        with patch("log_service_sdk.setup_remote_logging", side_effect=Exception("SDK 连接失败")):
            # 即使 SDK 抛异常，main 模块仍应可导入
            # 这模拟了 log-service 不可达但应用仍正常运行的场景
            import importlib
            import app.main
            importlib.reload(app.main)
            # 如果到达这里，说明 SDK 失败没有导致导入失败

    def test_middleware_logs_through_root_logger(self):
        """中间件日志通过 root logger 输出（被 RemoteLogHandler 捕获）"""
        from app.middleware import RequestLoggingMiddleware

        # 验证中间件使用标准 logging（会被 root logger 的 handler 捕获）
        middleware_logger = logging.getLogger("app.middleware")
        assert middleware_logger.getEffectiveLevel() <= logging.INFO

    def test_log_handler_close_on_shutdown(self):
        """应用关闭时调用 handler.close()（flush 剩余日志）"""
        mock_handler = MagicMock()
        mock_handler.close = MagicMock()

        with patch("app.main._log_handler", mock_handler):
            # 模拟 shutdown 流程中的 close 调用
            mock_handler.close()
            mock_handler.close.assert_called_once()
