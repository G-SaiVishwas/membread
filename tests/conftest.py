# pyright: off
"""Shared fixtures for the Membread test suite."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Config fixture — patches env before any Config() is created
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_env(monkeypatch):
    """Provide sane defaults so Config() never raises during tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-unit-tests")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("ENABLE_TEMPORAL", "true")
    monkeypatch.setenv("GRAPHITI_BACKEND", "memory")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "")


@pytest.fixture
def jwt_auth():
    """Return a JWTAuthenticator configured for tests."""
    from src.auth.jwt_authenticator import JWTAuthenticator
    return JWTAuthenticator(secret="test-jwt-secret", algorithm="HS256")


@pytest.fixture
def jwt_token(jwt_auth):
    """Generate a valid JWT token for test requests."""
    return jwt_auth.generate_token(tenant_id="test-tenant", user_id="test-user")


# ---------------------------------------------------------------------------
# Mock stores
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.store_embedding = AsyncMock(return_value="emb-001")
    store.similarity_search = AsyncMock(return_value=[])
    store.list_embeddings = AsyncMock(return_value=[])
    store.get_embedding_count = AsyncMock(return_value=0)
    return store


@pytest.fixture
def mock_graph_store():
    store = AsyncMock()
    store.create_node = AsyncMock(return_value="node-001")
    return store


@pytest.fixture
def mock_sql_store():
    store = AsyncMock()
    store.get_profile = AsyncMock(return_value=None)
    store.create_profile = AsyncMock()
    return store


@pytest.fixture
def mock_embedding_service():
    svc = AsyncMock()
    svc.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    return svc


@pytest.fixture
def mock_context_compressor():
    comp = MagicMock()
    comp.count_tokens = MagicMock(return_value=100)
    comp.compress = AsyncMock(return_value="compressed context")
    return comp


@pytest.fixture
def mock_governor():
    from src.models import ValidationResult
    gov = AsyncMock()
    gov.initialize = AsyncMock()
    gov.provenance_tracker = MagicMock()
    gov.provenance_tracker.generate_hash = MagicMock(return_value="hash-abc")
    gov.enforce_constraints = AsyncMock(return_value=ValidationResult(valid=True))
    return gov


@pytest.fixture
def memory_engine(
    mock_vector_store,
    mock_graph_store,
    mock_sql_store,
    mock_embedding_service,
    mock_governor,
    mock_context_compressor,
):
    """A MemoryEngine wired with mocks — no database required."""
    from src.memory_engine.memory_engine import MemoryEngine

    return MemoryEngine(
        vector_store=mock_vector_store,
        graph_store=mock_graph_store,
        sql_store=mock_sql_store,
        embedding_service=mock_embedding_service,
        governor=mock_governor,
        context_compressor=mock_context_compressor,
        graphiti_engine=None,
    )
