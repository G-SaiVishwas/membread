"""Main Governor class integrating all components."""

import asyncpg
import structlog

from src.governor.conflict_resolver import ConflictResolver
from src.governor.constraint_enforcer import ConstraintEnforcer
from src.governor.lattice_crawler import LatticeCrawler
from src.governor.provenance_tracker import ProvenanceTracker
from src.governor.routing_logic import RoutingLogic
from src.memory_engine.graph_store import GraphStore
from src.models import Operation, RoutingDecision, ValidationResult

logger = structlog.get_logger()


class Governor:
    """
    Deterministic routing and conflict resolution engine.
    Integrates all governor components.
    """

    def __init__(self, pool: asyncpg.Pool, graph_store: GraphStore):
        self.conflict_resolver = ConflictResolver(graph_store)
        self.constraint_enforcer = ConstraintEnforcer(pool)
        self.lattice_crawler = LatticeCrawler(graph_store)
        self.routing_logic = RoutingLogic()
        self.provenance_tracker = ProvenanceTracker()

    async def initialize(self) -> None:
        """Initialize governor components."""
        await self.constraint_enforcer.load_constraints()
        logger.info("governor_initialized")

    async def route_operation(
        self,
        operation: Operation,
    ) -> RoutingDecision:
        """Route operation to appropriate stores."""
        return await self.routing_logic.route_operation(
            operation=operation,
            privilege_layer=operation.privilege_layer,
        )

    async def enforce_constraints(
        self,
        operation: Operation,
    ) -> ValidationResult:
        """Validate operation against constraints."""
        return await self.constraint_enforcer.enforce_constraints(operation)
