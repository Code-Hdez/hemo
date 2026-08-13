"""Base helpers for synchronous extractor wrappers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

from app.modules.gemini_extraction.schemas import ExtractionAttemptError

T = TypeVar("T")


def run_with_timeout(
    callback: Callable[[], T],
    *,
    timeout_seconds: float,
    error_code: str,
    message: str,
) -> T:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(callback)
    try:
        return future.result(timeout=max(timeout_seconds, 0.1))
    except FutureTimeoutError as exc:
        future.cancel()
        raise ExtractionAttemptError(error_code, message) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
