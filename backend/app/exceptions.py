from __future__ import annotations

from typing import Any


class AppException(Exception):
    """应用异常基类"""

    def __init__(
        self,
        status_code: int = 500,
        code: str = "INTERNAL_ERROR",
        message: str = "内部服务错误",
        detail: Any = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class GeminiAPIError(AppException):
    """Gemini API 调用失败"""

    def __init__(self, message: str = "Gemini API 调用失败", detail: Any = None):
        super().__init__(
            status_code=502, code="GEMINI_API_ERROR", message=message, detail=detail
        )


class ImageProcessingError(AppException):
    """图像处理错误"""

    def __init__(self, message: str = "图像处理失败", detail: Any = None):
        super().__init__(
            status_code=422,
            code="IMAGE_PROCESSING_ERROR",
            message=message,
            detail=detail,
        )


class PromptRenderError(AppException):
    """模板渲染错误"""

    def __init__(self, message: str = "提示词模板渲染失败", detail: Any = None):
        super().__init__(
            status_code=500,
            code="PROMPT_RENDER_ERROR",
            message=message,
            detail=detail,
        )


class ValidationError(AppException):
    """输入校验错误"""

    def __init__(self, message: str = "输入参数校验失败", detail: Any = None):
        super().__init__(
            status_code=422, code="VALIDATION_ERROR", message=message, detail=detail
        )


class RateLimitError(AppException):
    """频率限制"""

    def __init__(self, message: str = "请求频率超限，请稍后重试", detail: Any = None):
        super().__init__(
            status_code=429, code="RATE_LIMIT_ERROR", message=message, detail=detail
        )


class ContentBlockedImageError(AppException):
    """模型内容安全拦截，返回占位图（如全黑图）"""

    def __init__(self, message: str = "生成内容触发安全策略，请调整提示词后重试", detail: Any = None):
        super().__init__(
            status_code=422,
            code="CONTENT_BLOCKED_IMAGE",
            message=message,
            detail=detail,
        )


class InsufficientCreditsError(AppException):
    """积分不足"""

    def __init__(self, current_balance: float, required: float):
        super().__init__(
            status_code=402,
            code="INSUFFICIENT_CREDITS",
            message="算力不足，请充值后重试",
            detail={
                "current_balance": current_balance,
                "required": required,
            },
        )
