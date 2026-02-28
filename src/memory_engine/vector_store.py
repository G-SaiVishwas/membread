"""Vector Store: Semantic embedding storage using PostgreSQL pgvector."""

import asyncpg
from typing import Optional
from uuid import UUID, uuid4
import structlog

from src.models import SearchResult

logger = structlog.get_logger()


class VectorStore:
    """
    Semantic embedding storage using PostgreSQL pgvector.
    Supports metadata filtering for multi-tenancy.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _set_tenant_context(self, conn: asyncpg.Connection, tenant_id: str) -> None:
        """Set tenant context for Row-Level Security."""
        await conn.execute("SELECT set_config('app.tenant_id', $1, false)", tenant_id)

    async def store_embedding(
        self,
        embedding: list[float],
        text: str,
        metadata: dict,
    ) -> str:
        """
        Store embedding with metadata.

        Args:
            embedding: Vector embedding (1536 dimensions for ada-002)
            text: Original text
            metadata: Must include tenant_id, user_id, timestamp

        Returns:
            Embedding ID
        """
        tenant_id = metadata.get("tenant_id")
        user_id = metadata.get("user_id")

        if not tenant_id or not user_id:
            raise ValueError("metadata must include tenant_id and user_id")

        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                embedding_id = await conn.fetchval(
                    """
                    INSERT INTO embeddings (tenant_id, user_id, embedding, text, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    UUID(tenant_id),
                    UUID(user_id),
                    embedding,
                    text,
                    metadata,
                )

                logger.info(
                    "vector_store_embedding_stored",
                    embedding_id=str(embedding_id),
                    tenant_id=tenant_id,
                    text_length=len(text),
                )

                return str(embedding_id)

        except Exception as e:
            logger.error(
                "vector_store_store_embedding_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def similarity_search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        user_id: Optional[str] = None,
        top_k: int = 10,
        metadata_filter: Optional[dict] = None,
    ) -> list[SearchResult]:
        """
        Perform semantic similarity search with filtering.

        Args:
            query_embedding: Query vector
            tenant_id: Required tenant filter
            user_id: Optional user filter
            top_k: Number of results
            metadata_filter: Additional metadata constraints

        Returns:
            List of search results with scores
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                # Build query with optional filters
                query = """
                    SELECT id, text, metadata, 
                           1 - (embedding <=> $1) as score
                    FROM embeddings
                    WHERE tenant_id = $2
                """
                params = [query_embedding, UUID(tenant_id)]
                param_idx = 3

                if user_id:
                    query += f" AND user_id = ${param_idx}"
                    params.append(UUID(user_id))
                    param_idx += 1

                # Add metadata filters
                if metadata_filter:
                    for key, value in metadata_filter.items():
                        query += f" AND metadata->>'{key}' = ${param_idx}"
                        params.append(str(value))
                        param_idx += 1

                query += f" ORDER BY embedding <=> $1 LIMIT ${param_idx}"
                params.append(top_k)

                rows = await conn.fetch(query, *params)

                results = [
                    SearchResult(
                        id=str(row["id"]),
                        text=row["text"],
                        metadata=row["metadata"],
                        score=float(row["score"]),
                        fallback=False,
                    )
                    for row in rows
                ]

                logger.info(
                    "vector_store_similarity_search_completed",
                    tenant_id=tenant_id,
                    results_count=len(results),
                    top_k=top_k,
                )

                return results

        except Exception as e:
            logger.error(
                "vector_store_similarity_search_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def delete_embedding(self, embedding_id: str, tenant_id: str) -> bool:
        """
        Delete an embedding.

        Args:
            embedding_id: Embedding to delete
            tenant_id: Tenant identifier

        Returns:
            True if deleted, False if not found
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                result = await conn.execute(
                    """
                    DELETE FROM embeddings
                    WHERE id = $1 AND tenant_id = $2
                    """,
                    UUID(embedding_id),
                    UUID(tenant_id),
                )

                deleted = result == "DELETE 1"

                if deleted:
                    logger.info(
                        "vector_store_embedding_deleted",
                        embedding_id=embedding_id,
                        tenant_id=tenant_id,
                    )

                return deleted

        except Exception as e:
            logger.error(
                "vector_store_delete_embedding_failed",
                embedding_id=embedding_id,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def get_embedding_count(self, tenant_id: str, user_id: Optional[str] = None) -> int:
        """
        Get count of embeddings for a tenant/user.

        Args:
            tenant_id: Tenant identifier
            user_id: Optional user filter

        Returns:
            Count of embeddings
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                if user_id:
                    count = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM embeddings
                        WHERE tenant_id = $1 AND user_id = $2
                        """,
                        UUID(tenant_id),
                        UUID(user_id),
                    )
                else:
                    count = await conn.fetchval(
                        """
                        SELECT COUNT(*) FROM embeddings
                        WHERE tenant_id = $1
                        """,
                        UUID(tenant_id),
                    )

                return count

        except Exception as e:
            logger.error(
                "vector_store_get_count_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise
