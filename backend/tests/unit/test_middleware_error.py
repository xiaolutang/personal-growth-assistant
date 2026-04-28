"""B57: 错误处理脱敏测试 — 通过 @app.exception_handler(Exception) 测试"""

import sys
import types
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """每个测试前后清理 settings 缓存"""
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _build_app():
    """构建应用（在 patch.dict 上下文内调用），注册与 main.py 相同的异常处理器"""
    from app.core.config import get_settings
    from app.middleware import get_request_id
    get_settings.cache_clear()

    app = FastAPI()

    @app.get("/crash")
    def crash():
        raise RuntimeError("数据库连接池耗尽: host=db.internal, port=5432")

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):
        from fastapi.responses import JSONResponse

        request_id = get_request_id()
        debug = get_settings().DEBUG
        if debug:
            error_message = str(exc)
            error_type = type(exc).__name__
        else:
            error_message = "Internal Server Error"
            error_type = "INTERNAL_ERROR"

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": error_message,
                    "type": error_type,
                    "request_id": request_id,
                },
            },
        )

    return app


def _build_validation_app():
    """构建包含 RequestValidationError 处理器的最小应用。"""
    if "langgraph.checkpoint.sqlite.aio" not in sys.modules:
        sqlite_pkg = types.ModuleType("langgraph.checkpoint.sqlite")
        aio_pkg = types.ModuleType("langgraph.checkpoint.sqlite.aio")
        aio_pkg.AsyncSqliteSaver = type("AsyncSqliteSaver", (), {})
        sys.modules["langgraph.checkpoint.sqlite"] = sqlite_pkg
        sys.modules["langgraph.checkpoint.sqlite.aio"] = aio_pkg

    from app.main import _json_safe

    app = FastAPI()

    class EchoRequest(BaseModel):
        query: str

    @app.post("/echo")
    def echo(payload: EchoRequest):
        return payload.model_dump()

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "detail": _json_safe(exc.errors()),
                "body": _json_safe(exc.body),
            },
        )

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


class TestValidationErrorSerialization:
    """422 验证错误应可稳定返回，不因 bytes body 再炸成 500。"""

    def test_validation_error_with_bytes_body_returns_422(self):
        app = _build_validation_app()
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post(
            "/echo",
            content='{"query":""}',
            headers={"Content-Type": "text/plain"},
        )

        assert resp.status_code == 422
        body = resp.json()
        assert body["body"] == '{"query":""}'
        assert body["detail"][0]["type"] == "model_attributes_type"
