"""Embedding service for generating semantic vectors."""

import asyncio
from typing import List
import structlog
from openai import AsyncOpenAI

from src.config import config
from src.models import RetryableError, MaxRetriesExceededError

logger = structlog.get_logger()


class EmbeddingService:
    """
    Async client for OpenAI embeddings API with retry logic.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or config.openai_api_key
        self.model = config.openai_embedding_model
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1536 dimensions for ada-002)
        """
        try:
            response = await self._retry_with_backoff(
                lambda: self.client.embeddings.create(
                    model=self.model,
                    input=text,
                )
            )

            embedding = response.data[0].embedding

            logger.info(
                "embedding_generated",
                model=self.model,
                text_length=len(text),
                embedding_dim=len(embedding),
            )

            return embedding

        except Exception as e:
            logger.error(
                "embedding_generation_failed",
                text_length=len(text),
                error=str(e),
            )
            raise

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            response = await self._retry_with_backoff(
                lambda: self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
            )

            embeddings = [item.embedding for item in response.data]

            logger.info(
                "batch_embeddings_generated",
                model=self.model,
                batch_size=len(texts),
                embedding_dim=len(embeddings[0]) if embeddings else 0,
            )

            return embeddings

        except Exception as e:
            logger.error(
                "batch_embedding_generation_failed",
                batch_size=len(texts),
                error=str(e),
            )
            raise

    async def _retry_with_backoff(
        self,
        operation,
        max_attempts: int = None,
        base_delay: float = None,
        max_delay: float = None,
    ):
        """
        Retry operation with exponential backoff.

        Args:
            operation: Async operation to retry
            max_attempts: Maximum retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds

        Returns:
            Operation result
        """
        max_attempts = max_attempts or config.max_retry_attempts
        base_delay = base_delay or config.retry_base_delay_seconds
        max_delay = max_delay or config.retry_max_delay_seconds

        for attempt in range(max_attempts):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise MaxRetriesExceededError(
                        f"Failed after {max_attempts} attempts: {str(e)}"
                    )

                # Check if error is retryable
                error_str = str(e).lower()
                if "rate limit" in error_str or "timeout" in error_str or "503" in error_str:
                    delay = min(base_delay * (2**attempt), max_delay)
                    logger.warning(
                        "retrying_operation",
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error
                    raise

        raise MaxRetriesExceededError(f"Failed after {max_attempts} attempts")
