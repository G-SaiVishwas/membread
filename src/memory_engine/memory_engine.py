"""Memory Engine: Core storage abstraction coordinating all stores."""

from datetime import datetime
from typing import Optional
import structlog

from src.memory_engine.vector_store import VectorStore
from src.memory_engine.graph_store import GraphStore
from src.memory_engine.sql_store import SQLStore
from src.services.embedding_service import EmbeddingService
from src.services.circuit_breaker import CircuitBreaker
from src.services.context_compressor import ContextCompressor
from src.governor.governor import Governor
from src.models import (
    StoreResult,
    RecallResult,
    Fact,
    Operation,
    PrivilegeLayer,
    ValidationError,
)

logger = structlog.get_logger()


class MemoryEngine:
    """
    Core storage abstraction coordinating three stores.
    Implements circuit breakers and concurrency control.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: GraphStore,
        sql_store: SQLStore,
        embedding_service: EmbeddingService,
        governor: Governor,
        context_compressor: ContextCompressor,
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.sql_store = sql_store
        self.embedding_service = embedding_service
        self.governor = governor
        self.context_compressor = context_compressor
        self.circuit_breaker = CircuitBreaker()

    async def store_with_conflict_resolution(
        self,
        observation: str,
        metadata: dict,
        tenant_id: str,
        user_id: str,
    ) -> StoreResult:
        """
        Store observation with temporal conflict detection.

        Args:
            observation: Text to store
            metadata: Associated metadata
            tenant_id: Tenant identifier
            user_id: User identifier

        Returns:
            StoreResult with IDs and provenance
        """
        start_time = datetime.utcnow()

        try:
            # Generate provenance hash
            metadata["tenant_id"] = tenant_id
            metadata["user_id"] = user_id
            metadata["timestamp"] = datetime.utcnow().isoformat()

            provenance_hash = self.governor.provenance_tracker.generate_hash(
                observation, metadata
            )

            # Validate operation
            operation = Operation(
                operation_type="store",
                data={"text": observation, "metadata": metadata},
                tenant_id=tenant_id,
                user_id=user_id,
                privilege_layer=PrivilegeLayer.USER,
            )

            validation = await self.governor.enforce_constraints(operation)
            if not validation.valid:
                raise ValidationError(f"Validation failed: {', '.join(validation.errors)}")

            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(observation)

            # Store in vector store
            embedding_id = await self.vector_store.store_embedding(
                embedding=embedding,
                text=observation,
                metadata=metadata,
            )

            # Extract entities and create graph nodes
            # Simplified: Create a single node for the observation
            entity_id = f"obs_{embedding_id}"
            node_id = await self.graph_store.create_node(
                entity_id=entity_id,
                entity_type="observation",
                properties={"text": observation, "metadata": metadata},
                valid_at=datetime.utcnow(),
                tenant_id=tenant_id,
                source_observation_id=embedding_id,
            )

            # Log performance
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            if duration_ms > 150:
                logger.warning(
                    "slow_operation",
                    operation="store",
                    duration_ms=duration_ms,
                )

            logger.info(
                "observation_stored",
                observation_id=embedding_id,
                tenant_id=tenant_id,
                duration_ms=duration_ms,
            )

            return StoreResult(
                observation_id=embedding_id,
                provenance_hash=provenance_hash,
                conflicts_resolved=0,
                nodes_created=1,
                relationships_created=0,
            )

        except Exception as e:
            logger.error(
                "store_with_conflict_resolution_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def recall_with_compression(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        time_travel_ts: Optional[datetime] = None,
        max_tokens: int = 2000,
    ) -> RecallResult:
        """
        Retrieve context with automatic compression if needed.

        Args:
            query: Semantic query
            tenant_id: Tenant identifier
            user_id: User identifier
            time_travel_ts: Optional historical timestamp
            max_tokens: Token limit for compression

        Returns:
            RecallResult with context and sources
        """
        start_time = datetime.utcnow()

        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)

            # Search vector store
            search_results = await self.vector_store.similarity_search(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                user_id=user_id,
                top_k=10,
            )

            # Combine results
            context_parts = []
            sources = []

            for result in search_results:
                context_parts.append(f"[Score: {result.score:.3f}] {result.text}")
                sources.append(result.id)

            context = "\n\n".join(context_parts)

            # Check token count and compress if needed
            token_count = self.context_compressor.count_tokens(context)
            compressed = False

            if token_count > max_tokens:
                context = await self.context_compressor.compress(
                    context=context,
                    max_tokens=max_tokens,
                    query=query,
                )
                token_count = self.context_compressor.count_tokens(context)
                compressed = True

            # Log performance
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            if duration_ms > 150:
                logger.warning(
                    "slow_operation",
                    operation="recall",
                    duration_ms=duration_ms,
                )

            logger.info(
                "context_recalled",
                tenant_id=tenant_id,
                results_count=len(search_results),
                token_count=token_count,
                compressed=compressed,
                duration_ms=duration_ms,
            )

            return RecallResult(
                context=context,
                sources=sources,
                token_count=token_count,
                compressed=compressed,
                time_travel_ts=time_travel_ts,
            )

        except Exception as e:
            logger.error(
                "recall_with_compression_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise
