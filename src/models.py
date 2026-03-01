"""Core data models for Membread."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4


class PrivilegeLayer(Enum):
    """Three-tier privilege system for memory operations."""

    IMMUTABLE = 0  # System constraints, cannot be modified
    ADMIN = 1  # Tenant admin operations, require audit logging
    USER = 2  # Regular user operations


@dataclass
class Observation:
    """Unstructured observation with temporal metadata and provenance."""

    id: str
    text: str
    tenant_id: str
    user_id: str
    timestamp: datetime
    metadata: dict[str, Any]
    provenance_hash: str


@dataclass
class Fact:
    """Structured fact extracted from observations."""

    id: str
    entity_id: str
    entity_type: str
    properties: dict[str, Any]
    valid_at: datetime
    invalid_at: Optional[datetime]
    tenant_id: str
    source_observation_id: str


@dataclass
class GraphNode:
    """Temporal graph node representing an entity version."""

    id: str
    entity_id: str
    entity_type: str
    properties: dict[str, Any]
    valid_at: datetime
    invalid_at: Optional[datetime]
    tenant_id: str
    source_observation_id: Optional[str] = None


@dataclass
class GraphRelationship:
    """Temporal graph relationship (edge) between nodes."""

    id: str
    from_node_id: str
    to_node_id: str
    relationship_type: str
    properties: dict[str, Any]
    valid_at: datetime
    invalid_at: Optional[datetime] = None


@dataclass
class UserProfile:
    """Structured user profile with preferences."""

    tenant_id: str
    user_id: str
    display_name: str
    preferences: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class StoreResult:
    """Result from storing an observation."""

    observation_id: str
    provenance_hash: str
    conflicts_resolved: int = 0
    nodes_created: int = 0
    relationships_created: int = 0


@dataclass
class RecallResult:
    """Result from recalling context."""

    context: str
    sources: list[str]
    token_count: int
    compressed: bool = False
    time_travel_ts: Optional[datetime] = None


@dataclass
class ProfileResult:
    """Result from getting user profile."""

    tenant_id: str
    user_id: str
    display_name: str
    preferences: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class ConflictResolution:
    """Actions to resolve temporal conflicts."""

    nodes_to_invalidate: list[str]
    nodes_to_create: list[GraphNode]
    relationships_to_create: list[GraphRelationship]
    reason: str


@dataclass
class SearchResult:
    """Result from vector similarity search."""

    id: str
    text: str
    metadata: dict[str, Any]
    score: float
    fallback: bool = False


@dataclass
class GraphPath:
    """Path through graph for multi-hop traversal."""

    entities: list[GraphNode]
    relationships: list[GraphRelationship]
    total_hops: int


@dataclass
class Operation:
    """Memory operation to be routed."""

    operation_type: str  # "store", "recall", "update", "delete"
    data: dict[str, Any]
    tenant_id: str
    user_id: str
    privilege_layer: PrivilegeLayer
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RoutingDecision:
    """Decision on which stores to use for an operation."""

    target_stores: list[str]  # ["vector", "graph", "sql"]
    execution_order: list[str]
    reason: str


@dataclass
class ValidationResult:
    """Result of constraint validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Constraint:
    """Layer 0 immutable constraint."""

    id: str
    constraint_type: str
    rule: dict[str, Any]
    description: Optional[str] = None


class CircuitBreakerState(Enum):
    """Circuit breaker states for fault tolerance."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, using fallback
    HALF_OPEN = "half_open"  # Testing if service recovered


# Exception classes
class MembreadError(Exception):
    """Base exception for Membread."""

    pass


class AuthenticationError(MembreadError):
    """Authentication failed."""

    pass


class AuthorizationError(MembreadError):
    """Authorization failed (privilege violation)."""

    pass


class ValidationError(MembreadError):
    """Validation failed (injection detected, invalid format)."""

    pass


class ConflictError(MembreadError):
    """Conflict detected (optimistic concurrency failure)."""

    pass


class PerformanceError(MembreadError):
    """Performance threshold exceeded."""

    pass


class InfrastructureError(MembreadError):
    """Infrastructure failure (database, API)."""

    pass


class CircuitBreakerOpenError(InfrastructureError):
    """Circuit breaker is open."""

    pass


class RetryableError(MembreadError):
    """Error that can be retried."""

    pass


class MaxRetriesExceededError(MembreadError):
    """Maximum retry attempts exceeded."""

    pass


# ── Temporal / Graphiti models ──────────────────────────────────────────────
# Canonical definitions live in src.memory_engine.engines.graphiti_engine
# to avoid circular imports.  Re-export here for convenience.

from src.memory_engine.engines.graphiti_engine import (
    TemporalSearchResult,
    EntityVersion,
)


@dataclass
class CapturePayload:
    """Payload received from the browser extension /capture endpoint."""

    conversation: list[dict[str, Any]]
    source: str = "browser_extension"
    url: Optional[str] = None
    title: Optional[str] = None
    captured_at: Optional[datetime] = None
