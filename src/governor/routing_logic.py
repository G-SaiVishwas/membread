"""Routing logic for memory operations."""

import structlog

from src.models import Operation, RoutingDecision, PrivilegeLayer

logger = structlog.get_logger()


class RoutingLogic:
    """
    Deterministic routing for memory operations.
    """

    async def route_operation(
        self,
        operation: Operation,
        privilege_layer: PrivilegeLayer,
    ) -> RoutingDecision:
        """
        Determine which stores to use for an operation.

        Args:
            operation: The memory operation to route
            privilege_layer: Security privilege level

        Returns:
            RoutingDecision specifying target stores and order
        """
        target_stores = []
        execution_order = []

        if operation.operation_type == "store":
            # Store operations use all three stores
            target_stores = ["vector", "graph", "sql"]
            execution_order = ["sql", "vector", "graph"]  # SQL first for profile
            reason = "Store operation requires all stores"

        elif operation.operation_type == "recall":
            # Recall uses vector + graph
            target_stores = ["vector", "graph"]
            execution_order = ["vector", "graph"]
            reason = "Recall operation uses vector and graph stores"

        elif operation.operation_type == "update":
            # Update uses SQL + graph
            target_stores = ["sql", "graph"]
            execution_order = ["sql", "graph"]
            reason = "Update operation uses SQL and graph stores"

        elif operation.operation_type == "delete":
            # Delete uses all stores
            target_stores = ["vector", "graph", "sql"]
            execution_order = ["graph", "vector", "sql"]
            reason = "Delete operation requires all stores"

        else:
            target_stores = []
            execution_order = []
            reason = f"Unknown operation type: {operation.operation_type}"

        logger.info(
            "operation_routed",
            operation_type=operation.operation_type,
            target_stores=target_stores,
            privilege=privilege_layer.name,
        )

        return RoutingDecision(
            target_stores=target_stores,
            execution_order=execution_order,
            reason=reason,
        )
