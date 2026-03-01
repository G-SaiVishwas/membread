"""Marketo connector — API-Key + Polling.

Captures leads, campaigns, and marketing activity.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.marketo")


class MarketoProvider(BaseProvider):
    provider_id = "marketo"
    provider_name = "Marketo"
    auth_method = "api_key"
    poll_interval_seconds = 600

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        munchkin_id = (config or {}).get("munchkin_id", "")
        client_id = (config or {}).get("client_id", "")
        client_secret = (config or {}).get("client_secret", "")
        if not munchkin_id:
            return items, cursor

        base = f"https://{munchkin_id}.mktorest.com"

        async with httpx.AsyncClient(timeout=30) as client:
            # Get access token via client credentials
            token_resp = await client.get(
                f"{base}/identity/oauth/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            if token_resp.status_code != 200:
                return items, cursor
            token = token_resp.json().get("access_token", "")

            headers = {"Authorization": f"Bearer {token}"}
            since = cursor or (
                datetime.now(UTC) - timedelta(hours=1)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Get recently updated leads
            resp = await client.get(
                f"{base}/rest/v1/activities/leadchanges.json",
                params={"sinceDatetime": since, "maxReturn": 50},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for activity in data.get("result", []):
                    lead_id = activity.get("leadId", "")
                    text = f"Marketo Lead Change: Lead {lead_id}"
                    attrs = activity.get("attributes", [])
                    changes = {a.get("name", ""): a.get("newValue", "") for a in attrs}
                    if changes:
                        text += " — " + ", ".join(f"{k}={v}" for k, v in list(changes.items())[:5])
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"marketo-change-{activity.get('marketoGUID', '')}",
                        entity_type="lead_change",
                        metadata={
                            "lead_id": str(lead_id),
                            "activity_type": activity.get("activityTypeId"),
                            "changes": changes,
                        },
                        timestamp=activity.get("activityDate"),
                    ))
                new_cursor = data.get("nextPageToken", cursor)
            else:
                new_cursor = cursor

        return items, new_cursor

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", payload.get("type", "unknown"))
        items.append(self._make_memory(
            text=f"Marketo event: {event}",
            source_id=f"marketo-wh-{payload.get('id', '')}",
            entity_type="marketing_event",
            metadata=payload,
        ))
        return items
