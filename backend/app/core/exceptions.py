"""自定义异常类"""


class AppException(Exception):
    """应用基础异常"""

    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(AppException):
    """资源未找到异常"""

    def __init__(self, message: str = "资源未找到"):
        super().__init__(message, code="NOT_FOUND", status_code=404)


class ValidationError(AppException):
    """验证错误异常"""

    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class ServiceUnavailableError(AppException):
    """服务不可用异常"""

    def __init__(self, message: str = "服务暂不可用"):
        super().__init__(message, code="SERVICE_UNAVAILABLE", status_code=503)
