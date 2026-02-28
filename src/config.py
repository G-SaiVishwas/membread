"""Configuration management for ChronosMCP."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """ChronosMCP configuration from environment variables."""

    # Database
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/chronos"
        )
    )
    database_pool_min_size: int = Field(
        default_factory=lambda: int(os.getenv("DATABASE_POOL_MIN_SIZE", "5"))
    )
    database_pool_max_size: int = Field(
        default_factory=lambda: int(os.getenv("DATABASE_POOL_MAX_SIZE", "20"))
    )

    # OpenAI
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_embedding_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")
    )
    openai_compression_model: str = Field(
        default_factory=lambda: os.getenv("OPENAI_COMPRESSION_MODEL", "gpt-4o-mini")
    )

    # JWT Authentication
    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-secret-key"))
    jwt_algorithm: str = Field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))

    # Performance
    response_timeout_ms: int = Field(
        default_factory=lambda: int(os.getenv("RESPONSE_TIMEOUT_MS", "200"))
    )
    slow_operation_threshold_ms: int = Field(
        default_factory=lambda: int(os.getenv("SLOW_OPERATION_THRESHOLD_MS", "150"))
    )
    max_context_tokens: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "2000"))
    )

    # Circuit Breaker
    circuit_breaker_failure_threshold: int = Field(
        default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
    )
    circuit_breaker_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_TIMEOUT_SECONDS", "60"))
    )
    circuit_breaker_half_open_attempts: int = Field(
        default_factory=lambda: int(os.getenv("CIRCUIT_BREAKER_HALF_OPEN_ATTEMPTS", "3"))
    )

    # Retry Logic
    max_retry_attempts: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    )
    retry_base_delay_seconds: float = Field(
        default_factory=lambda: float(os.getenv("RETRY_BASE_DELAY_SECONDS", "0.1"))
    )
    retry_max_delay_seconds: float = Field(
        default_factory=lambda: float(os.getenv("RETRY_MAX_DELAY_SECONDS", "2.0"))
    )

    # Logging
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_format: str = Field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))

    # SQLite Fallback
    sqlite_fallback_path: str = Field(
        default_factory=lambda: os.getenv("SQLITE_FALLBACK_PATH", "./fallback")
    )

    def validate_required(self) -> None:
        """Validate that required configuration is present."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if not self.jwt_secret or self.jwt_secret == "dev-secret-key":
            import warnings

            warnings.warn(
                "Using default JWT_SECRET. Set JWT_SECRET environment variable for production."
            )


# Global configuration instance
config = Config()
