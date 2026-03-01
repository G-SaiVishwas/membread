"""Outreach connector — OAuth2 + Polling.

Captures sales engagement sequences, prospects, and email activity.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.connectors.oauth import OAuthConfig
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.outreach")

OUTREACH_API = "https://api.outreach.io/api/v2"


class OutreachProvider(BaseProvider):
    provider_id = "outreach"
    provider_name = "Outreach"
    auth_method = "oauth2"
    poll_interval_seconds = 300

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://api.outreach.io/oauth/authorize",
            token_url="https://api.outreach.io/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["prospects.read", "sequences.read", "mailings.read", "accounts.read"],
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
        since = cursor or (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.api+json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            # Recent prospects
            resp = await client.get(
                f"{OUTREACH_API}/prospects",
                params={
                    "filter[updatedAt]": f"{since}..inf",
                    "page[limit]": 50,
                    "sort": "-updatedAt",
                },
                headers=headers,
            )
            if resp.status_code == 200:
                for prospect in resp.json().get("data", []):
                    attrs = prospect.get("attributes", {})
                    name = f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip()
                    email = attrs.get("emails", [""])[0] if attrs.get("emails") else ""
                    company = attrs.get("company", "")
                    text = f"Prospect: {name}"
                    if email:
                        text += f" ({email})"
                    if company:
                        text += f" at {company}"
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"outreach-prospect-{prospect['id']}",
                        entity_type="prospect",
                        metadata={
                            "outreach_id": prospect["id"],
                            "email": email,
                            "company": company,
                            "title": attrs.get("title", ""),
                            "stage": attrs.get("stage", ""),
                        },
                        timestamp=attrs.get("updatedAt"),
                    ))

            # Recent sequence states
            resp = await client.get(
                f"{OUTREACH_API}/sequenceStates",
                params={"filter[updatedAt]": f"{since}..inf", "page[limit]": 50},
                headers=headers,
            )
            if resp.status_code == 200:
                for state in resp.json().get("data", []):
                    attrs = state.get("attributes", {})
                    text = (
                        f"Sequence State: {attrs.get('state', '')} — "
                        f"Step {attrs.get('activeAt', '')}"
                    )
                    items.append(self._make_memory(
                        text=text,
                        source_id=f"outreach-seqstate-{state['id']}",
                        entity_type="sequence_event",
                        metadata={
                            "state": attrs.get("state"),
                            "step_count": attrs.get("stepsFinished", 0),
                        },
                        timestamp=attrs.get("updatedAt"),
                    ))

        return items, datetime.now(UTC).isoformat()

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("type", "unknown")
        data = payload.get("data", payload)
        items.append(self._make_memory(
            text=f"Outreach event: {event}",
            source_id=f"outreach-event-{data.get('id', '')}",
            entity_type="outreach_event",
            metadata={"event": event},
        ))
        return items
