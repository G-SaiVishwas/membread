"""Lattice crawler for multi-hop graph traversal."""

from typing import List, Optional, Set
import structlog

from src.models import GraphPath, GraphNode, GraphRelationship
from src.memory_engine.graph_store import GraphStore

logger = structlog.get_logger()


class LatticeCrawler:
    """
    Multi-hop reasoning across graph relationships using BFS/DFS.
    """

    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store

    async def multi_hop_traverse(
        self,
        start_entity: str,
        relationship_types: List[str],
        max_hops: int,
        tenant_id: str,
    ) -> List[GraphPath]:
        """
        Perform multi-hop reasoning across graph relationships.

        Args:
            start_entity: Starting entity for traversal
            relationship_types: Types of relationships to follow
            max_hops: Maximum traversal depth
            tenant_id: Tenant identifier

        Returns:
            List of graph paths with entities and relationships
        """
        paths: List[GraphPath] = []
        visited: Set[str] = set()

        # Get starting nodes
        start_nodes = await self.graph_store.get_current_nodes(
            tenant_id=tenant_id,
            limit=1000,
        )

        start_nodes = [n for n in start_nodes if n.entity_id == start_entity]

        if not start_nodes:
            return []

        # BFS traversal
        for start_node in start_nodes:
            await self._bfs_traverse(
                node=start_node,
                relationship_types=relationship_types,
                max_hops=max_hops,
                current_hop=0,
                current_path_entities=[start_node],
                current_path_rels=[],
                visited=visited,
                paths=paths,
            )

        logger.info(
            "multi_hop_traversal_completed",
            start_entity=start_entity,
            max_hops=max_hops,
            paths_found=len(paths),
        )

        return paths

    async def _bfs_traverse(
        self,
        node: GraphNode,
        relationship_types: List[str],
        max_hops: int,
        current_hop: int,
        current_path_entities: List[GraphNode],
        current_path_rels: List[GraphRelationship],
        visited: Set[str],
        paths: List[GraphPath],
    ) -> None:
        """Recursive BFS traversal."""
        if current_hop >= max_hops:
            # Save path
            paths.append(
                GraphPath(
                    entities=current_path_entities.copy(),
                    relationships=current_path_rels.copy(),
                    total_hops=current_hop,
                )
            )
            return

        visited.add(node.id)

        # Get outgoing relationships
        relationships = await self.graph_store.get_relationships(
            node_id=node.id,
            direction="outgoing",
        )

        # Filter by relationship types
        if relationship_types:
            relationships = [
                r for r in relationships if r.relationship_type in relationship_types
            ]

        for rel in relationships:
            if rel.to_node_id not in visited:
                # Get target node
                target_nodes = await self.graph_store.get_current_nodes(
                    tenant_id=node.tenant_id,
                    limit=1000,
                )
                target_node = next((n for n in target_nodes if n.id == rel.to_node_id), None)

                if target_node:
                    await self._bfs_traverse(
                        node=target_node,
                        relationship_types=relationship_types,
                        max_hops=max_hops,
                        current_hop=current_hop + 1,
                        current_path_entities=current_path_entities + [target_node],
                        current_path_rels=current_path_rels + [rel],
                        visited=visited,
                        paths=paths,
                    )
