"""Background polling scheduler for Membread connectors.

Runs as an asyncio background task that:
1. Queries sync_cursors for due polls
2. Gets decrypted tokens from connector_connections
3. Calls provider.poll() with the cursor
4. Stores resulting MemoryItems into the memory engine
5. Updates cursors and activity logs
6. Handles token refresh when tokens expire
"""

import asyncio
import logging
import time
from typing import Any, Callable, Awaitable

from src.connectors.db import ConnectorDB
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.polling")


class PollingScheduler:
    """Asyncio-based background polling engine."""

    def __init__(
        self,
        db: ConnectorDB,
        providers: dict[str, BaseProvider],
        store_memories_fn: Callable[[str, list[MemoryItem]], Awaitable[int]],
        refresh_token_fn: Callable[[str, str], Awaitable[str | None]] | None = None,
        poll_check_interval: int = 15,  # How often to check for due polls
    ):
        """
        Args:
            db: ConnectorDB instance for cursor and connection queries
            providers: Map of connector_id -> BaseProvider instance
            store_memories_fn: async fn(tenant_id, items) -> count stored
            refresh_token_fn: async fn(tenant_id, connector_id) -> new_access_token or None
            poll_check_interval: Seconds between checking for due polls
        """
        self.db = db
        self.providers = providers
        self.store_memories = store_memories_fn
        self.refresh_token = refresh_token_fn
        self.poll_check_interval = poll_check_interval
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start the polling background loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Polling scheduler started (check every %ds)", self.poll_check_interval)

    async def stop(self) -> None:
        """Stop the polling background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Polling scheduler stopped")

    async def _poll_loop(self) -> None:
        """Main loop: check for due polls and execute them."""
        while self._running:
            try:
                due = await self.db.get_due_polls()
                if due:
                    logger.info("Found %d connectors due for polling", len(due))
                    # Process polls concurrently but with a semaphore to avoid overwhelming
                    sem = asyncio.Semaphore(5)
                    tasks = [self._poll_with_semaphore(sem, cursor_row) for cursor_row in due]
                    await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error("Poll loop error: %s", e)

            await asyncio.sleep(self.poll_check_interval)

    async def _poll_with_semaphore(self, sem: asyncio.Semaphore, cursor_row: dict[str, Any]) -> None:
        async with sem:
            await self._execute_poll(cursor_row)

    async def _execute_poll(self, cursor_row: dict[str, Any]) -> None:
        """Execute a single poll for a connector."""
        tenant_id = str(cursor_row["tenant_id"])
        connector_id = cursor_row["connector_id"]
        cursor_value = cursor_row.get("cursor_value")

        provider = self.providers.get(connector_id)
        if not provider:
            logger.warning("No provider registered for %s", connector_id)
            return

        start = time.monotonic()

        try:
            # Get tokens
            tokens = await self.db.get_decrypted_tokens(tenant_id, connector_id)
            if not tokens:
                logger.warning("No tokens for %s:%s", tenant_id, connector_id)
                await self.db.record_cursor_error(tenant_id, connector_id, "No tokens available")
                return

            access_token = tokens.get("access_token")
            api_key = tokens.get("api_key")

            # Check if token needs refresh
            if tokens.get("token_expires_at"):
                from datetime import datetime, timedelta, timezone
                expires = tokens["token_expires_at"]
                if isinstance(expires, str):
                    expires = datetime.fromisoformat(expires)
                if expires <= datetime.now(timezone.utc) + timedelta(minutes=2):
                    if self.refresh_token:
                        new_token = await self.refresh_token(tenant_id, connector_id)
                        if new_token:
                            access_token = new_token
                        else:
                            logger.error("Token refresh failed for %s:%s", tenant_id, connector_id)
                            await self.db.update_connection_status(
                                tenant_id, connector_id, "error", "Token refresh failed"
                            )
                            return

            # Get connection config
            conn = await self.db.get_connection(tenant_id, connector_id)
            config: dict[str, Any] = conn.get("config", {}) if conn else {}

            # Execute poll
            items, new_cursor = await provider.poll(
                access_token=access_token,
                api_key=api_key,
                cursor=cursor_value,
                config=config,
            )

            duration_ms = int((time.monotonic() - start) * 1000)

            if items:
                # Store memories
                stored = await self.store_memories(tenant_id, items)
                await self.db.increment_memories(tenant_id, connector_id, stored)
                logger.info(
                    "Polled %s:%s — %d items, %d stored, %dms",
                    tenant_id[:8], connector_id, len(items), stored, duration_ms,
                )
            else:
                stored = 0

            # Update cursor
            await self.db.upsert_cursor(
                tenant_id,
                connector_id,
                cursor_value=new_cursor or cursor_value or "",
                items_fetched=len(items),
                poll_interval=provider.poll_interval_seconds,
            )

            # Log activity
            await self.db.log_activity(
                tenant_id,
                connector_id,
                "poll_completed",
                {
                    "items_found": len(items),
                    "items_stored": stored,
                    "cursor": new_cursor,
                },
                items_count=len(items),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error("Poll failed for %s:%s: %s", tenant_id, connector_id, e)
            await self.db.record_cursor_error(tenant_id, connector_id, str(e))
            await self.db.log_activity(
                tenant_id,
                connector_id,
                "poll_error",
                {"error": str(e)},
                duration_ms=duration_ms,
                error_message=str(e),
            )

    # ── Manual poll trigger ─────────────────────────────────────────

    async def poll_now(self, tenant_id: str, connector_id: str) -> dict[str, Any]:
        """Manually trigger a poll for a connector. Returns result summary."""
        cursor_row: dict[str, Any] = await self.db.get_cursor(tenant_id, connector_id)  # type: ignore[assignment]
        if not cursor_row:
            # Create initial cursor
            cursor_row = {
                "tenant_id": tenant_id,
                "connector_id": connector_id,
                "cursor_value": None,
            }

        await self._execute_poll(cursor_row)
        return {"status": "polled", "connector_id": connector_id}

    # ── Initialize cursors for new connection ───────────────────────

    async def initialize_polling(self, tenant_id: str, connector_id: str) -> None:
        """Set up initial polling cursor for a new connection."""
        provider = self.providers.get(connector_id)
        if not provider:
            return

        await self.db.upsert_cursor(
            tenant_id,
            connector_id,
            cursor_value="",  # Empty cursor = start from beginning
            items_fetched=0,
            poll_interval=provider.poll_interval_seconds,
        )
        logger.info("Polling initialized for %s:%s (every %ds)", tenant_id, connector_id, provider.poll_interval_seconds)
