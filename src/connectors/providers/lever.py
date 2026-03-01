"""Lever connector — OAuth2 + Webhooks + Polling.

Captures candidates, opportunities, and recruiting events.
"""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any

import httpx

from src.connectors.oauth import OAuthConfig
from src.connectors.providers.base import BaseProvider, MemoryItem

logger = logging.getLogger("membread.providers.lever")

LEVER_API = "https://api.lever.co/v1"


class LeverProvider(BaseProvider):
    provider_id = "lever"
    provider_name = "Lever"
    auth_method = "oauth2"
    poll_interval_seconds = 600

    supported_webhook_events = [
        "candidateHired",
        "candidateStageChange",
        "applicationCreated",
        "interviewCreated",
        "offerCreated",
    ]

    def get_oauth_config(self, client_id: str = "", client_secret: str = "") -> OAuthConfig:
        return OAuthConfig(
            provider_id=self.provider_id,
            authorize_url="https://auth.lever.co/authorize",
            token_url="https://auth.lever.co/oauth/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=[
                "offline_access",
                "candidates:read:admin",
                "opportunities:read:admin",
                "postings:read:admin",
            ],
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
        token = access_token or api_key
        # Cursor is an offset token or timestamp
        params: dict[str, Any] = {"limit": 50}
        if cursor:
            params["offset"] = cursor
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30) as client:
            # Fetch opportunities (candidates in pipeline)
            resp = await client.get(
                f"{LEVER_API}/opportunities",
                params=params,
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for opp in data.get("data", []):
                    name = opp.get("name", "Unknown")
                    stage = opp.get("stage", "")
                    posting = opp.get("posting", "")
                    origin = opp.get("origin", "")

                    text = f"Candidate: {name}"
                    if stage:
                        text += f" — Stage: {stage}"
                    if origin:
                        text += f" (Source: {origin})"

                    _contact = opp.get("contact", "")
                    emails = opp.get("emails", [])
                    email = emails[0] if emails else ""

                    items.append(self._make_memory(
                        text=text,
                        source_id=f"lever-opp-{opp['id']}",
                        entity_type="candidate",
                        metadata={
                            "lever_id": opp["id"],
                            "name": name,
                            "email": email,
                            "stage": stage,
                            "origin": origin,
                            "posting_id": posting,
                            "owner": opp.get("owner", ""),
                        },
                        timestamp=datetime.fromtimestamp(
                            opp.get("updatedAt", 0) / 1000
                        ).isoformat() if opp.get("updatedAt") else None,
                    ))

                new_cursor = data.get("next")
            else:
                new_cursor = cursor

        return items, new_cursor

    async def register_webhook(
        self,
        access_token: str,
        webhook_url: str,
        events: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Register Lever webhook."""
        async with httpx.AsyncClient(timeout=30) as client:
            webhooks_registered: list[str] = []
            for event in (events or self.supported_webhook_events):
                resp = await client.post(
                    f"{LEVER_API}/webhooks",
                    json={
                        "url": webhook_url,
                        "event": event,
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code in (200, 201):
                    data = resp.json().get("data", {})
                    webhooks_registered.append(data.get("id", ""))

            if webhooks_registered:
                return {
                    "webhook_id": ",".join(webhooks_registered),
                    "events": events or self.supported_webhook_events,
                }
            return None

    async def unregister_webhook(self, access_token: str, webhook_id: str) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            success = True
            for wid in webhook_id.split(","):
                resp = await client.delete(
                    f"{LEVER_API}/webhooks/{wid.strip()}",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code not in (200, 204):
                    success = False
            return success

    def verify_webhook(self, headers: dict[str, Any], body: bytes, secret: str) -> bool:
        sig = headers.get("x-lever-signature", "")
        if not sig or not secret:
            return True
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    async def transform_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, Any] | None = None,
    ) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        event = payload.get("event", "unknown")
        data = payload.get("data", {})

        if "candidate" in event.lower() or "application" in event.lower():
            name = data.get("name", data.get("candidateName", "Unknown"))
            text = f"Lever {event}: {name}"
            stage = data.get("toStage", data.get("stage", ""))
            if stage:
                text += f" → {stage}"
            items.append(self._make_memory(
                text=text,
                source_id=f"lever-event-{data.get('id', data.get('opportunityId', ''))}",
                entity_type="recruiting_event",
                metadata={"event": event, "candidate_name": name, "stage": stage},
            ))
        elif "interview" in event.lower():
            items.append(self._make_memory(
                text=f"Lever {event}: Interview scheduled",
                source_id=f"lever-interview-{data.get('id', '')}",
                entity_type="interview_event",
                metadata={"event": event},
            ))
        elif "offer" in event.lower():
            items.append(self._make_memory(
                text=f"Lever {event}: Offer created",
                source_id=f"lever-offer-{data.get('id', '')}",
                entity_type="offer_event",
                metadata={"event": event},
            ))

        return items
