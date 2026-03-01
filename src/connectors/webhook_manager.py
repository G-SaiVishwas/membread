# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Webhook lifecycle manager for Membread connectors.

Handles:
1. Registering webhooks on provider APIs after OAuth
2. Verifying inbound webhook signatures
3. Routing inbound webhooks to the correct provider's transform_webhook()
4. Storing resulting MemoryItems into the memory engine
5. Unregistering webhooks on disconnect
"""

import hashlib
import hmac
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from src.connectors.db import ConnectorDB
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.webhooks")

# Base URL for webhook endpoints — providers register this URL with their API
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000/api/webhooks")


class WebhookManager:
    """Manages webhook registration, verification, and routing."""

    def __init__(
        self,
        db: ConnectorDB,
        providers: dict[str, BaseProvider],
        store_memories_fn: Callable[[str, list[MemoryItem]], Awaitable[int]],
    ):
        self.db = db
        self.providers = providers
        self.store_memories = store_memories_fn
        self._processed_ids: set[str] = set()  # Idempotency cache

    # ── Registration ────────────────────────────────────────────────

    async def register_webhooks(
        self,
        tenant_id: str,
        connector_id: str,
        access_token: str,
    ) -> list[str]:
        """Register webhooks for a connector after OAuth completion.

        Returns list of registered webhook IDs.
        """
        provider = self.providers.get(connector_id)
        if not provider:
            logger.warning("No provider for webhook registration: %s", connector_id)
            return []

        if not provider.supported_webhook_events:
            logger.info("Provider %s has no webhook events to register", connector_id)
            return []

        webhook_url = f"{WEBHOOK_BASE_URL}/{connector_id}"
        registered_ids = []

        try:
            result = await provider.register_webhook(
                access_token=access_token,
                webhook_url=webhook_url,
                events=provider.supported_webhook_events,
            )

            if result and "webhook_id" in result:
                await self.db.save_webhook_registration(
                    tenant_id=tenant_id,
                    connector_id=connector_id,
                    provider_webhook_id=result["webhook_id"],
                    webhook_url=webhook_url,
                    events=result.get("events", provider.supported_webhook_events),
                    verification_secret=result.get("secret"),
                )
                registered_ids.append(result["webhook_id"])

                await self.db.log_activity(
                    tenant_id, connector_id, "webhook_registered",
                    {"webhook_id": result["webhook_id"], "events": result.get("events", [])},
                )
                logger.info("Webhook registered for %s: %s", connector_id, result["webhook_id"])

        except Exception as e:
            logger.error("Webhook registration failed for %s: %s", connector_id, e)
            await self.db.log_activity(
                tenant_id, connector_id, "webhook_registration_failed",
                {"error": str(e)},
                error_message=str(e),
            )

        return registered_ids

    # ── Unregistration ──────────────────────────────────────────────

    async def unregister_webhooks(
        self,
        tenant_id: str,
        connector_id: str,
        access_token: str | None = None,
    ) -> int:
        """Unregister all webhooks for a connector. Returns count removed."""
        provider = self.providers.get(connector_id)
        registrations = await self.db.get_webhook_registrations(tenant_id, connector_id)
        removed = 0

        for reg in registrations:
            try:
                if provider and access_token:
                    await provider.unregister_webhook(access_token, reg["provider_webhook_id"])
                await self.db.delete_webhook_registration(str(reg["id"]))
                removed += 1
            except Exception as e:
                logger.warning("Failed to unregister webhook %s: %s", reg["provider_webhook_id"], e)

        if removed:
            await self.db.log_activity(
                tenant_id, connector_id, "webhooks_unregistered",
                {"count": removed},
            )

        return removed

    # ── Inbound Processing ──────────────────────────────────────────

    async def handle_inbound(
        self,
        connector_id: str,
        payload: dict[str, Any],
        headers: dict[str, Any],
        body: bytes,
    ) -> dict[str, Any]:
        """Process an inbound webhook from a provider.

        1. Finds the provider
        2. Verifies signature
        3. Transforms payload to MemoryItems
        4. Stores memories
        5. Returns result summary
        """
        provider = self.providers.get(connector_id)
        if not provider:
            logger.warning("Inbound webhook for unknown provider: %s", connector_id)
            return {"status": "ignored", "reason": "unknown_provider"}

        # Idempotency check
        dedup_key = hashlib.sha256(body).hexdigest()[:24]
        if dedup_key in self._processed_ids:
            return {"status": "duplicate", "dedup_key": dedup_key}
        self._processed_ids.add(dedup_key)

        # Trim idempotency cache
        if len(self._processed_ids) > 10000:
            # Keep last 5000
            self._processed_ids = set(list(self._processed_ids)[-5000:])

        # Find which tenant this webhook belongs to
        # Look up via connector_connections that have this connector as connected
        connections = await self._find_connections_for_connector(connector_id)
        if not connections:
            logger.warning("No active connections for webhook connector %s", connector_id)
            return {"status": "ignored", "reason": "no_active_connections"}

        # Verify signature if possible
        for conn in connections:
            regs = await self.db.get_webhook_registrations(conn["tenant_id"], connector_id)
            for reg in regs:
                if reg.get("verification_secret"):
                    if not provider.verify_webhook(headers, body, reg["verification_secret"]):
                        logger.warning("Webhook signature verification failed for %s", connector_id)
                        return {"status": "rejected", "reason": "signature_invalid"}

        # Transform payload to MemoryItems
        try:
            items = await provider.transform_webhook(payload, headers)
        except Exception as e:
            logger.error("Webhook transform failed for %s: %s", connector_id, e)
            return {"status": "error", "reason": str(e)}

        if not items:
            return {"status": "ok", "items_stored": 0}

        # Store for each connected tenant
        total_stored = 0
        for conn in connections:
            try:
                stored = await self.store_memories(conn["tenant_id"], items)
                total_stored += stored
                await self.db.increment_memories(conn["tenant_id"], connector_id, stored)
                await self.db.log_activity(
                    conn["tenant_id"], connector_id, "webhook_received",
                    {"items_count": len(items), "stored": stored},
                    items_count=stored,
                )
            except Exception as e:
                logger.error("Memory storage failed for %s: %s", conn["tenant_id"], e)

        return {"status": "ok", "items_stored": total_stored, "items_received": len(items)}

    async def _find_connections_for_connector(self, connector_id: str) -> list[dict[str, Any]]:
        """Find all active connections for a given connector across tenants."""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT tenant_id::text as tenant_id
                FROM connector_connections
                WHERE connector_id = $1 AND status = 'connected' AND invalid_at IS NULL
                """,
                connector_id,
            )
            return [dict(r) for r in rows]

    # ── Signature Helpers ───────────────────────────────────────────

    @staticmethod
    def verify_hmac_sha256(body: bytes, signature: str, secret: str) -> bool:
        """Standard HMAC-SHA256 webhook verification."""
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        # Handle sha256= prefix
        if signature.startswith("sha256="):
            signature = signature[7:]
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def verify_hmac_sha1(body: bytes, signature: str, secret: str) -> bool:
        """HMAC-SHA1 webhook verification (GitHub, Shopify)."""
        expected = hmac.new(secret.encode(), body, hashlib.sha1).hexdigest()
        if signature.startswith("sha1="):
            signature = signature[5:]
        return hmac.compare_digest(expected, signature)
