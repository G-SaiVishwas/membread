"""Graph Store: Temporal graph database for entity relationships."""

from datetime import datetime
from uuid import UUID

import asyncpg
import structlog

from src.models import GraphNode, GraphRelationship

logger = structlog.get_logger()


class GraphStore:
    """
    Temporal graph database for entity relationships.
    Maintains valid_at/invalid_at timestamps for time-travel.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _set_tenant_context(self, conn: asyncpg.Connection, tenant_id: str) -> None:
        """Set tenant context for Row-Level Security."""
        await conn.execute("SELECT set_config('app.tenant_id', $1, false)", tenant_id)

    async def create_node(
        self,
        entity_id: str,
        entity_type: str,
        properties: dict,
        valid_at: datetime,
        tenant_id: str,
        source_observation_id: str | None = None,
    ) -> str:
        """
        Create a new graph node with temporal validity.

        Args:
            entity_id: Unique entity identifier
            entity_type: Type classification
            properties: Entity attributes
            valid_at: Timestamp when this version becomes valid
            tenant_id: Tenant identifier
            source_observation_id: Optional source observation

        Returns:
            Node ID
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                node_id = await conn.fetchval(
                    """
                    INSERT INTO graph_nodes
                    (tenant_id, entity_id, entity_type, properties, valid_at, source_observation_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    UUID(tenant_id),
                    entity_id,
                    entity_type,
                    properties,
                    valid_at,
                    UUID(source_observation_id) if source_observation_id else None,
                )

                logger.info(
                    "graph_store_node_created",
                    node_id=str(node_id),
                    entity_id=entity_id,
                    entity_type=entity_type,
                    tenant_id=tenant_id,
                )

                return str(node_id)

        except Exception as e:
            logger.error(
                "graph_store_create_node_failed",
                entity_id=entity_id,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def invalidate_node(
        self,
        node_id: str,
        invalid_at: datetime,
        reason: str,
    ) -> None:
        """
        Mark a node as invalid at a specific timestamp.

        Args:
            node_id: Node to invalidate
            invalid_at: Timestamp when node becomes invalid
            reason: Explanation for invalidation
        """
        try:
            async with self.pool.acquire() as conn:
                # Get tenant_id from node for RLS
                tenant_id = await conn.fetchval(
                    "SELECT tenant_id FROM graph_nodes WHERE id = $1",
                    UUID(node_id),
                )

                if not tenant_id:
                    raise ValueError(f"Node {node_id} not found")

                await self._set_tenant_context(conn, str(tenant_id))

                await conn.execute(
                    """
                    UPDATE graph_nodes
                    SET invalid_at = $1
                    WHERE id = $2 AND invalid_at IS NULL
                    """,
                    invalid_at,
                    UUID(node_id),
                )

                logger.info(
                    "graph_store_node_invalidated",
                    node_id=node_id,
                    invalid_at=invalid_at.isoformat(),
                    reason=reason,
                )

        except Exception as e:
            logger.error(
                "graph_store_invalidate_node_failed",
                node_id=node_id,
                error=str(e),
            )
            raise

    async def create_relationship(
        self,
        from_node: str,
        to_node: str,
        relationship_type: str,
        properties: dict,
        valid_at: datetime,
    ) -> str:
        """
        Create temporal relationship between nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            relationship_type: Relationship classification
            properties: Relationship attributes
            valid_at: Timestamp when relationship becomes valid

        Returns:
            Relationship ID
        """
        try:
            async with self.pool.acquire() as conn:
                rel_id = await conn.fetchval(
                    """
                    INSERT INTO graph_relationships
                    (from_node_id, to_node_id, relationship_type, properties, valid_at)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id
                    """,
                    UUID(from_node),
                    UUID(to_node),
                    relationship_type,
                    properties,
                    valid_at,
                )

                logger.info(
                    "graph_store_relationship_created",
                    rel_id=str(rel_id),
                    from_node=from_node,
                    to_node=to_node,
                    relationship_type=relationship_type,
                )

                return str(rel_id)

        except Exception as e:
            logger.error(
                "graph_store_create_relationship_failed",
                from_node=from_node,
                to_node=to_node,
                error=str(e),
            )
            raise

    async def query_at_timestamp(
        self,
        entity_id: str,
        timestamp: datetime,
        tenant_id: str,
    ) -> GraphNode | None:
        """
        Retrieve entity state at a specific historical timestamp.

        Args:
            entity_id: Entity to query
            timestamp: Historical timestamp
            tenant_id: Tenant identifier

        Returns:
            GraphNode if valid at timestamp, None otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                row = await conn.fetchrow(
                    """
                    SELECT id, entity_id, entity_type, properties,
                           valid_at, invalid_at, tenant_id, source_observation_id
                    FROM graph_nodes
                    WHERE tenant_id = $1
                      AND entity_id = $2
                      AND valid_at <= $3
                      AND (invalid_at IS NULL OR invalid_at > $3)
                    ORDER BY valid_at DESC
                    LIMIT 1
                    """,
                    UUID(tenant_id),
                    entity_id,
                    timestamp,
                )

                if not row:
                    return None

                return GraphNode(
                    id=str(row["id"]),
                    entity_id=row["entity_id"],
                    entity_type=row["entity_type"],
                    properties=row["properties"],
                    valid_at=row["valid_at"],
                    invalid_at=row["invalid_at"],
                    tenant_id=str(row["tenant_id"]),
                    source_observation_id=str(row["source_observation_id"])
                    if row["source_observation_id"]
                    else None,
                )

        except Exception as e:
            logger.error(
                "graph_store_query_at_timestamp_failed",
                entity_id=entity_id,
                timestamp=timestamp.isoformat(),
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def get_causal_chain(
        self,
        entity_id: str,
        tenant_id: str,
    ) -> list[GraphNode]:
        """
        Retrieve complete evolution history of an entity.

        Args:
            entity_id: Entity to trace
            tenant_id: Tenant identifier

        Returns:
            List of nodes ordered by valid_at timestamp
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                # Use the recursive CTE function from schema
                rows = await conn.fetch(
                    "SELECT * FROM get_causal_chain($1, $2)",
                    UUID(tenant_id),
                    entity_id,
                )

                nodes = [
                    GraphNode(
                        id=str(row["node_id"]),
                        entity_id=row["entity_id"],
                        entity_type=row["entity_type"],
                        properties=row["properties"],
                        valid_at=row["valid_at"],
                        invalid_at=row["invalid_at"],
                        tenant_id=tenant_id,
                    )
                    for row in rows
                ]

                logger.info(
                    "graph_store_causal_chain_retrieved",
                    entity_id=entity_id,
                    tenant_id=tenant_id,
                    chain_length=len(nodes),
                )

                return nodes

        except Exception as e:
            logger.error(
                "graph_store_get_causal_chain_failed",
                entity_id=entity_id,
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def get_current_nodes(
        self,
        tenant_id: str,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[GraphNode]:
        """
        Get currently valid nodes (invalid_at IS NULL).

        Args:
            tenant_id: Tenant identifier
            entity_type: Optional entity type filter
            limit: Maximum number of nodes

        Returns:
            List of currently valid nodes
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                if entity_type:
                    rows = await conn.fetch(
                        """
                        SELECT id, entity_id, entity_type, properties,
                               valid_at, invalid_at, tenant_id, source_observation_id
                        FROM graph_nodes
                        WHERE tenant_id = $1
                          AND entity_type = $2
                          AND invalid_at IS NULL
                        ORDER BY valid_at DESC
                        LIMIT $3
                        """,
                        UUID(tenant_id),
                        entity_type,
                        limit,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, entity_id, entity_type, properties,
                               valid_at, invalid_at, tenant_id, source_observation_id
                        FROM graph_nodes
                        WHERE tenant_id = $1
                          AND invalid_at IS NULL
                        ORDER BY valid_at DESC
                        LIMIT $2
                        """,
                        UUID(tenant_id),
                        limit,
                    )

                return [
                    GraphNode(
                        id=str(row["id"]),
                        entity_id=row["entity_id"],
                        entity_type=row["entity_type"],
                        properties=row["properties"],
                        valid_at=row["valid_at"],
                        invalid_at=row["invalid_at"],
                        tenant_id=str(row["tenant_id"]),
                        source_observation_id=str(row["source_observation_id"])
                        if row["source_observation_id"]
                        else None,
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(
                "graph_store_get_current_nodes_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise

    async def get_relationships(
        self,
        node_id: str,
        direction: str = "outgoing",  # "outgoing", "incoming", "both"
        relationship_type: str | None = None,
    ) -> list[GraphRelationship]:
        """
        Get relationships for a node.

        Args:
            node_id: Node to get relationships for
            direction: "outgoing", "incoming", or "both"
            relationship_type: Optional relationship type filter

        Returns:
            List of relationships
        """
        try:
            async with self.pool.acquire() as conn:
                if direction == "outgoing":
                    where_clause = "from_node_id = $1"
                elif direction == "incoming":
                    where_clause = "to_node_id = $1"
                else:  # both
                    where_clause = "(from_node_id = $1 OR to_node_id = $1)"

                query = f"""
                    SELECT id, from_node_id, to_node_id, relationship_type,
                           properties, valid_at, invalid_at
                    FROM graph_relationships
                    WHERE {where_clause}
                      AND invalid_at IS NULL
                """
                params = [UUID(node_id)]

                if relationship_type:
                    query += " AND relationship_type = $2"
                    params.append(relationship_type)

                rows = await conn.fetch(query, *params)

                return [
                    GraphRelationship(
                        id=str(row["id"]),
                        from_node_id=str(row["from_node_id"]),
                        to_node_id=str(row["to_node_id"]),
                        relationship_type=row["relationship_type"],
                        properties=row["properties"],
                        valid_at=row["valid_at"],
                        invalid_at=row["invalid_at"],
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(
                "graph_store_get_relationships_failed",
                node_id=node_id,
                error=str(e),
            )
            raise
