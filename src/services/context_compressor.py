"""Context compression using mini-LLM."""

import structlog
import tiktoken
from openai import AsyncOpenAI

from src.config import config

logger = structlog.get_logger()


class ContextCompressor:
    """
    Compress retrieved context using a mini-LLM to prevent token bloat.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or config.openai_api_key
        self.model = config.openai_compression_model
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.encoding = tiktoken.encoding_for_model("gpt-4")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    async def compress(
        self,
        context: str,
        max_tokens: int,
        query: str = "",
    ) -> str:
        """
        Compress context to fit within token limit.

        Args:
            context: Context to compress
            max_tokens: Maximum token count
            query: Optional query for context-aware compression

        Returns:
            Compressed context
        """
        current_tokens = self.count_tokens(context)

        if current_tokens <= max_tokens:
            return context

        try:
            # Use mini-LLM to summarize
            prompt = f"""Compress the following context while preserving key information.
Target: {max_tokens} tokens maximum.
{f'Focus on information relevant to: {query}' if query else ''}

Context:
{context}

Compressed version:"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3,
            )

            compressed = response.choices[0].message.content or ""
            compressed_tokens = self.count_tokens(compressed)

            logger.info(
                "context_compressed",
                original_tokens=current_tokens,
                compressed_tokens=compressed_tokens,
                compression_ratio=compressed_tokens / current_tokens if current_tokens > 0 else 0,
            )

            return compressed

        except Exception as e:
            logger.error(
                "context_compression_failed",
                original_tokens=current_tokens,
                error=str(e),
            )
            # Fallback: truncate
            return self._truncate_to_tokens(context, max_tokens)

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Fallback: Simple truncation to token limit."""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)
