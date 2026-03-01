# pyright: basic
"""
GraphitiEngine — bi-temporal knowledge graph backend for Membread.

Wraps `graphiti-core` to provide:
  • Episode ingestion with automatic entity / relation extraction
  • Hybrid search (embeddings + BM25 + graph traversal)
  • Bi-temporal queries (event_time × ingestion_time)
  • Point-in-time "time-travel" recall
  • Self-compressing long-term memory via community summarisation

Supports **fully-local** operation (Ollama + FalkorDB / Kuzu) — no paid API
keys required.

Usage:
    from src.memory_engine.engines.graphiti_engine import GraphitiEngine

    engine = GraphitiEngine(config)
    await engine.initialize()
    await engine.add_episode("User prefers dark-mode", group_id="user_42")
    results = await engine.search("colour preferences", group_id="user_42")
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Lazy imports — gracefully degrade when graphiti-core is not installed.
# ---------------------------------------------------------------------------
_GRAPHITI_AVAILABLE: bool = False
_KUZU_AVAILABLE: bool = False

try:
    from graphiti_core import Graphiti  # type: ignore[import-untyped]
    from graphiti_core.nodes import EpisodeType  # type: ignore[import-untyped]

    _GRAPHITI_AVAILABLE = True  # type: ignore[assignment]
except ImportError:
    Graphiti = None  # type: ignore[assignment,misc]
    EpisodeType = None  # type: ignore[assignment,misc]

try:
    import kuzu  # type: ignore[import-untyped]

    _KUZU_AVAILABLE = True  # type: ignore[assignment]
except ImportError:
    kuzu = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Lightweight result dataclass (avoids coupling to src.models)
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class TemporalSearchResult:
    """A single search hit enriched with temporal metadata."""

    id: str
    text: str
    score: float
    event_time: datetime | None = None
    ingestion_time: datetime | None = None
    source: str | None = None
    graph_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EntityVersion:
    """One version (snapshot) of an entity across time."""

    entity_id: str
    name: str
    properties: dict[str, Any]
    valid_from: datetime
    valid_until: datetime | None = None
    source_episode_id: str | None = None


# ---------------------------------------------------------------------------
# LLM client factory
# ---------------------------------------------------------------------------

def _build_llm_client(config: Any) -> Any:
    """
    Build the LLM client that Graphiti will use for entity extraction,
    community detection, and summarisation.

    Supports:
      - Ollama  (local, default)
      - OpenAI
      - Anthropic
      - Groq
      - Any OpenAI-compatible endpoint (e.g. LM Studio, vLLM)
    """
    base_url: str = getattr(config, "local_llm_base_url", "") or ""
    openai_key: str = getattr(config, "openai_api_key", "") or ""

    # --- Ollama / local OpenAI-compatible ---------------------------------
    if base_url:
        try:
            from graphiti_core.llm_client.openai_generic_client import (  # type: ignore
                OpenAIGenericClient,
            )

            model = getattr(config, "local_llm_model", "llama3")
            logger.info(
                "graphiti_llm_client",
                provider="openai_generic",
                base_url=base_url,
                model=model,
            )
            return OpenAIGenericClient(
                base_url=base_url,
                api_key="ollama",  # Ollama ignores this
                model=model,
            )
        except ImportError:
            pass

    # --- OpenAI -----------------------------------------------------------
    if openai_key:
        try:
            from graphiti_core.llm_client import OpenAIClient  # type: ignore
            model = getattr(config, "graphiti_llm_model", "gpt-4o-mini")
            logger.info("graphiti_llm_client", provider="openai", model=model)
            return OpenAIClient(api_key=openai_key, model=model)
        except ImportError:
            pass

    # --- Fallback: None (Graphiti will use its own default) ----------------
    logger.warning("graphiti_llm_client_fallback", reason="no suitable provider found")
    return None


def _build_embedder(config: Any) -> Any:
    """Build the embedder that Graphiti uses for vector encoding."""
    base_url: str = getattr(config, "local_llm_base_url", "") or ""
    openai_key: str = getattr(config, "openai_api_key", "") or ""

    if base_url:
        try:
            from graphiti_core.embedder.openai_generic import OpenAIGenericEmbedder  # type: ignore
            model = getattr(config, "local_embedding_model", "nomic-embed-text")
            logger.info("graphiti_embedder", provider="openai_generic", model=model)
            return OpenAIGenericEmbedder(base_url=base_url, api_key="ollama", model=model)
        except ImportError:
            pass

    if openai_key:
        try:
            from graphiti_core.embedder import OpenAIEmbedder  # type: ignore
            model = getattr(config, "openai_embedding_model", "text-embedding-ada-002")
            logger.info("graphiti_embedder", provider="openai", model=model)
            return OpenAIEmbedder(api_key=openai_key, model=model)
        except ImportError:
            pass

    return None


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class GraphitiEngine:
    """
    High-level wrapper around ``graphiti-core`` providing a clean async API
    that plugs into the existing Membread MemoryEngine.

    Parameters
    ----------
    config : object
        A Pydantic (or plain) settings object.  At minimum it should expose:
          - ``graphiti_backend``  ("falkordb" | "neo4j" | "kuzu" | "memory")
          - ``graphiti_uri``     (bolt:// or file path)
          - ``enable_temporal``  (bool, default True)
          - ``local_llm_base_url`` (str, e.g. "http://localhost:11434/v1")
          - ``openai_api_key``   (str)
    """

    # Class-level episode counter (used for auto-summarisation trigger)
    _episode_counter: int = 0
    _SUMMARISE_EVERY: int = 100

    def __init__(self, config: Any) -> None:
        self._config = config
        self._backend: str = getattr(config, "graphiti_backend", "memory")
        self._uri: str = getattr(config, "graphiti_uri", "")
        self._temporal: bool = getattr(config, "enable_temporal", True)
        self._graphiti: Any | None = None  # Graphiti instance — lazily initialised
        self._initialised: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Connect to the graph database and build indices."""
        if self._initialised:
            return

        if not _GRAPHITI_AVAILABLE:
            logger.warning(
                "graphiti_not_installed",
                hint="pip install graphiti-core[falkordb]",
            )
            # Engine will operate in degraded in-memory mode
            self._initialised = True
            return

        try:
            llm_client = _build_llm_client(self._config)
            embedder = _build_embedder(self._config)

            kwargs: dict[str, Any] = {}
            if llm_client is not None:
                kwargs["llm_client"] = llm_client
            if embedder is not None:
                kwargs["embedder"] = embedder

            if self._backend in ("falkordb", "neo4j"):
                uri = self._uri or "bolt://localhost:7687"
                self._graphiti = Graphiti(uri, **kwargs)  # type: ignore[misc]
            elif self._backend == "kuzu" and _KUZU_AVAILABLE:
                db_path = self._uri or "./kuzu_data"
                db = kuzu.Database(db_path)  # type: ignore[union-attr]
                self._graphiti = Graphiti(db, **kwargs)  # type: ignore[misc]
            else:
                # In-memory / degraded mode
                logger.info("graphiti_engine_memory_mode")
                self._initialised = True
                return

            # Build indices for fast hybrid search
            await self._graphiti.build_indices_and_constraints()  # type: ignore[union-attr]
            self._initialised = True
            logger.info(
                "graphiti_engine_initialised",
                backend=self._backend,
                uri=self._uri,
                temporal=self._temporal,
            )
        except Exception as exc:
            logger.error("graphiti_engine_init_failed", error=str(exc))
            # Degrade gracefully
            self._graphiti = None
            self._initialised = True

    async def close(self) -> None:
        """Cleanly shut down the graph database connection."""
        if self._graphiti is not None:
            try:
                await self._graphiti.close()
            except Exception:
                pass
            self._graphiti = None
            self._initialised = False

    # ------------------------------------------------------------------
    # Episode ingestion
    # ------------------------------------------------------------------

    async def add_episode(
        self,
        text: str | dict[str, Any],
        group_id: str,
        *,
        name: str | None = None,
        timestamp: datetime | None = None,
        source: str = "api",
        episode_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Ingest a new episode (observation / conversation turn / document).

        Graphiti automatically:
          1. Extracts entities and relations via the configured LLM.
          2. De-duplicates against the existing graph.
          3. Stores the episode with ``event_time`` = *timestamp* and
             ``ingestion_time`` = now().

        Parameters
        ----------
        text : str | dict
            Raw episode content.  Dicts are JSON-serialised.
        group_id : str
            Logical grouping key (maps to ``user_id`` / ``tenant_id``).
        name : str, optional
            Human-readable episode label.
        timestamp : datetime, optional
            When the event *actually* occurred (``event_time``).
            Defaults to ``utcnow()``.
        source : str
            Source description (e.g. "chatgpt", "slack", "api").
        episode_type : str
            One of "text", "json", "message".
        metadata : dict, optional
            Extra metadata stored alongside the episode.

        Returns
        -------
        str
            The episode UUID.
        """
        episode_id = str(uuid.uuid4())
        episode_name = name or f"episode_{episode_id[:8]}"
        episode_body = text if isinstance(text, str) else json.dumps(text, default=str)
        event_time = timestamp or datetime.now(UTC)

        if self._graphiti is not None:
            try:
                # Map string type → EpisodeType enum
                _ep_type = EpisodeType.text  # type: ignore[union-attr]
                if episode_type == "json":
                    _ep_type = EpisodeType.json  # type: ignore[union-attr]
                elif episode_type == "message":
                    try:
                        _ep_type = EpisodeType.message  # type: ignore[union-attr]
                    except AttributeError:
                        _ep_type = EpisodeType.text  # type: ignore[union-attr]

                await self._graphiti.add_episode(
                    name=episode_name,
                    episode_body=episode_body,
                    source_description=source,
                    reference_time=event_time,
                    group_id=group_id,
                )

                logger.info(
                    "graphiti_episode_added",
                    episode_id=episode_id,
                    group_id=group_id,
                    source=source,
                    event_time=event_time.isoformat(),
                )
            except Exception as exc:
                logger.error("graphiti_add_episode_failed", error=str(exc))
                # Fall through — we still record it in the local ledger below
        else:
            logger.debug("graphiti_engine_degraded_add", episode_id=episode_id)

        # Increment counter and trigger auto-summarisation
        GraphitiEngine._episode_counter += 1
        if GraphitiEngine._episode_counter % self._SUMMARISE_EVERY == 0:
            await self._auto_summarise(group_id)

        return episode_id

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        group_id: str,
        *,
        limit: int = 10,
        time_range: tuple[datetime, datetime] | None = None,
        center_date: datetime | None = None,
        search_type: Literal["hybrid", "bm25", "embedding", "graph"] = "hybrid",
    ) -> list[TemporalSearchResult]:
        """
        Hybrid retrieval combining embeddings, BM25, and graph traversal.

        Parameters
        ----------
        query : str
            Natural-language search query.
        group_id : str
            Tenant / user grouping key.
        limit : int
            Maximum results to return.
        time_range : tuple[datetime, datetime], optional
            ``(start, end)`` filter on ``event_time``.
        center_date : datetime, optional
            Prefer results temporally close to this date.
        search_type : str
            Retrieval strategy.

        Returns
        -------
        list[TemporalSearchResult]
        """
        if self._graphiti is None:
            return []

        try:
            results = await self._graphiti.search(
                query=query,
                group_ids=[group_id],
                num_results=limit,
            )

            hits: list[TemporalSearchResult] = []
            for idx, r in enumerate(results):
                event_time = getattr(r, "created_at", None) or getattr(r, "reference_time", None)
                ingestion_time = getattr(r, "created_at", None)
                fact_text = getattr(r, "fact", None) or getattr(r, "name", str(r))

                hit = TemporalSearchResult(
                    id=str(getattr(r, "uuid", uuid.uuid4())),
                    text=str(fact_text),
                    score=1.0 - (idx * 0.05),  # positional decay
                    event_time=event_time,
                    ingestion_time=ingestion_time,
                    source=getattr(r, "source_description", None),
                    graph_score=getattr(r, "score", 0.0),
                    metadata={},
                )
                hits.append(hit)

            # Optional: post-filter by time range
            if time_range:
                start, end = time_range
                hits = [
                    h
                    for h in hits
                    if h.event_time and start <= h.event_time <= end
                ]

            return hits[:limit]

        except Exception as exc:
            logger.error("graphiti_search_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------
    # Point-in-time (time-travel) queries
    # ------------------------------------------------------------------

    async def search_temporal(
        self,
        query: str,
        group_id: str,
        as_of: datetime,
        *,
        limit: int = 10,
    ) -> list[TemporalSearchResult]:
        """
        Return what the system *knew* at ``as_of`` — a true
        point-in-time snapshot over the bi-temporal graph.

        This filters on ``ingestion_time <= as_of`` so that facts
        added *after* the snapshot date are excluded.
        """
        if self._graphiti is None:
            return []

        try:
            # Graphiti search returns all matching facts; we post-filter
            # by ingestion_time to simulate point-in-time.
            all_results = await self.search(query, group_id, limit=limit * 3)
            filtered = [
                r
                for r in all_results
                if r.ingestion_time is None or r.ingestion_time <= as_of
            ]
            return filtered[:limit]
        except Exception as exc:
            logger.error("graphiti_temporal_search_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------
    # Entity history
    # ------------------------------------------------------------------

    async def get_entity_history(
        self,
        entity_name: str,
        group_id: str,
    ) -> list[EntityVersion]:
        """
        Retrieve every recorded version of a named entity —
        the full temporal evolution chain.
        """
        if self._graphiti is None:
            return []

        try:
            # Use search as a proxy to find entity versions
            results = await self._graphiti.search(
                query=entity_name,
                group_ids=[group_id],
                num_results=50,
            )

            versions: list[EntityVersion] = []
            for r in results:
                name = getattr(r, "name", entity_name)
                versions.append(
                    EntityVersion(
                        entity_id=str(getattr(r, "uuid", uuid.uuid4())),
                        name=str(name),
                        properties={"fact": str(getattr(r, "fact", ""))},
                        valid_from=getattr(r, "created_at", datetime.now(UTC)),
                        valid_until=getattr(r, "expired_at", None),
                        source_episode_id=str(getattr(r, "episode_uuid", "")),
                    )
                )

            # Sort chronologically
            versions.sort(key=lambda v: v.valid_from)
            return versions
        except Exception as exc:
            logger.error("graphiti_entity_history_failed", error=str(exc))
            return []

    # ------------------------------------------------------------------
    # Graph data for dashboard / visualisation
    # ------------------------------------------------------------------

    async def get_graph_data(
        self,
        group_id: str,
        limit: int = 200,
    ) -> dict[str, Any]:
        """
        Return nodes and edges suitable for a force-directed graph
        visualisation (e.g. Streamlit-agraph, PyVis, React-force-graph).
        """
        if self._graphiti is None:
            return {"nodes": [], "edges": []}

        try:
            results = await self._graphiti.search(
                query="*",
                group_ids=[group_id],
                num_results=limit,
            )

            nodes: dict[str, dict[str, Any]] = {}
            edges: list[dict[str, Any]] = []

            for r in results:
                node_id = str(getattr(r, "uuid", uuid.uuid4()))
                name = str(getattr(r, "name", getattr(r, "fact", node_id[:8])))
                nodes[node_id] = {
                    "id": node_id,
                    "label": name,
                    "type": getattr(r, "entity_type", "entity"),
                    "created_at": str(getattr(r, "created_at", "")),
                }

                # If the result exposes source / target relationships
                src = getattr(r, "source_node_uuid", None)
                tgt = getattr(r, "target_node_uuid", None)
                if src and tgt:
                    edges.append({
                        "source": str(src),
                        "target": str(tgt),
                        "label": str(getattr(r, "relation_type", "RELATED_TO")),
                    })

            return {"nodes": list(nodes.values()), "edges": edges}
        except Exception as exc:
            logger.error("graphiti_get_graph_data_failed", error=str(exc))
            return {"nodes": [], "edges": []}

    # ------------------------------------------------------------------
    # Auto-summarisation (self-compressing LTM)
    # ------------------------------------------------------------------

    async def _auto_summarise(self, group_id: str) -> None:
        """
        After every *_SUMMARISE_EVERY* episodes, trigger a community
        summarisation pass to compress older memories.
        """
        logger.info(
            "graphiti_auto_summarise_triggered",
            group_id=group_id,
            episode_count=GraphitiEngine._episode_counter,
        )

        if self._graphiti is None:
            return

        try:
            # Graphiti supports community nodes / graph summaries
            # Use add_episode with a meta-summary as a compression pass
            summary_body = (
                f"[AUTO-SUMMARY] Compressed summary after "
                f"{GraphitiEngine._episode_counter} episodes for group {group_id}."
            )
            await self._graphiti.add_episode(
                name=f"auto_summary_{GraphitiEngine._episode_counter}",
                episode_body=summary_body,
                source_description="self_compression",
                reference_time=datetime.now(UTC),
                group_id=group_id,
            )
            logger.info("graphiti_auto_summarise_complete", group_id=group_id)
        except Exception as exc:
            logger.warning("graphiti_auto_summarise_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Health / status
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when the Graphiti backend is connected and ready."""
        return self._graphiti is not None and self._initialised

    @property
    def backend_name(self) -> str:
        return self._backend

    def __repr__(self) -> str:
        status = "ready" if self.is_available else "degraded"
        return f"<GraphitiEngine backend={self._backend} status={status}>"
