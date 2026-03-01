"""Workday connector — OAuth2/API-Key + Polling.

Captures HR events, worker data, and workforce analytics.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.connectors.oauth import OAuthConfig
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.workday")


class WorkdayProvider(BaseProvider):
    provider_id = "workday"
    provider_name = "Workday"
    auth_method = "oauth2"
    poll_interval_seconds = 900

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://{tenant}.workday.com/oauth2/{tenant}/authorize",
            token_url="https://{tenant}.workday.com/oauth2/{tenant}/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["wd:workers:read"],
            token_endpoint_auth="client_secret_basic",
        )

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        tenant = (config or {}).get("tenant", "")
        if not tenant or not access_token:
            return items, cursor
        base = f"https://{tenant}.workday.com/api/v1"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{base}/workers", params={"limit": 50}, headers=headers)
            if resp.status_code == 200:
                for worker in resp.json().get("data", []):
                    name = worker.get("descriptor", "Unknown")
                    text = f"Worker: {name} — {worker.get('primaryWorkEmail', '')}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"workday-worker-{worker.get('id', '')}",
                        entity_type="worker",
                        metadata={"workday_id": worker.get("id"), "name": name},
                        timestamp=worker.get("lastModified"),
                    ))
        return items, datetime.now(UTC).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", "unknown")
        items.append(self._make_memory(
            text=f"Workday event: {event}",
            source_id=f"workday-event-{payload.get('id', '')}",
            entity_type="hr_event",
            metadata=payload,
        ))
        return items
