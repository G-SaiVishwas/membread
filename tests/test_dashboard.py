"""Smoke tests for the Streamlit dashboard module.

These tests import the dashboard helpers and verify they produce the
correct HTTP calls / data shapes without actually launching Streamlit
or requiring a running API server.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

streamlit = pytest.importorskip("streamlit", reason="streamlit not installed")


# ── patch ``requests`` before importing the dashboard ─────────────

@pytest.fixture(autouse=True)
def _mock_requests(monkeypatch):
    """Prevent real HTTP calls from the dashboard helpers."""
    monkeypatch.setattr("requests.get", MagicMock(return_value=MagicMock(
        json=MagicMock(return_value={"status": "healthy", "version": "0.1.0"}),
        status_code=200,
    )))
    monkeypatch.setattr("requests.post", MagicMock(return_value=MagicMock(
        json=MagicMock(return_value={"results": [], "context": "", "versions": []}),
        status_code=200,
        raise_for_status=MagicMock(),
    )))


class TestDashboardHelpers:
    """Test the API-calling helper functions."""

    def test_api_health(self):
        from ui.dashboard import api_health
        result = api_health()
        assert result["status"] == "healthy"

    def test_api_memory_count(self):
        from ui.dashboard import api_memory_count
        # The mock returns {"status": ...} which has no "count" key → default 0
        assert api_memory_count() == 0

    def test_headers_empty_without_token(self, monkeypatch):
        monkeypatch.setattr("ui.dashboard.TOKEN", "")
        from ui.dashboard import _headers
        assert _headers() == {}

    def test_headers_with_token(self, monkeypatch):
        monkeypatch.setattr("ui.dashboard.TOKEN", "my-jwt")
        from ui.dashboard import _headers
        h = _headers()
        assert h["Authorization"] == "Bearer my-jwt"


class TestDashboardImport:
    """Verify the dashboard module is importable and has expected pages."""

    def test_module_importable(self):
        import ui.dashboard as dash
        assert hasattr(dash, "main")
        assert hasattr(dash, "page_overview")
        assert hasattr(dash, "page_temporal_search")
        assert hasattr(dash, "page_entity_history")
        assert hasattr(dash, "page_graph")
