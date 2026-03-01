# pyright: reportMissingTypeStubs=false, reportMissingTypeArgument=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false
"""PostgreSQL database layer for connector infrastructure.

Handles encrypted token storage, sync cursors, webhook registrations,
and connector state — all with bi-temporal indexing and RLS.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import asyncpg
from cryptography.fernet import Fernet

# Encryption key — generate once and store in env; fallback for dev
_FERNET_KEY = os.getenv("CONNECTOR_ENCRYPTION_KEY", Fernet.generate_key().decode())
_fernet = Fernet(_FERNET_KEY.encode())


def encrypt(plaintext: str) -> str:
    """Encrypt a string (token, secret) for database storage."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a string from database storage."""
    return _fernet.decrypt(ciphertext.encode()).decode()


class ConnectorDB:
    """Async PostgreSQL operations for connector infrastructure."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    # ── Schema bootstrap ────────────────────────────────────────────

    async def initialize_schema(self) -> None:
        """Run schema_connectors.sql to create tables."""
        schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "schema_connectors.sql")
        if not os.path.exists(schema_path):
            schema_path = os.path.join(os.path.dirname(__file__), "..", "..", "schema_connectors.sql")
        try:
            with open(schema_path, "r") as f:
                sql = f.read()
            async with self.pool.acquire() as conn:
                await conn.execute(sql)
        except Exception as e:
            # Tables may already exist
            if "already exists" not in str(e).lower():
                raise

    # ── Provider Credentials ────────────────────────────────────────

    async def upsert_provider_credentials(
        self,
        tenant_id: str,
        provider_id: str,
        client_id: str,
        client_secret: str,
        scopes: str = "",
        extra_config: dict[str, Any] | None = None,
    ) -> str:
        """Store or update OAuth client credentials for a provider."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO provider_credentials (tenant_id, provider_id, client_id, client_secret_encrypted, scopes, extra_config)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tenant_id, provider_id) DO UPDATE SET
                    client_id = EXCLUDED.client_id,
                    client_secret_encrypted = EXCLUDED.client_secret_encrypted,
                    scopes = EXCLUDED.scopes,
                    extra_config = EXCLUDED.extra_config,
                    updated_at = NOW()
                RETURNING id
                """,
                uuid.UUID(tenant_id),
                provider_id,
                client_id,
                encrypt(client_secret),
                scopes,
                extra_config or {},
            )
            return str(row["id"])

    async def get_provider_credentials(self, tenant_id: str, provider_id: str) -> dict[str, Any] | None:
        """Get decrypted provider credentials."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM provider_credentials WHERE tenant_id = $1 AND provider_id = $2",
                uuid.UUID(tenant_id),
                provider_id,
            )
            if not row:
                return None
            return {
                "id": str(row["id"]),
                "tenant_id": str(row["tenant_id"]),
                "provider_id": row["provider_id"],
                "client_id": row["client_id"],
                "client_secret": decrypt(row["client_secret_encrypted"]),
                "scopes": row["scopes"],
                "extra_config": row["extra_config"],
            }

    # ── Connector Connections ───────────────────────────────────────

    async def get_connection(self, tenant_id: str, connector_id: str) -> dict[str, Any] | None:
        """Get active connection for a connector."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM connector_connections
                WHERE tenant_id = $1 AND connector_id = $2 AND invalid_at IS NULL
                ORDER BY valid_at DESC LIMIT 1
                """,
                uuid.UUID(tenant_id),
                connector_id,
            )
            if not row:
                return None
            return self._row_to_connection(row)

    async def get_all_connections(self, tenant_id: str) -> list[dict[str, Any]]:
        """Get all active connections for a tenant."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM connector_connections
                WHERE tenant_id = $1 AND invalid_at IS NULL
                ORDER BY connector_id
                """,
                uuid.UUID(tenant_id),
            )
            return [self._row_to_connection(r) for r in rows]

    async def create_connection(
        self,
        tenant_id: str,
        connector_id: str,
        auth_method: str,
        status: str = "pending_oauth",
        oauth_state: str | None = None,
        api_key: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> str:
        """Create a new connection record (bi-temporal: sets valid_at=now)."""
        async with self.pool.acquire() as conn:
            # Invalidate any existing connection
            await conn.execute(
                """
                UPDATE connector_connections
                SET invalid_at = NOW(), updated_at = NOW()
                WHERE tenant_id = $1 AND connector_id = $2 AND invalid_at IS NULL
                """,
                uuid.UUID(tenant_id),
                connector_id,
            )
            row = await conn.fetchrow(
                """
                INSERT INTO connector_connections (
                    tenant_id, connector_id, status, auth_method, oauth_state,
                    api_key_encrypted, config, valid_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                RETURNING id
                """,
                uuid.UUID(tenant_id),
                connector_id,
                status,
                auth_method,
                oauth_state,
                encrypt(api_key) if api_key else None,
                config or {},
            )
            return str(row["id"])

    async def update_connection_tokens(
        self,
        tenant_id: str,
        connector_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | None = None,
    ) -> None:
        """Store OAuth tokens after successful auth."""
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE connector_connections SET
                    access_token_encrypted = $3,
                    refresh_token_encrypted = $4,
                    token_expires_at = $5,
                    status = 'connected',
                    connected_at = NOW(),
                    last_sync_at = NOW(),
                    oauth_state = NULL,
                    error_message = NULL,
                    updated_at = NOW()
                WHERE tenant_id = $1 AND connector_id = $2 AND invalid_at IS NULL
                """,
                uuid.UUID(tenant_id),
                connector_id,
                encrypt(access_token),
                encrypt(refresh_token) if refresh_token else None,
                expires_at,
            )

    async def update_connection_status(
        self,
        tenant_id: str,
        connector_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update connection status."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE connector_connections SET
                    status = $3,
                    error_message = $4,
                    last_error_at = CASE WHEN $4 IS NOT NULL THEN NOW() ELSE last_error_at END,
                    updated_at = NOW()
                WHERE tenant_id = $1 AND connector_id = $2 AND invalid_at IS NULL
                """,
                uuid.UUID(tenant_id),
                connector_id,
                status,
                error_message,
            )

    async def disconnect(self, tenant_id: str, connector_id: str) -> None:
        """Disconnect: bi-temporal invalidation + status update."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE connector_connections SET
                    status = 'disconnected',
                    invalid_at = NOW(),
                    updated_at = NOW()
                WHERE tenant_id = $1 AND connector_id = $2 AND invalid_at IS NULL
                """,
                uuid.UUID(tenant_id),
                connector_id,
            )

    async def get_decrypted_tokens(self, tenant_id: str, connector_id: str) -> dict[str, Any] | None:
        """Get decrypted access/refresh tokens and API key."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT access_token_encrypted, refresh_token_encrypted, api_key_encrypted,
                       token_expires_at
                FROM connector_connections
                WHERE tenant_id = $1 AND connector_id = $2 AND invalid_at IS NULL
                """,
                uuid.UUID(tenant_id),
                connector_id,
            )
            if not row:
                return None
            result = {"token_expires_at": row["token_expires_at"]}
            if row["access_token_encrypted"]:
                result["access_token"] = decrypt(row["access_token_encrypted"])
            if row["refresh_token_encrypted"]:
                result["refresh_token"] = decrypt(row["refresh_token_encrypted"])
            if row["api_key_encrypted"]:
                result["api_key"] = decrypt(row["api_key_encrypted"])
            return result

    async def increment_memories(self, tenant_id: str, connector_id: str, count: int = 1) -> None:
        """Increment captured memories count."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE connector_connections SET
                    memories_captured = memories_captured + $3,
                    last_sync_at = NOW(),
                    updated_at = NOW()
                WHERE tenant_id = $1 AND connector_id = $2 AND invalid_at IS NULL
                """,
                uuid.UUID(tenant_id),
                connector_id,
                count,
            )

    async def get_connections_needing_refresh(self) -> list[dict[str, Any]]:
        """Find connections whose OAuth tokens expire within 5 minutes."""
        threshold = datetime.now(timezone.utc) + timedelta(minutes=5)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM connector_connections
                WHERE invalid_at IS NULL
                  AND status = 'connected'
                  AND token_expires_at IS NOT NULL
                  AND token_expires_at < $1
                  AND refresh_token_encrypted IS NOT NULL
                """,
                threshold,
            )
            return [self._row_to_connection(r) for r in rows]

    # ── Sync Cursors ────────────────────────────────────────────────

    async def get_cursor(self, tenant_id: str, connector_id: str) -> dict[str, Any] | None:
        """Get polling cursor for a connector."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sync_cursors WHERE tenant_id = $1 AND connector_id = $2",
                uuid.UUID(tenant_id),
                connector_id,
            )
            if not row:
                return None
            return dict(row)

    async def upsert_cursor(
        self,
        tenant_id: str,
        connector_id: str,
        cursor_value: str,
        items_fetched: int = 0,
        poll_interval: int = 60,
    ) -> None:
        """Update or create polling cursor."""
        next_poll = datetime.now(timezone.utc) + timedelta(seconds=poll_interval)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO sync_cursors (tenant_id, connector_id, cursor_value, last_poll_at, next_poll_at, poll_interval_seconds, items_fetched_total)
                VALUES ($1, $2, $3, NOW(), $4, $5, $6)
                ON CONFLICT (tenant_id, connector_id) DO UPDATE SET
                    cursor_value = EXCLUDED.cursor_value,
                    last_poll_at = NOW(),
                    next_poll_at = EXCLUDED.next_poll_at,
                    items_fetched_total = sync_cursors.items_fetched_total + EXCLUDED.items_fetched_total,
                    consecutive_errors = 0,
                    last_error = NULL,
                    updated_at = NOW()
                """,
                uuid.UUID(tenant_id),
                connector_id,
                cursor_value,
                next_poll,
                poll_interval,
                items_fetched,
            )

    async def record_cursor_error(self, tenant_id: str, connector_id: str, error: str) -> None:
        """Record a polling error and back off."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE sync_cursors SET
                    consecutive_errors = consecutive_errors + 1,
                    last_error = $3,
                    next_poll_at = NOW() + (poll_interval_seconds * LEAST(consecutive_errors + 1, 10)) * INTERVAL '1 second',
                    updated_at = NOW()
                WHERE tenant_id = $1 AND connector_id = $2
                """,
                uuid.UUID(tenant_id),
                connector_id,
                error,
            )

    async def get_due_polls(self) -> list[dict[str, Any]]:
        """Find connectors that are due for polling."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT sc.*, cc.status as conn_status
                FROM sync_cursors sc
                JOIN connector_connections cc ON sc.tenant_id = cc.tenant_id
                    AND sc.connector_id = cc.connector_id
                    AND cc.invalid_at IS NULL
                WHERE sc.next_poll_at <= NOW()
                  AND cc.status = 'connected'
                ORDER BY sc.next_poll_at ASC
                LIMIT 50
                """,
            )
            return [dict(r) for r in rows]

    # ── Webhook Registrations ───────────────────────────────────────

    async def save_webhook_registration(
        self,
        tenant_id: str,
        connector_id: str,
        provider_webhook_id: str,
        webhook_url: str,
        events: list[str],
        verification_secret: str | None = None,
    ) -> str:
        """Save a webhook we registered on a provider."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO webhook_registrations (
                    tenant_id, connector_id, provider_webhook_id, webhook_url, events, verification_secret
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                uuid.UUID(tenant_id),
                connector_id,
                provider_webhook_id,
                webhook_url,
                events,
                verification_secret,
            )
            return str(row["id"])

    async def get_webhook_registrations(self, tenant_id: str, connector_id: str) -> list[dict[str, Any]]:
        """Get webhook registrations for a connector."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM webhook_registrations
                WHERE tenant_id = $1 AND connector_id = $2 AND status = 'active'
                """,
                uuid.UUID(tenant_id),
                connector_id,
            )
            return [dict(r) for r in rows]

    async def delete_webhook_registration(self, registration_id: str) -> None:
        """Mark a webhook registration as inactive."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE webhook_registrations SET status = 'inactive', updated_at = NOW() WHERE id = $1",
                uuid.UUID(registration_id),
            )

    # ── Activity Logging ────────────────────────────────────────────

    async def log_activity(
        self,
        tenant_id: str,
        connector_id: str,
        activity_type: str,
        details: dict[str, Any] | None = None,
        items_count: int = 0,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log connector activity with bi-temporal timestamp."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO connector_activity (
                    tenant_id, connector_id, activity_type, details,
                    items_count, duration_ms, error_message, valid_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """,
                uuid.UUID(tenant_id),
                connector_id,
                activity_type,
                details or {},
                items_count,
                duration_ms,
                error_message,
            )

    # ── Connection History (bi-temporal queries) ────────────────────

    async def get_connection_history(
        self, tenant_id: str, connector_id: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get full temporal history of a connection (all state changes)."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM connector_connections
                WHERE tenant_id = $1 AND connector_id = $2
                ORDER BY valid_at DESC
                LIMIT $3
                """,
                uuid.UUID(tenant_id),
                connector_id,
                limit,
            )
            return [self._row_to_connection(r) for r in rows]

    # ── Helpers ─────────────────────────────────────────────────────

    def _row_to_connection(self, row: asyncpg.Record) -> dict[str, Any]:
        """Convert a database row to a connection dict (no decryption of tokens)."""
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "connector_id": row["connector_id"],
            "status": row["status"],
            "auth_method": row["auth_method"],
            "has_access_token": row["access_token_encrypted"] is not None,
            "has_refresh_token": row["refresh_token_encrypted"] is not None,
            "has_api_key": row["api_key_encrypted"] is not None,
            "token_expires_at": row["token_expires_at"].isoformat() if row["token_expires_at"] else None,
            "webhook_id": row["webhook_id"],
            "config": row["config"] or {},
            "error_message": row["error_message"],
            "memories_captured": row["memories_captured"] or 0,
            "last_sync_at": row["last_sync_at"].isoformat() if row["last_sync_at"] else None,
            "connected_at": row["connected_at"].isoformat() if row["connected_at"] else None,
            "valid_at": row["valid_at"].isoformat() if row["valid_at"] else None,
            "invalid_at": row["invalid_at"].isoformat() if row["invalid_at"] else None,
        }
