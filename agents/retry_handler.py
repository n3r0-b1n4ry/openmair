"""
Advanced Error Handling & Retry Handler cho hệ thống AIOps

Hỗ trợ cả sync và async functions.
"""
import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Any, Optional, Type
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Trạng thái của Circuit Breaker"""
    CLOSED = "closed"  # Bình thường, cho phép request đi qua
    OPEN = "open"      # Đã mở, chặn request
    HALF_OPEN = "half_open"  # Đang thử lại


class CircuitBreaker:
    """
    Circuit Breaker Pattern để ngăn chặn cascade failures
    
    Khi một service fail quá nhiều lần, circuit breaker sẽ mở để ngăn chặn
    các request tiếp theo, giúp hệ thống không bị quá tải.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Khởi tạo Circuit Breaker
        
        Args:
            failure_threshold (int): Số lần fail tối đa trước khi mở circuit
            recovery_timeout (float): Thời gian chờ trước khi thử lại (giây)
            expected_exception (Type[Exception]): Loại exception cần theo dõi
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable) -> Callable:
        """
        Decorator để wrap function với circuit breaker (hỗ trợ cả sync và async)
        
        Args:
            func (Callable): Function cần wrap
            
        Returns:
            Callable: Function đã được wrap
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                if self.state == CircuitState.OPEN:
                    if self._should_attempt_reset():
                        self.state = CircuitState.HALF_OPEN
                        logger.info("Circuit breaker chuyển sang HALF_OPEN state")
                    else:
                        raise Exception("Circuit breaker đang OPEN, request bị chặn")
                
                try:
                    result = await func(*args, **kwargs)
                    
                    if self.state == CircuitState.HALF_OPEN:
                        self._reset()
                        logger.info("Circuit breaker đã reset về CLOSED state")
                    
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
            
            return async_wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if self.state == CircuitState.OPEN:
                    if self._should_attempt_reset():
                        self.state = CircuitState.HALF_OPEN
                        logger.info("Circuit breaker chuyển sang HALF_OPEN state")
                    else:
                        raise Exception("Circuit breaker đang OPEN, request bị chặn")
                
                try:
                    result = func(*args, **kwargs)
                    
                    if self.state == CircuitState.HALF_OPEN:
                        self._reset()
                        logger.info("Circuit breaker đã reset về CLOSED state")
                    
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
            
            return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Kiểm tra xem có nên thử reset circuit không"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_failure(self):
        """Xử lý khi có failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker đã OPEN sau {self.failure_count} failures. "
                f"Sẽ thử lại sau {self.recovery_timeout} giây"
            )
    
    def _reset(self):
        """Reset circuit breaker về trạng thái bình thường"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


# Tạo circuit breaker mặc định cho LLM calls
llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0,
    expected_exception=Exception
)


def with_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exponential_base: int = 2
):
    """
    Decorator để thêm retry logic với exponential backoff
    
    tenacity >= 8.2.0 tự động hỗ trợ async functions.
    
    Args:
        max_attempts (int): Số lần thử tối đa
        min_wait (float): Thời gian chờ tối thiểu (giây)
        max_wait (float): Thời gian chờ tối đa (giây)
        exponential_base (int): Cơ số cho exponential backoff
    """
    def decorator(func: Callable) -> Callable:
        retry_decorator = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=exponential_base, min=min_wait, max=max_wait),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        return retry_decorator(func)
    return decorator


def with_circuit_breaker(circuit_breaker: Optional[CircuitBreaker] = None):
    """
    Decorator để thêm circuit breaker pattern
    
    Args:
        circuit_breaker (Optional[CircuitBreaker]): Circuit breaker instance. 
                                                   Nếu None, sử dụng mặc định
    """
    if circuit_breaker is None:
        circuit_breaker = llm_circuit_breaker
    
    def decorator(func: Callable) -> Callable:
        return circuit_breaker.call(func)
    
    return decorator


def with_retry_and_circuit_breaker(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    circuit_breaker: Optional[CircuitBreaker] = None
):
    """
    Decorator kết hợp cả retry và circuit breaker
    
    Args:
        max_attempts (int): Số lần thử tối đa
        min_wait (float): Thời gian chờ tối thiểu (giây)
        max_wait (float): Thời gian chờ tối đa (giây)
        circuit_breaker (Optional[CircuitBreaker]): Circuit breaker instance
    """
    def decorator(func: Callable) -> Callable:
        # Áp dụng retry trước
        func_with_retry = with_retry(max_attempts, min_wait, max_wait)(func)
        # Sau đó áp dụng circuit breaker
        func_with_cb = with_circuit_breaker(circuit_breaker)(func_with_retry)
        
        return func_with_cb
    
    return decorator


class RateLimiter:
    """
    Rate Limiter để giới hạn số lượng request trong một khoảng thời gian
    
    Sử dụng Token Bucket algorithm để implement rate limiting
    """
    
    def __init__(self, max_requests: int, time_window: float):
        """
        Khởi tạo Rate Limiter
        
        Args:
            max_requests (int): Số request tối đa trong time window
            time_window (float): Khoảng thời gian (giây)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def allow_request(self) -> bool:
        """
        Kiểm tra xem request có được phép thực hiện không
        
        Returns:
            bool: True nếu được phép, False nếu không
        """
        current_time = time.time()
        
        # Xóa các request cũ ngoài time window
        self.requests = [
            req_time for req_time in self.requests
            if current_time - req_time < self.time_window
        ]
        
        # Kiểm tra số lượng request
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """
        Tính thời gian cần chờ trước khi request tiếp theo được phép
        
        Returns:
            float: Thời gian chờ (giây)
        """
        if not self.requests:
            return 0.0
        
        oldest_request = self.requests[0]
        wait = self.time_window - (time.time() - oldest_request)
        return max(0.0, wait)


def with_rate_limiter(rate_limiter: RateLimiter):
    """
    Decorator để thêm rate limiting (hỗ trợ cả sync và async)
    
    Args:
        rate_limiter (RateLimiter): Rate limiter instance
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                if not rate_limiter.allow_request():
                    wt = rate_limiter.wait_time()
                    logger.warning(
                        f"Rate limit exceeded. Cần chờ {wt:.2f} giây"
                    )
                    await asyncio.sleep(wt)
                
                return await func(*args, **kwargs)
            
            return async_wrapper
        else:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if not rate_limiter.allow_request():
                    wt = rate_limiter.wait_time()
                    logger.warning(
                        f"Rate limit exceeded. Cần chờ {wt:.2f} giây"
                    )
                    time.sleep(wt)
                
                return func(*args, **kwargs)
            
            return wrapper
    return decorator


# Tạo rate limiter mặc định cho LLM API calls
llm_rate_limiter = RateLimiter(max_requests=10, time_window=1.0)  # 10 requests/giây


def with_all_protections(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
    rate_limiter: Optional[RateLimiter] = None
):
    """
    Decorator kết hợp tất cả các cơ chế bảo vệ:
    - Retry với exponential backoff
    - Circuit breaker
    - Rate limiting
    
    Args:
        max_attempts (int): Số lần thử tối đa
        min_wait (float): Thời gian chờ tối thiểu (giây)
        max_wait (float): Thời gian chờ tối đa (giây)
        circuit_breaker (Optional[CircuitBreaker]): Circuit breaker instance
        rate_limiter (Optional[RateLimiter]): Rate limiter instance
    """
    def decorator(func: Callable) -> Callable:
        # Sử dụng biến local để tránh UnboundLocalError
        _rate_limiter = rate_limiter if rate_limiter is not None else llm_rate_limiter
        
        # Áp dụng rate limiting
        func_with_rl = with_rate_limiter(_rate_limiter)(func)
        
        # Áp dụng retry
        func_with_retry = with_retry(max_attempts, min_wait, max_wait)(func_with_rl)
        
        # Áp dụng circuit breaker
        func_with_cb = with_circuit_breaker(circuit_breaker)(func_with_retry)
        
        return func_with_cb
    
    return decorator


# Export các decorator và class
__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "llm_circuit_breaker",
    "with_retry",
    "with_circuit_breaker",
    "with_retry_and_circuit_breaker",
    "RateLimiter",
    "llm_rate_limiter",
    "with_rate_limiter",
    "with_all_protections"
]
