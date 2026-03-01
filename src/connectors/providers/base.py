"""Abstract base class for all connector providers.

Every provider (HubSpot, Salesforce, Shopify, etc.) inherits from this
and implements the methods relevant to its auth method and data model.
"""

import abc
import logging
from datetime import UTC, datetime
from typing import Any

from src.connectors.oauth import OAuthConfig

logger = logging.getLogger("membread.providers")


class MemoryItem:
    """A single memory extracted from a provider's data.

    Normalised format that gets fed into Membread's memory engine
    (VectorStore + GraphStore + bi-temporal indexing).
    """

    def __init__(
        self,
        text: str,
        source: str,
        source_id: str,
        *,
        entity_type: str = "observation",
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
        relationships: list[dict[str, Any]] | None = None,
    ):
        self.text = text
        self.source = source  # provider id, e.g. "hubspot"
        self.source_id = source_id  # dedupe key from provider
        self.entity_type = entity_type  # observation, contact, deal, ticket, etc.
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(UTC).isoformat()
        self.relationships = relationships or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source": self.source,
            "source_id": self.source_id,
            "entity_type": self.entity_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "relationships": self.relationships,
        }


class BaseProvider(abc.ABC):
    """Abstract base for all connector providers.

    Lifecycle:
    1. User clicks "Connect" → get_auth_method() determines flow
    2. For OAuth: get_oauth_config() → authorize URL → callback
    3. After auth: on_connected() → register webhooks, initial sync
    4. Ongoing: poll() for incremental data, handle_webhook() for push
    5. Disconnect: on_disconnected() → unregister webhooks
    """

    # ── Identity ────────────────────────────────────────────────────

    provider_id: str = ""
    """Unique provider identifier (matches connector id in AVAILABLE_CONNECTORS)."""

    provider_name: str = ""
    """Human-readable provider name."""

    auth_method: str = "oauth2"
    """Auth method: 'oauth2', 'api_key', 'webhook', 'mcp', 'sdk', 'browser-extension'."""

    poll_interval_seconds: int = 300
    """Default polling interval in seconds."""

    supported_webhook_events: list[str] = []
    """Webhook event types this provider supports."""

    # ── OAuth2 ──────────────────────────────────────────────────────

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        """Return OAuth2 configuration for this provider.

        Can be called without args to get URL metadata (authorize_url, token_url, scopes).
        Override in OAuth providers. Default raises NotImplementedError.
        """
        raise NotImplementedError(f"{self.provider_id} does not support OAuth2")

    # ── Webhook Registration ────────────────────────────────────────

    async def register_webhook(
        self,
        access_token: str,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Register webhooks with the provider's API.

        Returns {"webhook_id": "...", "events": [...]} or None.
        Called automatically after successful OAuth.
        """
        return None

    async def unregister_webhook(
        self,
        access_token: str,
        webhook_id: str,
    ) -> bool:
        """Unregister a webhook from the provider. Returns success."""
        return False

    def verify_webhook(self, headers: dict[str, Any], body: bytes, secret: str) -> bool:
        """Verify an incoming webhook signature. Default: accept all."""
        return True

    # ── Data Extraction ─────────────────────────────────────────────

    @abc.abstractmethod
    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        """Poll provider API for new/updated data since cursor.

        Returns (list of MemoryItems, new_cursor or None).
        The cursor is opaque — could be a timestamp, page token, offset, etc.
        """
        ...

    @abc.abstractmethod
    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        """Transform an incoming webhook payload into MemoryItems."""
        ...

    # ── Lifecycle Hooks ─────────────────────────────────────────────

    async def on_connected(
        self,
        tenant_id: str,
        access_token: str | None = None,
        api_key: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Called after successful authentication.

        Good place to do initial data sync, register webhooks, validate access.
        Returns optional metadata dict.
        """
        return None

    async def on_disconnected(
        self,
        tenant_id: str,
        access_token: str | None = None,
        webhook_ids: list[str] | None = None,
    ) -> None:
        """Called when user disconnects. Clean up webhooks, etc."""
        if access_token and webhook_ids:
            for wid in webhook_ids:
                try:
                    await self.unregister_webhook(access_token, wid)
                except Exception as e:
                    logger.warning("Failed to unregister webhook %s: %s", wid, e)

    # ── API Key Validation ──────────────────────────────────────────

    async def validate_api_key(self, api_key: str, config: dict[str, Any] | None = None) -> bool:
        """Validate an API key against the provider. Override for API-key providers."""
        return True

    # ── Helpers ─────────────────────────────────────────────────────

    def _make_memory(
        self,
        text: str,
        source_id: str,
        entity_type: str = "observation",
        metadata: dict[str, Any] | None = None,
        timestamp: str | None = None,
        relationships: list[dict[str, Any]] | None = None,
    ) -> MemoryItem:
        """Helper to create a MemoryItem with this provider's source."""
        return MemoryItem(
            text=text,
            source=self.provider_id,
            source_id=source_id,
            entity_type=entity_type,
            metadata=metadata,
            timestamp=timestamp,
            relationships=relationships,
        )
