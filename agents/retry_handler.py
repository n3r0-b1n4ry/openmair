"""
Advanced Error Handling & Retry Handler for the AIOps System

Supports both sync and async functions.
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
    """Circuit Breaker states"""
    CLOSED = "closed"  # Normal, allows requests to pass through
    OPEN = "open"      # Open, blocks requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit Breaker Pattern to prevent cascade failures
    
    When a service fails too many times, the circuit breaker opens to prevent
    further requests, helping the system avoid overload.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        """
        Initialize Circuit Breaker
        
        Args:
            failure_threshold (int): Maximum failures before opening the circuit
            recovery_timeout (float): Time to wait before retrying (seconds)
            expected_exception (Type[Exception]): Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable) -> Callable:
        """
        Decorator to wrap a function with circuit breaker (supports both sync and async)
        
        Args:
            func (Callable): Function to wrap
            
        Returns:
            Callable: Wrapped function
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                if self.state == CircuitState.OPEN:
                    if self._should_attempt_reset():
                        self.state = CircuitState.HALF_OPEN
                        logger.info("Circuit breaker transitioning to HALF_OPEN state")
                    else:
                        raise Exception("Circuit breaker is OPEN, request blocked")
                
                try:
                    result = await func(*args, **kwargs)
                    
                    if self.state == CircuitState.HALF_OPEN:
                        self._reset()
                        logger.info("Circuit breaker has reset to CLOSED state")
                    
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
                        logger.info("Circuit breaker transitioning to HALF_OPEN state")
                    else:
                        raise Exception("Circuit breaker is OPEN, request blocked")
                
                try:
                    result = func(*args, **kwargs)
                    
                    if self.state == CircuitState.HALF_OPEN:
                        self._reset()
                        logger.info("Circuit breaker has reset to CLOSED state")
                    
                    return result
                except self.expected_exception as e:
                    self._on_failure()
                    raise e
            
            return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if a circuit reset should be attempted"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_failure(self):
        """Handle a failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPENED after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout} seconds"
            )
    
    def _reset(self):
        """Reset circuit breaker to normal state"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


# Create default circuit breaker for LLM calls
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
    Decorator to add retry logic with exponential backoff
    
    tenacity >= 8.2.0 automatically supports async functions.
    
    Args:
        max_attempts (int): Maximum number of attempts
        min_wait (float): Minimum wait time (seconds)
        max_wait (float): Maximum wait time (seconds)
        exponential_base (int): Base for exponential backoff
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
    Decorator to add circuit breaker pattern
    
    Args:
        circuit_breaker (Optional[CircuitBreaker]): Circuit breaker instance.
                                                   If None, uses default
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
    Decorator combining both retry and circuit breaker
    
    Args:
        max_attempts (int): Maximum number of attempts
        min_wait (float): Minimum wait time (seconds)
        max_wait (float): Maximum wait time (seconds)
        circuit_breaker (Optional[CircuitBreaker]): Circuit breaker instance
    """
    def decorator(func: Callable) -> Callable:
        # Apply retry first
        func_with_retry = with_retry(max_attempts, min_wait, max_wait)(func)
        # Then apply circuit breaker
        func_with_cb = with_circuit_breaker(circuit_breaker)(func_with_retry)
        
        return func_with_cb
    
    return decorator


class RateLimiter:
    """
    Rate Limiter to restrict the number of requests within a time window
    
    Uses the Token Bucket algorithm to implement rate limiting
    """
    
    def __init__(self, max_requests: int, time_window: float):
        """
        Initialize Rate Limiter
        
        Args:
            max_requests (int): Maximum requests in the time window
            time_window (float): Time window (seconds)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def allow_request(self) -> bool:
        """
        Check if a request is allowed
        
        Returns:
            bool: True if allowed, False if not
        """
        current_time = time.time()
        
        # Remove old requests outside the time window
        self.requests = [
            req_time for req_time in self.requests
            if current_time - req_time < self.time_window
        ]
        
        # Check request count
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """
        Calculate the wait time before the next request is allowed
        
        Returns:
            float: Wait time (seconds)
        """
        if not self.requests:
            return 0.0
        
        oldest_request = self.requests[0]
        wait = self.time_window - (time.time() - oldest_request)
        return max(0.0, wait)


def with_rate_limiter(rate_limiter: RateLimiter):
    """
    Decorator to add rate limiting (supports both sync and async)
    
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
                        f"Rate limit exceeded. Waiting {wt:.2f} seconds"
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
                        f"Rate limit exceeded. Waiting {wt:.2f} seconds"
                    )
                    time.sleep(wt)
                
                return func(*args, **kwargs)
            
            return wrapper
    return decorator


# Create default rate limiter for LLM API calls
llm_rate_limiter = RateLimiter(max_requests=10, time_window=1.0)  # 10 requests/second


def with_all_protections(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
    rate_limiter: Optional[RateLimiter] = None
):
    """
    Decorator combining all protection mechanisms:
    - Retry with exponential backoff
    - Circuit breaker
    - Rate limiting
    
    Args:
        max_attempts (int): Maximum number of attempts
        min_wait (float): Minimum wait time (seconds)
        max_wait (float): Maximum wait time (seconds)
        circuit_breaker (Optional[CircuitBreaker]): Circuit breaker instance
        rate_limiter (Optional[RateLimiter]): Rate limiter instance
    """
    def decorator(func: Callable) -> Callable:
        # Use local variable to avoid UnboundLocalError
        _rate_limiter = rate_limiter if rate_limiter is not None else llm_rate_limiter
        
        # Apply rate limiting
        func_with_rl = with_rate_limiter(_rate_limiter)(func)
        
        # Apply retry
        func_with_retry = with_retry(max_attempts, min_wait, max_wait)(func_with_rl)
        
        # Apply circuit breaker
        func_with_cb = with_circuit_breaker(circuit_breaker)(func_with_retry)
        
        return func_with_cb
    
    return decorator


# Export decorators and classes
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
