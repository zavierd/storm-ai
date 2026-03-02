import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import AppException

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException):
        logger.warning(
            "业务异常 [%s] %s: %s", exc.code, exc.message, exc.detail
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "detail": exc.detail,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception):
        logger.exception("未处理的异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "内部服务错误",
                    "detail": None,
                },
            },
        )
