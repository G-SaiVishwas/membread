# pyright: off
"""Unit tests for the GraphitiEngine wrapper.

These tests exercise the GraphitiEngine *without* requiring a running
FalkorDB or Graphiti-core installation.  All graph-database interactions
are mocked so the test suite runs in CI with zero external dependencies.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory_engine.engines.graphiti_engine import (
    EntityVersion,
    GraphitiEngine,
    TemporalSearchResult,
    _build_embedder,
    _build_llm_client,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides):
    """Create a minimal config-like object."""
    defaults = {
        "graphiti_backend": "memory",
        "graphiti_uri": "",
        "enable_temporal": True,
        "local_llm_base_url": "",
        "openai_api_key": "sk-test",
        "local_llm_model": "llama3",
        "local_embedding_model": "nomic-embed-text",
        "graphiti_llm_model": "gpt-4o-mini",
        "openai_embedding_model": "text-embedding-ada-002",
        "summarise_every_n": 100,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


# ══════════════════════════════════════════════════════════════════════
# Initialisation
# ══════════════════════════════════════════════════════════════════════


class TestGraphitiEngineInit:
    """Initialisation and lifecycle."""

    @pytest.mark.asyncio
    async def test_init_memory_mode(self):
        """Engine should start in degraded mode when backend='memory'."""
        engine = GraphitiEngine(_make_config(graphiti_backend="memory"))
        await engine.initialize()

        assert engine._initialised is True
        assert engine._graphiti is None  # no real connection
        assert engine.backend_name == "memory"

    @pytest.mark.asyncio
    async def test_is_available_false_in_memory_mode(self):
        engine = GraphitiEngine(_make_config(graphiti_backend="memory"))
        await engine.initialize()
        # In memory mode _graphiti is None → is_available = False
        assert engine.is_available is False

    @pytest.mark.asyncio
    async def test_double_init_is_idempotent(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()
        await engine.initialize()  # should not raise
        assert engine._initialised is True

    @pytest.mark.asyncio
    async def test_close_is_safe_in_memory_mode(self):
        """close() should not raise when no graph connection exists."""
        engine = GraphitiEngine(_make_config())
        await engine.initialize()
        await engine.close()  # no-op in memory mode
        # Still in initialised state because there was nothing to close
        assert engine._graphiti is None

    def test_repr_degraded(self):
        engine = GraphitiEngine(_make_config())
        assert "degraded" in repr(engine)


# ══════════════════════════════════════════════════════════════════════
# Episode ingestion
# ══════════════════════════════════════════════════════════════════════


class TestAddEpisode:
    """add_episode() behaviour."""

    @pytest.mark.asyncio
    async def test_add_episode_returns_uuid(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        episode_id = await engine.add_episode(
            text="Alice works at Google",
            group_id="tenant-1",
        )

        # Should be a valid UUID-4 string
        assert uuid.UUID(episode_id).version == 4

    @pytest.mark.asyncio
    async def test_add_episode_dict_body(self):
        """Dict bodies should be JSON-serialised without error."""
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        episode_id = await engine.add_episode(
            text={"role": "user", "content": "hello"},
            group_id="g1",
        )
        assert episode_id  # non-empty

    @pytest.mark.asyncio
    async def test_add_episode_with_graphiti(self):
        """When _graphiti is set AND EpisodeType is available, it delegates."""
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        mock_graphiti = AsyncMock()
        engine._graphiti = mock_graphiti

        # Also need EpisodeType to be non-None for the call path
        import src.memory_engine.engines.graphiti_engine as ge
        original_ep_type = ge.EpisodeType

        # Create a minimal EpisodeType mock
        ep_mock = MagicMock()
        ep_mock.text = "text"
        ep_mock.json = "json"
        ep_mock.message = "message"
        ge.EpisodeType = ep_mock

        try:
            ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
            await engine.add_episode(
                text="Bob switched to Rust",
                group_id="t1",
                timestamp=ts,
                source="test",
            )

            mock_graphiti.add_episode.assert_awaited_once()
            call_kwargs = mock_graphiti.add_episode.call_args
            assert call_kwargs.kwargs["group_id"] == "t1"
        finally:
            ge.EpisodeType = original_ep_type


# ══════════════════════════════════════════════════════════════════════
# Search
# ══════════════════════════════════════════════════════════════════════


class _FakeSearchResult:
    """Mimics a Graphiti search result object."""
    def __init__(self, fact, created_at=None, uuid_=None):
        self.fact = fact
        self.name = fact
        self.created_at = created_at or datetime.now(timezone.utc)
        self.reference_time = self.created_at
        self.uuid = uuid_ or uuid.uuid4()
        self.source_description = "test"
        self.score = 0.9


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_empty_when_degraded(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        results = await engine.search("hello", "g1")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_temporal_results(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            _FakeSearchResult("Alice works at Google"),
            _FakeSearchResult("Alice moved to Meta"),
        ])
        engine._graphiti = mock_graphiti

        hits = await engine.search("Alice employer", "g1", limit=5)

        assert len(hits) == 2
        assert isinstance(hits[0], TemporalSearchResult)
        assert "Google" in hits[0].text

    @pytest.mark.asyncio
    async def test_search_time_range_filter(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        t3 = datetime(2024, 12, 1, tzinfo=timezone.utc)

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            _FakeSearchResult("early", created_at=t1),
            _FakeSearchResult("middle", created_at=t2),
            _FakeSearchResult("late", created_at=t3),
        ])
        engine._graphiti = mock_graphiti

        hits = await engine.search(
            "all", "g1",
            time_range=(datetime(2024, 5, 1, tzinfo=timezone.utc),
                        datetime(2024, 7, 1, tzinfo=timezone.utc)),
        )

        assert len(hits) == 1
        assert "middle" in hits[0].text


# ══════════════════════════════════════════════════════════════════════
# Temporal search (point-in-time)
# ══════════════════════════════════════════════════════════════════════


class TestTemporalSearch:
    @pytest.mark.asyncio
    async def test_temporal_search_degraded(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        results = await engine.search_temporal(
            "q", "g1", as_of=datetime.now(timezone.utc)
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_temporal_search_filters_by_ingestion_time(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        t_early = datetime(2024, 3, 1, tzinfo=timezone.utc)
        t_late = datetime(2024, 9, 1, tzinfo=timezone.utc)

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            _FakeSearchResult("old fact", created_at=t_early),
            _FakeSearchResult("new fact", created_at=t_late),
        ])
        engine._graphiti = mock_graphiti

        as_of = datetime(2024, 6, 1, tzinfo=timezone.utc)
        hits = await engine.search_temporal("q", "g1", as_of=as_of)

        # Only the old fact should survive the ingestion-time filter
        assert len(hits) == 1
        assert "old" in hits[0].text


# ══════════════════════════════════════════════════════════════════════
# Entity history
# ══════════════════════════════════════════════════════════════════════


class TestEntityHistory:
    @pytest.mark.asyncio
    async def test_entity_history_degraded(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()
        assert await engine.get_entity_history("Alice", "g1") == []

    @pytest.mark.asyncio
    async def test_entity_history_returns_versions(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            _FakeSearchResult("Alice v1", created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)),
            _FakeSearchResult("Alice v2", created_at=datetime(2024, 6, 1, tzinfo=timezone.utc)),
        ])
        engine._graphiti = mock_graphiti

        versions = await engine.get_entity_history("Alice", "g1")
        assert len(versions) == 2
        assert isinstance(versions[0], EntityVersion)
        assert versions[0].valid_from < versions[1].valid_from


# ══════════════════════════════════════════════════════════════════════
# Graph data (dashboard visualisation)
# ══════════════════════════════════════════════════════════════════════


class TestGraphData:
    @pytest.mark.asyncio
    async def test_graph_data_degraded(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()
        data = await engine.get_graph_data("g1")
        assert data == {"nodes": [], "edges": []}

    @pytest.mark.asyncio
    async def test_graph_data_returns_nodes_and_edges(self):
        engine = GraphitiEngine(_make_config())
        await engine.initialize()

        fake = _FakeSearchResult("Node A")
        fake.source_node_uuid = uuid.uuid4()
        fake.target_node_uuid = uuid.uuid4()
        fake.entity_type = "person"
        fake.relation_type = "WORKS_AT"

        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[fake])
        engine._graphiti = mock_graphiti

        data = await engine.get_graph_data("g1", limit=10)
        assert len(data["nodes"]) >= 1
        assert len(data["edges"]) >= 1


# ══════════════════════════════════════════════════════════════════════
# LLM / embedder factory helpers
# ══════════════════════════════════════════════════════════════════════


class TestFactoryHelpers:
    def test_build_llm_client_returns_none_without_providers(self):
        cfg = _make_config(local_llm_base_url="", openai_api_key="")
        result = _build_llm_client(cfg)
        assert result is None

    def test_build_embedder_returns_none_without_providers(self):
        cfg = _make_config(local_llm_base_url="", openai_api_key="")
        result = _build_embedder(cfg)
        assert result is None


# ══════════════════════════════════════════════════════════════════════
# Auto-summarisation
# ══════════════════════════════════════════════════════════════════════


class TestAutoSummarise:
    @pytest.mark.asyncio
    async def test_auto_summarise_triggers_at_threshold(self):
        engine = GraphitiEngine(_make_config(summarise_every_n=3))
        await engine.initialize()
        engine._SUMMARISE_EVERY = 3
        GraphitiEngine._episode_counter = 0

        # Add 3 episodes — the third should trigger summarisation
        for i in range(3):
            await engine.add_episode(text=f"ep {i}", group_id="g1")

        assert GraphitiEngine._episode_counter == 3

        # Reset for other tests
        GraphitiEngine._episode_counter = 0
