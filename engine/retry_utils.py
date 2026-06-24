"""通用 API 调用重试工具 —— 指数退避 + 随机抖动。

用法装饰器:
    @retry_with_backoff()
    def call_api():
        ...

用法显式调用:
    result = retry_with_backoff(call_api, max_retries=3)(args)

重试规则:
    - 最多重试 max_retries 次（默认 3 次）
    - 等待时间: base_delay × (2 ^ attempt) + 随机抖动（0~20%）
    - 仅对以下情况重试：
      - 网络异常（ConnectionError, TimeoutError, requests.ConnectionError）
      - HTTP 状态码 429（限流）、5xx（服务端错误）
    - 以下情况不重试直接报错：
      - HTTP 4xx（除 429 外）：认证/参数错误
    - 可通过 retryable_exceptions 参数额外指定可重试的异常类型
"""

import random
import time
from functools import wraps
from typing import Callable, Optional

import requests

# 默认不重试的 HTTP 状态码（429 限流除外，它应该重试）
NO_RETRY_STATUSES = {400, 401, 403, 404, 422}


def _is_retryable_exception(e: Exception) -> bool:
    """判断异常是否可重试（网络/超时类异常）。"""
    if isinstance(e, (ConnectionError, TimeoutError)):
        return True
    if isinstance(e, requests.ConnectionError):
        return True
    if isinstance(e, requests.Timeout):
        return True
    if isinstance(e, requests.exceptions.ConnectionError):
        return True
    if isinstance(e, requests.exceptions.Timeout):
        return True
    return False


def _has_http_status(e: Exception) -> Optional[int]:
    """从异常中提取 HTTP 状态码（如果有的话）。"""
    if hasattr(e, 'response') and e.response is not None:
        return e.response.status_code
    if isinstance(e, requests.HTTPError) and e.response is not None:
        return e.response.status_code
    # 检查被包裹的异常
    if hasattr(e, 'args') and e.args:
        for arg in e.args:
            if isinstance(arg, requests.Response):
                return arg.status_code
    return None


def retry_with_backoff(
    func: Optional[Callable] = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 8.0,
    retryable_exceptions: Optional[tuple] = None,
):
    """带指数退避 + 随机抖动的重试装饰器/包装器。

    可以用作装饰器:
        @retry_with_backoff()
        def call_api(): ...

    也可用作显式调用:
        retry_with_backoff(call_api, max_retries=3)(args...)

    Args:
        func: 要重试的函数（装饰器模式时为 None）
        max_retries: 最大重试次数（默认 3）
        base_delay: 基础等待秒数（默认 1.0）
        max_delay: 最大等待秒数（默认 8.0）
        retryable_exceptions: 指定额外的可重试异常类型（如 (ValueError,)），
                              默认不重试的异常若在此列表中则会被强制重试

    Returns:
        装饰器或包装后的函数
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries + 1):  # +1 因为第一次是原始调用
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    # 判断是否应该重试
                    should_retry = True

                    # 检查 HTTP 状态码
                    status = _has_http_status(e)
                    if status is not None:
                        if status in NO_RETRY_STATUSES:
                            # 4xx（除 429）不重试
                            should_retry = False
                        elif status == 429:
                            # 限流 — 应该重试但多等一会
                            should_retry = True
                        elif 500 <= status < 600:
                            # 5xx 服务端错误 — 重试
                            should_retry = True
                        else:
                            should_retry = True
                    else:
                        # 没有 HTTP 状态码，检查异常类型
                        should_retry = _is_retryable_exception(e)

                    # 如果异常类型在 retryable_exceptions 中，强制重试
                    if not should_retry and retryable_exceptions is not None:
                        if isinstance(e, retryable_exceptions):
                            should_retry = True

                    if not should_retry or attempt >= max_retries:
                        # 不重试或已达到最大重试次数，向上抛出
                        raise

                    # 计算等待时间：指数退避 + 随机抖动
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = delay * random.uniform(0, 0.2)
                    total_delay = delay + jitter

                    func_name = getattr(fn, '__name__', repr(fn))
                    print(f"  [retry] {func_name} 失败 (attempt {attempt + 1}/{max_retries}), "
                          f"{total_delay:.1f}s 后重试... ({type(e).__name__}: {e})")
                    time.sleep(total_delay)

            # 不应该到达这里
            raise last_error  # type: ignore

        return wrapper

    # 支持 @retry_with_backoff() 和 retry_with_backoff(func) 两种调用方式
    if func is not None:
        return decorator(func)
    return decorator


__all__ = ["retry_with_backoff"]
