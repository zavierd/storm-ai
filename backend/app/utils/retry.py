from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.exceptions import GeminiAPIError, RateLimitError

logger = logging.getLogger(__name__)


def _is_retryable_error(exc: BaseException) -> bool:
    """判断是否为可重试的错误（429/500/503）"""
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, GeminiAPIError):
        detail = str(exc.detail) if exc.detail else ""
        return any(code in detail for code in ("429", "500", "503"))
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True
    return False


def _log_retry(state: RetryCallState) -> None:
    """重试时记录日志"""
    logger.warning(
        "第 %d 次重试，异常: %s",
        state.attempt_number,
        state.outcome.exception() if state.outcome else "unknown",
    )


def create_retry_decorator(
    max_retries: int = 3,
    min_wait: float = 1,
    max_wait: float = 30,
) -> Callable[[Any], Any]:
    """创建针对 Gemini API 错误的重试装饰器"""
    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception(_is_retryable_error),
        before_sleep=_log_retry,
        reraise=True,
    )
