"""Integration tests for the FastAPI HTTP endpoints.

Uses FastAPI's TestClient to exercise all temporal endpoints
(``/api/memory/search/temporal``, ``/api/memory/entity/history``,
``/api/memory/graph``, ``/api/capture``) plus the core store/recall
flow — all without a real database.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.server import create_app
from src.auth.jwt_authenticator import JWTAuthenticator
from src.memory_engine.engines.graphiti_engine import (
    EntityVersion,
    TemporalSearchResult,
)
from src.models import RecallResult, StoreResult


# ───────────────────────────────────────────────────────────────────
# Fixtures
# ───────────────────────────────────────────────────────────────────


@pytest.fixture
def auth():
    return JWTAuthenticator(secret="test-jwt-secret", algorithm="HS256")


@pytest.fixture
def token(auth):
    return auth.generate_token(tenant_id="t1", user_id="u1")


@pytest.fixture
def mock_engine():
    """MemoryEngine mock with temporal methods."""
    engine = AsyncMock()

    # Core
    engine.store_with_conflict_resolution = AsyncMock(
        return_value=StoreResult(
            observation_id="obs-001",
            provenance_hash="hash-abc",
            conflicts_resolved=0,
            nodes_created=1,
        )
    )
    engine.recall_with_compression = AsyncMock(
        return_value=RecallResult(
            context="Some recalled context",
            sources=["src-1"],
            token_count=42,
            compressed=False,
        )
    )

    # Vector store helpers
    engine.vector_store = AsyncMock()
    engine.vector_store.list_embeddings = AsyncMock(return_value=[])
    engine.vector_store.get_embedding_count = AsyncMock(return_value=7)

    # Temporal
    engine.search_temporal = AsyncMock(return_value=[
        TemporalSearchResult(
            id="hit-1",
            text="Alice works at Google",
            score=0.95,
            event_time=datetime(2024, 1, 15, tzinfo=timezone.utc),
            ingestion_time=datetime(2024, 1, 16, tzinfo=timezone.utc),
            source="api",
        ),
    ])
    engine.get_entity_history = AsyncMock(return_value=[
        EntityVersion(
            entity_id="ent-1",
            name="Alice",
            properties={"employer": "Google"},
            valid_from=datetime(2024, 1, 15, tzinfo=timezone.utc),
        ),
    ])
    engine.get_graph_data = AsyncMock(return_value={
        "nodes": [{"id": "n1", "label": "Alice", "type": "person"}],
        "edges": [{"source": "n1", "target": "n2", "label": "WORKS_AT"}],
    })

    return engine


@pytest.fixture
def mock_sql_store():
    return AsyncMock()


@pytest.fixture
def client(mock_engine, mock_sql_store, auth):
    app = create_app(mock_engine, mock_sql_store, auth)
    return TestClient(app)


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ───────────────────────────────────────────────────────────────────
# Health & root
# ───────────────────────────────────────────────────────────────────


class TestHealthEndpoints:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["version"] == "0.1.0"


# ───────────────────────────────────────────────────────────────────
# Auth
# ───────────────────────────────────────────────────────────────────


class TestAuth:
    def test_missing_token_returns_401(self, client):
        r = client.post("/api/memory/store", json={"observation": "hi"})
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        r = client.post(
            "/api/memory/store",
            json={"observation": "hi"},
            headers={"Authorization": "Bearer bad-token"},
        )
        assert r.status_code == 401

    def test_generate_token(self, client):
        r = client.post("/api/auth/token", json={"tenant_id": "t1", "user_id": "u1"})
        assert r.status_code == 200
        assert "token" in r.json()


# ───────────────────────────────────────────────────────────────────
# Core endpoints
# ───────────────────────────────────────────────────────────────────


class TestCoreEndpoints:
    def test_store(self, client, token):
        r = client.post(
            "/api/memory/store",
            json={"observation": "hello world", "metadata": {"tag": "test"}},
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["observation_id"] == "obs-001"
        assert body["message"] == "Observation stored successfully"

    def test_recall(self, client, token):
        r = client.post(
            "/api/memory/recall",
            json={"query": "what happened?"},
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        assert r.json()["context"] == "Some recalled context"

    def test_memory_count(self, client, token):
        r = client.get("/api/memory/count", headers=_auth_headers(token))
        assert r.status_code == 200
        assert r.json()["count"] == 7

    def test_memory_list(self, client, token):
        r = client.get("/api/memory/list", headers=_auth_headers(token))
        assert r.status_code == 200
        assert r.json()["items"] == []


# ───────────────────────────────────────────────────────────────────
# Temporal endpoints
# ───────────────────────────────────────────────────────────────────


class TestTemporalEndpoints:
    def test_temporal_search(self, client, token, mock_engine):
        r = client.post(
            "/api/memory/search/temporal",
            json={"query": "Where did Alice work?", "limit": 5},
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["results"]) == 1
        assert "Google" in body["results"][0]["text"]

    def test_temporal_search_with_as_of(self, client, token):
        r = client.post(
            "/api/memory/search/temporal",
            json={"query": "Where did Alice work?", "as_of": "2024-06-01T00:00:00"},
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["as_of"] == "2024-06-01T00:00:00"

    def test_entity_history(self, client, token):
        r = client.post(
            "/api/memory/entity/history",
            json={"entity_name": "Alice"},
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["entity_name"] == "Alice"
        assert len(body["versions"]) == 1
        assert body["versions"][0]["name"] == "Alice"

    def test_graph_data(self, client, token):
        r = client.get(
            "/api/memory/graph",
            params={"limit": 100},
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["nodes"]) == 1
        assert len(body["edges"]) == 1


# ───────────────────────────────────────────────────────────────────
# Capture endpoint (browser extension)
# ───────────────────────────────────────────────────────────────────


class TestCaptureEndpoint:
    def test_capture_ingests_messages(self, client, token, mock_engine):
        r = client.post(
            "/api/capture",
            json={
                "conversation": [
                    {"role": "user", "content": "What is the weather?"},
                    {"role": "assistant", "content": "It's sunny."},
                ],
                "source": "chatgpt",
                "url": "https://chat.openai.com/c/123",
                "title": "Weather chat",
            },
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["episodes_ingested"] == 2
        assert "chatgpt" in body["message"]

    def test_capture_skips_empty_content(self, client, token, mock_engine):
        r = client.post(
            "/api/capture",
            json={
                "conversation": [
                    {"role": "user", "content": ""},
                    {"role": "assistant", "content": "answer"},
                ],
                "source": "claude",
            },
            headers=_auth_headers(token),
        )
        assert r.status_code == 200
        assert r.json()["episodes_ingested"] == 1

    def test_capture_requires_auth(self, client):
        r = client.post(
            "/api/capture",
            json={"conversation": [], "source": "test"},
        )
        assert r.status_code == 401
