"""Circuit breaker for fault tolerance."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog

from src.config import config
from src.models import CircuitBreakerOpenError, CircuitBreakerState

logger = structlog.get_logger()


class CircuitBreaker:
    """
    Circuit breaker for database connections and external services.
    Implements CLOSED -> OPEN -> HALF_OPEN state machine.
    """

    def __init__(
        self,
        failure_threshold: int = None,
        timeout_seconds: int = None,
        half_open_attempts: int = None,
    ):
        self.failure_threshold = failure_threshold or config.circuit_breaker_failure_threshold
        self.timeout_seconds = timeout_seconds or config.circuit_breaker_timeout_seconds
        self.half_open_attempts = half_open_attempts or config.circuit_breaker_half_open_attempts

        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time: datetime | None = None

    async def execute(
        self,
        operation: Callable,
        fallback: Callable | None = None,
    ) -> Any:
        """
        Execute operation with circuit breaker protection.

        State transitions:
        - CLOSED → OPEN: After failure_threshold consecutive failures
        - OPEN → HALF_OPEN: After timeout_seconds elapsed
        - HALF_OPEN → CLOSED: After half_open_attempts successes
        - HALF_OPEN → OPEN: On any failure

        Args:
            operation: Primary operation to execute
            fallback: Optional fallback operation

        Returns:
            Operation result or fallback result
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("circuit_breaker_half_open")
            else:
                if fallback:
                    logger.warning("circuit_breaker_open_using_fallback")
                    return await fallback()
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = await operation()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()

            # If circuit just opened and fallback exists, use it
            if self.state == CircuitBreakerState.OPEN and fallback:
                logger.warning(
                    "circuit_breaker_opened_using_fallback",
                    error=str(e),
                )
                return await fallback()

            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if not self.last_failure_time:
            return True

        elapsed = datetime.utcnow() - self.last_failure_time
        return elapsed.total_seconds() >= self.timeout_seconds

    def _on_success(self) -> None:
        """Handle successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_attempts:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("circuit_breaker_closed")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.last_failure_time = datetime.utcnow()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.success_count = 0
            logger.warning("circuit_breaker_reopened")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold,
                )

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.state

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("circuit_breaker_manually_reset")
