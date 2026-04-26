"""B57: 错误处理中间件脱敏测试"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """每个测试前后清理 settings 缓存"""
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _build_app():
    """构建应用（在 patch.dict 上下文内调用）"""
    from app.core.config import get_settings
    get_settings.cache_clear()

    from app.middleware import ErrorHandlerMiddleware

    app = FastAPI()

    @app.get("/crash")
    def crash():
        raise RuntimeError("数据库连接池耗尽: host=db.internal, port=5432")

    @app.get("/health")
    def health():
        return {"ok": True}

    app.add_middleware(ErrorHandlerMiddleware)
    return app


class TestErrorHandlerSanitization:
    """生产环境 500 错误不暴露内部异常详情"""

    def test_production_hides_exception_details(self):
        """非 DEBUG 模式下不返回 str(e) 和异常类型名"""
        env = {"DATA_DIR": "/tmp/test_b57_middleware", "DEBUG": "false"}
        with patch.dict("os.environ", env, clear=False):
            app = _build_app()
            client = TestClient(app, raise_server_exceptions=False)

            resp = client.get("/crash")
            assert resp.status_code == 500
            body = resp.json()
            error = body["error"]
            assert error["message"] == "Internal Server Error"
            assert error["type"] == "INTERNAL_ERROR"
            assert "RuntimeError" not in str(body)
            assert "db.internal" not in str(body)
            assert "5432" not in str(body)

    def test_debug_mode_shows_exception_details(self):
        """DEBUG=true 模式下返回详细异常信息"""
        env = {"DATA_DIR": "/tmp/test_b57_middleware", "DEBUG": "true"}
        with patch.dict("os.environ", env, clear=False):
            app = _build_app()
            client = TestClient(app, raise_server_exceptions=False)

            resp = client.get("/crash")
            assert resp.status_code == 500
            body = resp.json()
            error = body["error"]
            assert "数据库连接池耗尽" in error["message"]
            assert error["type"] == "RuntimeError"

    def test_production_request_id_still_present(self):
        """生产环境仍返回 request_id"""
        env = {"DATA_DIR": "/tmp/test_b57_middleware", "DEBUG": "false"}
        with patch.dict("os.environ", env, clear=False):
            app = _build_app()
            client = TestClient(app, raise_server_exceptions=False)

            resp = client.get("/crash")
            assert resp.status_code == 500
            body = resp.json()
            assert "request_id" in body["error"]
