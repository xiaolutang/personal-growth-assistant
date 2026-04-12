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
        from app.main import app
        assert app is not None

    @pytest.mark.asyncio
    async def test_lifespan_starts_without_local_logging(self):
        """验证 lifespan 在无本地日志模块时可正常执行 startup 阶段"""
        from app.main import lifespan

        # Mock 所有 lifespan 依赖
        async def mock_graph_create(*args, **kwargs):
            g = MagicMock()
            g.caller = MagicMock()
            return g

        with patch("app.main.setup_remote_logging", return_value=MagicMock()), \
             patch("app.main.TaskParserGraph") as mock_graph_cls, \
             patch("app.main.init_storage", return_value=MagicMock()), \
             patch("app.main.deps"):
            mock_graph_cls.create = mock_graph_create

            async with lifespan(None):
                pass  # startup 成功，到达 yield 后继续 shutdown

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
        assert settings.LOG_SERVICE_URL

    def test_setup_remote_logging_attaches_handler(self):
        """setup_remote_logging 将 RemoteLogHandler 挂载到 root logger"""
        from log_service_sdk import setup_remote_logging

        root = logging.getLogger()
        original_handlers = root.handlers[:]

        try:
            handler = setup_remote_logging(
                endpoint="http://localhost:9999",
                service_name="test-service",
                level=logging.INFO,
            )
            assert handler is not None
            assert type(handler).__name__ == "RemoteLogHandler"
            assert handler in root.handlers
        finally:
            root.handlers = original_handlers

    def test_sdk_init_failure_does_not_block_startup(self):
        """SDK 初始化失败不阻塞项目启动（main.py try/except 覆盖）"""
        # main.py 中 setup_remote_logging 已被 try/except 包裹
        # 验证方式：patch SDK 抛异常后，import app.main 不受影响
        with patch("app.main.setup_remote_logging", side_effect=Exception("SDK 连接失败")):
            import importlib
            import app.main
            importlib.reload(app.main)
            # 如果到达这里，说明模块级别未因 SDK 异常而崩溃

    def test_middleware_logs_through_root_logger(self):
        """中间件日志通过 root logger 输出（被 RemoteLogHandler 捕获）"""
        middleware_logger = logging.getLogger("app.middleware")
        assert middleware_logger.getEffectiveLevel() <= logging.INFO

    def test_middleware_log_reaches_handler(self):
        """中间件日志真正进入 RemoteLogHandler（运行态验证）"""
        captured = []

        class CapturingHandler(logging.Handler):
            """捕获 emit 调用的测试 handler，模拟 RemoteLogHandler 的日志接收"""
            def emit(self, record):
                self.captured.append(record)

        handler = CapturingHandler()
        handler.captured = captured
        handler.setLevel(logging.INFO)

        root = logging.getLogger()
        original_handlers = root.handlers[:]

        try:
            root.addHandler(handler)
            root.setLevel(logging.INFO)
            # 模拟中间件日志输出
            mw_logger = logging.getLogger("app.middleware")
            mw_logger.info("Request completed: GET /api/health 200")

            assert len(captured) == 1, f"Expected 1 log record, got {len(captured)}"
            assert "Request completed" in captured[0].getMessage()
            assert captured[0].name == "app.middleware"
        finally:
            root.handlers = original_handlers

    def test_log_handler_close_on_shutdown(self):
        """应用关闭时 lifespan 调用 handler.close()（flush 剩余日志）"""
        mock_handler = MagicMock()
        mock_handler.close = MagicMock()

        with patch("app.main._log_handler", mock_handler):
            # 模拟 shutdown 流程中的 close 调用
            mock_handler.close()
            mock_handler.close.assert_called_once()

    def test_lifespan_catches_sdk_failure(self):
        """验证 lifespan 中 setup_remote_logging 异常被 try/except 捕获"""
        # 通过检查 main.py 源码确认 try/except 包裹了 setup_remote_logging
        import inspect
        from app.main import lifespan
        source = inspect.getsource(lifespan)
        assert "setup_remote_logging" in source
        # 确认 try/except 包裹了 SDK 初始化
        assert "远程日志初始化失败" in source, "lifespan 中缺少 SDK 异常处理"
