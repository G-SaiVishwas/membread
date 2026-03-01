"""SalesLoft connector — OAuth2 + Polling.

Captures cadence steps, calls, and emails from sales engagement.
"""

import logging
from datetime import datetime, timezone

import httpx

from typing import Any

from src.connectors.oauth import OAuthConfig

from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.salesloft")

SALESLOFT_API = "https://api.salesloft.com/v2"


class SalesLoftProvider(BaseProvider):
    provider_id = "salesloft"
    provider_name = "SalesLoft"
    auth_method = "oauth2"
    poll_interval_seconds = 300

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://accounts.salesloft.com/oauth/authorize",
            token_url="https://accounts.salesloft.com/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[],
            token_endpoint_auth="client_secret_post",
        )

    async def poll(
        self,
        access_token: str | None = None,
        api_key: str | None = None,
        cursor: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[list[MemoryItem], str | None]:
        items: list[MemoryItem] = []
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Recent people
            params: dict[str, Any] = {"per_page": 50, "sort_by": "updated_at", "sort_direction": "DESC"}
            if cursor:
                params["updated_at[gt]"] = cursor
            resp = await client.get(f"{SALESLOFT_API}/people.json", params=params, headers=headers)
            if resp.status_code == 200:
                for person in resp.json().get("data", []):
                    name = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                    email = person.get("email_address", "")
                    text = f"SalesLoft Contact: {name} ({email})"
                    if person.get("title"):
                        text += f" — {person['title']}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"salesloft-person-{person['id']}",
                        entity_type="contact",
                        metadata={
                            "salesloft_id": person["id"],
                            "email": email,
                            "title": person.get("title", ""),
                            "company": person.get("account", {}).get("name", ""),
                        },
                        timestamp=person.get("updated_at"),
                    ))

            # Recent activities
            resp = await client.get(
                f"{SALESLOFT_API}/activities/calls.json",
                params={"per_page": 25, "sort_by": "updated_at", "sort_direction": "DESC"},
                headers=headers,
            )
            if resp.status_code == 200:
                for call in resp.json().get("data", []):
                    disposition = call.get("disposition", "")
                    text = f"SalesLoft Call: {disposition} — Duration: {call.get('duration', 0)}s"
                    if call.get("to"):
                        text += f" to {call['to']}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"salesloft-call-{call['id']}",
                        entity_type="call",
                        metadata={
                            "disposition": disposition,
                            "duration": call.get("duration"),
                            "sentiment": call.get("sentiment"),
                        },
                        timestamp=call.get("created_at"),
                    ))

        return items, datetime.now(timezone.utc).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", "unknown")
        items.append(self._make_memory(
            text=f"SalesLoft event: {event}",
            source_id=f"salesloft-event-{payload.get('id', '')}",
            entity_type="sales_event",
            metadata={"event": event},
        ))
        return items
