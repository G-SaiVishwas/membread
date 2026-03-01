"""Pluggable memory engine backends.

The default backend is the Graphiti bi-temporal knowledge graph engine which
provides real-time incremental updates, hybrid retrieval (embedding + BM25 +
graph traversal), and point-in-time historical queries.
"""

from src.memory_engine.engines.graphiti_engine import GraphitiEngine

__all__ = ["GraphitiEngine"]
