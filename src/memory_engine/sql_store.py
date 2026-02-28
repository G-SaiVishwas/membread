"""SQL Store: Relational storage for user profiles with Row-Level Security."""

import asyncpg
from datetime import datetime
from typing import Optional
from uuid import UUID
import structlog

from src.models import UserProfile, PrivilegeLayer
from src.database import db_pool

logger = structlog.get_logger()


class SQLStore:
    """
    Relational storage for user profiles with Row-Level Security.
    Enforces multi-tenant isolation at database level.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def _set_tenant_context(self, conn: asyncpg.Connection, tenant_id: str) -> None:
        """Set tenant context for Row-Level Security."""
        await conn.execute("SELECT set_config('app.tenant_id', $1, false)", tenant_id)

    async def get_profile(
        self, tenant_id: str, user_id: str
    ) -> Optional[UserProfile]:
        """
        Retrieve user profile with RLS enforcement.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier

        Returns:
            UserProfile if exists and accessible, None otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                # Set tenant context for RLS
                await self._set_tenant_context(conn, tenant_id)

                row = await conn.fetchrow(
                    """
                    SELECT tenant_id, user_id, display_name, preferences, 
                           created_at, updated_at
                    FROM users
                    WHERE tenant_id = $1 AND user_id = $2
                    """,
                    UUID(tenant_id),
                    UUID(user_id),
                )

                if not row:
                    return None

                return UserProfile(
                    tenant_id=str(row["tenant_id"]),
                    user_id=str(row["user_id"]),
                    display_name=row["display_name"],
                    preferences=row["preferences"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        except Exception as e:
            logger.error(
                "sql_store_get_profile_failed",
                tenant_id=tenant_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def create_profile(
        self,
        tenant_id: str,
        user_id: str,
        display_name: str,
        preferences: Optional[dict] = None,
    ) -> UserProfile:
        """
        Create a new user profile.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            display_name: User's display name
            preferences: User preferences dictionary

        Returns:
            Created UserProfile
        """
        if preferences is None:
            preferences = {}

        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                row = await conn.fetchrow(
                    """
                    INSERT INTO users (tenant_id, user_id, display_name, preferences)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (tenant_id, user_id) DO UPDATE
                    SET display_name = EXCLUDED.display_name,
                        preferences = EXCLUDED.preferences,
                        updated_at = NOW()
                    RETURNING tenant_id, user_id, display_name, preferences, 
                              created_at, updated_at
                    """,
                    UUID(tenant_id),
                    UUID(user_id),
                    display_name,
                    preferences,
                )

                logger.info(
                    "sql_store_profile_created",
                    tenant_id=tenant_id,
                    user_id=user_id,
                )

                return UserProfile(
                    tenant_id=str(row["tenant_id"]),
                    user_id=str(row["user_id"]),
                    display_name=row["display_name"],
                    preferences=row["preferences"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )

        except Exception as e:
            logger.error(
                "sql_store_create_profile_failed",
                tenant_id=tenant_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def update_profile(
        self,
        tenant_id: str,
        user_id: str,
        updates: dict,
        privilege_layer: PrivilegeLayer,
    ) -> bool:
        """
        Update user profile with privilege checking.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            updates: Fields to update (display_name, preferences)
            privilege_layer: Security privilege level

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                # Build update query dynamically
                set_clauses = []
                params = [UUID(tenant_id), UUID(user_id)]
                param_idx = 3

                if "display_name" in updates:
                    set_clauses.append(f"display_name = ${param_idx}")
                    params.append(updates["display_name"])
                    param_idx += 1

                if "preferences" in updates:
                    set_clauses.append(f"preferences = ${param_idx}")
                    params.append(updates["preferences"])
                    param_idx += 1

                if not set_clauses:
                    return False

                set_clauses.append("updated_at = NOW()")
                query = f"""
                    UPDATE users
                    SET {', '.join(set_clauses)}
                    WHERE tenant_id = $1 AND user_id = $2
                """

                result = await conn.execute(query, *params)

                # Log if this is a Layer 1 operation
                if privilege_layer == PrivilegeLayer.ADMIN:
                    await self.create_audit_log(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        operation="update_profile",
                        details={"updates": updates, "privilege": "ADMIN"},
                    )

                logger.info(
                    "sql_store_profile_updated",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    privilege=privilege_layer.name,
                )

                return result == "UPDATE 1"

        except Exception as e:
            logger.error(
                "sql_store_update_profile_failed",
                tenant_id=tenant_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def create_audit_log(
        self,
        tenant_id: str,
        user_id: str,
        operation: str,
        details: dict,
    ) -> str:
        """
        Create audit log entry for Layer 1 operations.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            operation: Operation type
            details: Operation details

        Returns:
            Audit log ID
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                log_id = await conn.fetchval(
                    """
                    INSERT INTO audit_logs (tenant_id, user_id, operation, details)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    UUID(tenant_id),
                    UUID(user_id),
                    operation,
                    details,
                )

                logger.info(
                    "audit_log_created",
                    tenant_id=tenant_id,
                    user_id=user_id,
                    operation=operation,
                    log_id=str(log_id),
                )

                return str(log_id)

        except Exception as e:
            logger.error(
                "sql_store_create_audit_log_failed",
                tenant_id=tenant_id,
                user_id=user_id,
                operation=operation,
                error=str(e),
            )
            raise

    async def get_audit_logs(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Retrieve audit logs with optional filtering.

        Args:
            tenant_id: Tenant identifier
            user_id: Optional user filter
            operation: Optional operation filter
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        try:
            async with self.pool.acquire() as conn:
                await self._set_tenant_context(conn, tenant_id)

                query = """
                    SELECT id, tenant_id, user_id, operation, details, created_at
                    FROM audit_logs
                    WHERE tenant_id = $1
                """
                params = [UUID(tenant_id)]
                param_idx = 2

                if user_id:
                    query += f" AND user_id = ${param_idx}"
                    params.append(UUID(user_id))
                    param_idx += 1

                if operation:
                    query += f" AND operation = ${param_idx}"
                    params.append(operation)
                    param_idx += 1

                query += f" ORDER BY created_at DESC LIMIT ${param_idx}"
                params.append(limit)

                rows = await conn.fetch(query, *params)

                return [
                    {
                        "id": str(row["id"]),
                        "tenant_id": str(row["tenant_id"]),
                        "user_id": str(row["user_id"]),
                        "operation": row["operation"],
                        "details": row["details"],
                        "created_at": row["created_at"].isoformat(),
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(
                "sql_store_get_audit_logs_failed",
                tenant_id=tenant_id,
                error=str(e),
            )
            raise
