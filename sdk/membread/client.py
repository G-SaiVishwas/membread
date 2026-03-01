"""
Membread Python Client — core HTTP client for the Membread API.

All integrations (LangChain, CrewAI, AutoGen, OpenAI) use this client
under the hood. It stores/recalls from one central knowledge base.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Optional

import httpx


class MembreadClient:
    """Low-level client for the Membread memory API.

    Args:
        api_url: Base URL of the Membread API (default: http://localhost:8000).
        token: JWT bearer token for authentication.
        timeout: Request timeout in seconds (default: 30).
        source: Default source label for stored memories.
        agent_id: Default agent identifier.

    Example::

        client = MembreadClient(token="eyJ...")
        client.store("User prefers dark mode")
        ctx = client.recall("user preferences")
        print(ctx["context"])
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        token: str = "",
        timeout: float = 30.0,
        source: str = "sdk",
        agent_id: str = "default",
    ):
        self.api_url = api_url.rstrip("/")
        self.source = source
        self.agent_id = agent_id
        self._client = httpx.Client(
            base_url=self.api_url,
            headers={
                "Authorization": f"Bearer {token}" if token else "",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        # Simple dedup cache (hash -> timestamp)
        self._recent_hashes: dict[str, float] = {}
        self._dedup_window = 30.0  # seconds

    # ── Core API ─────────────────────────────────────────────────

    def store(
        self,
        observation: str,
        *,
        source: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        deduplicate: bool = True,
    ) -> dict:
        """Store an observation in the central knowledge base.

        Args:
            observation: Text content to store.
            source: Override default source label.
            agent_id: Override default agent ID.
            session_id: Session/conversation identifier for continuity.
            metadata: Additional key-value metadata.
            deduplicate: Skip if identical text was stored within dedup window.

        Returns:
            API response dict with observation_id, provenance_hash, etc.
        """
        if deduplicate and self._is_duplicate(observation):
            return {"status": "duplicate", "message": "Skipped — same content recently stored"}

        payload = {
            "observation": observation,
            "metadata": {
                "source": source or self.source,
                "agent_id": agent_id or self.agent_id,
                **({"session_id": session_id} if session_id else {}),
                **(metadata or {}),
            },
        }

        resp = self._client.post("/api/memory/store", json=payload)
        resp.raise_for_status()
        return resp.json()

    def recall(
        self,
        query: str,
        *,
        max_tokens: int = 2000,
        time_travel_ts: str | None = None,
    ) -> dict:
        """Recall context from the central knowledge base.

        Args:
            query: Natural language query to match against stored memories.
            max_tokens: Maximum tokens in returned context.
            time_travel_ts: Optional ISO timestamp to recall state at a point in time.

        Returns:
            Dict with context string, sources list, token_count, cross_tool flag.
        """
        payload = {
            "query": query,
            "max_tokens": max_tokens,
        }
        if time_travel_ts:
            payload["time_travel_ts"] = time_travel_ts

        resp = self._client.post("/api/memory/recall", json=payload)
        resp.raise_for_status()
        return resp.json()

    def list_memories(self, limit: int = 50) -> list[dict]:
        """List recent memories for the current tenant."""
        resp = self._client.get("/api/memory/list", params={"limit": limit})
        resp.raise_for_status()
        return resp.json().get("items", [])

    def count(self) -> int:
        """Return total memory count for the current tenant."""
        resp = self._client.get("/api/memory/count")
        resp.raise_for_status()
        return resp.json().get("count", 0)

    def stats(self) -> dict:
        """Get live dashboard stats."""
        resp = self._client.get("/api/stats")
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict:
        """Check API health."""
        resp = self._client.get("/health")
        resp.raise_for_status()
        return resp.json()

    # ── Connector management ─────────────────────────────────────

    def list_connectors(self) -> list[dict]:
        """List all available connectors with status."""
        resp = self._client.get("/api/connectors")
        resp.raise_for_status()
        return resp.json().get("connectors", [])

    def connect(self, connector_id: str) -> dict:
        """Activate a connector."""
        resp = self._client.post("/api/connectors/connect", json={"connector_id": connector_id})
        resp.raise_for_status()
        return resp.json()

    def disconnect(self, connector_id: str) -> dict:
        """Deactivate a connector."""
        resp = self._client.post("/api/connectors/disconnect", json={"connector_id": connector_id})
        resp.raise_for_status()
        return resp.json()

    # ── Internal ─────────────────────────────────────────────────

    def _is_duplicate(self, text: str) -> bool:
        h = hashlib.sha256(text.encode()).hexdigest()[:16]
        now = time.time()
        # Prune expired
        self._recent_hashes = {k: v for k, v in self._recent_hashes.items() if now - v < self._dedup_window}
        if h in self._recent_hashes:
            return True
        self._recent_hashes[h] = now
        return False

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
