# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""OAuth2 Authorization Code Grant engine for Membread connectors.

Handles the full OAuth2 lifecycle:
1. Generate authorize URL with PKCE + state
2. Handle callback: exchange code for tokens
3. Token refresh when access_token expires
4. Token encryption via ConnectorDB
"""

import os
import hashlib
import base64
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlencode

import httpx

from src.connectors.db import ConnectorDB

logger = logging.getLogger("membread.oauth")

# Pending OAuth flows: state -> flow metadata
# In production, use Redis or database; for single-process this is fine.
_pending_flows: dict[str, dict[str, Any]] = {}

# Base URL for our callback — set via environment or inferred from request
OAUTH_CALLBACK_URL = os.getenv("OAUTH_CALLBACK_URL", "http://localhost:8000/api/oauth/callback")


class OAuthConfig:
    """OAuth2 configuration for a single provider."""

    def __init__(
        self,
        provider_id: str,
        authorize_url: str,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: list[str],
        *,
        use_pkce: bool = False,
        token_endpoint_auth: str = "client_secret_post",  # or "client_secret_basic"
        extra_authorize_params: dict[str, Any] | None = None,
        extra_token_params: dict[str, Any] | None = None,
        revoke_url: str | None = None,
    ):
        self.provider_id = provider_id
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.use_pkce = use_pkce
        self.token_endpoint_auth = token_endpoint_auth
        self.extra_authorize_params = extra_authorize_params or {}
        self.extra_token_params = extra_token_params or {}
        self.revoke_url = revoke_url


class OAuthEngine:
    """Manages OAuth2 flows for all providers."""

    def __init__(self, db: ConnectorDB):
        self.db = db
        self._http = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self._http.aclose()

    # ── Step 1: Generate authorize URL ──────────────────────────────

    def start_flow(
        self,
        oauth_config: OAuthConfig,
        tenant_id: str,
        connector_id: str,
        redirect_after: str | None = None,
    ) -> str:
        """Generate the OAuth authorize URL and store flow state.

        Returns the URL the frontend should redirect/popup to.
        """
        state = secrets.token_urlsafe(32)

        flow: dict[str, Any] = {
            "provider_id": oauth_config.provider_id,
            "tenant_id": tenant_id,
            "connector_id": connector_id,
            "redirect_after": redirect_after or "http://localhost:3000/connectors",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "oauth_config": oauth_config,  # Stored for handle_callback
        }

        # PKCE
        code_verifier: str | None = None
        code_challenge: str | None = None
        if oauth_config.use_pkce:
            code_verifier = secrets.token_urlsafe(64)
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")
            flow["code_verifier"] = code_verifier

        _pending_flows[state] = flow

        params: dict[str, Any] = {
            "client_id": oauth_config.client_id,
            "redirect_uri": OAUTH_CALLBACK_URL,
            "response_type": "code",
            "state": state,
            "scope": " ".join(oauth_config.scopes),
            **oauth_config.extra_authorize_params,
        }

        if oauth_config.use_pkce:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        url = f"{oauth_config.authorize_url}?{urlencode(params)}"
        logger.info("OAuth flow started for %s tenant=%s state=%s", connector_id, tenant_id, state[:8])
        return url

    # ── Step 2: Handle callback ─────────────────────────────────────

    async def handle_callback(
        self,
        state: str,
        code: str,
        oauth_config: OAuthConfig | None = None,
    ) -> dict[str, Any]:
        """Exchange authorization code for tokens and store them.

        If oauth_config is not provided, it will be retrieved from the
        pending flow state (stored during start_flow).

        Returns {"success": True, "connector_id": ..., "tenant_id": ..., ...} or raises.
        """
        flow = _pending_flows.pop(state, None)
        if not flow:
            raise ValueError("Invalid or expired OAuth state parameter")

        # Check expiry (10 minute window)
        created = datetime.fromisoformat(flow["created_at"])
        if datetime.now(timezone.utc) - created > timedelta(minutes=10):
            raise ValueError("OAuth flow expired (>10 minutes)")

        # Use stored oauth_config if not explicitly provided
        if oauth_config is None:
            oauth_config = flow.get("oauth_config")
        if oauth_config is None:
            raise ValueError("No OAuth config available for callback")

        # Build token request
        data: dict[str, Any] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": OAUTH_CALLBACK_URL,
            **oauth_config.extra_token_params,
        }

        if oauth_config.use_pkce and "code_verifier" in flow:
            data["code_verifier"] = flow["code_verifier"]

        headers = {"Accept": "application/json"}

        if oauth_config.token_endpoint_auth == "client_secret_basic":
            import base64 as b64
            creds = b64.b64encode(
                f"{oauth_config.client_id}:{oauth_config.client_secret}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"
        else:
            # client_secret_post (most common)
            data["client_id"] = oauth_config.client_id
            data["client_secret"] = oauth_config.client_secret

        # Exchange code for tokens
        resp = await self._http.post(oauth_config.token_url, data=data, headers=headers)

        if resp.status_code != 200:
            error_detail = resp.text[:500]
            logger.error("OAuth token exchange failed for %s: %s", flow["connector_id"], error_detail)
            await self.db.update_connection_status(
                flow["tenant_id"],
                flow["connector_id"],
                "error",
                f"Token exchange failed: {resp.status_code}",
            )
            raise ValueError(f"Token exchange failed: {resp.status_code} — {error_detail}")

        token_data = resp.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        if not access_token:
            raise ValueError("No access_token in response")

        # Store tokens encrypted in DB
        await self.db.update_connection_tokens(
            flow["tenant_id"],
            flow["connector_id"],
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(expires_in) if expires_in else None,
        )

        await self.db.log_activity(
            flow["tenant_id"],
            flow["connector_id"],
            "oauth_completed",
            {"has_refresh_token": refresh_token is not None, "expires_in": expires_in},
        )

        logger.info("OAuth completed for %s tenant=%s", flow["connector_id"], flow["tenant_id"])

        return {
            "success": True,
            "connector_id": flow["connector_id"],
            "tenant_id": flow["tenant_id"],
            "redirect": flow.get("redirect_after", "/connectors"),
            "token_data": token_data,  # Pass to caller for webhook registration etc.
        }

    # ── Token Refresh ───────────────────────────────────────────────

    async def refresh_token(
        self,
        tenant_id: str,
        connector_id: str,
        oauth_config: OAuthConfig,
    ) -> str | None:
        """Refresh an expired access token. Returns new access_token or None."""
        tokens = await self.db.get_decrypted_tokens(tenant_id, connector_id)
        if not tokens or "refresh_token" not in tokens:
            logger.warning("No refresh token for %s:%s", tenant_id, connector_id)
            return None

        data: dict[str, Any] = {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            **oauth_config.extra_token_params,
        }

        headers = {"Accept": "application/json"}

        if oauth_config.token_endpoint_auth == "client_secret_basic":
            import base64 as b64
            creds = b64.b64encode(
                f"{oauth_config.client_id}:{oauth_config.client_secret}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"
        else:
            data["client_id"] = oauth_config.client_id
            data["client_secret"] = oauth_config.client_secret

        try:
            resp = await self._http.post(oauth_config.token_url, data=data, headers=headers)
            if resp.status_code != 200:
                logger.error("Token refresh failed for %s:%s — %s", tenant_id, connector_id, resp.status_code)
                await self.db.record_cursor_error(tenant_id, connector_id, f"Token refresh failed: {resp.status_code}")
                return None

            token_data = resp.json()
            new_access = token_data.get("access_token")
            new_refresh = token_data.get("refresh_token", tokens["refresh_token"])
            expires_in = token_data.get("expires_in")

            await self.db.update_connection_tokens(
                tenant_id, connector_id,
                access_token=new_access,
                refresh_token=new_refresh,
                expires_in=int(expires_in) if expires_in else None,
            )

            logger.info("Token refreshed for %s:%s", tenant_id, connector_id)
            return new_access
        except Exception as e:
            logger.error("Token refresh error for %s:%s: %s", tenant_id, connector_id, e)
            return None

    # ── Token Revocation ────────────────────────────────────────────

    async def revoke_token(
        self,
        tenant_id: str,
        connector_id: str,
        oauth_config: OAuthConfig,
    ) -> bool:
        """Revoke tokens at the provider (best-effort)."""
        if not oauth_config.revoke_url:
            return False

        tokens = await self.db.get_decrypted_tokens(tenant_id, connector_id)
        if not tokens:
            return False

        access_token = tokens.get("access_token")
        if not access_token:
            return False

        try:
            resp = await self._http.post(
                oauth_config.revoke_url,
                data={"token": access_token},
                headers={"Accept": "application/json"},
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning("Token revocation failed: %s", e)
            return False

    # ── Auto-refresh background task ────────────────────────────────

    async def refresh_expiring_tokens(self, get_oauth_config_fn: Callable[[str], OAuthConfig | None]) -> int:
        """Refresh all tokens expiring within 5 minutes.

        get_oauth_config_fn(connector_id) -> OAuthConfig or None
        Returns count of tokens refreshed.
        """
        connections = await self.db.get_connections_needing_refresh()
        refreshed = 0
        for conn in connections:
            config = get_oauth_config_fn(conn["connector_id"])
            if config:
                result = await self.refresh_token(conn["tenant_id"], conn["connector_id"], config)
                if result:
                    refreshed += 1
        return refreshed
